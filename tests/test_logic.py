import math
import os
import struct
import sys
import tempfile
import unittest
import wave

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from animauto import config, logic  # noqa: E402


def _write_wav(path, chunks, rate=8000, sampwidth=2, channels=1):
    """chunks: [(секунды, амплитуда 0..1)] — синус 220 Гц."""
    frames = bytearray()
    full = (1 << (8 * sampwidth - 1)) - 1
    for seconds, amp in chunks:
        for i in range(int(seconds * rate)):
            v = int(amp * full * math.sin(2 * math.pi * 220 * i / rate))
            for _ in range(channels):
                if sampwidth == 2:
                    frames += struct.pack("<h", v)
                elif sampwidth == 3:
                    frames += (v & 0xFFFFFF).to_bytes(3, "little")
    with wave.open(path, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(sampwidth)
        w.setframerate(rate)
        w.writeframes(bytes(frames))


class BlinkTests(unittest.TestCase):
    def test_blinks_inside_range_and_spaced(self):
        frames = logic.plan_blinks(1, 240, 24, 2.0, 5.0, 3, seed=7)
        self.assertTrue(frames)
        for f in frames:
            self.assertGreaterEqual(f, 1)
            self.assertLessEqual(f + 3, 240)
        gaps = [b - a for a, b in zip(frames, frames[1:])]
        self.assertTrue(all(48 - 1 <= g <= 120 + 1 for g in gaps), gaps)

    def test_deterministic_with_seed(self):
        self.assertEqual(logic.plan_blinks(0, 500, 24, 2, 4, 3, seed=1),
                         logic.plan_blinks(0, 500, 24, 2, 4, 3, seed=1))

    def test_too_short_range(self):
        self.assertEqual(logic.plan_blinks(0, 2, 24, 2, 4, 3), [])


class LipsyncTests(unittest.TestCase):
    def test_envelope_and_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "a.wav")
            _write_wav(path, [(0.5, 0.0), (0.5, 0.9), (0.5, 0.0), (0.5, 0.3)])
            env = logic.read_wav_envelope(path, 24)
            self.assertEqual(len(env), 48)
            self.assertLess(env[5], 0.01)
            self.assertGreater(env[18], 0.5)
            points, _ = logic.lipsync_keys(env, config.LIPSYNC_THRESHOLDS, 2, 1)
            levels = dict(points)
            self.assertEqual(points[0], (0, 0))
            self.assertTrue(any(lv == 3 for lv in levels.values()))
            # тихий кусок открывает рот меньше громкого
            quiet = [lv for i, lv in points if i >= 36]
            self.assertTrue(quiet and max(quiet) < 3)

    def test_stereo_24bit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "b.wav")
            _write_wav(path, [(0.25, 0.5)], sampwidth=3, channels=2)
            env = logic.read_wav_envelope(path, 24)
            self.assertEqual(len(env), 6)
            self.assertAlmostEqual(env[2], 0.5 / math.sqrt(2), places=2)

    def test_min_hold_removes_flicker(self):
        levels = [0, 0, 0, 2, 0, 0, 3, 3, 3, 1, 3, 3]
        out = logic.enforce_min_hold(levels, 2)
        self.assertEqual(len(out), len(levels))
        runs = logic.change_points(out)
        lengths = [b[0] - a[0] for a, b in zip(runs, runs[1:])] + [len(out) - runs[-1][0]]
        self.assertTrue(all(n >= 2 for n in lengths), out)


class NamingTests(unittest.TestCase):
    def test_opposite(self):
        self.assertEqual(logic.opposite_name("FKHip_L", config.SIDE_TOKENS), "FKHip_R")
        self.assertEqual(logic.opposite_name("batja:IKArm_R", config.SIDE_TOKENS), "batja:IKArm_L")
        self.assertIsNone(logic.opposite_name("RootX_M", config.SIDE_TOKENS))

    def test_flip_rules(self):
        self.assertEqual(logic.flip_attrs("ns:IKLeg_L", config.MIRROR_RULES_SIDE), {"tx", "ry", "rz"})
        self.assertEqual(logic.flip_attrs("FKShoulder_L", config.MIRROR_RULES_SIDE), set())
        self.assertEqual(logic.flip_attrs("RootX_M", config.MIRROR_RULES_CENTER), {"tx", "ry", "rz"})


class PoleTests(unittest.TestCase):
    def test_pole_in_front_of_knee(self):
        pos = logic.pole_vector_position((0, 10, 0), (0, 5, 1), (0, 0, 0), 0.5)
        self.assertAlmostEqual(pos[0], 0)
        self.assertAlmostEqual(pos[1], 5)
        self.assertGreater(pos[2], 1)

    def test_straight_limb(self):
        self.assertEqual(logic.pole_vector_position((0, 2, 0), (0, 1, 0), (0, 0, 0)), (0, 1, 0))


if __name__ == "__main__":
    unittest.main()
