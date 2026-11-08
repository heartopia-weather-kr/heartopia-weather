"""Effects integration and development preview; fixture data stays in memory."""
import functools
import json
import tempfile
import threading
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
url=f'http://127.0.0.1:{server.server_port}'
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,channel='msedge')
        context=browser.new_context(viewport={'width':1536,'height':1000},timezone_id='America/Los_Angeles')
        page=context.new_page();errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.clock.install(time=datetime.fromisoformat('2026-11-08T08:00:00+00:00'))
        original=json.loads((ROOT/'weather.json').read_text(encoding='utf-8'));fixture=original
        page.route('**/weather.json?*',lambda route:route.fulfill(json=fixture))
        page.goto(url);page.locator('.day-card').last.wait_for();page.locator('#notice-close').click()
        assert page.locator('.hero-atmosphere').get_attribute('data-effect')=='sunny' # next hour is Clear
        assert page.locator('.hero .icon-art').first.get_attribute('href')=='design-reference/icons-light.png'
        page.evaluate('window.firstEffect=document.querySelector(".atmosphere-plane")')
        page.clock.run_for(121000)
        assert page.evaluate('window.firstEffect===document.querySelector(".atmosphere-plane")')
        page.clock.run_for(15*60000)
        assert page.evaluate('window.firstEffect===document.querySelector(".atmosphere-plane")')
        page.clock.set_system_time(datetime.fromisoformat('2026-11-08T08:59:00+00:00'));page.clock.run_for(121000)
        assert page.locator('.hero-atmosphere').get_attribute('data-effect')=='clear'
        fixture=json.loads(json.dumps(original))
        for row in fixture['days'][0]['weather']:row['weather']='Moon Rain'
        page.clock.run_for(15*60000+2000)
        page.wait_for_function("document.querySelector('.hero-atmosphere').dataset.effect==='moon-rain'")
        page.evaluate('window.rainEffect=document.querySelector(".atmosphere-plane:not(.is-leaving)")')
        for theme in ['midnight','light']:
            page.evaluate('(theme)=>WeatherTheme.set(theme)',theme)
            assert page.evaluate('window.rainEffect===document.querySelector(".atmosphere-plane:not(.is-leaving)")')
        for width in [1536,1024,768,390,320]:
            page.set_viewport_size({'width':width,'height':900})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert page.evaluate("""() => {
                const host=document.querySelector('.hero'),root=host.querySelector('.hero-atmosphere'),h=host.getBoundingClientRect(),r=root.getBoundingClientRect();
                const css=getComputedStyle(root);
                return Math.abs(r.width-host.clientWidth)<1 && Math.abs(r.height-host.clientHeight)<1 && css.pointerEvents==='none' && css.overflow==='hidden' && root.getAttribute('aria-hidden')==='true';
            }""")
            assert page.evaluate((ROOT/'tests/clock_geometry.js').read_text())==[]
        page.set_viewport_size({'width':390,'height':500})
        page.evaluate('window.scrollTo(0,document.documentElement.scrollHeight)')
        page.wait_for_function("document.querySelector('.hero-atmosphere').dataset.paused==='true'")
        assert page.locator('.atmosphere-particle').first.evaluate('(node)=>getComputedStyle(node).animationPlayState')=='paused'
        page.locator('.hero').scroll_into_view_if_needed()
        page.wait_for_function("document.querySelector('.hero-atmosphere').dataset.paused==='false'")
        page.evaluate("Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'))")
        assert page.locator('.hero-atmosphere').get_attribute('data-paused')=='true'
        page.evaluate("delete document.hidden;document.dispatchEvent(new Event('visibilitychange'))")
        assert page.locator('.hero-atmosphere').get_attribute('data-paused')=='false'
        page.emulate_media(reduced_motion='reduce')
        page.wait_for_function("document.querySelector('.hero-atmosphere').children.length===0")
        assert page.locator('.hero-atmosphere').evaluate('(node)=>getComputedStyle(node).display')=='none'
        page.emulate_media(reduced_motion='no-preference')
        page.wait_for_function("document.querySelector('.hero-atmosphere').children.length===1")
        fixture=original
        page.clock.set_system_time(datetime.fromisoformat('2026-11-08T20:59:00+00:00'));page.clock.run_for(121000)
        assert page.locator('.hero-atmosphere').get_attribute('data-effect')=='sunny'
        fixture=json.loads(json.dumps(original))
        for row in fixture['days'][1]['weather']:row['weather']='Unregistered weather'
        page.clock.run_for(15*60000+2000)
        page.wait_for_function("document.querySelector('.hero-atmosphere').dataset.effect==='none'")
        page.clock.run_for(2000)
        page.wait_for_function("document.querySelector('.hero-atmosphere').children.length===0")
        page.clock.set_system_time(datetime.fromisoformat('2026-11-20T08:00:00+00:00'));page.clock.run_for(121000)
        assert page.locator('.hero-atmosphere').get_attribute('data-effect')=='none'
        assert page.locator('.hero-atmosphere').count()==1
        preview=context.new_page();preview.on('pageerror',lambda error:errors.append(str(error)))
        preview.goto(url+'/tests/effects-preview.html')
        assert preview.locator('.hero-atmosphere').count()==21
        assert len(set(preview.locator('.hero-atmosphere').evaluate_all('(nodes)=>nodes.map(n=>n.dataset.effect)')))==21
        assert preview.locator('.hero-atmosphere .atmosphere-particle').count()<=200
        storage=preview.evaluate('JSON.stringify({...localStorage})')
        for index,item in enumerate(preview.evaluate('WeatherCore.catalog.map(row=>[row[0],row[1]])')):
            preview.locator('.preview-grid .hero').nth(index).click()
            assert preview.locator('#preview-detail').is_visible()
            expected=preview.evaluate('(key)=>WeatherAtmosphere.select(key).id',item[0])
            assert preview.locator('#preview-detail-card .hero-atmosphere').get_attribute('data-effect')==expected
            assert preview.locator('#preview-detail-weather .weather-icon').count()==2
            assert preview.locator('.preview-grid').get_attribute('data-suspended')=='true'
            preview.keyboard.press('Escape')
            preview.locator('#preview-detail-card .hero-atmosphere').wait_for(state='detached')
            assert preview.locator('.preview-grid .hero').nth(index).evaluate('(node)=>node===document.activeElement')
        preview.locator('.preview-grid .hero[data-weather="Heavy Rain"]').click()
        preview.locator('#preview-detail-theme').click()
        assert preview.evaluate('document.documentElement.dataset.theme')=='midnight'
        slider=preview.locator('#preview-detail [data-preview-strength]')
        slider.evaluate("node=>{node.value='160';node.dispatchEvent(new Event('input',{bubbles:true}))}")
        assert preview.locator('#preview-detail [data-preview-strength-value]').inner_text()=='160%'
        assert preview.evaluate('document.documentElement.style.getPropertyValue("--preview-strength")')=='1.6'
        assert page.evaluate('document.documentElement.style.getPropertyValue("--preview-strength")')==''
        assert preview.evaluate('JSON.stringify({...localStorage})')==storage
        slider.evaluate("node=>{node.value='100';node.dispatchEvent(new Event('input',{bubbles:true}))}")
        # Observe real compositor-driven falling motion, not just selected styles.
        before=preview.locator('#preview-detail .atmosphere-particle').first.evaluate('(node)=>getComputedStyle(node).transform')
        preview.wait_for_timeout(1500)
        assert preview.locator('#preview-detail .atmosphere-particle').first.evaluate('(node)=>getComputedStyle(node).transform')!=before
        for width in [1536,1024,768,390,320]:
            preview.set_viewport_size({'width':width,'height':900})
            assert preview.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert preview.locator('#preview-detail').evaluate('(node)=>{const r=node.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.top>=0&&r.bottom<=innerHeight&&node.scrollWidth<=node.clientWidth}')
        preview.set_viewport_size({'width':900,'height':700})
        preview.locator('#preview-detail-close').click()
        preview.locator('.preview-grid .hero[data-weather="Meteor Shower 3"]').click()
        observation=preview.evaluate("""async () => {
            const particles=[...document.querySelectorAll('#preview-detail .atmosphere-particle')];
            const previous=particles.map(()=>false);let appearances=0,peak=0;
            await new Promise(resolve=>{const sample=setInterval(()=>{
                particles.forEach((node,i)=>{const opacity=Number(getComputedStyle(node).opacity);peak=Math.max(peak,opacity);const active=opacity>.2;if(active&&!previous[i])appearances++;previous[i]=active;});
            },150);setTimeout(()=>{clearInterval(sample);resolve()},22000)});
            return {appearances,peak};
        }""")
        assert observation['appearances']>=2 and observation['peak']>.5,observation
        preview.screenshot(path=str(Path(tempfile.gettempdir())/'heartopia-effects-expanded.png'),full_page=True)
        preview.mouse.click(2,2)
        assert not preview.locator('#preview-detail').is_visible()
        preview.set_viewport_size({'width':1536,'height':1000})
        for theme in ['light','midnight']:
            preview.evaluate('(theme)=>document.documentElement.dataset.theme=theme',theme)
            # Freeze representative animations mid-cycle for a reproducible QA sheet.
            preview.evaluate("""document.querySelectorAll('.hero-atmosphere').forEach(n=>{
                n.dataset.paused='false';n.getAnimations({subtree:true}).forEach(a=>{
                    a.pause();const t=a.effect.getTiming(),name=a.animationName||'';
                    const phase=name.includes('meteor')?.92:name.includes('spark')?.87:.5;
                    a.currentTime=Number(t.duration)*phase+(['atmosphere-meteor','atmosphere-spark','atmosphere-aurora'].includes(name)?Number(t.delay):0);
                });
            })""")
            preview.screenshot(path=str(Path(tempfile.gettempdir())/f'heartopia-effects-{theme}.png'),full_page=True)
        preview.evaluate("for(let i=0;i<30;i++)previewControllers[0].update(i%2?'Snow':'Heavy Rain')")
        assert preview.locator('.hero-atmosphere').first.locator('.atmosphere-plane').count()<=2
        preview.evaluate('previewControllers.forEach(controller=>controller.destroy())')
        assert preview.locator('.hero-atmosphere').count()==0
        assert not errors,errors
        browser.close()
        print('PASS: 21 effects/expanded views, isolated strength control, original A durations, real rain motion + 22-second meteor observation, themes, 320-1536px, reduced motion/offscreen/hidden-tab pause, current/KST/reload, fallback and cleanup')
finally:
    server.shutdown();server.server_close()
