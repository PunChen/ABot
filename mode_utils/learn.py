# -*- coding: utf-8 -*-
import re

from .base import Mode

_URL_RE = re.compile(r"^https?://\S+$", re.I)


class LearnMode(Mode):
    """LEARN 模式: 学习词条("Q => A")或从 URL 抓取知识。"""

    name = "learn"

    def process(self, db, text):
        text = text.strip()
        if _URL_RE.match(text):
            return db.learn_url(text)
        return db.update(text)
