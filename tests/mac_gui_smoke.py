"""Launch the actual Cocoa host window; no permission prompts or service start."""
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import AppKit
from PyObjCTools import AppHelper
from continuity.launcher import native_gui
from continuity.permissions import PERMISSIONS

result = {}

def check_window():
    try:
        windows = [w for w in AppKit.NSApplication.sharedApplication().windows()
                   if str(w.title()).startswith('Work Continuity')]
        assert len(windows) == 1, 'Expected one native Host window'
        window = windows[0]
        assert window.isVisible(), 'Host window must be visible'
        assert len(window.contentView().subviews()) >= 12, 'Host controls not constructed'
        buttons = {}
        for view in window.contentView().subviews():
            if isinstance(view, AppKit.NSButton):
                selector = view.action()
                selector = selector.decode() if isinstance(selector, bytes) else str(selector)
                buttons[selector] = view
        for spec in PERMISSIONS:
            assert str(buttons[spec.request_selector].title()) == '请求权限'
            assert str(buttons[spec.settings_selector].title()) == '打开' + spec.title + '设置'
            assert buttons[spec.request_selector].target() == buttons[spec.settings_selector].target()
        assert 'permissions:' not in buttons, 'Old combined prompt must not exist'
        result['separate_permission_buttons'] = True
        result['native_window_constructed'] = True
        result['visible_controls'] = len(window.contentView().subviews())
    except Exception as error:
        result['error'] = repr(error)
    finally:
        # NSApplicationMain does not return; validate before exiting this test process.
        print(json.dumps(result), flush=True)
        print('Scope: Cocoa UI construction only, not permissions/capture/input.', flush=True)
        os._exit(0 if result.get('native_window_constructed') else 1)

AppHelper.callLater(1.0, check_window)
native_gui()
