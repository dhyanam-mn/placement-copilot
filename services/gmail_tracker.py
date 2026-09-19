import os
import re
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session

from models import Application
from schemas import ApplicationStatusPatchRequest
from routers.applications import update_application_status

logger = logging.getLogger("placement_copilot.gmail_tracker")

CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "credentials.json")
TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "token.json")

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

ATS_DOMAINS = {
    "greenhouse.io", "boards.greenhouse.io", "lever.co", "api.lever.co",
    "ashbyhq.com", "workday.com", "myworkday.com", "workday-online.com",
    "smartrecruiters.com", "jobvite.com", "bamboohr.com", "icims.com"
}


# ==============================================================================
# 1. Deterministic Email Classifier
# ==============================================================================

CLASSIFICATION_PATTERNS: List[Tuple[str, str, List[str]]] = [
    (
        "offer",
        "OFFER",
        [
            r"offer letter",
            r"pleased to offer",
            r"extending an offer",
            r"job offer from",
            r"offer of employment",
            r"congratulations.*offer",
        ],
    ),
    (
        "regret",
        "REJECTED",
        [
            r"unfortunately",
            r"regret to inform",
            r"decided to move forward with other",
            r"pursuing other candidates",
            r"not moving forward",
            r"will not be moving forward",
            r"not selected for this role",
            r"position has been filled",
            r"status of your application.*rejected",
        ],
    ),
    (
        "interview",
        "INTERVIEW",
        [
            r"interview invitation",
            r"schedule an interview",
            r"invite you for an interview",
            r"interview request",
            r"next round of interviews",
            r"technical interview",
            r"behavioral interview",
            r"screening call",
            r"schedule a 30-minute call",
            r"invitation to interview",
        ],
    ),
    (
        "assessment",
        "OA_INVITE",
        [
            r"online assessment",
            r"coding test",
            r"assessment invite",
            r"take the assessment",
            r"hackerrank",
            r"codesignal",
            r"codility",
            r"test invitation",
            r"oa invitation",
            r"technical assessment",
            r"complete the online test",
        ],
    ),
    (
        "application received",
        "APPLIED",
        [
            r"thank you for applying",
            r"thanks for applying",
            r"application received",
            r"received your application",
            r"application submitted",
            r"successfully applied",
            r"we have received your application",
        ],
    ),
]


def classify_email(subject: str, body: str) -> Optional[Tuple[str, str]]:
    text = f"{subject}\n{body}".lower()

    for category, status_enum, patterns in CLASSIFICATION_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                logger.info(f"Classified email as '{category}' ({status_enum}) via pattern '{pattern}'")
                return category, status_enum

    return None


# ==============================================================================
# 2. Company & Application Matching Logic
# ==============================================================================

def extract_sender_email_and_name(sender_str: str) -> Tuple[str, str]:
    """Extract email address and display name from sender string."""
    if not sender_str:
        return ("", "")
    sender_str = sender_str.strip()
    match = re.search(r"^(.*?)\s*<([^>]+)>$", sender_str)
    if match:
        name = match.group(1).strip().strip('"').strip("'")
        email = match.group(2).strip().lower()
        return (email, name)
    if "@" in sender_str:
        return (sender_str.lower(), "")
    return (sender_str.lower(), "")


def extract_domain(sender_email: str) -> str:
    """Extract clean domain from email address string e.g. 'hr@razorpay.com' -> 'razorpay.com'."""
    email, _ = extract_sender_email_and_name(sender_email)
    if "@" in email:
        return email.split("@")[1].strip().lower()
    return email.strip().lower()


def extract_second_level_label(domain: str) -> str:
    """Extract the second-level label (SLD / main brand name) from a domain."""
    if not domain:
        return ""
    parts = domain.lower().split(".")
    tlds = {"com", "co", "in", "io", "org", "net", "ai", "dev", "app", "tech", "careers", "gov", "edu", "uk", "us", "ca"}
    non_tld_parts = [p for p in parts if p not in tlds]
    if non_tld_parts:
        return non_tld_parts[-1]
    return parts[0] if parts else ""


def normalize_company_name(company: str) -> str:
    """
    Clean and normalize company name for robust matching.
    Lowercases, strips punctuation, and removes common corporate suffixes.
    """
    if not company:
        return ""
    cleaned = company.lower()
    cleaned = re.sub(r'[^\w\s]', '', cleaned)
    words = [
        w for w in cleaned.split()
        if w not in {
            "pvt", "ltd", "limited", "technologies", "technology", "tech",
            "inc", "llc", "corp", "corporation", "solutions", "labs",
            "suite", "group", "services", "software", "private"
        }
    ]
    return " ".join(words) if words else cleaned.strip()


def match_email_to_application(
    db: Session, sender: str, subject: str, body: str
) -> Optional[Application]:
    """
    Fuzzy match an email against existing applications in the database.
    1. Extracts registrable domain and second-level label (SLD).
    2. Compares SLD label and normalized company name.
    3. Handles ATS senders (greenhouse.io, lever.co, ashbyhq.com, workday) by matching display name, subject, or body.
    4. Logs unmatched emails with exact reason.
    """
    applications = db.query(Application).all()
    if not applications:
        logger.warning(f"Unmatched email from '{sender}' (subject: '{subject}'): Reason - Applications table is empty")
        return None

    email, display_name = extract_sender_email_and_name(sender)
    domain = extract_domain(email)
    sld_label = extract_second_level_label(domain)

    is_ats = any(domain.endswith(ats_dom) for ats_dom in ATS_DOMAINS)

    display_name_norm = normalize_company_name(display_name)
    subject_norm = normalize_company_name(subject)
    full_text_lower = f"{display_name} {subject} {body}".lower()

    best_app = None
    best_score = 0.0

    for app in applications:
        comp_norm = normalize_company_name(app.company)
        comp_raw_lower = app.company.lower().strip()
        if not comp_norm:
            comp_norm = comp_raw_lower

        score = 0.0

        if is_ats:
            # ATS Senders: Match company in display name, subject, or body
            if comp_norm and (re.search(r'\b' + re.escape(comp_norm) + r'\b', display_name_norm) or re.search(r'\b' + re.escape(comp_raw_lower) + r'\b', display_name.lower())):
                score += 0.90
            elif comp_norm and (re.search(r'\b' + re.escape(comp_norm) + r'\b', subject_norm) or re.search(r'\b' + re.escape(comp_raw_lower) + r'\b', subject.lower())):
                score += 0.85
            elif comp_norm and re.search(r'\b' + re.escape(comp_norm) + r'\b', full_text_lower):
                score += 0.70
        else:
            # Non-ATS Senders: Match SLD label against normalized company name
            if comp_norm and sld_label and (comp_norm == sld_label or comp_norm in sld_label or sld_label in comp_norm):
                score += 0.90
            elif comp_norm and (re.search(r'\b' + re.escape(comp_norm) + r'\b', display_name_norm) or re.search(r'\b' + re.escape(comp_raw_lower) + r'\b', display_name.lower())):
                score += 0.85
            elif comp_norm and (re.search(r'\b' + re.escape(comp_norm) + r'\b', subject_norm) or re.search(r'\b' + re.escape(comp_raw_lower) + r'\b', subject.lower())):
                score += 0.80
            elif comp_norm and re.search(r'\b' + re.escape(comp_norm) + r'\b', full_text_lower):
                score += 0.60

        # Role match boost
        if score > 0 and app.role and app.role.lower() in full_text_lower:
            score += 0.10

        if score > best_score:
            best_score = score
            best_app = app

    if best_score >= 0.60:
        logger.info(f"Matched email from '{sender}' to Application ID {best_app.id} ({best_app.company}) with score {best_score:.2f}")
        return best_app

    reason = f"No matching application found for domain label '{sld_label}' or ATS display name/subject (best score: {best_score:.2f})"
    logger.warning(f"Unmatched email from '{sender}' (subject: '{subject}'): Reason - {reason}")
    return None


# ==============================================================================
# 3. Nudges & Auto-Ghost Sweeper
# ==============================================================================

def get_stale_application_nudges(db: Session, threshold_days: Optional[int] = None) -> Dict[str, Any]:
    """Returns open applications stale past threshold_days (below ghost_days)."""
    from services.settings_service import get_nudge_days, get_ghost_days
    if threshold_days is None:
        threshold_days = get_nudge_days(db)
    ghost_days = get_ghost_days(db)

    now = datetime.now(timezone.utc)
    open_statuses = ("DISCOVERED", "READY_TO_APPLY", "APPLIED", "OA_INVITE", "INTERVIEW")

    open_apps = (
        db.query(Application)
        .filter(Application.status.in_(open_statuses))
        .order_by(Application.last_contact_date.asc())
        .all()
    )

    nudges = []
    for app in open_apps:
        if app.last_contact_date:
            app_contact = app.last_contact_date
            if app_contact.tzinfo is None:
                app_contact = app_contact.replace(tzinfo=timezone.utc)
            days_inactive = (now - app_contact).days
        else:
            days_inactive = 0

        if threshold_days <= days_inactive < ghost_days:
            nudges.append({
                "id": app.id,
                "company": app.company,
                "role": app.role,
                "status": app.status,
                "status_source": app.status_source,
                "match_score": app.match_score,
                "last_contact_date": app.last_contact_date.isoformat(),
                "days_inactive": days_inactive,
                "nudge_message": f"Application for '{app.company}' ({app.role}) has had no response for {days_inactive} days. Consider following up with the recruiter.",
            })

    return {
        "threshold_days": threshold_days,
        "ghost_days": ghost_days,
        "total_nudges": len(nudges),
        "nudges": nudges,
    }


async def run_auto_ghost_sweep(db: Session) -> Dict[str, Any]:
    """
    Staleness sweep for applications >= ghost_days old:
    Transitions status to GHOSTED with status_source='auto_ghost'.
    MUST NOT modify last_contact_date, only last_updated.
    Triggers per-row gap report and Notification record.
    """
    from services.settings_service import get_ghost_days
    ghost_days = get_ghost_days(db)

    now = datetime.now(timezone.utc)
    open_statuses = ("DISCOVERED", "READY_TO_APPLY", "APPLIED", "OA_INVITE", "INTERVIEW")

    stale_apps = (
        db.query(Application)
        .filter(Application.status.in_(open_statuses))
        .all()
    )

    ghosted_count = 0
    updated_items = []

    for app in stale_apps:
        if app.last_contact_date:
            app_contact = app.last_contact_date
            if app_contact.tzinfo is None:
                app_contact = app_contact.replace(tzinfo=timezone.utc)
            days_inactive = (now - app_contact).days
        else:
            days_inactive = 0

        if days_inactive >= ghost_days:
            from services.status_service import set_status
            updated_app = await set_status(db, app.id, "GHOSTED", source="auto_ghost")

            ghosted_count += 1
            updated_items.append({
                "id": updated_app.id,
                "company": updated_app.company,
                "role": updated_app.role,
                "status": updated_app.status,
                "status_source": updated_app.status_source,
                "days_inactive": days_inactive,
                "last_contact_date": updated_app.last_contact_date.isoformat(),
            })

    return {
        "status": "success",
        "total_stale_checked": len(stale_apps),
        "total_ghosted": ghosted_count,
        "ghosted_applications": updated_items,
    }


# ==============================================================================
# 4. Sync State Persistence
# ==============================================================================

def load_sync_state(db: Session = None) -> Dict[str, Any]:
    from models import GmailSyncState
    from database import SessionLocal
    
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
        
    try:
        record = db.query(GmailSyncState).first()
        if record:
            return {
                "last_synced_history_id": record.last_synced_history_id,
                "last_synced_timestamp": record.last_synced_timestamp.isoformat() if record.last_synced_timestamp else None,
                "total_messages_processed": record.total_messages_processed,
                "last_sync_at": record.updated_at.isoformat() if record.updated_at else None,
            }
    except Exception as e:
        logger.error(f"Error reading sync state from DB: {e}")
    finally:
        if close_db:
            db.close()
            
    return {
        "last_synced_history_id": None,
        "last_synced_timestamp": None,
        "total_messages_processed": 0,
        "last_sync_at": None,
    }


def save_sync_state(state: Dict[str, Any], db: Session = None) -> None:
    from models import GmailSyncState
    from database import SessionLocal
    from dateutil import parser
    
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
        
    try:
        record = db.query(GmailSyncState).first()
        if not record:
            record = GmailSyncState()
            db.add(record)
            
        record.last_synced_history_id = state.get("last_synced_history_id")
        timestamp_str = state.get("last_synced_timestamp")
        if timestamp_str:
            record.last_synced_timestamp = parser.isoparse(timestamp_str) if isinstance(timestamp_str, str) else timestamp_str
        record.total_messages_processed = state.get("total_messages_processed", 0)
        
        db.commit()
    except Exception as e:
        logger.error(f"Error saving sync state to DB: {e}")
        db.rollback()
    finally:
        if close_db:
            db.close()


# ==============================================================================
# 5. Gmail API OAuth Client & Fetcher
# ==============================================================================

def get_gmail_service():
    if not os.path.exists(CREDENTIALS_FILE) and not os.path.exists(TOKEN_FILE):
        logger.warning("Gmail OAuth credentials.json/token.json not found. Live API sync disabled.")
        return None

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        creds = None
        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, GMAIL_SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            elif os.path.exists(CREDENTIALS_FILE):
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, GMAIL_SCOPES)
                creds = flow.run_local_server(port=0)
                with open(TOKEN_FILE, "w") as token:
                    token.write(creds.to_json())

        if creds and creds.valid:
            return build("gmail", "v1", credentials=creds)
    except Exception as e:
        logger.error(f"Failed to initialize Gmail API service: {e}")

    return None


def fetch_gmail_messages(service, start_history_id: Optional[str] = None) -> List[Dict[str, Any]]:
    if not service:
        return []

    messages = []
    msg_ids = set()
    try:
        if start_history_id:
            try:
                res = service.users().history().list(userId="me", startHistoryId=start_history_id, historyTypes=["messageAdded"]).execute()
                histories = res.get("history", [])
                for h in histories:
                    for m_added in h.get("messagesAdded", []):
                        msg_ids.add(m_added["message"]["id"])
            except Exception as hist_err:
                logger.warning(f"History list failed ({hist_err}), falling back to recent messages.list")
                res = service.users().messages().list(userId="me", maxResults=20).execute()
                msg_ids = {m["id"] for m in res.get("messages", [])}
        else:
            res = service.users().messages().list(userId="me", maxResults=20).execute()
            msg_ids = {m["id"] for m in res.get("messages", [])}

        for m_id in msg_ids:
            msg_data = service.users().messages().get(userId="me", id=m_id, format="full").execute()
            history_id = msg_data.get("historyId")
            headers = msg_data.get("payload", {}).get("headers", [])

            sender = ""
            subject = ""
            for h in headers:
                name_lower = h.get("name", "").lower()
                if name_lower == "from":
                    sender = h.get("value", "")
                elif name_lower == "subject":
                    subject = h.get("value", "")

            snippet = msg_data.get("snippet", "")

            messages.append({
                "id": m_id,
                "history_id": history_id,
                "sender": sender,
                "subject": subject,
                "body": snippet,
            })
    except Exception as e:
        logger.error(f"Error fetching messages from Gmail API: {e}")

    return messages


# ==============================================================================
# 6. Core Sync Pipeline Executor
# ==============================================================================

async def sync_gmail_tracker(
    db: Session, mock_messages: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    state = load_sync_state(db)
    messages_to_process = []

    if mock_messages is not None:
        messages_to_process = mock_messages
    else:
        service = get_gmail_service()
        if service:
            messages_to_process = fetch_gmail_messages(service, state.get("last_synced_history_id"))
        else:
            logger.info("Gmail service unavailable and no mock_messages provided. Zero messages synced.")

    synced_count = 0
    matched_count = 0
    updated_applications = []
    max_history_id = state.get("last_synced_history_id")

    for msg in messages_to_process:
        sender = msg.get("sender", "")
        subject = msg.get("subject", "")
        body = msg.get("body", "")
        history_id = str(msg.get("history_id") or msg.get("id") or "")

        classification = classify_email(subject, body)
        if not classification:
            logger.info(f"Skipping unclassified email: '{subject}'")
            continue

        category, status_enum = classification

        app = match_email_to_application(db, sender, subject, body)
        if not app:
            continue

        from services.status_service import set_status
        updated_app = await set_status(db, app.id, status_enum, source="gmail_auto")

        synced_count += 1
        matched_count += 1
        updated_applications.append({
            "application_id": updated_app.id,
            "company": updated_app.company,
            "old_status": app.status,
            "new_status": updated_app.status,
            "category": category,
            "last_contact_date": updated_app.last_contact_date.isoformat(),
            "gap_report_triggered": updated_app.gap_report_id is not None,
        })

        if history_id and (not max_history_id or history_id > str(max_history_id)):
            max_history_id = history_id

    state["last_synced_history_id"] = max_history_id or state.get("last_synced_history_id")
    state["last_synced_timestamp"] = datetime.now(timezone.utc).isoformat()
    state["total_messages_processed"] = state.get("total_messages_processed", 0) + len(messages_to_process)
    save_sync_state(state, db)

    return {
        "status": "success",
        "messages_received": len(messages_to_process),
        "messages_classified_and_matched": matched_count,
        "updated_applications": updated_applications,
        "sync_state": state,
    }
