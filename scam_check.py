import re
from typing import Dict, List, Any, Optional

# Known legitimate company domain mapping
KNOWN_COMPANY_DOMAINS = {
    "google": ["google.com", "alphabet.com"],
    "razorpay": ["razorpay.com"],
    "microsoft": ["microsoft.com"],
    "amazon": ["amazon.com", "amazon.in"],
    "swiggy": ["swiggy.in", "swiggy.com"],
    "flipkart": ["flipkart.com"],
    "technova": ["technova.com", "technovasolutions.com"],
}

# Public email services commonly misused for fake corporate outreach
PUBLIC_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "aol.com"
}

# Curated red-flag phrases grouped by scam indicator categories
RED_FLAG_PHRASES = {
    "payment_demands": [
        "processing fee",
        "registration fee",
        "pay before interview",
        "security deposit",
        "wire transfer",
        "bank details",
        "gift card",
        "refundable fee",
        "training fee",
        "laptop deposit",
        "pay upfront",
    ],
    "urgency_pressure": [
        "respond within 24 hours",
        "lose the offer",
        "urgent",
        "immediate response required",
        "offer expires",
        "limited seats",
        "act fast",
    ],
    "unofficial_channels": [
        "telegram",
        "whatsapp group",
        "crypto",
        "bitcoin",
    ]
}

# Lookalike keywords appended to fake hiring domains
LOOKALIKE_INDICATORS = [
    "-careers", "-hr", "-jobs", "-recruitment", "-hiring", "-portal", "-verify", "jobs-", "careers-"
]

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

def check_scam(
    sender_email: Optional[str] = None,
    claimed_company: Optional[str] = None,
    message_text: Optional[str] = None,
    input_data: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Deterministic Scam Check Rule Engine.
    
    Accepts either individual arguments or a dictionary payload:
    { "sender_email": "...", "claimed_company": "...", "message_text": "..." }

    Returns:
    {
        "risk_score": float (0.0 - 1.0),
        "flagged_reasons": list of strings,
        "explanation_text": None
    }
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
    norm_company = normalize_company_name(claimed_company)

    # 1. Public Email Domain Check
    if domain in PUBLIC_EMAIL_DOMAINS:
        flagged_reasons.append(
            f"sender email uses a public email domain ({domain}) for corporate hiring outreach"
        )
        risk_score += 0.35

    # 2. Domain Match & Lookalike Check
    elif domain and claimed_company:
        matched_known_domains = None
        for known_key, valid_domains in KNOWN_COMPANY_DOMAINS.items():
            if known_key in norm_company or norm_company in known_key:
                matched_known_domains = valid_domains
                break

        if matched_known_domains:
            if domain not in matched_known_domains:
                is_lookalike = any(ind in domain for ind in LOOKALIKE_INDICATORS)
                if is_lookalike:
                    flagged_reasons.append(
                        f"sender domain '{domain}' appears to be a lookalike domain for claimed company '{claimed_company}'"
                    )
                    risk_score += 0.5
                else:
                    flagged_reasons.append(
                        f"sender domain '{domain}' does not match official domain for claimed company '{claimed_company}'"
                    )
                    risk_score += 0.4
        else:
            domain_parts = domain.split(".")
            root_domain = domain_parts[0] if domain_parts else domain
            
            is_lookalike = any(ind in domain for ind in LOOKALIKE_INDICATORS)
            if is_lookalike and norm_company in root_domain:
                flagged_reasons.append(
                    f"sender domain '{domain}' appears to be a lookalike domain for claimed company '{claimed_company}'"
                )
                risk_score += 0.5
            elif norm_company and norm_company not in root_domain and root_domain not in norm_company:
                flagged_reasons.append(
                    f"sender domain '{domain}' does not match claimed company '{claimed_company}'"
                )
                risk_score += 0.35

    # 3. Red-Flag Phrases Check
    if message_text:
        msg_lower = message_text.lower()
        
        # Payment demand phrases
        matched_payments = [p for p in RED_FLAG_PHRASES["payment_demands"] if p in msg_lower]
        if matched_payments:
            phrases_str = ", ".join(f"'{p}'" for p in matched_payments)
            flagged_reasons.append(f"message contains payment/fee demand phrase(s): {phrases_str}")
            risk_score += min(0.5, 0.3 * len(matched_payments))

        # Urgency & pressure phrases
        matched_urgency = [p for p in RED_FLAG_PHRASES["urgency_pressure"] if p in msg_lower]
        if matched_urgency:
            phrases_str = ", ".join(f"'{p}'" for p in matched_urgency)
            flagged_reasons.append(f"message contains high-urgency/pressure phrase(s): {phrases_str}")
            risk_score += 0.25

        # Unofficial contact channel phrases
        matched_channels = [p for p in RED_FLAG_PHRASES["unofficial_channels"] if p in msg_lower]
        if matched_channels:
            phrases_str = ", ".join(f"'{p}'" for p in matched_channels)
            flagged_reasons.append(f"message requests communication over unofficial channel: {phrases_str}")
            risk_score += 0.3

    final_risk_score = min(1.0, round(risk_score, 2))

    return {
        "risk_score": final_risk_score,
        "flagged_reasons": flagged_reasons,
        "explanation_text": None
    }

if __name__ == "__main__":
    sample_input = {
        "sender_email": "hr@technova-careers.in",
        "claimed_company": "TechNova Solutions",
        "message_text": "Urgent: You must pay a registration fee of $50 within 24 hours to secure your interview slot on Telegram."
    }
    print("Scam Check Result:")
    import json
    print(json.dumps(check_scam(input_data=sample_input), indent=2))
