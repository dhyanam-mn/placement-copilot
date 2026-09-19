import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session

logger = logging.getLogger("placement_copilot.scam_check")

REQUIRED_CATEGORIES = {
    "public_domain": [
        ("gmail.com", 0.35), ("yahoo.com", 0.35), ("hotmail.com", 0.35),
        ("outlook.com", 0.35), ("icloud.com", 0.35), ("aol.com", 0.35)
    ],
    "lookalike": [
        ("-careers", 0.5), ("-hr", 0.5), ("-jobs", 0.5),
        ("-recruitment", 0.5), ("-hiring", 0.5), ("-portal", 0.5),
        ("-verify", 0.5), ("jobs-", 0.5), ("careers-", 0.5)
    ],
    "payment_demand": [
        ("registration fee", 0.5), ("processing fee", 0.5), ("security deposit", 0.5),
        ("refundable fee", 0.5), ("upfront payment", 0.5), ("pay fee", 0.5), ("payment demanded", 0.5)
    ],
    "urgency": [
        ("urgent", 0.25), ("immediately", 0.25), ("within 24 hours", 0.25),
        ("act fast", 0.25), ("quick action required", 0.25)
    ],
    "unofficial_channel": [
        ("whatsapp", 0.25), ("telegram", 0.25), ("google chat", 0.25), ("signal", 0.25)
    ]
}

def extract_domain(email: str) -> str:
    """Extract and normalize domain part from an email string."""
    if not email:
        return ""
    if "@" in email:
        return email.split("@")[-1].lower().strip()
    return email.lower().strip()

def normalize_company_name(company: str) -> str:
    """Clean company name for fuzzy key matching."""
    if not company:
        return ""
    cleaned = company.lower()
    cleaned = re.sub(r'[^a-z0-9\s]', '', cleaned)
    words = [
        w for w in cleaned.split()
        if w not in {"inc", "llc", "corp", "corporation", "ltd", "limited", "solutions", "technologies", "tech", "group", "pvt"}
    ]
    return "".join(words) if words else cleaned.replace(" ", "")


def load_scam_patterns(db: Optional[Session] = None) -> Dict[str, List[Tuple[str, float]]]:
    """
    Loads ALL phrase categories strictly from scam_patterns DB table.
    Seeds any missing required categories/patterns with source_note='TODO'.
    Fails loudly if any required category cannot be loaded.
    """
    from models import ScamPattern
    from database import SessionLocal

    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        all_patterns = db.query(ScamPattern).all()
        existing_patterns = {(p.category, p.pattern.lower().strip()) for p in all_patterns}

        seeded_any = False
        for cat, default_items in REQUIRED_CATEGORIES.items():
            for pattern_text, weight in default_items:
                if (cat, pattern_text.lower().strip()) not in existing_patterns:
                    db.add(ScamPattern(category=cat, pattern=pattern_text, weight=weight, source_note="TODO"))
                    seeded_any = True

        if seeded_any:
            db.commit()
            all_patterns = db.query(ScamPattern).all()

        patterns_by_cat: Dict[str, List[Tuple[str, float]]] = {}
        for p in all_patterns:
            patterns_by_cat.setdefault(p.category, []).append((p.pattern.lower().strip(), float(p.weight)))

        # Fail loudly if any required category is missing
        for cat in REQUIRED_CATEGORIES:
            if cat not in patterns_by_cat or not patterns_by_cat[cat]:
                raise RuntimeError(f"Required scam_patterns category '{cat}' is missing in database!")

        return patterns_by_cat
    finally:
        if close_db:
            db.close()


def check_scam(
    sender_email: Optional[str] = None,
    claimed_company: Optional[str] = None,
    message_text: Optional[str] = None,
    input_data: Optional[Dict[str, str]] = None,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Deterministic Scam Check Rule Engine reading patterns strictly from DB scam_patterns table.
    """
    if input_data and isinstance(input_data, dict):
        sender_email = sender_email or input_data.get("sender_email", "")
        claimed_company = claimed_company or input_data.get("claimed_company", "")
        message_text = message_text or input_data.get("message_text", "")

    sender_email = (sender_email or "").strip()
    claimed_company = (claimed_company or "").strip()
    message_text = (message_text or "").strip()

    flagged_reasons: List[str] = []
    risk_score = 0.0

    domain = extract_domain(sender_email)
    company_key = normalize_company_name(claimed_company)
    text_lower = message_text.lower() if message_text else ""

    scam_patterns = load_scam_patterns(db)

    public_domains = {p[0] for p in scam_patterns.get("public_domain", [])}
    lookalikes = scam_patterns.get("lookalike", [])
    payment_phrases = scam_patterns.get("payment_demand", [])
    urgency_phrases = scam_patterns.get("urgency", [])
    unofficial_phrases = scam_patterns.get("unofficial_channel", [])

    # 1. Check for Public Domain Usage for Corporate Roles
    if domain and domain in public_domains and company_key:
        if company_key not in domain:
            risk_score += 0.35
            flagged_reasons.append(f"uses public email domain ({domain}) for corporate outreach")

    # 2. Check for Lookalike / Fake HR Domains
    if domain and company_key and domain not in public_domains:
        core_domain = domain.split(".")[0].replace("-", "")
        if company_key != core_domain:
            risk_score += 0.4
            flagged_reasons.append(f"sender domain '{domain}' does not match claimed company '{claimed_company}'")
        for indicator, w in lookalikes:
            if indicator in domain:
                risk_score += w
                flagged_reasons.append(f"domain uses suspicious '{indicator}' suffix common in recruitment fraud")
                break

    # 3. Check for Payment Demands / Upfront Fees
    for phrase, w in payment_phrases:
        if phrase in text_lower:
            risk_score += w
            flagged_reasons.append(f"message contains payment/fee demand phrase(s): '{phrase}'")
            break

    # 4. Check for False Urgency / Pressure
    for phrase, w in urgency_phrases:
        if phrase in text_lower:
            risk_score += w
            flagged_reasons.append(f"message contains high-urgency/pressure phrase(s): '{phrase}'")
            break

    # 5. Check for Unofficial / Suspicious Comms Channels
    for phrase, w in unofficial_phrases:
        if phrase in text_lower:
            risk_score += w
            flagged_reasons.append(f"message requests communication over unofficial channel: '{phrase}'")
            break

    final_risk_score = min(1.0, round(risk_score, 2))

    return {
        "risk_score": final_risk_score,
        "flagged_reasons": flagged_reasons,
        "explanation_text": None
    }


async def generate_scam_explanation_background(scam_check_id: int) -> None:
    """Asynchronous background worker post-insert to populate LLM scam explanation."""
    from database import SessionLocal
    from models import ScamCheck
    from services.model_service_client import call_llm_generate, ModelServiceUnavailableError

    db = SessionLocal()
    try:
        scam_record = db.query(ScamCheck).filter(ScamCheck.id == scam_check_id).first()
        if not scam_record or scam_record.explanation_text is not None:
            return

        context = {
            "flagged_reasons": scam_record.flagged_reasons,
            "recruiter_info": {
                "name": scam_record.recruiter_name,
                "email_domain": scam_record.recruiter_domain,
            },
        }
        try:
            llm_resp = await call_llm_generate("scam_explanation", context=context)
            scam_record.explanation_text = llm_resp.get("generated_text")
        except (ModelServiceUnavailableError, Exception):
            reasons_summary = ", ".join(scam_record.flagged_reasons) if isinstance(scam_record.flagged_reasons, list) else str(scam_record.flagged_reasons)
            scam_record.explanation_text = f"High risk job posting: {reasons_summary}."

        db.commit()
    except Exception as e:
        logger.error(f"Background scam explanation failed for ID {scam_check_id}: {e}")
    finally:
        db.close()
