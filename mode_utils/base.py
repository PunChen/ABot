# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod


class Mode(ABC):
    """对话模式基类。

    各模式实现 process(db, text) -> str, 由 Bot 按当前状态查表分发。
    """

    name = "mode"

    @abstractmethod
    def process(self, db, text):
        """处理一句输入, 返回给用户的回复文本。"""
