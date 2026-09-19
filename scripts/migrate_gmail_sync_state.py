import os
import sys
import json
import logging
from dateutil import parser
from sqlalchemy import text

sys.path.insert(0, os.path.abspath("."))
from database import SessionLocal
from models import GmailSyncState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migrate_gmail_sync_state")

def migrate():
    json_path = os.path.abspath("gmail_sync_state.json")
    db = SessionLocal()
    try:
        record = db.query(GmailSyncState).first()
        if not record:
            record = GmailSyncState()
            db.add(record)

        if os.path.exists(json_path):
            logger.info(f"Reading json contents from {json_path}...")
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if data.get("last_synced_history_id"):
                record.last_synced_history_id = str(data["last_synced_history_id"])
            if data.get("last_synced_timestamp"):
                record.last_synced_timestamp = parser.isoparse(data["last_synced_timestamp"])
            if data.get("total_messages_processed"):
                record.total_messages_processed = int(data["total_messages_processed"])

            db.commit()
            logger.info("Successfully migrated gmail_sync_state.json into DB gmail_sync_state table.")
            
            os.remove(json_path)
            logger.info(f"Deleted file {json_path}.")
        else:
            logger.info("gmail_sync_state.json not found, ensuring DB record exists.")
            db.commit()

    except Exception as e:
        db.rollback()
        logger.error(f"Migration error: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
