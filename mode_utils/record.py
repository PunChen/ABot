# -*- coding: utf-8 -*-
from .base import Mode


class RecordMode(Mode):
    """RECORD 模式: 记录用户说的每句话。"""

    name = "record"

    def process(self, db, text):
        return db.insert(text)
