"""Malformed forecast/recovery regression. All payloads remain in memory."""
import copy
import functools
import json
import threading
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT)))
threading.Thread(target=server.serve_forever, daemon=True).start()
url = f'http://127.0.0.1:{server.server_port}'
original = json.loads((ROOT / 'weather.json').read_text(encoding='utf-8'))
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel='msedge')
        context = browser.new_context(timezone_id='America/Los_Angeles')
        timer_hook = """
            const interval = window.setInterval;
            window.setInterval = function(callback, delay, ...args) {
                if (delay === 15 * 60000) window.retryForecast = callback;
                return interval.call(this, callback, delay, ...args);
            };
        """
        # Install after Playwright's clock shim, immediately before app startup.
        context.route('**/assets/weather-app.js', lambda route: route.fulfill(
            body=timer_hook + (ROOT / 'assets/weather-app.js').read_text(encoding='utf-8'),
            content_type='application/javascript'))
        errors = []
        payload = copy.deepcopy(original)
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.clock.install(time=datetime.fromisoformat('2026-11-08T08:00:00+00:00'))
        page.route('**/weather.json?*', lambda route: route.fulfill(json=payload))
        page.goto(url)
        page.locator('.day-card').last.wait_for()
        page.locator('#notice-close').click()
        page.locator('#calculator-toggle').click()
        page.locator('#calculator-run').click()
        selectors = ['#current-weather', '#week-days', '#periods', '#day-summary', '#clock-center', '#status', '#calculator-result']
        snapshot = [page.locator(selector).inner_text() for selector in selectors]
        mutations = [
            lambda x: x['days'][0].pop('status'),
            lambda x: x['days'][0].update(status=None),
            lambda x: x['days'][0].update(status=5),
            lambda x: x['days'][0].update(status={}),
            lambda x: x['days'][0].pop('dateLabel'),
            lambda x: x.update(updated=123),
            lambda x: x['days'][0]['weather'][0].update(weather=[]),
            lambda x: x['days'][0]['weather'][0].pop('changed'),
        ]
        for mutate in mutations:
            snapshot = [page.locator(selector).inner_text() for selector in selectors]
            payload = copy.deepcopy(original)
            mutate(payload)
            page.evaluate('async () => await window.retryForecast()')
            assert page.locator('#load-error').is_visible()
            assert snapshot == [page.locator(selector).inner_text() for selector in selectors]
            assert page.locator('#calculator-dialog').is_visible()
            # Timed rendering still uses the last valid payload.
            page.clock.run_for(60000)
            assert page.locator('#calculator-run').is_enabled()
        payload = copy.deepcopy(original)
        payload['updated'] = '2026-11-08 17:50'
        page.evaluate('async () => await window.retryForecast()')
        assert page.locator('#load-error').is_hidden()
        assert '17:50' in page.locator('#status').inner_text()
        assert page.locator('#calculator-dialog').is_visible()
        page.locator('#calculator-run').click()
        assert page.locator('#calculator-result .result-summary').count() == 1
        page.locator('#calculator-close').click()
        page.locator('.day-card').first.click()
        assert page.locator('#periods .weather-row').count() == 24
        page.keyboard.press('Escape')

        # First request invalid: no partial forecast, then recover via the same retry.
        payload = copy.deepcopy(original)
        payload['days'][0].pop('status')
        failed = context.new_page()
        failed.on('pageerror', lambda error: errors.append(str(error)))
        failed.clock.install(time=datetime.fromisoformat('2026-11-08T08:00:00+00:00'))
        failed.route('**/weather.json?*', lambda route: route.fulfill(json=payload))
        failed.goto(url)
        failed.locator('#load-error').wait_for(state='visible')
        assert failed.locator('.day-card').count() == 0
        assert failed.locator('#periods .weather-row').count() == 0
        assert failed.locator('#calculator-run').is_disabled()
        assert '날씨 정보를 불러오지 못했어요.' in failed.locator('#current-weather').inner_text()
        payload = copy.deepcopy(original)
        failed.evaluate('async () => await window.retryForecast()')
        assert failed.locator('.day-card').count() == 7
        assert failed.locator('#periods .weather-row').count() == 24
        assert failed.locator('#load-error').is_hidden()
        assert failed.locator('#calculator-run').is_enabled()
        assert not errors, errors
        browser.close()
        print('PASS: 8 malformed refreshes preserve valid forecast/modal/result; timed rendering remains safe; valid refresh recovers; invalid first load shows error and recovers; no JS errors')
finally:
    server.shutdown()
    server.server_close()
