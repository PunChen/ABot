# -*- coding: utf-8 -*-
"""端到端冒烟: 模拟一连串用户输入, 走真实 process_event 分发与模式闭环。

python tests/smoke_repl.py
"""
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for path in (os.path.dirname(ROOT), HERE):
    if path not in sys.path:
        sys.path.insert(0, path)

from fake_astrbot import install_fake_astrbot  # noqa: E402

install_fake_astrbot()

import ABot.db_utils.database as database  # noqa: E402

# 数据文件重定向到临时目录, 不污染仓库
TMP = tempfile.mkdtemp(prefix="abot-smoke-")
database.base_dir = TMP

from ABot.main import process_event  # noqa: E402

failures = []


def check(label, ret, expect):
    ok = expect in (ret or "")
    print(f"[{'OK' if ok else 'FAIL'}] {label}: {ret!r}")
    if not ok:
        failures.append(label)


def main():
    check("help", process_event("help"), "abot switch")
    check("switch-talk", process_event("switch 1"), "success")
    check("talk-miss", process_event("hello"), "sorry")
    check("switch-learn", process_event("switch 3"), "success")
    check("learn", process_event("你好 => 嗨"), "learned")
    check("learn-usage", process_event("no separator"), "learn usage")
    check("switch-talk2", process_event("switch 1"), "success")
    check("talk-hit", process_event("你好"), "嗨")
    check("switch-record", process_event("switch 2"), "success")
    check("record", process_event("my name is chenhao"), "recorded")
    check("records", process_event("records"), "chenhao")
    check("switch-talk3", process_event("switch 1"), "success")
    check("summary", process_event("summary"), "imported 1")
    check("summary-find", process_event("name"), "chenhao")
    check("stop", process_event("stop"), "stopped")
    check("stopped-text", process_event("hello"), "stopped")
    check("restart", process_event("switch 1"), "success")
    check("after-restart", process_event("你好"), "嗨")
    check("bad-switch", process_event("switch abc"), "usage")
    check("records-cleared", process_event("records"), "no records")
    check("voice-off", process_event("voice off"), "disabled")
    check("voice-scope-group", process_event("voice group"), "group")
    check("voice-scope-private", process_event("voice private"), "private")
    check("lang", process_event("lang chinese"), "chinese")

    print()
    if failures:
        print(f"FAILED: {len(failures)} -> {failures}")
        return 1
    print("ALL SMOKE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    try:
        code = main()
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
    sys.exit(code)
