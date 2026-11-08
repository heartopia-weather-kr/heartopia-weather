"""Local Light/Midnight regression checks. No collector or forecast writes."""
import functools
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args):
        pass
server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
url=f'http://127.0.0.1:{server.server_port}'
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,channel='msedge')
        context=browser.new_context(viewport={'width':1536,'height':1000},timezone_id='America/Los_Angeles')
        page=context.new_page()
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.clock.install(time=datetime.fromisoformat('2026-11-08T08:00:00+00:00'))
        page.goto(url)
        page.locator('.day-card').last.wait_for()
        page.locator('#notice-close').click()
        assert page.evaluate('WeatherTheme.get()')=='light'
        page.wait_for_function("document.querySelectorAll('#clock-hours .alpha-ready').length===12")
        clock=page.locator('#clock-center').inner_text()
        geometry=page.locator('.weather-clock').bounding_box()
        assert abs(geometry['width']-442)<.1
        assert abs(geometry['width']-geometry['height'])<.1
        assert page.locator('.orbit-shift').evaluate('(node)=>parseFloat(getComputedStyle(node).strokeWidth)')==.85
        assert page.locator('.orbit-base').evaluate('(node)=>parseFloat(getComputedStyle(node).strokeWidth)')==.5
        light_glow=page.locator('.change-ring').first.evaluate('(node)=>getComputedStyle(node).filter')
        page.locator('[data-theme-choice="midnight"]').click()
        assert page.evaluate('localStorage.getItem("heartopiaTheme")')=='midnight'
        assert page.locator('[data-theme-choice="midnight"]').get_attribute('aria-pressed')=='true'
        assert page.locator('#clock-center').inner_text()==clock
        assert page.locator('.weather-clock').bounding_box()==geometry
        assert page.locator('.change-ring').first.evaluate('(node)=>getComputedStyle(node).filter')!=light_glow
        page.locator('#clock-am').click()
        assert page.locator('#clock-center').inner_text()==clock
        page.locator('#clock-pm').click()
        assert page.locator('#clock-center').inner_text()==clock
        # The original Light layer remains in place; Midnight uses extracted art.
        assert page.locator('.weather-icon image.icon-art').first.get_attribute('href')=='design-reference/icons-light.png'
        assert page.locator('.hero .weather-icon').first.evaluate('(node)=>getComputedStyle(node).mixBlendMode')=='normal'
        page.wait_for_function("[...document.querySelectorAll('.weather-icon')].every(n=>n.classList.contains('alpha-ready'))")
        assert page.locator('.hero .icon-art').first.evaluate('(node)=>getComputedStyle(node).display')=='none'
        assert page.locator('.hero .icon-midnight').first.evaluate('(node)=>getComputedStyle(node).display')=='block'
        assert page.locator('.hero .icon-midnight').first.get_attribute('href').startswith('assets/midnight-icons/')

        # Theme restoration is recorded in the head, before any visible body.
        html=(ROOT/'index.html').read_text(encoding='utf-8').replace('</head>','<script>window.headTheme=document.documentElement.dataset.theme;</script></head>')
        page.route(url+'/',lambda route:route.fulfill(body=html,content_type='text/html'))
        page.reload()
        page.locator('.day-card').last.wait_for()
        if page.locator('#notice-dialog').is_visible():
            page.locator('#notice-close').click()
        assert page.evaluate('window.headTheme')=='midnight'
        page.unroute(url+'/')

        # Changing theme changes attributes only; it must preserve live modal state.
        page.locator('#calculator-toggle').click()
        page.locator('#calculator-date').select_option('2')
        page.locator('#calculator-start').select_option('19')
        page.locator('#calculator-end').select_option('21')
        page.locator('#calculator-run').click()
        result=page.locator('#calculator-result').inner_text()
        assert page.locator('.result-summary').is_visible()
        for theme in ['light','midnight']:
            page.evaluate('(theme)=>WeatherTheme.set(theme)',theme)
            assert page.locator('.hero .icon-midnight').first.evaluate('(node)=>getComputedStyle(node).display')==('block' if theme=='midnight' else 'none')
            assert page.locator('#calculator-dialog').is_visible()
            assert page.locator('#calculator-date').input_value()=='2'
            assert page.locator('#calculator-start').input_value()=='19'
            assert page.locator('#calculator-end').input_value()=='21'
            assert page.locator('#calculator-result').inner_text()==result
            assert page.locator('#clock-center').inner_text()==clock
        page.locator('#calculator-close').click()
        assert page.locator('#calculator-toggle').evaluate('(node)=>node===document.activeElement')

        # Contrast checks for the explicit, solid text/surface pairs in Midnight.
        page.locator('.day-card').nth(4).click()
        assert page.evaluate(r"""() => {
            const rgb=s=>s.match(/[\d.]+/g).slice(0,3).map(Number);
            const luminance=c=>c.map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
            return ['.mark-changed','.mark-unchanged','.period-count','.summary-badge','#status'].every(selector=>{
                const css=getComputedStyle(document.querySelector(selector)),a=luminance(rgb(css.color)),b=luminance(rgb(css.backgroundColor));
                return (Math.max(a,b)+.05)/(Math.min(a,b)+.05)>=4.5;
            });
        }""")
        selected=page.locator('#selected-date').inner_text()
        page.evaluate("WeatherTheme.set('light')")
        assert page.locator('#forecast-dialog').is_visible()
        assert page.locator('#selected-date').inner_text()==selected
        page.keyboard.press('Escape')

        for theme in ['light','midnight']:
            page.evaluate('(theme)=>WeatherTheme.set(theme)',theme)
            for width in [1536,1024,768,390,360,320]:
                page.set_viewport_size({'width':width,'height':900})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(theme,width)
                assert page.evaluate((ROOT/'tests/clock_geometry.js').read_text())==[],(theme,width)
                assert page.evaluate("""() => {
                    const clock=document.querySelector('.weather-clock').getBoundingClientRect();
                    const labels=[...document.querySelectorAll('#clock-hours>.clock-time')];
                    return Math.abs(clock.width-clock.height)<.1 && labels.filter(label=>{
                        const box=label.getBoundingClientRect();
                        return Math.hypot((box.left+box.width/2-clock.left)/clock.width*100-50,(box.top+box.height/2-clock.top)/clock.height*100-50)<52.49;
                    }).length>=8;
                }"""),(theme,width,'label spacing')
                assert page.locator('#clock-center').inner_text()==clock
                assert 'update-shutter.png' in page.locator('.upcoming').evaluate('(node)=>getComputedStyle(node).backgroundImage')
                assert page.evaluate("""() => {
                    const clock=document.querySelector('.clock-card').getBoundingClientRect();
                    const rects=[...document.querySelectorAll('#clock-hours .weather-icon,#clock-hours .clock-time')].map(n=>n.getBoundingClientRect());
                    return rects.every(a=>a.left>=clock.left&&a.right<=clock.right&&a.top>=clock.top&&a.bottom<=clock.bottom)&&
                        rects.every((a,i)=>rects.slice(i+1).every(b=>a.right<=b.left||b.right<=a.left||a.bottom<=b.top||b.bottom<=a.top));
                }"""),(theme,width,'clock overflow',page.evaluate("""()=>{const nodes=[...document.querySelectorAll('#clock-hours .weather-icon,#clock-hours .clock-time')];return nodes.flatMap((a,i)=>nodes.slice(i+1).filter(b=>{const x=a.getBoundingClientRect(),y=b.getBoundingClientRect();return !(x.right<=y.left||y.right<=x.left||x.bottom<=y.top||y.bottom<=x.top)}).map(b=>({a:a.outerHTML.slice(0,160),b:b.outerHTML.slice(0,160),ra:a.getBoundingClientRect().toJSON(),rb:b.getBoundingClientRect().toJSON()})))}"""))
                for opener,dialog,close in [('.day-card','#forecast-dialog','#forecast-close'),('#calculator-toggle','#calculator-dialog','#calculator-close')]:
                    page.locator(opener).first.click()
                    assert page.locator(dialog).evaluate('(node)=>{const b=node.getBoundingClientRect();return b.left>=0&&b.right<=innerWidth&&b.top>=0&&b.bottom<=innerHeight&&node.scrollWidth<=node.clientWidth}'),(theme,width,dialog)
                    page.locator(close).click()
                if width in [1536,1024,390]:
                    page.screenshot(path=str(Path(tempfile.gettempdir())/f'heartopia-{theme}-{width}.png'),full_page=True)
            page.locator('#notice-open').click()
            assert page.locator('#notice-dialog').is_visible()
            page.keyboard.press('Escape')
        page.evaluate("WeatherTheme.set('midnight')")
        page.locator('.day-card').nth(4).click()
        page.screenshot(path=str(Path(tempfile.gettempdir())/'heartopia-midnight-detail.png'),full_page=True)
        page.keyboard.press('Escape')
        page.locator('#calculator-toggle').click()
        page.screenshot(path=str(Path(tempfile.gettempdir())/'heartopia-midnight-calculator.png'),full_page=True)
        page.keyboard.press('Escape')
        # Test all 21 keys through the shared production renderer, using an
        # in-memory fixture only; no changes to the real forecast file.
        import json
        fixture=json.loads((ROOT/'weather.json').read_text(encoding='utf-8'))
        keys=list(json.loads((ROOT/'assets/midnight-icons/manifest.json').read_text()))
        for day in fixture['days']:
            for i,row in enumerate(day['weather']):
                row['weather']=keys[i%21];row['changed']=True
            day['changes']=24;day['changeRate']=100
        page.route('**/weather.json?*',lambda route:route.fulfill(json=fixture))
        page.clock.run_for(15*60000+500)
        page.wait_for_function("document.querySelector('#today-changes').textContent==='24회'")
        page.locator('.day-card').first.click()
        shown=page.locator('#periods .weather-icon').evaluate_all("nodes=>nodes.map(n=>({key:n.dataset.weatherKey,file:n.querySelector('.icon-midnight').getAttribute('href'),display:getComputedStyle(n.querySelector('.icon-midnight')).display}))")
        assert len(set(row['key'] for row in shown))==21
        for row in shown:
            expected=json.loads((ROOT/'assets/midnight-icons/manifest.json').read_text())[row['key']]['file']
            assert row['file']=='assets/midnight-icons/'+expected
            assert row['display']=='block'
        for path in ['.hero .icon-midnight','.week .icon-midnight','#clock-hours .icon-midnight','#periods .icon-midnight']:
            assert page.locator(path).first.evaluate('(node)=>getComputedStyle(node).display')=='block'
        page.evaluate("WeatherTheme.set('light')")
        assert page.locator('#forecast-dialog').is_visible()
        assert page.locator('#periods .icon-midnight').first.evaluate('(node)=>getComputedStyle(node).display')=='none'
        assert page.locator('#periods .icon-art').first.evaluate('(node)=>getComputedStyle(node).display')!='none'
        assert not errors,errors
        browser.close()
        print('PASS: Light/Midnight restore, 21 extracted neon mappings in every region, CSS-only icon swap, shutter background, contrast >=4.5, KST/AM-PM/glow, modal/input/result preservation, both themes at 320/360/390/768/1024/1536px, no JS errors')
finally:
    server.shutdown()
    server.server_close()
