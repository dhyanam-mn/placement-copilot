import os
import sys

sys.path.insert(0, os.path.abspath("."))

from sqlalchemy import text
from database import SessionLocal

db = SessionLocal()
dupes = db.execute(text("""
    SELECT company, role, source, COUNT(*) 
    FROM applications 
    GROUP BY company, role, source 
    HAVING COUNT(*) > 1;
""")).fetchall()

print(f"Duplicates count: {len(dupes)}")
for d in dupes:
    print(d)
db.close()
