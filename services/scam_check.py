from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from models import Application, ScamCheck
from services.model_service_client import call_llm_generate, ModelServiceUnavailableError
from scam_check import check_scam

def _run_rule_layer(
    recruiter_name: Optional[str],
    recruiter_domain: Optional[str],
    claimed_company: Optional[str],
    message_text: Optional[str] = None
) -> tuple:
    """
    Deterministic rule layer for fraud screening.
    Delegates to standalone scam_check module.
    """
    sender_email = f"recruiter@{recruiter_domain}" if recruiter_domain and "@" not in recruiter_domain else (recruiter_domain or "")
    res = check_scam(
        sender_email=sender_email,
        claimed_company=claimed_company or "",
        message_text=message_text or ""
    )
    return res["risk_score"], res["flagged_reasons"]

async def run_scam_check(
    db: Session,
    application: Application,
    recruiter_name: Optional[str],
    recruiter_domain: Optional[str],
    claimed_company: Optional[str],
    message_text: Optional[str] = None
) -> ScamCheck:
    """Run Scam-Check Agent on a recruiter contact for an application."""
    company_name = claimed_company or application.company
    risk_score, flagged_reasons = _run_rule_layer(recruiter_name, recruiter_domain, company_name, message_text)

    explanation_text = None
    if risk_score > 0:
        context = {
            "flagged_reasons": flagged_reasons,
            "recruiter_info": {
                "name": recruiter_name,
                "claimed_company": company_name,
                "email_domain": recruiter_domain,
            },
        }
        try:
            llm_resp = await call_llm_generate("scam_explanation", context=context)
            explanation_text = llm_resp.get("generated_text")
        except (ModelServiceUnavailableError, Exception):
            reasons_summary = ", and ".join(flagged_reasons)
            explanation_text = f"This looks risky: {reasons_summary}. Exercise caution before proceeding with {company_name}."

    scam_record = ScamCheck(
        application_id=application.id,
        recruiter_name=recruiter_name,
        recruiter_domain=recruiter_domain,
        risk_score=risk_score,
        flagged_reasons=flagged_reasons,
        explanation_text=explanation_text,
    )

    db.add(scam_record)
    db.commit()
    db.refresh(scam_record)

    return scam_record
