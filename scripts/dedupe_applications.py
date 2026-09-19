import os
import sys
import logging

sys.path.insert(0, os.path.abspath("."))

from sqlalchemy import text
from database import SessionLocal, engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dedupe_applications")

def deduplicate_and_add_constraint():
    # Phase 1: Pure DB Session for Deduplication
    db = SessionLocal()
    try:
        logger.info("Normalizing whitespace in company, role, source...")
        db.execute(text("UPDATE applications SET company = TRIM(REGEXP_REPLACE(company, '\\s+', ' ', 'g')), role = TRIM(REGEXP_REPLACE(role, '\\s+', ' ', 'g')), source = TRIM(REGEXP_REPLACE(source, '\\s+', ' ', 'g'));"))
        db.commit()

        logger.info("Setting self-referential FK pointers to NULL...")
        db.execute(text("""
            UPDATE applications
            SET tailored_resume_id = NULL, gap_report_id = NULL
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM applications
                GROUP BY company, role, source
            );
        """))
        db.commit()

        logger.info("Remapping child table foreign keys...")
        for table in ["tailored_resumes", "gap_reports", "scam_checks", "prep_recommendations", "status_events"]:
            db.execute(text(f"""
                WITH min_map AS (
                    SELECT company, role, source, MIN(id) AS min_id
                    FROM applications
                    GROUP BY company, role, source
                )
                UPDATE {table} t
                SET application_id = m.min_id
                FROM applications a
                JOIN min_map m ON a.company = m.company AND a.role = m.role AND a.source = m.source
                WHERE t.application_id = a.id AND a.id != m.min_id;
            """))
        db.commit()

        logger.info("Deleting all duplicate application rows...")
        res = db.execute(text("""
            DELETE FROM applications
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM applications
                GROUP BY company, role, source
            );
        """))
        deleted_count = res.rowcount
        db.commit()
        logger.info(f"Deduplication phase finished. Total deleted rows: {deleted_count}")

    except Exception as e:
        db.rollback()
        logger.error(f"Error during deduplication: {e}")
        raise e
    finally:
        db.close()

    # Phase 2: DDL on fresh Connection
    with engine.connect() as conn:
        logger.info("Adding UNIQUE constraint uq_applications_company_role_source...")
        conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'uq_applications_company_role_source'
                ) THEN
                    ALTER TABLE applications ADD CONSTRAINT uq_applications_company_role_source UNIQUE (company, role, source);
                END IF;
            END $$;
        """))
        conn.commit()
    logger.info("UNIQUE constraint uq_applications_company_role_source successfully added.")

if __name__ == "__main__":
    deduplicate_and_add_constraint()
