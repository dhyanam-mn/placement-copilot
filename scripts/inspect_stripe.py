import os
import sys

sys.path.insert(0, os.path.abspath("."))

from sqlalchemy import text
from database import SessionLocal

db = SessionLocal()
rows = db.execute(text("SELECT id, company, role, source, octet_length(role) FROM applications WHERE company = 'Stripe' AND role LIKE '%Sales Manager%';")).fetchall()
for r in rows:
    print(r)
db.close()
