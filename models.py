from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import relationship
from database import Base

# CRITICAL: Postgres native ENUM types mapped with create_type=False
# Mandatory because types already exist in DB from schema.sql
application_status_enum = ENUM(
    'DISCOVERED',
    'READY_TO_APPLY',
    'APPLIED',
    'OA_INVITE',
    'INTERVIEW',
    'REJECTED',
    'GHOSTED',
    'OFFER',
    name='application_status',
    create_type=False,
)

status_source_type_enum = ENUM(
    'gmail_auto',
    'auto_ghost',
    'manual',
    name='status_source_type',
    create_type=False,
)


class Application(Base):
    __tablename__ = 'applications'

    id = Column(Integer, primary_key=True, index=True)
    company = Column(Text, nullable=False)
    role = Column(Text, nullable=False)
    jd_text = Column(Text, nullable=False)
    source = Column(Text, nullable=False)

    status = Column(
        application_status_enum,
        nullable=False,
        default='DISCOVERED',
    )
    status_source = Column(
        status_source_type_enum,
        nullable=True,
    )

    match_score = Column(Float, nullable=True)

    tailored_resume_id = Column(
        Integer,
        ForeignKey('tailored_resumes.id', use_alter=True, name='fk_tailored_resume'),
        nullable=True,
    )
    gap_report_id = Column(
        Integer,
        ForeignKey('gap_reports.id', use_alter=True, name='fk_gap_report'),
        nullable=True,
    )

    last_contact_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_updated = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    tailored_resumes = relationship('TailoredResume', back_populates='application', foreign_keys='TailoredResume.application_id')
    gap_reports = relationship('GapReport', back_populates='application', foreign_keys='GapReport.application_id')
    scam_checks = relationship('ScamCheck', back_populates='application')


class TailoredResume(Base):
    __tablename__ = 'tailored_resumes'

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey('applications.id', ondelete='CASCADE'), nullable=False)
    resume_data = Column(JSONB, nullable=False)
    match_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    application = relationship('Application', foreign_keys=[application_id], back_populates='tailored_resumes')


class GapReport(Base):
    __tablename__ = 'gap_reports'

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey('applications.id', ondelete='CASCADE'), nullable=True)
    report_type = Column(Text, nullable=False)
    summary_text = Column(Text, nullable=False)
    details = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

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

    application = relationship('Application', back_populates='scam_checks')
