"""Read-only checks of the published weather mapping and change rules."""
import json
import subprocess
import unittest
from datetime import date, datetime

import weather


class WeatherRulesTest(unittest.TestCase):
    def test_all_frontend_display_mappings(self):
        catalog = json.loads(subprocess.check_output(
            ["node", "-e", "require('./assets/weather-core.js');console.log(JSON.stringify(WeatherCore.catalog.map(x=>x.slice(0,2))))"],
            text=True, encoding="utf-8",
        ))
        self.assertEqual(len(catalog), 24)
        for name, korean in weather.KO.items():
            with self.subTest(name=name):
                self.assertEqual(dict(catalog)[name], korean)
                self.assertIn(name, weather.ICONS)

    def test_names_and_special(self):
        for identifier, english in [(204, "Heavy Rain"), (301, "Moon Rainbow")]:
            with self.subTest(identifier=identifier):
                table = {"2026-11-07": [identifier]*24, "2026-11-08": [identifier]*24}
                day = weather.build_day(date(2026, 11, 8), {2026: table})
                self.assertTrue(all(row["weather"] == english for row in day["weather"]))
                self.assertTrue(all(row["name"] == weather.KO[english] for row in day["weather"]))
                self.assertTrue(all(row["special"] == (identifier == 301) for row in day["weather"]))
                self.assertEqual(day["changes"], 0)

    def test_preserved_change_rules(self):
        self.assertEqual(weather.normalized("Rainbow 2"), weather.normalized("Rainbow 1"))
        self.assertNotEqual(weather.normalized("Aurora 2"), weather.normalized("Aurora 1"))
        self.assertNotEqual(weather.normalized("Meteor Shower 2"), weather.normalized("Meteor Shower 1"))

    def test_existing_forecast_matches_rules(self):
        data = weather.build(datetime(2026, 11, 8, tzinfo=weather.KST))
        for day in data["days"]:
            self.assertEqual(len(day["weather"]), 24)
            for before, row in zip(day["weather"], day["weather"][1:]):
                self.assertEqual(row["changed"], weather.normalized(row["weather"]) != weather.normalized(before["weather"]))


if __name__ == "__main__":
    unittest.main()
