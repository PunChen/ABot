# -*- coding: utf-8 -*-
import os
import sys

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TESTS_DIR)  # 插件根目录
PARENT = os.path.dirname(ROOT)  # 以命名空间包 ABot 导入

for path in (PARENT, TESTS_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from fake_astrbot import install_fake_astrbot  # noqa: E402

install_fake_astrbot()
