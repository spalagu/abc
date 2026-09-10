"""Real mobile-sized Chromium client over HTTP, explicit fixture host only."""
import json
import os
from pathlib import Path
import shutil
import sys
import threading
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright, expect
from continuity.fixture import FixtureAdapter
from continuity.server import make_server

root = Path(__file__).resolve().parents[1]
server = make_server(FixtureAdapter(), root/'web', port=0)
port = server.server_address[1]
origin = f'http://127.0.0.1:{port}'
server.origins = {origin}
server.authorities = {f'127.0.0.1:{port}'}
threading.Thread(target=server.serve_forever, daemon=True).start()
errors = []
try:
    with sync_playwright() as p:
        exe = os.environ.get('CHROMIUM_PATH') or shutil.which('chromium')
        browser = p.chromium.launch(headless=True, executable_path=exe, args=['--no-sandbox'])
        context = browser.new_context(viewport={'width':390,'height':844}, device_scale_factor=1, is_mobile=True, has_touch=True)
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(origin+'/#token='+server.engine.token)
        page.wait_for_selector('#pair[hidden]', state='attached')
        page.select_option('#window','101')
        expect(page.locator('#target')).to_contain_text('101')
        page.click('#claim')
        expect(page.locator('#linkState')).to_contain_text('有控制权')
        page.click('#semantics')
        page.wait_for_selector('#nodes textarea')
        page.fill('#nodes textarea','Draft written from mobile view')
        page.get_by_text('写入原控件（替换全文，不提交）').click()
        expect(page.locator('#nodes textarea')).to_have_value('Draft written from mobile view')
        expect(page.locator('#frame')).to_be_enabled()
        assert server.engine.adapter.value == 'Draft written from mobile view'
        page.click('#frame')
        expect(page.locator('#frameInfo')).to_contain_text('完整基线')
        first = server.engine.budget.used
        page.click('#frame')
        expect(page.locator('#frameInfo')).to_contain_text('局部增量 · 0 块')
        static_delta = server.engine.budget.used-first
        assert 0 < static_delta < 512, static_delta
        page.reload()
        page.wait_for_selector('#pair[hidden]', state='attached')
        page.click('#semantics')
        expect(page.locator('#nodes textarea')).to_have_value('Draft written from mobile view')
        with page.expect_download() as event:
            page.click('#export')
        report = json.loads(Path(event.value.path()).read_text())
        encoded=json.dumps(report)
        assert server.engine.token not in encoded
        assert 'Draft written' not in encoded
        assert not errors, errors
        os.makedirs(root/'test-results',exist_ok=True)
        page.screenshot(path=str(root/'test-results'/'mobile-fixture.png'),full_page=True)
        print(json.dumps({'browser':'Chromium mobile viewport','adapter':'FIXTURE ONLY',
                          'semantic_write':True,'reload_continuity':True,'static_frame_body_bytes':static_delta,
                          'no_private_content_in_report':True,'js_errors':errors},indent=2))
        context.close();browser.close()
finally:
    server.shutdown();server.server_close()
