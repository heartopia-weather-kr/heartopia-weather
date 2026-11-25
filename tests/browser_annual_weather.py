"""Exercise the distributed annual file in real desktop and mobile viewports."""
import functools
import threading
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASIS = "데이터 기준일: 2026.11.23"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def expect_date(page, date):
    expect(page.locator("#today-date")).to_have_attribute("datetime", date)
    expect(page.locator(".day-card")).to_have_count(7)
    expect(page.locator("#calculator-date option")).to_have_count(9)
    expect(page.locator("#status")).to_have_text(BASIS)
    expect(page.locator(".clock-hour")).to_have_count(12)


def run(browser, url, options):
    context = browser.new_context(timezone_id="America/Los_Angeles", **options)
    context.grant_permissions(["clipboard-read", "clipboard-write"])
    context.route("**/notice.json?*", lambda route: route.fulfill(json={"enabled": False}))
    page = context.new_page()
    errors = []
    requests = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("request", lambda request: requests.append(request.url))
    clock = page.clock
    clock.install(time=datetime.fromisoformat("2026-11-25T23:59:00+09:00"))
    page.goto(url)
    expect_date(page, "2026-11-25")
    expect(page.locator("html")).to_have_attribute("data-theme", "light")
    page.locator('[data-theme-choice="midnight"]').click()
    expect(page.locator("html")).to_have_attribute("data-theme", "midnight")
    expect(page.locator(".hero .icon-midnight").first).to_have_css("display", "block")
    page.locator("#weather-copy").click()
    expect(page.locator("#weather-copy-text")).to_contain_text("복사 완료")
    assert "11월 25일" in page.evaluate("navigator.clipboard.readText()")
    page.locator("#redeem-open").click()
    expect(page.locator("#redeem-dialog")).to_be_visible()
    expect(page.locator("#redeem-active-count")).not_to_have_text("0")
    page.locator("#redeem-close").click()
    page.locator(".day-card").first.click()
    expect(page.locator("#periods .weather-row")).to_have_count(24)
    expect(page.locator("#periods .special-star").first).to_be_visible()
    page.locator("#view-grouped").click()
    expect(page.locator("#periods .weather-row")).to_have_count(6)
    page.locator("#forecast-close").click()
    clock.run_for(60_100)
    expect_date(page, "2026-11-26")
    expect(page.locator("#clock-am")).to_have_attribute("aria-pressed", "true")
    page.locator("#calculator-toggle").click()
    page.locator("#calculator-run").click()
    expect(page.locator("#calculator-result .result-summary")).to_contain_text("변동률")
    page.locator("#calculator-close").click()
    page.locator('[data-theme-choice="light"]').click()
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")

    # Change the wall clock while timers are idle, then simulate foregrounding.
    clock.set_system_time(datetime.fromisoformat("2026-11-30T23:59:00+09:00"))
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    expect_date(page, "2026-11-30")
    clock.run_for(60_100)
    expect_date(page, "2026-12-01")
    clock.set_system_time(datetime.fromisoformat("2026-12-08T12:00:00+09:00"))
    page.evaluate("window.dispatchEvent(new Event('pageshow'))")
    expect_date(page, "2026-12-08")
    assert page.locator(".hero-forecast strong").first.inner_text() != "?"
    clock.set_system_time(datetime.fromisoformat("2026-12-31T23:59:00+09:00"))
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    expect_date(page, "2026-12-31")
    expect(page.locator(".hero-forecast strong").last).to_have_text("?")
    clock.run_for(60_100)
    expect_date(page, "2027-01-01")
    expect(page.locator("#today-changes")).to_have_text("?")
    expect(page.locator("#clock-center strong").first).to_have_text("?")
    page.locator("#calculator-toggle").click()
    page.locator("#calculator-run").click()
    expect(page.locator("#calculator-result .form-error")).to_contain_text("데이터가 없어")
    assert sum(url.endswith("/annual-weather.json") for url in requests) == 1
    assert not any("/weather.json" in url for url in requests)
    page.reload()
    expect_date(page, "2027-01-01")
    assert not errors, errors
    context.close()


if __name__ == "__main__":
    handler = functools.partial(QuietHandler, directory=str(ROOT))
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True, channel="msedge")
                url = f"http://127.0.0.1:{server.server_port}"
                run(browser, url, {"viewport": {"width": 1536, "height": 1000}})
                print("PASS: desktop annual weather, KST date boundaries and UI")
                run(browser, url, {"viewport": {"width": 390, "height": 844}, "is_mobile": True, "has_touch": True})
                print("PASS: mobile annual weather, KST date boundaries and UI")
        finally:
            server.shutdown()
