# -*- coding: utf-8 -*-
import threading

from ..const_utils import constant
from ..const_utils.constant import BotStatus, Language
from ..db_utils import database
from ..lang_utils import language
from ..mode_utils.learn import LearnMode
from ..mode_utils.record import RecordMode
from ..mode_utils.talk import TalkMode
from astrbot.api import logger

status_lock = threading.Lock()

_LANGUAGE_ALIASES = {
    "chinese": Language.CHINESE,
    "zh": Language.CHINESE,
    "中文": Language.CHINESE,
    "汉语": Language.CHINESE,
    "english": Language.ENGLISH,
    "en": Language.ENGLISH,
    "英文": Language.ENGLISH,
    "英语": Language.ENGLISH,
}


class Bot:
    def __init__(self, db_inst=None):
        self.status = BotStatus.INIT
        self.db_inst = db_inst if db_inst is not None else database.DB()
        self.running = False
        self.language = Language.ENGLISH
        # 语音回复开关(输出侧)
        self.voice_reply = False
        # 语音输入作用域: True=仅私聊, False=群聊也响应
        self.voice_scope_private = True
        self.modes = {
            BotStatus.TALK: TalkMode(),
            BotStatus.RECORD: RecordMode(),
            BotStatus.LEARN: LearnMode(),
        }
        self.status = BotStatus.TALK

    # ---------- 运行状态 ----------

    def is_running(self):
        return self.running

    def set_running(self, running):
        self.running = running
        if self.running:
            logger.info("hello, what can i help?")
        else:
            self.db_inst.save()

    def switch_status(self, status_value):
        with status_lock:
            if constant.contains_value(BotStatus, status_value):
                tgt_status = BotStatus(status_value)
                logger.info(f"try switch status: {self.status} -> {tgt_status}")
                self.status = tgt_status
                if not self.running:
                    self.running = True  # switch 视为恢复运行
                    logger.info("hello, what can i help?")
                result = f"switch to status: {tgt_status}({status_value}) success"
                logger.info(result)
                return result
            result = f"switch to status: {status_value} failed"
            logger.error(result)
            return result

    # ---------- 设置 ----------

    def set_language(self, value):
        lang = _LANGUAGE_ALIASES.get(str(value).strip().lower())
        if lang is None:
            return "usage: lang <chinese|english>"
        self.language = lang
        return f"language set to {lang.value}"

    def set_voice_reply(self, value):
        value = str(value).strip().lower()
        if value not in ("on", "off", "开", "关"):
            return "usage: voice <on|off>"
        self.voice_reply = value in ("on", "开")
        return f"voice reply {'enabled' if self.voice_reply else 'disabled'}"

    def set_voice_scope(self, value):
        """语音输入作用域: private=仅私聊, group=群聊也响应。"""
        value = str(value).strip().lower()
        if value in ("private", "私聊"):
            self.voice_scope_private = True
            return "voice input scope: private"
        if value in ("group", "群聊"):
            self.voice_scope_private = False
            return "voice input scope: group"
        return "usage: voice <on|off> | voice <private|group>"

    # ---------- 对话入口 ----------

    def on_text(self, text):
        if self.status == BotStatus.INIT:
            return "init: bot not ready!"
        mode = self.modes.get(self.status)
        if mode is None:
            return f"mode {self.status} not supported"
        return mode.process(self.db_inst, text)

    def on_records(self):
        return self.db_inst.records_text()

    def on_voice(self, audio):
        logger.info("on_voice try parse audio...")
        text = language.audio2text(audio, self.language)
        if not text:
            return "sorry, i can not understand the audio"
        logger.info(f"voice recognized: {text}")
        return self.on_text(text)

    # ---------- 命令委托 ----------

    def clear_records(self):
        return self.db_inst.clear_records()

    def summarize_records(self, keep=False):
        return self.db_inst.summarize_records(keep)

    def forget(self, key):
        return self.db_inst.forget(key)

    def learn_url(self, url):
        return self.db_inst.learn_url(url)
