code = '''

# --- 9. GET /applications/{id}/prep-question ---
@router.get("/applications/{id}/prep-question")
def get_prep_question(id: int, db: Session = Depends(get_db)):
    """Deterministically generate an interview question based on the application's gap report."""
    app = db.query(Application).filter(Application.id == id).first()
    if not app:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"application id {id} does not exist"},
        )
        
    gap_report = db.query(GapReport).filter(GapReport.application_id == id, GapReport.report_type == 'per_row').first()
    
    missing = []
    matched = []
    if gap_report and gap_report.details:
        missing = gap_report.details.get("missing_skills", [])
        matched = gap_report.details.get("matched_skills", [])
        
    if missing:
        skill = missing[0]
        question = f"Your profile doesn't explicitly highlight experience with {skill}, which is a key requirement for this role. How would you quickly get up to speed with it, or how does your past experience translate?"
        tags = [skill]
    elif matched:
        skill = matched[0]
        question = f"You have experience with {skill}. Walk me through a complex problem you solved using {skill}, focusing on trade-offs you had to make."
        tags = [skill]
    else:
        question = f"Walk me through your overall approach to the technical challenges associated with the {app.role} role."
        tags = ["problem solving", "system design"]
        
    return {
        "question": question,
        "question_tags": tags
    }
'''
with open('routers/applications.py', 'a') as f:
    f.write(code)
