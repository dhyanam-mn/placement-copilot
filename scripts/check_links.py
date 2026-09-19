#!/usr/bin/env python3
"""
Resource Link Health Checker Script
Performs HTTP HEAD checks (with GET fallback) for every resource URL in the resources table,
updating verified_at timestamp and is_active flag.
"""

import sys
import os
import logging
from datetime import datetime, timezone
import urllib.request
import urllib.error

# Ensure root workspace is in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

from database import SessionLocal
from models import Resource

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("check_links")


def check_url_active(url: str, timeout: int = 5) -> bool:
    """HEAD check URL status; fall back to GET if 405 Method Not Allowed."""
    headers = {"User-Agent": "Placement-Copilot/1.0 (Resource-Verifier)"}
    try:
        req = urllib.request.Request(url, headers=headers, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 400
    except urllib.error.HTTPError as e:
        if e.code == 405:  # Method Not Allowed for HEAD, try GET
            try:
                req = urllib.request.Request(url, headers=headers, method="GET")
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return 200 <= resp.status < 400
            except Exception:
                return False
        return False
    except Exception:
        return False


def run_link_check():
    db = SessionLocal()
    try:
        resources = db.query(Resource).all()
        logger.info(f"Starting link verification for {len(resources)} resources...")

        active_count = 0
        inactive_count = 0

        now = datetime.now(timezone.utc)

        for res in resources:
            is_active = check_url_active(res.url)
            res.is_active = is_active
            res.verified_at = now

            status_str = "ACTIVE" if is_active else "INACTIVE"
            logger.info(f"[{status_str}] Resource #{res.id} ('{res.title}'): {res.url}")

            if is_active:
                active_count += 1
            else:
                inactive_count += 1

        db.commit()
        logger.info(f"Link check complete! Total: {len(resources)} | Active: {active_count} | Inactive: {inactive_count}")
        return {
            "total": len(resources),
            "active": active_count,
            "inactive": inactive_count,
        }
    except Exception as exc:
        logger.error(f"Error executing link check: {exc}")
        db.rollback()
        return {"total": 0, "active": 0, "inactive": 0, "error": str(exc)}
    finally:
        db.close()


if __name__ == "__main__":
    run_link_check()
