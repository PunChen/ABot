# -*- coding: utf-8 -*-
"""最小 astrbot 桩: 让插件模块可以在没有真实 AstrBot 的环境下导入与测试。

只实现本插件用到的 API 形状:
- astrbot.api.logger
- astrbot.api.event.filter / AstrMessageEvent / EventMessageType
- astrbot.api.star.Context / Star / register
- astrbot.api.message_components.Plain / Record
"""
import sys
import types


def install_fake_astrbot():
    if "astrbot" in sys.modules:
        return

    class _Logger:
        def info(self, *args, **kwargs):
            pass

        def warning(self, *args, **kwargs):
            pass

        def warn(self, *args, **kwargs):
            pass

        def error(self, *args, **kwargs):
            pass

        def debug(self, *args, **kwargs):
            pass

    class _EventMessageType:
        ALL = "all"
        PRIVATE_MESSAGE = "private"
        GROUP_MESSAGE = "group"

    class _Filter:
        EventMessageType = _EventMessageType

        def command(self, name, **kwargs):
            def deco(fn):
                fn._abot_command = name
                return fn

            return deco

        def event_message_type(self, message_type):
            def deco(fn):
                return fn

            return deco

        def permission_type(self, permission_type):
            def deco(fn):
                return fn

            return deco

    astrbot = types.ModuleType("astrbot")
    api = types.ModuleType("astrbot.api")
    api.logger = _Logger()

    event_mod = types.ModuleType("astrbot.api.event")

    class AstrMessageEvent:
        pass

    event_mod.filter = _Filter()
    event_mod.AstrMessageEvent = AstrMessageEvent
    event_mod.EventMessageType = _EventMessageType

    star_mod = types.ModuleType("astrbot.api.star")

    class Star:
        def __init__(self, context=None):
            self.context = context

    class Context:
        pass

    def register(name, desc, author):
        def deco(cls):
            return cls

        return deco

    star_mod.Star = Star
    star_mod.Context = Context
    star_mod.register = register

    comp_mod = types.ModuleType("astrbot.api.message_components")

    class _BaseComponent:
        pass

    class Plain(_BaseComponent):
        def __init__(self, text=""):
            self.text = text

    class Record(_BaseComponent):
        def __init__(self, file=None, url=None):
            self.file = file
            self.url = url

    class Image(_BaseComponent):
        def __init__(self, file=None, url=None):
            self.file = file
            self.url = url

    comp_mod.Plain = Plain
    comp_mod.Record = Record
    comp_mod.Image = Image

    astrbot.api = api
    api.event = event_mod
    api.star = star_mod
    api.message_components = comp_mod

    sys.modules["astrbot"] = astrbot
    sys.modules["astrbot.api"] = api
    sys.modules["astrbot.api.event"] = event_mod
    sys.modules["astrbot.api.star"] = star_mod
    sys.modules["astrbot.api.message_components"] = comp_mod
