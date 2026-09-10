"""Launch the actual Cocoa host window; no permission prompts or service start."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import AppKit
from PyObjCTools import AppHelper
from continuity.launcher import native_gui

result = {}

def check_window():
    try:
        windows = [w for w in AppKit.NSApplication.sharedApplication().windows()
                   if str(w.title()).startswith('Work Continuity')]
        assert len(windows) == 1, 'Expected one native Host window'
        window = windows[0]
        assert window.isVisible(), 'Host window must be visible'
        assert len(window.contentView().subviews()) >= 12, 'Host controls not constructed'
        result['native_window_constructed'] = True
        result['visible_controls'] = len(window.contentView().subviews())
    except Exception as error:
        result['error'] = repr(error)
    finally:
        AppHelper.stopEventLoop()

AppHelper.callLater(1.0, check_window)
native_gui()
print(json.dumps(result))
assert result.get('native_window_constructed'), result
print('Native Cocoa UI launch passed. NOT a permission/capture/input test.')
