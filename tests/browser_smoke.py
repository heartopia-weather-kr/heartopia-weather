"""Local browser smoke test. Does not run the collector or touch forecast files."""
import contextlib
import functools
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT)))
threading.Thread(target=server.serve_forever, daemon=True).start()
url = f'http://127.0.0.1:{server.server_port}'
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel='msedge')
        context = browser.new_context(viewport={'width': 1536, 'height': 1000}, timezone_id='America/Los_Angeles')
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.clock.install(time=__import__('datetime').datetime.fromisoformat('2026-11-08T08:00:00+00:00'))
        page.goto(url)
        page.locator('.day-card').last.wait_for()
        page.locator('#notice-close').click()
        assert page.locator('#refresh').count()==0
        def assert_no_drag(selector):
            node=page.locator(selector).first
            assert node.evaluate('(node)=>getComputedStyle(node).userSelect')=='none',selector
            box=node.bounding_box()
            page.evaluate('getSelection().removeAllRanges()')
            page.mouse.move(box['x']+3,box['y']+box['height']/2)
            page.mouse.down()
            page.mouse.move(box['x']+box['width']-3,box['y']+box['height']/2,steps=10)
            page.mouse.up()
            assert page.evaluate('getSelection().toString()')=='',selector
        assert page.locator('.brand').evaluate('(node)=>getComputedStyle(node).userSelect')=='none'
        assert page.locator('.weather-icon image.icon-art').first.get_attribute('draggable')=='false'
        assert page.locator('.weather-icon').first.evaluate('(node)=>getComputedStyle(node).webkitUserDrag')=='none'
        heading=page.locator('#today-title').bounding_box()
        page.evaluate('getSelection().removeAllRanges()')
        page.mouse.move(heading['x']+3,heading['y']+heading['height']/2)
        page.mouse.down()
        page.mouse.move(heading['x']+heading['width']-3,heading['y']+heading['height']/2,steps=10)
        page.mouse.up()
        assert page.evaluate('getSelection().toString()')==''
        assert page.locator('.day-card').count() == 7
        assert page.locator('#periods .weather-row').count() == 24
        assert not page.locator('#forecast-dialog').is_visible()
        assert page.locator('main .hourly').count() == 0
        assert page.locator('#warning').count() == 0
        assert page.locator('#status').inner_text() == '마지막 업데이트: 2026-11-08 16:50 (KST)'
        assert page.locator('.icon-catalog').count() == 0
        assert page.evaluate('WeatherCore.catalog.length') == 21
        assert page.locator('#today-date').count() == 0
        assert page.locator('#clock-now, .clock-caption').count() == 0
        assert page.locator('#week-title svg.line-icon').count() == 1
        assert page.locator('.upcoming svg').count() == 1
        assert page.locator('.hero-transition #current-change').inner_text() == '⭕ 변경'
        assert page.locator('#current-change').get_attribute('class').endswith('is-changed')
        assert page.evaluate("async () => { const image = new Image(); image.src = 'assets/hero-landscape.png'; await image.decode(); return image.naturalWidth > 0; }")
        assert page.locator('.clock-hour').count() == 12
        assert page.locator('#clock-title button').count() == 0
        assert page.locator('#today-changes').inner_text() == '8회'
        main_clock = page.locator('#clock-center').inner_text()
        main_today = page.locator('#current-weather').inner_text()
        calculator_date = page.locator('#calculator-date').input_value()
        forecast = json.loads((ROOT/'weather.json').read_text(encoding='utf-8'))
        for index, day in enumerate(forecast['days']):
            page.locator('.day-card').nth(index).click()
            assert page.locator('#forecast-dialog').is_visible()
            if index==0:
                for selector in ['#hourly-title','#selected-date','#day-summary','.period-heading h3']:
                    assert_no_drag(selector)
                assert page.locator('#forecast-dialog .weather-icon').first.evaluate('(node)=>getComputedStyle(node).webkitUserDrag')=='none'
            summary=' '.join(page.locator('#day-summary').inner_text().split())
            assert f"변경 {day['changes']}회" in summary
            assert f"변동률 {day['changeRate']:g}%" in summary
            assert page.locator('#day-summary strong').all_text_contents() == [f"{day['changes']}회", f"{day['changeRate']:g}%"]
            assert page.locator('#day-summary').get_attribute('class').endswith('level-low' if day['changeRate']<=25 else 'level-normal' if day['changeRate']<=50 else 'level-high')
            assert page.locator('#periods .period:visible').count() == 4
            assert page.locator('#view-vertical, #view-slider, #period-nav, #forecast-dialog .rule-caption').count() == 0
            assert page.locator('#periods .row-time').all_text_contents() == [row['time'] for row in day['weather']]
            assert page.locator('#periods .weather-row.special').count() == sum(row['special'] or row['weather']=='Moon Rainbow' for row in day['weather'])
            assert page.locator('#periods .mark-changed').count()==sum(row['changed'] for row in day['weather'])
            assert page.locator('#periods .mark-unchanged').count()==sum(not row['changed'] for row in day['weather'])
            assert page.locator('.period-count').all_text_contents()==[f"변경 {sum(row['changed'] for row in day['weather'][i:i+6])}회" for i in range(0,24,6)]
            assert page.evaluate("""() => {
                const badge=document.querySelector('#day-summary'), base=getComputedStyle(badge);
                return [...badge.querySelectorAll('strong')].every(n=>{
                    const css=getComputedStyle(n),ratio=parseFloat(css.fontSize)/parseFloat(base.fontSize);
                    return ratio>=1.1 && ratio<=1.15 && css.whiteSpace==='nowrap';
                }) && getComputedStyle(badge.querySelector('.badge-level')).fontSize===base.fontSize;
            }""")
            assert page.locator('#clock-center').inner_text() == main_clock
            assert page.locator('#current-weather').inner_text() == main_today
            assert page.locator('#calculator-date').input_value() == calculator_date
            page.locator('#forecast-close').click()
        page.locator('.day-card').first.click()
        page.locator('#next-date').click()
        assert '09' in page.locator('#selected-date').inner_text()
        assert page.locator('#periods .period:visible').count() == 4
        page.keyboard.press('Escape')
        assert not page.locator('#forecast-dialog').is_visible()
        page.locator('.day-card').nth(2).click()
        page.mouse.click(2, 2)
        assert not page.locator('#forecast-dialog').is_visible()
        def normalize(value):
            import re
            value=value.strip().lower()
            return 'rainbow' if re.fullmatch(r'rainbow(?:\s+\d+)?',value) else value

        def check_shifts(day_index, start):
            page.wait_for_function("document.querySelectorAll('#clock-hours .weather-icon.alpha-ready').length===12")
            day=forecast['days'][day_index]
            for hour in range(start,start+12):
                index=(hour+18)%24
                previous=day['weather'][index-1] if index else forecast['days'][day_index-1]['weather'][23] if day_index else None
                expected=previous is not None and normalize(day['weather'][index]['weather'])!=normalize(previous['weather'])
                slot=page.locator(f'.clock-hour[data-hour="{hour}"]')
                assert bool(slot.locator('.weather-shift').count()) == expected, (day_index,hour,expected)
                glow=slot.locator('.weather-icon').evaluate('(node)=>getComputedStyle(node).filter')
                assert glow=='none'
                assert bool(page.locator(f'.change-ring[data-hour="{hour}"]').count())==expected
                assert bool(page.locator(f'#clock-change-sectors path[data-hour="{hour}"]').count())==expected
                assert slot.locator('.clock-icon-wrap').evaluate('(node)=>getComputedStyle(node,"::before").content') in ['none','normal']
                assert slot.locator('.weather-icon').evaluate('(node)=>getComputedStyle(node).animationName')=='none'

        page.locator('#clock-am').click()
        assert page.locator('#clock-am').get_attribute('aria-pressed') == 'true'
        assert page.locator('.clock-time').all_text_contents() == ['12']+[str(i) for i in range(1,12)]
        assert page.locator('.clock-hour').evaluate_all('(nodes)=>nodes.map(n=>Number(n.dataset.hour))') == list(range(12))
        assert page.locator('.clock-hour button, button.clock-hour, .clock-hour[tabindex], .clock-hour[aria-pressed], .clock-hour.current, .clock-hour.active').count()==0
        before=page.locator('#clock-center').inner_text()
        page.locator('.clock-hour[data-hour="0"]').click()
        assert page.locator('#clock-center').inner_text()==before
        check_shifts(0,0)
        page.locator('#clock-pm').click()
        assert page.locator('#clock-center').inner_text()==before
        check_shifts(0,12)
        assert page.locator('.clock-hour').evaluate_all('(nodes)=>nodes.map(n=>Number(n.dataset.hour))') == list(range(12,24))
        # Actual KST center advances independently from the chosen outer period.
        page.clock.set_system_time(__import__('datetime').datetime.fromisoformat('2026-11-08T02:59:00+00:00'))
        page.clock.run_for(121000)
        assert page.locator('#clock-pm').get_attribute('aria-pressed') == 'true'
        assert page.locator('.center-time').inner_text().startswith('12:')
        page.clock.set_system_time(__import__('datetime').datetime.fromisoformat('2026-11-08T14:59:00+00:00'))
        page.clock.run_for(121000)
        assert page.locator('#clock-am').get_attribute('aria-pressed') == 'true'
        assert page.locator('.center-time').inner_text().startswith('00:')
        assert page.locator('#clock-center>strong').first.inner_text() == forecast['days'][0]['weather'][18]['name']
        check_shifts(0,0)
        page.clock.set_system_time(__import__('datetime').datetime.fromisoformat('2026-11-08T20:59:00+00:00'))
        page.clock.run_for(121000)
        assert page.locator('.center-time').inner_text().startswith('06:')
        assert page.locator('#clock-center>strong').first.inner_text() == forecast['days'][1]['weather'][0]['name']
        check_shifts(1,0)
        page.clock.set_system_time(__import__('datetime').datetime.fromisoformat('2026-11-08T10:00:00+00:00'))
        page.clock.run_for(121000)
        assert page.locator('#current-change').get_attribute('class').endswith('is-unchanged')
        page.clock.set_system_time(__import__('datetime').datetime.fromisoformat('2026-11-08T08:00:00+00:00'))
        page.clock.run_for(121000)
        main_height=page.locator('main').evaluate('(node)=>node.getBoundingClientRect().height')
        for target in ['.calculator-toggle small','.calculator-toggle .chevron']:
            page.locator(target).click()
            assert not page.locator('#calculator-dialog').is_visible(), target
        card=page.locator('.calculator-toggle')
        card.click(position={'x':card.bounding_box()['width']/2,'y':5})
        assert not page.locator('#calculator-dialog').is_visible()
        small=page.locator('.calculator-toggle small')
        small.click(position={'x':0,'y':small.bounding_box()['height']/2})
        assert not page.locator('#calculator-dialog').is_visible()
        assert page.locator('#calculator-toggle .calculator-title').count()==1
        page.locator('.calculator-title').click()
        assert page.locator('#calculator-dialog').is_visible()
        page.keyboard.press('Escape')
        icon=page.locator('#calculator-toggle svg').bounding_box()
        title=page.locator('.calculator-title').bounding_box()
        page.mouse.click((icon['x']+icon['width']+title['x'])/2,icon['y']+icon['height']/2)
        assert page.locator('#calculator-dialog').is_visible()
        page.keyboard.press('Escape')
        assert card.evaluate('(node)=>getComputedStyle(node).cursor')=='default'
        assert page.locator('#calculator-toggle').evaluate('(node)=>getComputedStyle(node).cursor')=='pointer'
        box=page.locator('#calculator-toggle').bounding_box()
        assert box['width']>=44 and box['height']>=44
        page.locator('#clock-pm').focus()
        page.keyboard.press('Tab')
        assert page.locator('#calculator-toggle').evaluate('(node)=>node===document.activeElement')
        page.keyboard.press('Enter')
        assert page.locator('#calculator-dialog').is_visible()
        page.keyboard.press('Escape')
        assert page.locator('#calculator-toggle').evaluate('(node)=>node===document.activeElement')
        page.keyboard.press('Space')
        assert page.locator('#calculator-dialog').is_visible()
        page.locator('#calculator-close').click()
        page.locator('#calculator-toggle').click()
        for selector in ['#calculator-title','#calculator-dialog .rule-caption']:
            assert_no_drag(selector)
        # A temporary text control verifies that modal input selection and native
        # typing/copy/paste stay enabled without adding a production input field.
        page.evaluate("""() => {
            const input=document.createElement('input');input.id='selection-probe';input.value='copy test';
            document.querySelector('#calculator-body').prepend(input);
        }""")
        probe=page.locator('#selection-probe')
        probe.focus()
        page.keyboard.press('Control+A')
        assert probe.evaluate('(node)=>node.selectionEnd-node.selectionStart')==9
        page.keyboard.press('Control+C')
        probe.fill('')
        page.keyboard.press('Control+V')
        assert probe.input_value()=='copy test'
        probe.fill('typed value')
        assert probe.input_value()=='typed value'
        probe.evaluate('(node)=>node.remove()')
        for selector in ['#calculator-date','#calculator-start','#calculator-end']:
            assert page.locator(selector).evaluate('(node)=>getComputedStyle(node).userSelect')=='text'
        page.locator('#calculator-start').select_option('23')
        page.locator('#calculator-end').select_option('2')
        page.locator('#calculator-run').click()
        assert page.locator('.result-summary').count() == 1
        assert_no_drag('.result-summary')
        page.locator('#calculator-start').select_option('5')
        page.locator('#calculator-end').select_option('6')
        page.locator('#calculator-run').click()
        assert page.locator('.form-error').count() == 1
        assert page.locator('#calculator-dialog').is_visible()
        assert page.locator('#calculator-toggle svg.calculator-icon').count()==1
        assert page.locator('main #calculator-body').count()==0
        assert page.locator('#calculator-start option').count()==24
        assert page.locator('#calculator-end option').count()==24
        page.keyboard.press('Shift+Tab')
        assert page.locator('#calculator-dialog').evaluate('(node)=>node.contains(document.activeElement)')
        assert page.locator('main').evaluate('(node)=>node.getBoundingClientRect().height')==main_height
        assert page.locator('body').evaluate('(node)=>getComputedStyle(node).overflow')=='hidden'
        page.locator('#calculator-close').click()
        assert page.locator('#calculator-toggle').evaluate('(node)=>node===document.activeElement')
        page.locator('#calculator-toggle').click()
        assert page.locator('#calculator-start').input_value()=='5'
        page.keyboard.press('Escape')
        assert not page.locator('#calculator-dialog').is_visible()
        page.locator('#calculator-toggle').click()
        page.mouse.click(2,2)
        assert not page.locator('#calculator-dialog').is_visible()
        page.locator('.day-card').first.click()
        assert page.locator('dialog[open]').count()==1
        page.keyboard.press('Escape')
        page.screenshot(path=str(Path(tempfile.gettempdir())/'heartopia-desktop.png'), full_page=True)
        for width in [1536, 390, 360, 320, 768, 1024]:
            page.set_viewport_size({'width':width, 'height':900})
            assert page.locator('#status').is_visible()
            page.wait_for_function("document.querySelectorAll('#clock-hours .weather-icon.alpha-ready').length===12")
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'Overflow at {width}'
            assert page.evaluate("""() => {
                const icons = [...document.querySelectorAll('.hero-forecast .weather-icon')].map(n => n.getBoundingClientRect());
                const badge = document.querySelector('.change-badge').getBoundingClientRect();
                const arrow = document.querySelector('.hero-transition').getBoundingClientRect();
                return icons.length === 2 && icons[0].width === icons[1].width &&
                    icons[0].right <= arrow.left && arrow.right <= icons[1].left &&
                    icons.every(icon => icon.top >= badge.bottom);
            }"""), f'Hero overlap at {width}'
            page.locator('.day-card').nth(4).click()
            assert page.evaluate("""() => {
                const dialog=document.querySelector('#forecast-dialog'), box=dialog.getBoundingClientRect();
                return box.left>=0 && box.right<=innerWidth && box.top>=0 && box.bottom<=innerHeight && dialog.scrollWidth<=dialog.clientWidth;
            }"""), f'Dialog overflow at {width}'
            columns=page.locator('#periods').evaluate('(node)=>getComputedStyle(node).gridTemplateColumns.split(" ").length')
            assert columns == (1 if width<=760 else 2 if width<=1150 else 4), (width,columns)
            assert page.evaluate("""() => {
                const clock=document.querySelector('.clock-card').getBoundingClientRect();
                const slots=[...document.querySelectorAll('.clock-hour .weather-icon, #clock-hours>.clock-time')].map(n=>n.getBoundingClientRect());
                return slots.every(r=>r.left>=clock.left && r.right<=clock.right && r.top>=clock.top && r.bottom<=clock.bottom)
                    && slots.every((a,i)=>slots.slice(i+1).every(b=>a.right<=b.left || b.right<=a.left || a.bottom<=b.top || b.bottom<=a.top));
            }"""), f'Clock slot overlap at {width}'
            assert page.evaluate((ROOT/'tests/clock_geometry.js').read_text())==[],width
            if width == 390:
                page.screenshot(path=str(Path(tempfile.gettempdir())/'heartopia-detail-mobile.png'), full_page=True)
            page.keyboard.press('Escape')
            page.locator('#calculator-toggle').click()
            assert page.evaluate("""() => {
                const dialog=document.querySelector('#calculator-dialog'),box=dialog.getBoundingClientRect();
                return box.left>=0 && box.right<=innerWidth && box.top>=0 && box.bottom<=innerHeight && dialog.scrollWidth<=dialog.clientWidth;
            }"""), f'Calculator overflow at {width}'
            if width==390:
                page.screenshot(path=str(Path(tempfile.gettempdir())/'heartopia-calculator-mobile.png'), full_page=True)
            page.keyboard.press('Escape')
            assert page.locator('#calculator-toggle').evaluate('(node)=>node===document.activeElement')
        page.set_viewport_size({'width':390, 'height':844})
        page.screenshot(path=str(Path(tempfile.gettempdir())/'heartopia-mobile.png'), full_page=True)
        page.locator('#notice-open').click()
        page.locator('#notice-hide').click()
        page.reload()
        page.locator('.day-card').last.wait_for()
        assert not page.locator('#notice-dialog').is_visible()
        # Stale forecasts remain browsable, but are never labeled today's forecast.
        page.clock.set_system_time(__import__('datetime').datetime.fromisoformat('2026-11-20T08:00:00+00:00'))
        page.clock.run_for(15*60000+500)
        page.wait_for_function("document.querySelector('#current-weather').textContent.includes('현재 날짜의 예보가 없어요')")
        assert page.locator('#status').inner_text() == '마지막 업데이트: 2026-11-08 16:50 (KST)'
        assert page.locator('#warning').count() == 0
        assert '현재 날짜의 예보가 없어요' in page.locator('#current-weather').inner_text()
        # A fresh visit with a failed request must contain no fake forecasts.
        failed = context.new_page()
        failed.clock.install(time=__import__('datetime').datetime.fromisoformat('2026-11-08T08:00:00+00:00'))
        failed.on('pageerror', lambda error: errors.append(str(error)))
        failed.route('**/weather.json?*', lambda route: route.fulfill(status=503, body='unavailable'))
        failed.goto(url)
        failed.locator('#load-error').wait_for(state='visible')
        assert failed.locator('.day-card').count() == 0
        assert failed.locator('#periods .weather-row').count() == 0
        assert failed.locator('#calculator-run').is_disabled()
        if failed.locator('#notice-dialog').is_visible():
            failed.locator('#notice-close').click()
        failed.unroute('**/weather.json?*')
        failed.clock.run_for(15*60000+500)
        failed.locator('.day-card').last.wait_for()
        assert failed.locator('#calculator-run').is_enabled()
        # Dense, test-only alternating forecast: all twelve outer icons glow.
        # Fixture stays in memory; never write or change the real weather.json.
        dense=json.loads(json.dumps(forecast))
        for day in dense['days']:
            for i,row in enumerate(day['weather']):
                row['weather']='Sunny' if i%2 else 'Cloudy'
                row['changed']=True
            day['changes']=24
            day['changeRate']=100
        dense_page=context.new_page()
        dense_page.on('pageerror',lambda error:errors.append(str(error)))
        dense_page.clock.install(time=__import__('datetime').datetime.fromisoformat('2026-11-08T08:00:00+00:00'))
        dense_page.route('**/weather.json?*',lambda route:route.fulfill(json=dense))
        dense_page.goto(url)
        dense_page.locator('.day-card').last.wait_for()
        if dense_page.locator('#notice-dialog').is_visible():
            dense_page.locator('#notice-close').click()
        page_glow="document.querySelectorAll('#clock-hours .weather-icon.alpha-ready').length===12"
        dense_page.wait_for_function(page_glow)
        assert dense_page.locator('.weather-shift').count()==12
        assert dense_page.locator('.change-ring').count()==12
        for width in [1536,768,390,320]:
            dense_page.set_viewport_size({'width':width,'height':900})
            for theme in ['light','midnight']:
                dense_page.evaluate('(theme)=>WeatherTheme.set(theme)',theme)
                assert dense_page.evaluate((ROOT/'tests/clock_geometry.js').read_text())==[],(theme,width)
                if width in [1536,390]:
                    dense_page.screenshot(path=str(Path(tempfile.gettempdir())/f'heartopia-rings-{theme}-{width}.png'),full_page=True)
            assert dense_page.evaluate("""() => {
                const rects=[...document.querySelectorAll('#clock-hours .weather-icon')].map(n=>n.getBoundingClientRect());
                // At most 3 CSS pixels of quiet outer falloff per icon.
                return rects.every((a,i)=>rects.slice(i+1).every(b=>a.right+6<=b.left || b.right+6<=a.left || a.bottom+6<=b.top || b.bottom+6<=a.top));
            }"""),f'Consecutive glow overlap at {width}'
        assert not errors, errors
        browser.close()
        print('PASS: actual-change rings/sector orbit, shared centers, 12 consecutive changes in both themes, 320-1536px no overlaps, no refresh button, automatic retry/15-minute fetch, KST boundaries, existing modal/calculator behavior, no JS errors')
        print('Screenshots:', Path(tempfile.gettempdir())/'heartopia-desktop.png', Path(tempfile.gettempdir())/'heartopia-mobile.png')
finally:
    server.shutdown()
    server.server_close()
