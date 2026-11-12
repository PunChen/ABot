# -*- coding: utf-8 -*-
from .base import Mode


class TalkMode(Mode):
    """TALK 模式: 三层检索知识库并回应。"""

    name = "talk"

    def process(self, db, text):
        return db.find(text)
