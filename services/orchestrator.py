import logging
from typing import TypedDict, List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver

from database import SessionLocal
from models import Application
from scam_check import check_scam
from services.tailoring import tailor_resume_for_application
from services.gap_agent import generate_per_row_gap_report
from services.prep_agent import generate_prep_recommendations, get_application_prep_recommendations

logger = logging.getLogger("placement_copilot.orchestrator")


class ApplicationState(TypedDict):
    application_id: int
    company: str
    role: str
    jd_text: str
    source: str
    status: str
    status_source: Optional[str]
    risk_score: float
    flagged_reasons: List[str]
    tailored_resume_id: Optional[int]
    gap_report_id: Optional[int]
    prep_recommendations: List[dict]
    error: Optional[str]


# ==============================================================================
# NODE FUNCTIONS
# ==============================================================================

def scout_node(state: ApplicationState) -> ApplicationState:
    """Scout Node: Initializes job application state from DB."""
    db = SessionLocal()
    try:
        app = db.query(Application).filter(Application.id == state["application_id"]).first()
        if app:
            state["status"] = app.status or "DISCOVERED"
            state["company"] = app.company
            state["role"] = app.role
            state["jd_text"] = app.jd_text
            state["source"] = app.source
        logger.info(f"[Orchestrator] Scout Node completed for App ID {state['application_id']}.")
    finally:
        db.close()
    return state


async def scam_check_node(state: ApplicationState) -> ApplicationState:
    """Scam Check Node: Evaluates risk for job application."""
    db = SessionLocal()
    try:
        app = db.query(Application).filter(Application.id == state["application_id"]).first()
        if app:
            import re
            sender_email = app.source if "@" in app.source else ""
            if not sender_email and app.jd_text:
                match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', app.jd_text)
                if match:
                    sender_email = match.group(0)

            scam_res = check_scam(sender_email=sender_email, claimed_company=app.company, message_text=app.jd_text)
            state["risk_score"] = scam_res.get("risk_score", 0.0)
            state["flagged_reasons"] = scam_res.get("flagged_reasons", [])

            if state["risk_score"] >= 0.7:
                from services.status_service import set_status
                await set_status(db, app.id, "REJECTED", source="manual")
                state["status"] = "FLAGGED_SCAM"
                logger.warning(f"[Orchestrator] App ID {app.id} flagged as scam (risk score: {state['risk_score']}).")
        logger.info(f"[Orchestrator] Scam Check Node completed for App ID {state['application_id']}.")
    finally:
        db.close()
    return state


async def tailoring_node(state: ApplicationState) -> ApplicationState:
    """Tailoring Node: Tailors resume for application and transitions state to READY_TO_APPLY."""
    db = SessionLocal()
    try:
        app = db.query(Application).filter(Application.id == state["application_id"]).first()
        if app and app.status != "FLAGGED_SCAM":
            tailor_res = tailor_resume_for_application(db, app)
            state["tailored_resume_id"] = tailor_res.get("tailored_resume_id")

            from services.status_service import set_status
            await set_status(db, app.id, "READY_TO_APPLY", source="manual")
            state["status"] = "READY_TO_APPLY"
            logger.info(f"[Orchestrator] Tailoring Node completed for App ID {app.id}. Status set to READY_TO_APPLY.")
    finally:
        db.close()
    return state


def tracker_node(state: ApplicationState) -> ApplicationState:
    """Tracker Node: Reads latest status signal from DB."""
    db = SessionLocal()
    try:
        app = db.query(Application).filter(Application.id == state["application_id"]).first()
        if app:
            state["status"] = app.status
            state["status_source"] = app.status_source
            state["gap_report_id"] = app.gap_report_id
            logger.info(f"[Orchestrator] Tracker Node synced App ID {app.id} (status: {app.status}).")
    finally:
        db.close()
    return state


async def gap_analysis_node(state: ApplicationState) -> ApplicationState:
    """Gap Analysis Node: Generates per-row gap report for REJECTED/GHOSTED rows."""
    db = SessionLocal()
    try:
        app = db.query(Application).filter(Application.id == state["application_id"]).first()
        if app and app.status in ("GHOSTED", "REJECTED"):
            report = await generate_per_row_gap_report(db, app)
            if report:
                state["gap_report_id"] = report.get("id")
            logger.info(f"[Orchestrator] Gap Analysis Node completed for App ID {app.id}.")
    finally:
        db.close()
    return state


async def prep_node(state: ApplicationState) -> ApplicationState:
    """Prep Node: Generates learning recommendations for INTERVIEW rows."""
    db = SessionLocal()
    try:
        app = db.query(Application).filter(Application.id == state["application_id"]).first()
        if app and app.status == "INTERVIEW":
            recs = await generate_prep_recommendations(db, app)
            state["prep_recommendations"] = recs
            logger.info(f"[Orchestrator] Prep Node completed for App ID {app.id} ({len(recs)} resources).")
    finally:
        db.close()
    return state


# ==============================================================================
# CONDITIONAL EDGES
# ==============================================================================

def route_after_scam_check(state: ApplicationState) -> str:
    if state.get("status") == "FLAGGED_SCAM" or state.get("risk_score", 0.0) >= 0.7:
        return "end"
    return "tailoring"


def route_after_tracker(state: ApplicationState) -> str:
    status = state.get("status")
    if status in ("REJECTED", "GHOSTED"):
        return "gap_analysis"
    elif status == "INTERVIEW":
        return "prep"
    return "end"


# ==============================================================================
# GRAPH COMPILATION
# ==============================================================================

def build_orchestrator_graph():
    builder = StateGraph(ApplicationState)

    builder.add_node("scout", scout_node)
    builder.add_node("scam_check", scam_check_node)
    builder.add_node("tailoring", tailoring_node)
    builder.add_node("tracker", tracker_node)
    builder.add_node("gap_analysis", gap_analysis_node)
    builder.add_node("prep", prep_node)

    builder.add_edge(START, "scout")
    builder.add_edge("scout", "scam_check")

    builder.add_conditional_edges(
        "scam_check",
        route_after_scam_check,
        {
            "end": END,
            "tailoring": "tailoring",
        },
    )

    # After tailoring, graph interrupts before tracker_node until student confirms applied
    builder.add_edge("tailoring", "tracker")

    builder.add_conditional_edges(
        "tracker",
        route_after_tracker,
        {
            "gap_analysis": "gap_analysis",
            "prep": "prep",
            "end": END,
        },
    )

    builder.add_edge("gap_analysis", END)
    builder.add_edge("prep", END)

    # Compile graph with MemorySaver and interrupt checkpoint at READY_TO_APPLY (before tracker node)
    checkpointer = MemorySaver()
    compiled = builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["tracker"],
    )
    return compiled


orchestrator_graph = build_orchestrator_graph()


# ==============================================================================
# WORKFLOW EXECUTION HELPERS
# ==============================================================================

async def run_application_workflow(db: Session, app: Application) -> Dict[str, Any]:
    """
    Launches initial workflow for an application:
    scout -> scam_check -> tailoring -> interrupt at READY_TO_APPLY.
    """
    initial_state: ApplicationState = {
        "application_id": app.id,
        "company": app.company,
        "role": app.role,
        "jd_text": app.jd_text,
        "source": app.source,
        "status": app.status or "DISCOVERED",
        "status_source": app.status_source,
        "risk_score": 0.0,
        "flagged_reasons": [],
        "tailored_resume_id": app.tailored_resume_id,
        "gap_report_id": app.gap_report_id,
        "prep_recommendations": [],
        "error": None,
    }

    thread_config = {"configurable": {"thread_id": str(app.id)}}
    final_state = await orchestrator_graph.ainvoke(initial_state, config=thread_config)
    return final_state


async def confirm_application_applied(db: Session, application_id: int) -> Dict[str, Any]:
    """
    Resumes workflow from READY_TO_APPLY checkpoint after student confirms application submission:
    Updates DB status to APPLIED and advances graph through tracker -> (gap/prep if applicable).
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise ValueError(f"Application id {application_id} not found.")

    if app.status != "READY_TO_APPLY":
        logger.warning(f"Application {application_id} status is {app.status}, proceeding with APPLIED transition.")

    from services.status_service import set_status
    app = await set_status(db, application_id, "APPLIED", source="manual")

    thread_config = {"configurable": {"thread_id": str(application_id)}}

    # Update state in graph checkpointer to reflect status = APPLIED
    current_state = orchestrator_graph.get_state(thread_config)
    if current_state and current_state.values:
        updated_values = dict(current_state.values)
        updated_values["status"] = "APPLIED"
        updated_values["status_source"] = "manual"
        orchestrator_graph.update_state(thread_config, updated_values)

    # Resume graph execution past the tracker interrupt
    final_state = await orchestrator_graph.ainvoke(None, config=thread_config)
    return final_state
