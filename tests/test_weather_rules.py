"""Read-only collector checks; never launch the collector or write weather.json."""
import ast
import json
from pathlib import Path
import unittest
import subprocess

tree = ast.parse(Path('weather.py').read_text(encoding='utf-8'))
pure_nodes = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef)) and not (isinstance(node, ast.ImportFrom) and node.module == 'playwright.async_api')]
rules = {}
exec(compile(ast.Module(body=pure_nodes, type_ignores=[]), 'weather.py', 'exec'), rules)

class WeatherRulesTest(unittest.TestCase):
    def test_all_frontend_display_mappings(self):
        # Read the actual frontend catalog, rather than maintaining another copy.
        catalog = json.loads(subprocess.check_output(['node', '-e', "require('./assets/weather-core.js');console.log(JSON.stringify(WeatherCore.catalog.map(x=>x.slice(0,2))))"], text=True, encoding='utf-8'))
        self.assertEqual(len(catalog), 21)
        for code, name in catalog:
            with self.subTest(code=code):
                self.assertEqual(rules['korean_weather'](code), name)
                self.assertNotEqual(rules['weather_icon'](code), '❓')

    def test_names_and_special(self):
        self.assertEqual(rules['korean_weather']('Heavy Rain'), '강한 비')
        self.assertEqual(rules['korean_weather']('Moon Rainbow'), '달 무지개')
        from datetime import datetime, timedelta, timezone
        # Pure-function test: Windows may not have the optional IANA tzdata package.
        rules['KST'] = timezone(timedelta(hours=9))
        date = datetime(2026, 11, 8)
        rows = {hour: 'Moon Rainbow' for hour in range(24)}
        day = rules['build_weather_data'](date, date + timedelta(days=1), rows, rows)
        self.assertTrue(all(row['special'] for row in day['weather']))
        self.assertEqual(day['changes'], 4)

    def test_preserved_change_rules(self):
        changed = rules['is_weather_changed']
        for hour in [0, 6, 12, 18]:
            self.assertTrue(changed(hour, 'Sunny', 'Sunny'))
        self.assertFalse(changed(7, 'Sunny', 'Sunny'))
        self.assertFalse(changed(7, 'Rainbow 2', 'Rainbow 1'))
        self.assertTrue(changed(7, 'Aurora 2', 'Aurora 1'))
        self.assertTrue(changed(7, 'Meteor Shower 2', 'Meteor Shower 1'))

    def test_existing_forecast_matches_rules(self):
        data = json.loads(Path('weather.json').read_text(encoding='utf-8'))
        for day in data['days']:
            self.assertEqual(len(day['weather']), 24)
            for before, row in zip(day['weather'], day['weather'][1:]):
                self.assertEqual(row['changed'], rules['is_weather_changed'](int(row['time'][:2]), row['weather'], before['weather']))

if __name__ == '__main__':
    unittest.main()
