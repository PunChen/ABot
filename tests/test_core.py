# -*- coding: utf-8 -*-
"""核心逻辑单测: 三层检索 / 学习 / 记录汇总 / URL 学习 / 命令分发 / Bot 状态机。

pytest 可用时: python -m pytest tests -q
纯 Python:     python tests/run_tests.py
"""
import os
import shutil
import sys
import tempfile
import unittest

from ABot.bot_utils.bot import Bot
from ABot.command_utils.Command import Command
from ABot.const_utils import constant
from ABot.const_utils.constant import BotStatus, Language
from ABot.db_utils.database import DB
from ABot.lang_utils import text as text_utils


class TempDBTest(unittest.TestCase):
    """每个用例使用独立临时目录, 不污染仓库内 data.json / record.json。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="abot-test-")
        self.db = self.make_db()
        self.db.data.update(
            {
                "hello": "hi",
                "what is time": "time is a flow",
                "你好": "嗨",
            }
        )
        self.db._rebuild_index()

    def make_db(self):
        return DB(
            data_file_path=os.path.join(self.tmp, "data.json"),
            record_file_path=os.path.join(self.tmp, "record.json"),
        )

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class TextUtilsTest(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(text_utils.normalize("Ｈｅｌｌｏ, World!"), "hello world")
        self.assertEqual(text_utils.normalize("什么是时间？"), "什么是时间")
        self.assertEqual(text_utils.normalize("  a   b  "), "a b")

    def test_tokenize(self):
        tokens = text_utils.tokenize("What is the time")
        self.assertIn("time", tokens)
        self.assertNotIn("what", tokens)  # 停用词

    def test_extract_nouns_fallback(self):
        nouns = text_utils.extract_nouns("hello world machine learning", top=5)
        self.assertTrue(nouns)
        self.assertIn("machine", nouns)


class FindTest(TempDBTest):
    def test_l1_exact(self):
        self.assertEqual(self.db.find("hello"), "hi")
        self.assertEqual(self.db.find("你好"), "嗨")

    def test_l1_normalized(self):
        self.assertEqual(self.db.find("HELLO!"), "hi")
        self.assertEqual(self.db.find("What  is time?"), "time is a flow")

    def test_l2_token_overlap(self):
        self.assertEqual(self.db.find("what time is it"), "time is a flow")

    def test_l3_close_match(self):
        self.assertEqual(self.db.find("helo"), "hi")

    def test_miss(self):
        self.assertIn("sorry", self.db.find("completely irrelevant query"))


class LearnTest(TempDBTest):
    def test_update_and_find(self):
        msg = self.db.update("who are you => I am abot")
        self.assertIn("learned", msg)
        self.assertEqual(self.db.find("who are you"), "I am abot")

    def test_update_persists(self):
        self.db.update("cats => meow")
        reloaded = self.make_db()
        self.assertEqual(reloaded.find("cats"), "meow")

    def test_update_merge_answers(self):
        self.db.update("greeting => hello there | hey")
        got = self.db.find("greeting")
        self.assertIn(got, ("hello there", "hey"))

    def test_update_overwrite_existing(self):
        msg = self.db.update("hello => yo")
        self.assertIn("updated", msg)
        got = self.db.find("hello")
        self.assertIn(got, ("hi", "yo"))

    def test_update_bad_syntax(self):
        self.assertIn("learn usage", self.db.update("just a sentence"))

    def test_forget(self):
        self.db.update("cats => meow")
        self.assertIn("forgot", self.db.forget("cats"))
        self.assertIn("sorry", self.db.find("cats"))

    def test_forget_missing(self):
        self.assertIn("no entry", self.db.forget("nothing here"))


class RecordTest(TempDBTest):
    def test_insert_and_records_text(self):
        self.assertIn("recorded", self.db.insert("i am chenhao"))
        self.assertIn("i am chenhao", self.db.records_text())

    def test_insert_persists(self):
        self.db.insert("remember me")
        reloaded = self.make_db()
        self.assertIn("remember me", reloaded.records_text())

    def test_clear_records(self):
        self.db.insert("a")
        self.assertIn("cleared", self.db.clear_records())
        self.assertEqual(self.db.records_text(), "(no records yet)")


class SummarizeTest(TempDBTest):
    def test_pattern_import(self):
        self.db.insert("my name is chenhao")
        self.db.insert("the sky is blue")
        msg = self.db.summarize_records()
        self.assertIn("imported 2", msg)
        self.assertEqual(self.db.find("name"), "chenhao")
        self.assertEqual(self.db.find("the sky"), "blue")

    def test_default_clears_records(self):
        self.db.insert("my name is chenhao")
        self.db.summarize_records()
        self.assertEqual(self.db.records_text(), "(no records yet)")

    def test_keep_records(self):
        self.db.insert("my name is chenhao")
        self.db.summarize_records(keep=True)
        self.assertIn("chenhao", self.db.records_text())

    def test_short_key_skipped(self):
        # "我是学生" 可匹配 "我" 是 "学生", 但单字 key 应被跳过, 改走名词 "学生"
        self.db.insert("我是学生")
        self.db.summarize_records()
        self.assertNotIn("我", self.db.data)
        self.assertIn("学生", self.db.data)

    def test_skipped_counted(self):
        self.db.insert("")
        msg = self.db.summarize_records()
        self.assertIn("skipped 1", msg)


class ConcurrencyTest(TempDBTest):
    def test_find_during_update(self):
        import threading

        errors = []

        def writer():
            try:
                for i in range(100):
                    self.db.update(f"q{i} => a{i}")
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        thread = threading.Thread(target=writer)
        thread.start()
        try:
            for i in range(100):
                self.db.find(f"q{i} question")
        finally:
            thread.join()
        self.assertEqual(errors, [])


class LearnUrlTest(TempDBTest):
    def test_invalid_url(self):
        self.assertIn("invalid url", self.db.learn_url("not a url"))

    def test_learn_url_with_mocked_crawler(self):
        from ABot.web_utils import crawler

        original = crawler.crawl

        def fake_crawl(url, max_entries=30):
            return [("人工智能", "人工智能是研究如何让机器模拟人类智能的学科。")]

        crawler.crawl = fake_crawl
        try:
            msg = self.db.learn_url("https://zh.wikipedia.org/wiki/人工智能")
        finally:
            crawler.crawl = original
        self.assertIn("learned 1", msg)
        self.assertIn("人工智能", self.db.data)
        self.assertIn("模拟人类智能", self.db.find("人工智能"))


class CommandTest(unittest.TestCase):
    def test_match(self):
        self.assertEqual(Command.match("switch 1"), (Command.SWITCH, "1"))
        self.assertEqual(Command.match("STOP"), (Command.STOP, ""))
        self.assertEqual(Command.match("hello"), (None, "hello"))
        self.assertEqual(Command.match(""), (None, ""))

    def test_value2name(self):
        self.assertEqual(constant.value2name(BotStatus, 1), "TALK")
        self.assertIsNone(constant.value2name(BotStatus, 99))


class CrawlerTextTest(unittest.TestCase):
    def test_extract_text_fallback(self):
        from ABot.web_utils import crawler

        old = sys.modules.get("trafilatura", None)
        sys.modules["trafilatura"] = None  # 强制 ImportError, 走正则降级
        try:
            text = crawler._extract_text(
                "<html><body><p>Hello world</p><script>bad()</script></body></html>"
            )
        finally:
            if old is None:
                sys.modules.pop("trafilatura", None)
            else:
                sys.modules["trafilatura"] = old
        self.assertIn("Hello world", text)
        self.assertNotIn("bad()", text)
        self.assertNotIn("<p>", text)

    def test_first_sentence(self):
        from ABot.web_utils import crawler

        self.assertEqual(
            crawler._first_sentence("人工智能是学科。第二句。"), "人工智能是学科。"
        )
        long_text = "a" * 500
        self.assertEqual(len(crawler._first_sentence(long_text)), 200)

    def test_looks_chinese(self):
        self.assertTrue(text_utils.looks_chinese("什么是人工智能"))
        self.assertFalse(text_utils.looks_chinese("what is ai"))


class LanguageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="abot-lang-")
        from ABot.lang_utils import language

        self.language = language
        self.old_audio_dir = language.AUDIO_DIR
        language.AUDIO_DIR = self.tmp

    def tearDown(self):
        self.language.AUDIO_DIR = self.old_audio_dir
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_prepare_wav_passthrough(self):
        wav_path = os.path.join(self.tmp, "a.wav")
        with open(wav_path, "wb") as fp:
            fp.write(b"RIFF")
        self.assertEqual(self.language.prepare_wav(wav_path), wav_path)

    def test_prepare_wav_unsupported(self):
        amr_path = os.path.join(self.tmp, "a.amr")
        with open(amr_path, "wb") as fp:
            fp.write(b"amr data")
        self.assertIsNone(self.language.prepare_wav(amr_path))

    def test_is_silk(self):
        silk_path = os.path.join(self.tmp, "a.silk")
        with open(silk_path, "wb") as fp:
            fp.write(b"#!SILK_V3" + b"\x00" * 8)
        self.assertTrue(self.language._is_silk(silk_path))
        wav_path = os.path.join(self.tmp, "b.wav")
        with open(wav_path, "wb") as fp:
            fp.write(b"RIFF")
        self.assertFalse(self.language._is_silk(wav_path))


class BotTest(TempDBTest):
    def test_talk_mode(self):
        bot = Bot(db_inst=self.db)
        self.assertEqual(bot.status, BotStatus.TALK)
        self.assertEqual(bot.on_text("hello"), "hi")

    def test_switch_mode(self):
        bot = Bot(db_inst=self.db)
        self.assertIn("success", bot.switch_status(3))
        self.assertEqual(bot.status, BotStatus.LEARN)
        self.assertIn("learned", bot.on_text("cats => meow"))
        bot.switch_status(1)
        self.assertEqual(bot.on_text("cats"), "meow")

    def test_language_and_voice_settings(self):
        bot = Bot(db_inst=self.db)
        self.assertIn("chinese", bot.set_language("中文"))
        self.assertEqual(bot.language, Language.CHINESE)
        self.assertIn("usage", bot.set_language("klingon"))
        self.assertIn("enabled", bot.set_voice_reply("on"))
        self.assertTrue(bot.voice_reply)
        self.assertIn("disabled", bot.set_voice_reply("off"))

    def test_voice_scope(self):
        bot = Bot(db_inst=self.db)
        self.assertTrue(bot.voice_scope_private)
        self.assertIn("group", bot.set_voice_scope("group"))
        self.assertFalse(bot.voice_scope_private)
        self.assertIn("private", bot.set_voice_scope("private"))
        self.assertTrue(bot.voice_scope_private)
        self.assertIn("usage", bot.set_voice_scope("everywhere"))

    def test_stop_saves(self):
        bot = Bot(db_inst=self.db)
        bot.on_text("hello")
        bot.set_running(False)
        self.assertFalse(bot.is_running())


class TtsResultTest(TempDBTest):
    """_build_result: TTS 超长截断与失败回退纯文本。"""

    def setUp(self):
        super().setUp()
        import asyncio

        from ABot import main as abot_main

        self.asyncio = asyncio
        self.abot_main = abot_main

        class FakeEvent:
            def chain_result(self, chain):
                return ("chain", chain)

            def plain_result(self, text):
                return ("plain", text)

        self.event = FakeEvent()

    def tearDown(self):
        self.abot_main.bot = None
        super().tearDown()

    def run_result(self, text):
        return self.asyncio.run(
            self.abot_main.ABot._build_result(None, self.event, text)
        )

    def test_tts_truncates_long_text(self):
        bot = Bot(db_inst=self.db)
        bot.voice_reply = True
        self.abot_main.bot = bot
        calls = []

        def fake_tts(text, lang):
            calls.append(text)
            return "fake.wav"

        original = self.abot_main.language.text2audio
        self.abot_main.language.text2audio = fake_tts
        try:
            result = self.run_result("x" * 300)
        finally:
            self.abot_main.language.text2audio = original
        self.assertEqual(calls[0], "x" * self.abot_main.TTS_MAX_CHARS)
        self.assertEqual(result[0], "chain")

    def test_tts_failure_falls_back_to_plain(self):
        bot = Bot(db_inst=self.db)
        bot.voice_reply = True
        self.abot_main.bot = bot
        original = self.abot_main.language.text2audio
        self.abot_main.language.text2audio = lambda text, lang: None
        try:
            result = self.run_result("reply")
        finally:
            self.abot_main.language.text2audio = original
        self.assertEqual(result, ("plain", "reply"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
