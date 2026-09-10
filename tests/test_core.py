import io
import json
import math
import struct
import unittest
from PIL import Image
from continuity.core import FrameState, ImageBudget, Problem, pack_frame, parse_roi


def unpack(raw):
    n = struct.unpack('!I', raw[:4])[0]
    header = json.loads(raw[4:4+n])
    return header, raw[4+n:]


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.image = Image.new('RGB', (640, 480), (30, 80, 140))
        self.args = ((1, 2, 'birth'), (0, 0, 640, 480))

    def first(self):
        return pack_frame(self.image, FrameState(), '', *self.args, width=640)

    def test_initial_binary_not_base64(self):
        raw, state, header = self.first()
        decoded, body = unpack(raw)
        self.assertTrue(decoded['full'])
        self.assertEqual(len(body), header['image_bytes'])
        self.assertEqual(len(decoded['tiles']), 20)
        self.assertTrue(body.startswith(b'\xff\xd8'))
        self.assertEqual(state.revision, decoded['revision'])

    def test_static_image_has_no_jpeg_body(self):
        _, state, _ = self.first()
        raw, new, h = pack_frame(self.image, state, state.revision, *self.args, width=640)
        self.assertFalse(h['full'])
        self.assertEqual(h['tiles'], [])
        self.assertEqual(h['image_bytes'], 0)
        self.assertLess(len(raw), 512)

    def test_one_pixel_changes_only_one_tile(self):
        _, state, _ = self.first()
        self.image.putpixel((1, 1), (250, 250, 250))
        _, _, h = pack_frame(self.image, state, state.revision, *self.args, width=640)
        self.assertEqual(len(h['tiles']), 1)
        self.assertEqual((h['tiles'][0]['x'], h['tiles'][0]['y']), (0, 0))

    def test_unknown_base_forces_full_recovery(self):
        _, state, _ = self.first()
        _, _, h = pack_frame(self.image, state, 'lost-frame', *self.args, width=640)
        self.assertTrue(h['full'])
        self.assertEqual(len(h['tiles']), 20)

    def test_crop_and_parameter_change_require_baseline(self):
        _, state, _ = self.first()
        _, _, h = pack_frame(self.image, state, state.revision, *self.args, width=640, roi=(0, .5, 1, .5))
        self.assertTrue(h['full'])
        self.assertEqual((h['width'], h['height']), (640, 240))

    def test_invalid_roi(self):
        for value in [None, [], [0,0,2,1], [0,0,0,1], [0,0,float('nan'),1], [False,0,1,1], [.8,0,.5,1]]:
            with self.subTest(value=value), self.assertRaises(Problem):
                parse_roi(value)

    def test_invalid_image_settings(self):
        for key, value in [('width',True),('width',20000),('quality',float('inf')),('quality','bad')]:
            with self.subTest(key=key, value=value), self.assertRaises(Problem):
                pack_frame(self.image, FrameState(), '', *self.args, **{key:value})

    def test_budget_does_not_commit_rejected_transfer(self):
        budget = ImageBudget(limit=100, per_frame=90)
        budget.consume(70)
        with self.assertRaises(Problem): budget.consume(31)
        self.assertEqual(budget.used, 70)
        self.assertEqual(budget.blocked, 1)
        with self.assertRaises(Problem): budget.consume(91)
        self.assertEqual(budget.used, 70)
