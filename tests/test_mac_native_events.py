"""Native event construction only. No posting, activation, or permission changes."""
import os
import sys
import unittest


@unittest.skipUnless(sys.platform == 'darwin', 'macOS frameworks unavailable')
class MacNativeConstructionTests(unittest.TestCase):
    def test_right_button_window_fields_and_unicode(self):
        import Quartz as q
        import ApplicationServices as a
        first = a.AXUIElementCreateApplication(os.getpid())
        second = a.AXUIElementCreateApplication(os.getpid())
        self.assertEqual(first, second, 'AX identity equality must work for scoped routing')
        source = q.CGEventSourceCreate(q.kCGEventSourceStatePrivate)
        event = q.CGEventCreateMouseEvent(source, q.kCGEventRightMouseDown, (250.0, 350.0), q.kCGMouseButtonRight)
        self.assertIsNotNone(event)
        q.CGEventSetIntegerValueField(event, q.kCGMouseEventClickState, 1)
        q.CGEventSetIntegerValueField(event, q.kCGMouseEventWindowUnderMousePointer, 123)
        q.CGEventSetIntegerValueField(event, q.kCGMouseEventWindowUnderMousePointerThatCanHandleThisEvent, 123)
        self.assertEqual(q.CGEventGetType(event), q.kCGEventRightMouseDown)
        self.assertEqual(q.CGEventGetIntegerValueField(event, q.kCGMouseEventButtonNumber), q.kCGMouseButtonRight)
        self.assertEqual(q.CGEventGetIntegerValueField(event, q.kCGMouseEventWindowUnderMousePointer), 123)
        key = q.CGEventCreateKeyboardEvent(source, 0, True)
        q.CGEventKeyboardSetUnicodeString(key, 4, '汉字😀')
        self.assertTrue(callable(q.CGEventPostToPid))
        self.assertTrue(callable(a.AXUIElementCopyElementAtPosition))
