import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import weather


def now(year, month, day):
    return datetime(year, month, day, 12, tzinfo=ZoneInfo("Asia/Seoul"))


class CalendarWeatherTests(unittest.TestCase):
    def test_year_scoped_2026_source_has_366_records(self):
        raw = json.loads((weather.ROOT / "data/weather-2026.json").read_text())
        self.assertEqual(len(raw), 366)
        self.assertTrue(all(len(row["weatherIds"]) == 24 for row in raw))

    def test_2026_nonleap_february_does_not_shift_march(self):
        data = weather.build(now(2026, 2, 28))
        self.assertEqual([day["startDate"] for day in data["days"][:3]],
                         ["2026-02-28", "2026-03-01", "2026-03-02"])
        self.assertEqual(data["days"][1]["weather"][0]["weather"],
                         weather.weather_name(weather.load_year(2026)["2026-03-01"][0], 0))

    def test_year_boundary_never_borrows_2026(self):
        data = weather.build(now(2026, 12, 31))
        self.assertEqual(data["days"][1]["startDate"], "2027-01-01")
        self.assertEqual(data["days"][1]["weather"][0]["name"], "?")
        self.assertIsNone(data["days"][1]["changeRate"])
        self.assertEqual(len(data["days"]), 9)

    def test_missing_future_year_leap_day_kept(self):
        data = weather.build(now(2028, 2, 28))
        self.assertEqual([day["startDate"] for day in data["days"][:3]],
                         ["2028-02-28", "2028-02-29", "2028-03-01"])
        self.assertTrue(all(row["name"] == "?" for row in data["days"][1]["weather"]))

    def test_early_next_year_upload_is_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "data"
            folder.mkdir()
            (folder / "weather-2027.json").write_text(json.dumps([
                {"month": 1, "day": 1, "weatherIds": [102]*24},
                {"month": 1, "day": 2, "weatherIds": [101]*24}
            ]))
            with patch.object(weather, "ROOT", Path(tmp)):
                data = weather.build(now(2026, 12, 31))
            self.assertEqual(data["days"][1]["weather"][0]["weather"], "Cloudy")
            self.assertEqual(data["days"][2]["weather"][7]["weather"], "Sunny")
            self.assertEqual(data["days"][3]["weather"][0]["weather"], "Unknown")

    def test_missing_hour_does_not_shift_adjacent_hours(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "data"
            folder.mkdir()
            (folder / "weather-2027.json").write_text(json.dumps([
                {"month": 1, "day": 1, "weatherIds": [101]*12 + [999] + [102]*11}
            ]))
            with patch.object(weather, "ROOT", Path(tmp)):
                data = weather.build(now(2027, 1, 1))
            rows = data["days"][0]["weather"]
            self.assertEqual(rows[11]["weather"], "Sunny")
            self.assertEqual(rows[12]["weather"], "Unknown")
            self.assertEqual(rows[13]["weather"], "Cloudy")
            self.assertFalse(rows[13]["changed"])
            self.assertIsNone(data["days"][0]["changeRate"])

    def test_no_forced_six_hour_change(self):
        self.assertEqual(weather.normalized("Rainbow 2"), weather.normalized("Rainbow"))
        self.assertNotEqual(weather.normalized("Meteor Shower 1"), weather.normalized("Meteor Shower 2"))


if __name__ == "__main__":
    unittest.main()
