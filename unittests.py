import unittest
from core.taint import Taint


class TestTaint(unittest.TestCase):
    def test_taint(self):
        eq = self.assertEqual
        eq(bool(Taint(7)), True)
        eq(bool(Taint(0)), False)
        eq(Taint(7) & Taint(3), Taint(3))
        eq(Taint(1) | Taint(2), Taint(3))
        eq(Taint(3), Taint(3))
        eq(Taint(7) & ~Taint(1), Taint(6))

        self.assertRaises(AttributeError, lambda: Taint(7) & 3)
        self.assertRaises(AttributeError, lambda: Taint(7) & ~1)


if __name__ == '__main__':
    unittest.main()
