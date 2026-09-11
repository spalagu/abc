"""Prompt/route regression tests without requesting any real privileges."""
import ast
from pathlib import Path
import unittest
from unittest.mock import Mock
from continuity.permissions import (ACCESSIBILITY, SCREEN_RECORDING, PERMISSIONS,
                                    request_permission, permission_hint, runtime_identity)


class PermissionTests(unittest.TestCase):
    def setUp(self):
        self.ax, self.quartz = Mock(), Mock()
        self.ax.kAXTrustedCheckOptionPrompt = 'prompt'

    def test_accessibility_request_never_requests_screen_or_opens_settings(self):
        self.ax.AXIsProcessTrustedWithOptions.return_value = False
        self.assertFalse(request_permission('accessibility', self.ax, self.quartz))
        self.ax.AXIsProcessTrustedWithOptions.assert_called_once_with({'prompt': True})
        self.assertEqual(self.quartz.mock_calls, [])
        self.assertEqual(len(self.ax.mock_calls), 1)

    def test_screen_request_never_requests_accessibility(self):
        self.quartz.CGRequestScreenCaptureAccess.return_value = True
        self.assertTrue(request_permission('screen_recording', self.ax, self.quartz))
        self.quartz.CGRequestScreenCaptureAccess.assert_called_once_with()
        self.assertEqual(self.ax.mock_calls, [])

    def test_denial_is_not_reported_as_grant(self):
        self.quartz.CGRequestScreenCaptureAccess.return_value = False
        self.assertFalse(request_permission('screen_recording', self.ax, self.quartz))

    def test_request_failure_does_not_fall_through_to_other_prompt(self):
        self.ax.AXIsProcessTrustedWithOptions.side_effect = RuntimeError('test')
        with self.assertRaises(RuntimeError):
            request_permission('accessibility', self.ax, self.quartz)
        self.assertEqual(self.quartz.mock_calls, [])

    def test_unknown_permission_has_no_side_effect(self):
        with self.assertRaises(ValueError):
            request_permission('All', self.ax, self.quartz)
        self.assertEqual(self.ax.mock_calls + self.quartz.mock_calls, [])

    def test_distinct_settings_urls_and_button_selectors(self):
        self.assertTrue(ACCESSIBILITY.settings_url.endswith('?Privacy_Accessibility'))
        self.assertTrue(SCREEN_RECORDING.settings_url.endswith('?Privacy_ScreenCapture'))
        selectors = [s for p in PERMISSIONS for s in (p.request_selector, p.settings_selector)]
        self.assertEqual(len(set(selectors)), 4)

    def test_packaged_hint_does_not_tell_user_to_authorize_terminal(self):
        hint = permission_hint('screen_recording', packaged=True)
        self.assertIn('WorkContinuity.app', hint)
        self.assertIn('＋', hint)
        self.assertNotIn('Python', hint)
        self.assertNotIn('Terminal', hint)

    def test_source_hint_does_not_invent_an_app_identity(self):
        hint = permission_hint('accessibility', packaged=False)
        self.assertIn('源码', hint)
        self.assertIn('系统弹窗', hint)
        self.assertNotIn('WorkContinuity.app', hint)

    def test_runtime_uses_current_app_not_hardcoded_applications_path(self):
        path = '/Users/test/Downloads/Demo Copy.app/Contents/MacOS/WorkContinuity'
        data = runtime_identity(path, True, '/some/Python.framework', 'example.bundle')
        self.assertEqual(data['app_path'], '/Users/test/Downloads/Demo Copy.app')
        self.assertEqual(data['bundle_id'], 'example.bundle')

    def test_source_python_bundle_is_not_misidentified_as_our_app(self):
        data = runtime_identity('/opt/bin/python3', False, '/Python.app', 'org.python')
        self.assertEqual(data['app_path'], '')
        self.assertEqual(data['reveal_path'], '/opt/bin/python3')

    def test_no_bundle_does_not_guess_an_install_location(self):
        data = runtime_identity('/tmp/WorkContinuity', True)
        self.assertEqual(data['app_path'], '')
        self.assertEqual(data['reveal_path'], '/tmp/WorkContinuity')

    def test_native_button_handlers_route_to_matching_permission(self):
        # Check the actual Host methods, not only a separate routing dictionary.
        source = Path(__file__).resolve().parents[1]/'continuity/launcher.py'
        nodes = {n.name: n for n in ast.walk(ast.parse(source.read_text())) if isinstance(n, ast.FunctionDef)}
        for name, method, key in [
            ('requestAccessibility_', 'requestPermission_', 'accessibility'),
            ('requestScreenRecording_', 'requestPermission_', 'screen_recording'),
            ('openAccessibility_', 'openPermissionSettings_', 'accessibility'),
            ('openScreenRecording_', 'openPermissionSettings_', 'screen_recording')]:
            with self.subTest(handler=name):
                call = nodes[name].body[0].value
                self.assertEqual(call.func.attr, method)
                self.assertEqual(call.args[0].value, key)
        self.assertNotIn('permissions_', nodes)
        self.assertNotIn('settings_', nodes)
