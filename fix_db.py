import os
from sqlalchemy import create_engine, text
DB_URL = os.getenv('DATABASE_URL', 'postgresql+pg8000://postgres:a@localhost:5432/placement_copilot')
engine = create_engine(DB_URL)
with engine.begin() as conn:
    conn.execute(text('ALTER TABLE applications DROP CONSTRAINT IF EXISTS applications_source_check;'))
    conn.execute(text("ALTER TABLE applications ADD CONSTRAINT applications_source_check CHECK (source IN ('adzuna', 'greenhouse', 'lever', 'unstop'));"))
print('Constraint updated successfully!')
