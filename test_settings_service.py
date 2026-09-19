import sys
import os
import unittest

root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, root_dir)

from database import SessionLocal
from services.settings_service import (
    get_ghost_days,
    get_nudge_days,
    get_scam_threshold,
    get_scout_interval_hours,
    refresh_settings_cache,
)

class TestSettingsService(unittest.TestCase):

    def setUp(self):
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    def test_settings_defaults_and_refresh(self):
        cache = refresh_settings_cache(self.db)
        self.assertIn("ghost_days", cache)
        self.assertEqual(get_ghost_days(self.db), 45)
        self.assertIsInstance(get_nudge_days(self.db), int)
        self.assertIsInstance(get_scam_threshold(self.db), float)
        self.assertIsInstance(get_scout_interval_hours(self.db), int)

if __name__ == "__main__":
    unittest.main()
