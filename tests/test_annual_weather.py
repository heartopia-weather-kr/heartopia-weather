import json
import unittest
from datetime import date, datetime, time, timedelta

import build_annual_weather as annual
import weather


class AnnualWeatherTests(unittest.TestCase):
    def test_release_matches_all_legacy_days_and_raw_ids(self):
        release = json.loads(annual.OUTPUT.read_text(encoding="utf-8"))
        source = weather.load_year(2026)
        day = date(2026, 1, 1)
        missing = []
        total = 0
        for offset in range(0, 365, 9):
            legacy = weather.build(datetime.combine(day + timedelta(days=offset), time(), weather.KST))
            for old in legacy["days"][:min(9, 365 - offset)]:
                key = old["startDate"]
                current = release["days"][key]
                self.assertEqual([row["id"] for row in current["weather"]], source[key], key)
                for row in current["weather"]:
                    total += 1
                    if row["weather"] == "Unknown":
                        missing.append((key, row["time"], row["id"]))
                expected = {key: value for key, value in old.items() if key not in ("updated", "updatedTime", "periods")}
                expected["weather"] = [{**row, "id": identifier} for row, identifier in zip(old["weather"], source[key])]
                self.assertEqual(current, expected, key)
        self.assertEqual(total, 8760)
        self.assertEqual(sum(key.startswith("2026-") for key in release["days"]), 365)
        self.assertEqual(release, annual.annual_data(release["basisDate"], annual.forecast_days()))
        print(f"2026: {total} hourly rows, {len(missing)} missing/unmapped; {missing}")
