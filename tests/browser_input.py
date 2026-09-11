"""Real browser events -> HTTP -> fixture. Not real macOS event acceptance."""
import json
import os
from pathlib import Path
import sys
import threading
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright, expect
from continuity.core import Problem
from continuity.fixture import FixtureAdapter
from continuity.server import make_server

root = Path(__file__).resolve().parents[1]
adapter = FixtureAdapter()
server = make_server(adapter, root/'web', port=0)
origin = f'http://127.0.0.1:{server.server_address[1]}'
server.origins = {origin}
server.authorities = {origin.split('://')[1]}
threading.Thread(target=server.serve_forever, daemon=True).start()


def ready(page):
    expect(page.locator('#frame')).to_be_enabled()


def attach(page, control=True):
    page.goto(origin+'/#token='+server.engine.token)
    expect(page.locator('#pair')).to_be_hidden()
    page.select_option('#window','101')
    expect(page.locator('#target')).to_contain_text('101')
    if control:
        page.click('#claim')
        expect(page.locator('#linkState')).to_contain_text('有控制权')
    page.click('#frame')
    expect(page.locator('#canvas')).to_be_visible()
    ready(page)


def observe_menu(page):
    # Attach on the canvas itself: the handler intentionally stops propagation.
    page.evaluate("""() => document.querySelector('#canvas').addEventListener('contextmenu', event => {
      document.body.dataset.menuPrevented=String(event.defaultPrevented);
    })""")


try:
    with sync_playwright() as p:
        name = os.environ.get('WC_BROWSER', 'chromium')
        options = {'headless': True}
        if os.environ.get('CHROMIUM_PATH') and name == 'chromium':
            options['executable_path'] = os.environ['CHROMIUM_PATH']
        browser = getattr(p,name).launch(**options)
        context = browser.new_context(viewport={'width':1000,'height':800})
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        attach(page, control=False)
        observe_menu(page)
        canvas=page.locator('#canvas')
        count=adapter.clicks
        canvas.click(button='right',position={'x':80,'y':80})
        expect(page.locator('body')).to_have_attribute('data-menu-prevented','false')
        assert adapter.clicks == count, 'Read-only must not deliver right click'
        # The WebKit GTK native menu is outside the DOM; page Escape does not
        # reliably dismiss it. Close this read-only context instead of changing
        # app policy or letting the native menu swallow the next test's click.
        context.close()
        context = browser.new_context(viewport={'width':1000,'height':800})
        page = context.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        attach(page)
        observe_menu(page)
        canvas=page.locator('#canvas')
        page.check('#clickMode')
        with page.expect_response(lambda r:r.url.endswith('/api/action')) as response:
            canvas.click(position={'x':120,'y':120})
        assert response.value.ok
        ready(page)
        assert adapter.last_input['button']=='left'
        assert adapter.last_input['input_route']=='background'
        assert adapter.clicks==count+1
        assert 0 <= adapter.last_input['x'] <= 1
        with page.expect_response(lambda r:r.url.endswith('/api/action')) as response:
            canvas.click(button='right',position={'x':150,'y':150})
        assert response.value.ok
        ready(page)
        expect(page.locator('body')).to_have_attribute('data-menu-prevented','true')
        assert adapter.last_input['button']=='right'
        assert adapter.clicks==count+2, 'One right click must not become left+right'
        expect(page.locator('#inputStatus')).to_contain_text('合成测试')
        original=adapter.visual_action
        def reject(*args):
            raise Problem('background_unsupported','测试：后台不支持，未执行',409)
        adapter.visual_action=reject
        with page.expect_response(lambda r:r.url.endswith('/api/action')) as response:
            canvas.click(position={'x':150,'y':150})
        assert response.value.status==409
        ready(page)
        expect(page.locator('#inputStatus')).to_contain_text('后台不支持')
        expect(page.locator('#feedback')).to_be_visible()
        assert adapter.clicks==count+2
        adapter.visual_action=original
        page.click('#release')
        ready(page)
        context.close()
        context=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
        page=context.new_page()
        page.on('pageerror',lambda e:errors.append(str(e)))
        attach(page)
        page.check('#clickMode')
        page.select_option('#pointerButton','right')
        with page.expect_response(lambda r:r.url.endswith('/api/action')) as response:
            page.locator('#canvas').tap(position={'x':60,'y':60})
        assert response.value.ok
        ready(page)
        assert adapter.last_input['button']=='right'
        assert adapter.clicks==count+3
        assert not errors,errors
        out=root/'test-results';out.mkdir(exist_ok=True)
        report={'browser':name,'fixture_only':True,'left_click':True,'right_click':True,
                'one_event_per_click':True,'browser_menu_suppressed_only_when_enabled':True,
                'mobile_right_tap':True,'visible_error':True,'js_errors':errors}
        (out/f'input-{name}.json').write_text(json.dumps(report,indent=2))
        page.screenshot(path=str(out/f'input-{name}.png'),full_page=True)
        print(json.dumps(report,indent=2))
        context.close();browser.close()
finally:
    server.shutdown();server.server_close()
