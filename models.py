from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, Boolean, ForeignKey, func,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import relationship
from database import Base

application_status_enum = ENUM(
    'DISCOVERED', 'READY_TO_APPLY', 'APPLIED', 'OA_INVITE', 'INTERVIEW', 'REJECTED', 'GHOSTED', 'OFFER',
    name='application_status', create_type=False,
)

status_source_type_enum = ENUM(
    'gmail_auto', 'auto_ghost', 'manual',
    name='status_source_type', create_type=False,
)

class Application(Base):
    __tablename__ = 'applications'
    id = Column(Integer, primary_key=True, index=True)
    company = Column(Text, nullable=False)
    role = Column(Text, nullable=False)
    jd_text = Column(Text, nullable=False)
    source = Column(Text, nullable=False)
    status = Column(application_status_enum, nullable=False, default='DISCOVERED')
    status_source = Column(status_source_type_enum, nullable=True)
    match_score = Column(Float, nullable=True)
    tailored_resume_id = Column(Integer, ForeignKey('tailored_resumes.id', use_alter=True, name='fk_tailored_resume'), nullable=True)
    gap_report_id = Column(Integer, ForeignKey('gap_reports.id', use_alter=True, name='fk_gap_report'), nullable=True)
    last_contact_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_updated = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    is_demo = Column(Boolean, nullable=False, default=False)
    
    tailored_resumes = relationship('TailoredResume', back_populates='application', foreign_keys='TailoredResume.application_id', cascade='all, delete-orphan')
    gap_reports = relationship('GapReport', back_populates='application', foreign_keys='GapReport.application_id', cascade='all, delete-orphan')
    scam_checks = relationship('ScamCheck', back_populates='application', cascade='all, delete-orphan')

class TailoredResume(Base):
    __tablename__ = 'tailored_resumes'
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey('applications.id', ondelete='CASCADE'), nullable=False)
    resume_data = Column(JSONB, nullable=False)
    match_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    is_demo = Column(Boolean, nullable=False, default=False)
    application = relationship('Application', foreign_keys=[application_id], back_populates='tailored_resumes')

class GapReport(Base):
    __tablename__ = 'gap_reports'
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey('applications.id', ondelete='CASCADE'), nullable=True)
    report_type = Column(Text, nullable=False)
    summary_text = Column(Text, nullable=False)
    details = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    is_demo = Column(Boolean, nullable=False, default=False)
    application = relationship('Application', foreign_keys=[application_id], back_populates='gap_reports')

class ScamCheck(Base):
    __tablename__ = 'scam_checks'
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey('applications.id', ondelete='CASCADE'), nullable=True)
    recruiter_name = Column(Text, nullable=True)
    recruiter_domain = Column(Text, nullable=True)
    risk_score = Column(Float, nullable=False)
    flagged_reasons = Column(JSONB, nullable=False)
    explanation_text = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    is_demo = Column(Boolean, nullable=False, default=False)
    application = relationship('Application', back_populates='scam_checks')

class Profile(Base):
    __tablename__ = 'profile'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, nullable=False)
    contact_info = Column(Text, nullable=True)
    email = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    is_demo = Column(Boolean, nullable=False, default=False)
    projects = relationship('ProfileProject', back_populates='profile')

class ProfileProject(Base):
    __tablename__ = 'profile_projects'
    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey('profile.id', ondelete='CASCADE'), nullable=False)
    project_name = Column(Text, nullable=False)
    bullet_text = Column(Text, nullable=False)
    skill_tags = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    is_demo = Column(Boolean, nullable=False, default=False)
    profile = relationship('Profile', back_populates='projects')

class Skill(Base):
    __tablename__ = 'skills'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, nullable=False, unique=True)
    category = Column(Text, nullable=True)
    aliases = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    is_demo = Column(Boolean, nullable=False, default=False)

class Resource(Base):
    __tablename__ = 'resources'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    is_demo = Column(Boolean, nullable=False, default=False)
    skills = relationship('ResourceSkill', back_populates='resource')

class PrepRecommendation(Base):
    __tablename__ = 'prep_recommendations'
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey('applications.id', ondelete='CASCADE'), nullable=False)
    resource_id = Column(Integer, ForeignKey('resources.id', ondelete='CASCADE'), nullable=False)
    reason = Column(Text, nullable=False)
    est_hours = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    is_demo = Column(Boolean, nullable=False, default=False)

    application = relationship('Application', foreign_keys=[application_id])
    resource = relationship('Resource', foreign_keys=[resource_id])

class ResourceSkill(Base):
    __tablename__ = 'resource_skills'
    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(Integer, ForeignKey('resources.id', ondelete='CASCADE'), nullable=False)
    skill_name = Column(Text, ForeignKey('skills.name', ondelete='CASCADE'), nullable=False)
    weight = Column(Float, default=1.0)
    resource = relationship('Resource', back_populates='skills')

class ScamPattern(Base):
    __tablename__ = 'scam_patterns'
    id = Column(Integer, primary_key=True, index=True)
    category = Column(Text, nullable=False)
    pattern = Column(Text, nullable=False)
    weight = Column(Float, nullable=False)
    source_note = Column(Text, nullable=False, default='TODO')
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    is_demo = Column(Boolean, nullable=False, default=False)

class CompanyWatchlist(Base):
    __tablename__ = 'company_watchlist'
    id = Column(Integer, primary_key=True, index=True)
    company = Column(Text, nullable=False, unique=True)
    ats = Column(Text, nullable=True)
    token = Column(Text, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    is_demo = Column(Boolean, nullable=False, default=False)

class Setting(Base):
    __tablename__ = 'settings'
    key = Column(Text, primary_key=True)
    value = Column(JSONB, nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

class StatusEvent(Base):
    __tablename__ = 'status_events'
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey('applications.id', ondelete='CASCADE'), nullable=False)
    old_status = Column(Text, nullable=True)
    new_status = Column(Text, nullable=False)
    event_source = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    is_demo = Column(Boolean, nullable=False, default=False)

class Notification(Base):
    __tablename__ = 'notifications'
    id = Column(Integer, primary_key=True, index=True)
    type = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    is_demo = Column(Boolean, nullable=False, default=False)

class LLMCache(Base):
    __tablename__ = 'llm_cache'
    prompt_hash = Column(Text, primary_key=True)
    response = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    is_demo = Column(Boolean, nullable=False, default=False)

class GmailSyncState(Base):
    __tablename__ = 'gmail_sync_state'
    id = Column(Integer, primary_key=True, index=True)
    last_synced_history_id = Column(Text, nullable=True)
    last_synced_timestamp = Column(DateTime(timezone=True), nullable=True)
    total_messages_processed = Column(Integer, default=0)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
