import os
import re
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session

from models import Application
from schemas import ApplicationStatusPatchRequest
from routers.applications import update_application_status

logger = logging.getLogger("placement_copilot.gmail_tracker")

# File path for persisting sync state (last_synced_history_id, last_synced_timestamp)
SYNC_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gmail_sync_state.json")
CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "credentials.json")
TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "token.json")

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


# ==============================================================================
# 1. Deterministic Email Classifier
# ==============================================================================

# Keywords and Regex patterns for classification (order matters for priority)
CLASSIFICATION_PATTERNS: List[Tuple[str, str, List[str]]] = [
    # (Category Name, Status Enum, Patterns/Keywords)
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
    """
    Classifies an incoming email into one of:
    - ("offer", "OFFER")
    - ("regret", "REJECTED")
    - ("interview", "INTERVIEW")
    - ("assessment", "OA_INVITE")
    - ("application received", "APPLIED")
    Returns (category, status_enum) or None if unclassified.
    Uses pure deterministic keyword and regex matching per system design rules.
    """
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

def extract_domain(sender_email: str) -> str:
    """Extract clean domain from email address string e.g. 'hr@razorpay.com' -> 'razorpay.com'."""
    if "<" in sender_email and ">" in sender_email:
        sender_email = sender_email.split("<")[1].split(">")[0]
    sender_email = sender_email.strip().lower()
    if "@" in sender_email:
        return sender_email.split("@")[1]
    return ""


def match_email_to_application(
    db: Session, sender: str, subject: str, body: str
) -> Optional[Application]:
    """
    Fuzzy match an email against existing applications in the database.
    Checks:
    1. Direct match on company name (case-insensitive) in sender email, domain, subject, or body.
    2. Normalized word overlap between company name and sender/subject text.

    Returns the matching Application object if confident, or None if no confident match.
    Does NOT create new application rows if unmatched.
    """
    applications = db.query(Application).all()
    if not applications:
        return None

    sender_domain = extract_domain(sender)
    full_text = f"{sender} {sender_domain} {subject} {body}".lower()

    best_app = None
    best_score = 0.0

    for app in applications:
        company_clean = app.company.lower().strip()
        # Remove common business suffixes for matching
        company_base = re.sub(r"\b(inc|llc|ltd|pvt|solutions|tech|technologies|suite|labs)\b", "", company_clean).strip()
        if not company_base:
            company_base = company_clean

        score = 0.0

        # Exact company name in subject or sender
        if company_clean in sender.lower() or company_clean in subject.lower():
            score += 1.0
        elif company_base and (company_base in sender.lower() or company_base in subject.lower()):
            score += 0.85
        elif company_base and company_base in sender_domain:
            score += 0.8
        elif company_base and company_base in full_text:
            score += 0.6

        # Check role match boost if company matched
        if score > 0 and app.role.lower() in full_text:
            score += 0.2

        if score > best_score:
            best_score = score
            best_app = app

    # Confidence threshold for a match
    if best_score >= 0.6:
        logger.info(f"Matched email from '{sender}' to Application ID {best_app.id} ({best_app.company}) with score {best_score}")
        return best_app

    logger.warning(f"No confident application match found for email from '{sender}' (best score: {best_score})")
    return None


# ==============================================================================
# 3. Sync State Persistence
# ==============================================================================

def load_sync_state() -> Dict[str, Any]:
    """Load sync state (last_synced_history_id, last_synced_timestamp, etc.) from disk."""
    if os.path.exists(SYNC_STATE_FILE):
        try:
            with open(SYNC_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading sync state file: {e}")
    return {
        "last_synced_history_id": None,
        "last_synced_timestamp": None,
        "total_messages_processed": 0,
        "last_sync_at": None,
    }


def save_sync_state(state: Dict[str, Any]) -> None:
    """Save updated sync state to disk."""
    try:
        state["last_sync_at"] = datetime.now(timezone.utc).isoformat()
        with open(SYNC_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving sync state file: {e}")


# ==============================================================================
# 4. Gmail API OAuth Client & Fetcher
# ==============================================================================

def get_gmail_service():
    """
    Initialize Gmail API service using google-auth-oauthlib.
    Requires credentials.json and token.json.
    Returns Google API resource object or None if OAuth credentials are not configured.
    """
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
    """
    Fetch new Gmail messages since start_history_id or last 20 messages.
    Returns list of parsed message dictionaries: [{ 'id': ..., 'sender': ..., 'subject': ..., 'body': ..., 'history_id': ... }].
    """
    if not service:
        return []

    messages = []
    try:
        if start_history_id:
            res = service.users().history().list(userId="me", startHistoryId=start_history_id, historyTypes=["messageAdded"]).execute()
            histories = res.get("history", [])
            msg_ids = set()
            for h in histories:
                for m_added in h.get("messagesAdded", []):
                    msg_ids.add(m_added["message"]["id"])
        else:
            res = service.users().messages().list(userId="me", maxResults=20).execute()
            msg_ids = [m["id"] for m in res.get("messages", [])]

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

            # Extract text body snippet or body
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
# 5. Core Sync Pipeline Executor
# ==============================================================================

async def sync_gmail_tracker(
    db: Session, mock_messages: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Main Gmail Tracker sync runner:
    1. Loads sync state.
    2. Fetches messages from live Gmail API OR mock_messages (if passed for testing/demo).
    3. For each message:
       - Checks historyId/timestamp to avoid re-processing.
       - Classifies email into status category.
       - Matches email to application in DB.
       - If matched, calls update_application_status(status_source="gmail_auto").
       - Fires gap report if status becomes REJECTED or GHOSTED.
    4. Updates sync state and returns sync execution summary.
    """
    state = load_sync_state()
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
            logger.info(f"Skipping classified email '{subject}' - no matching application row.")
            continue

        # Invoke status update endpoint logic with status_source='gmail_auto'
        patch_payload = ApplicationStatusPatchRequest(status=status_enum, status_source="gmail_auto")
        updated_app = await update_application_status(app.id, patch_payload, db)

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

    # Update state
    state["last_synced_history_id"] = max_history_id or state.get("last_synced_history_id")
    state["last_synced_timestamp"] = datetime.now(timezone.utc).isoformat()
    state["total_messages_processed"] = state.get("total_messages_processed", 0) + len(messages_to_process)
    save_sync_state(state)

    return {
        "status": "success",
        "messages_received": len(messages_to_process),
        "messages_classified_and_matched": matched_count,
        "updated_applications": updated_applications,
        "sync_state": state,
    }
