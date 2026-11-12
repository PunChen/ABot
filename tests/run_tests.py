# -*- coding: utf-8 -*-
"""纯 Python 测试入口(无需 pytest): python tests/run_tests.py"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for path in (os.path.dirname(ROOT), HERE):
    if path not in sys.path:
        sys.path.insert(0, path)

from fake_astrbot import install_fake_astrbot  # noqa: E402

install_fake_astrbot()

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.discover(HERE, pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
