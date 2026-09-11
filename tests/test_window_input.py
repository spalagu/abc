"""Routing regression tests with fake frameworks, not evidence of native delivery."""
from types import SimpleNamespace
from unittest import TestCase, mock
from continuity.core import Window, FrameState, Problem
from continuity.window_input import WindowInput, click_button, screen_point


class RoutingTests(TestCase):
    def setUp(self):
        self.w = Window(7, 77, 'birth', 'Test', 'Target', (100, 200, 800, 600))
        self.frame = FrameState(bounds=self.w.bounds, roi=(.25, .25, .5, .5))
        self.attrs = {
            'root': {'AXFocusedWindow': 'target', 'AXFocusedUIElement': 'field'},
            'target': {'AXRole': 'AXWindow'},
            'button': {'AXParent': 'target', 'AXRole': 'AXButton'},
            'field': {'AXParent': 'target', 'AXRole': 'AXTextArea'},
            'label': {'AXParent': 'button', 'AXRole': 'AXStaticText'},
            'other': {'AXRole': 'AXWindow'},
        }
        self.adapter = mock.Mock()
        self.adapter.ensure.return_value = self.w
        self.adapter._ax_window.return_value = ('root', 'target')
        self.adapter._get.side_effect = lambda obj, name, default=None: self.attrs.get(obj, {}).get(name, default)
        self.ax = mock.Mock()
        self.ax.AXIsProcessTrusted.return_value = True
        self.ax.AXUIElementCopyElementAtPosition.return_value = (0, 'label')
        self.ax.AXUIElementCopyActionNames.side_effect = lambda el, _: (0, ['AXPress', 'AXShowMenu'] if el == 'button' else [])
        self.ax.AXUIElementPerformAction.return_value = 0
        self.ax.AXUIElementIsAttributeSettable.return_value = (0, True)
        self.ax.AXUIElementSetAttributeValue.return_value = 0
        self.q = mock.Mock()
        for i, name in enumerate(('kCGEventSourceStatePrivate', 'kCGMouseButtonLeft', 'kCGMouseButtonRight',
                    'kCGEventLeftMouseDown', 'kCGEventLeftMouseUp', 'kCGEventRightMouseDown', 'kCGEventRightMouseUp',
                    'kCGMouseEventClickState', 'kCGMouseEventWindowUnderMousePointer',
                    'kCGMouseEventWindowUnderMousePointerThatCanHandleThisEvent', 'kCGEventFlagMaskCommand',
                    'kCGEventFlagMaskControl', 'kCGScrollEventUnitLine', 'kCGHIDEventTap')):
            setattr(self.q, name, i)
        self.q.CGEventCreateMouseEvent.side_effect = lambda src, kind, point, btn: (kind, point, btn)
        self.q.CGEventCreateKeyboardEvent.side_effect = lambda src, code, down: (code, down)
        self.k = mock.Mock()
        self.k.NSWorkspace.sharedWorkspace.return_value.frontmostApplication.return_value.processIdentifier.return_value = 900
        self.router = WindowInput(self.adapter, self.ax, self.q, self.k)
        self.sleep = mock.patch('continuity.window_input.time.sleep').start()
        self.addCleanup(mock.patch.stopall)

    def perform(self, action='click', **changes):
        data = {'x': .5, 'y': .5, 'button': 'left', **changes}
        return self.router.perform(self.w, action, data, self.frame)

    def no_global_or_activate(self):
        self.q.CGEventPost.assert_not_called()
        self.adapter.activate.assert_not_called()
        self.adapter._frontmost.assert_not_called()

    def test_left_hit_descendant_uses_ax_without_foreground(self):
        result = self.perform()
        self.ax.AXUIElementPerformAction.assert_called_once_with('button', 'AXPress')
        self.assertEqual(result['delivery'], 'ax_acknowledged')
        self.q.CGEventPostToPid.assert_not_called()
        self.no_global_or_activate()

    def test_right_is_ax_showmenu_not_press(self):
        result = self.perform(button='right')
        self.ax.AXUIElementPerformAction.assert_called_once_with('button', 'AXShowMenu')
        self.assertIn('独立窗口', result['message'])
        self.no_global_or_activate()

    def test_foreign_hit_is_rejected_not_clicked(self):
        self.ax.AXUIElementCopyElementAtPosition.return_value = (0, 'other')
        with self.assertRaises(Problem): self.perform()
        self.ax.AXUIElementPerformAction.assert_not_called()
        self.q.CGEventPostToPid.assert_not_called()
        self.no_global_or_activate()

    def test_missing_ax_does_not_silently_use_raw_input(self):
        self.ax.AXUIElementCopyActionNames.side_effect = lambda el, _: (0, [])
        with self.assertRaises(Problem) as caught: self.perform()
        self.assertEqual(caught.exception.code, 'background_unsupported')
        self.q.CGEventPostToPid.assert_not_called()
        self.no_global_or_activate()

    def test_ax_attempt_failure_never_replayed_via_pid(self):
        self.ax.AXUIElementPerformAction.return_value = -25204
        with self.assertRaises(Problem): self.perform()
        self.q.CGEventPostToPid.assert_not_called()
        self.no_global_or_activate()

    def test_direct_right_down_up_route_to_pid(self):
        result = self.perform(input_route='direct', button='right')
        calls = self.q.CGEventCreateMouseEvent.call_args_list
        self.assertEqual([x.args[1] for x in calls], [self.q.kCGEventRightMouseDown, self.q.kCGEventRightMouseUp])
        self.assertEqual([x.args[3] for x in calls], [self.q.kCGMouseButtonRight]*2)
        self.assertEqual([x.args[0] for x in self.q.CGEventPostToPid.call_args_list], [77, 77])
        self.assertEqual(result['delivery'], 'submitted_unconfirmed')
        self.no_global_or_activate()

    def test_direct_left_sets_window_hint_and_coordinates(self):
        self.perform(input_route='direct', x=0, y=1)
        event = self.q.CGEventCreateMouseEvent.call_args_list[0]
        self.assertEqual(event.args[2], (300, 650))
        self.q.CGEventSetIntegerValueField.assert_any_call((self.q.kCGEventLeftMouseDown, (300,650), self.q.kCGMouseButtonLeft), self.q.kCGMouseEventWindowUnderMousePointer, 7)
        self.no_global_or_activate()

    def test_direct_requires_selected_ax_focused_window(self):
        self.attrs['root']['AXFocusedWindow'] = 'other'
        with self.assertRaises(Problem): self.perform(input_route='direct')
        self.q.CGEventPostToPid.assert_not_called()
        self.no_global_or_activate()

    def test_direct_revalidates_before_side_effect(self):
        self.adapter.ensure.side_effect = [self.w, Window(7,77,'birth','Test','Target',(0,0,800,600))]
        with self.assertRaises(Problem): self.perform(input_route='direct')
        self.q.CGEventPostToPid.assert_not_called()

    def test_direct_text_is_not_global(self):
        result = self.perform('text', input_route='direct', text='汉字😀')
        self.assertEqual(self.q.CGEventPostToPid.call_count, 2)
        self.assertEqual(self.q.CGEventKeyboardSetUnicodeString.call_args_list[0].args[1], 4)
        self.no_global_or_activate()

    def test_secure_input_is_rejected(self):
        self.attrs['field']['AXSubrole'] = 'AXSecureTextField'
        for route in ('direct', 'background'):
            with self.subTest(route=route), self.assertRaises(Problem): self.perform('text', input_route=route, text='private')
        self.ax.AXUIElementSetAttributeValue.assert_not_called()
        self.q.CGEventPostToPid.assert_not_called()

    def test_bad_button_and_invalid_coordinate(self):
        for b in ('middle', '', 2, None, []):
            with self.subTest(button=b), self.assertRaises(Problem): self.perform(button=b)
        with self.assertRaises(Problem): self.perform(x=float('nan'), input_route='direct')
        self.q.CGEventPostToPid.assert_not_called()

    def test_foreground_route_explicitly_checks_foreground(self):
        self.adapter._frontmost.side_effect = Problem('not_frontmost', 'Not frontmost', 409)
        with self.assertRaises(Problem): self.perform(input_route='foreground')
        self.q.CGEventPost.assert_not_called()
        self.q.CGEventPostToPid.assert_not_called()

    def test_front_change_reported_not_restored(self):
        self.k.NSWorkspace.sharedWorkspace.return_value.frontmostApplication.side_effect = [
            SimpleNamespace(processIdentifier=lambda:900), SimpleNamespace(processIdentifier=lambda:77)]
        result = self.perform()
        self.assertTrue(result['foreground_changed'])
        self.no_global_or_activate()
