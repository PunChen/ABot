# -*- coding: utf-8 -*-
"""ABot 插件入口。

- `abot` 命令: 单一入口, 子命令在 process_event 内统一分发
- 语音消息监听: Record/silk -> wav -> ASR -> 按当前模式处理
所有阻塞操作(db/tts/asr/crawl)经 asyncio.to_thread 下放线程池, 不卡事件循环。
"""
import asyncio

import astrbot.api.message_components as Comp
from .bot_utils.bot import Bot
from .command_utils.Command import Command
from .lang_utils import language
from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star

bot = None

# 语音输入默认仅私聊响应, 避免群聊被语音刷屏
VOICE_PRIVATE_ONLY = True

HELP_TEXT = """abot commands:
  abot <text>                  talk to abot (depends on mode)
  abot switch <0-3>            switch mode: 0=init 1=talk 2=record 3=learn
  abot records [clear]         show / clear records
  abot summary [keep]          import records into knowledge
  abot forget <question>       remove a learned entry
  abot crawl <url>             learn terms from a webpage
  abot lang <chinese|english>  language for voice
  abot voice <on|off>          reply with voice
  abot stop                    stop abot and save
  abot help                    show this help
learn mode: 'abot <question> => <answer>' or 'abot <url>'"""


def _ensure_bot():
    global bot
    if bot is None:
        bot = Bot()
        bot.set_running(True)
    return bot


def process_event(text):
    """同步命令分发与对话入口(插件线程池与 CLI 共用)。"""
    text = (text or "").strip()
    if not text:
        return HELP_TEXT
    _ensure_bot()
    cmd, args = Command.match(text)
    # 停止状态下仅保留 help/stop/switch(用于重启)
    if cmd == Command.HELP:
        return HELP_TEXT
    if cmd == Command.STOP:
        if bot.is_running():
            bot.set_running(False)
            return "bot stopped, data saved. send 'abot switch <mode>' to restart"
        return "bot is already stopped"
    if cmd == Command.SWITCH:
        value = args.split()[0] if args else ""
        if not value.lstrip("-").isdigit():
            return "usage: switch <0-3>  (0=init 1=talk 2=record 3=learn)"
        return bot.switch_status(int(value))
    if not bot.is_running():
        return "bot is stopped. send 'abot switch <1-3>' to restart"
    if cmd == Command.RECORDS:
        if args.strip() == "clear":
            return bot.clear_records()
        return bot.on_records()
    if cmd == Command.SUMMARY:
        return bot.summarize_records(keep=args.strip() == "keep")
    if cmd == Command.FORGET:
        if not args.strip():
            return "usage: forget <question>"
        return bot.forget(args.strip())
    if cmd == Command.LANG:
        return bot.set_language(args)
    if cmd == Command.VOICE:
        return bot.set_voice_reply(args)
    if cmd == Command.CRAWL:
        return bot.learn_url(args.strip())
    # 普通文本: 按当前模式处理
    return bot.on_text(text)


# ---------- 语音消息辅助 ----------

def _is_private_chat(event):
    try:
        return bool(event.is_private_chat())
    except Exception:
        return True


def _extract_voice_source(event):
    """从消息链/原始 OneBot 事件中提取语音来源(本地路径或 URL)。

    AstrBot 开启 provider STT 时会把 Record 段替换成 Plain,
    所以要同时检查原始 OneBot 事件兜底。
    """
    # 1) 当前消息链(STT 未替换时 Record 仍在)
    try:
        for seg in (event.message_obj.message or []):
            if isinstance(seg, Comp.Record):
                src = getattr(seg, "url", None) or getattr(seg, "file", None)
                if src:
                    return str(src)
    except Exception:
        pass
    # 2) 原始 OneBot 事件兜底
    try:
        raw = getattr(event.message_obj, "raw_message", None)
        segments = (
            raw.get("message") if isinstance(raw, dict)
            else getattr(raw, "message", None)
        )
        if isinstance(segments, list):
            for seg in segments:
                if isinstance(seg, dict) and seg.get("type") == "record":
                    data = seg.get("data") or {}
                    src = data.get("url") or data.get("file")
                    if src:
                        return str(src)
    except Exception:
        pass
    return None


class ABot(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command("abot")
    async def abot(self, event: AstrMessageEvent):
        """abot 命令: 对话/学习/记录/管理, 详见 'abot help'"""
        message_str = event.message_str.removeprefix("abot").strip()
        message_ret = await asyncio.to_thread(process_event, message_str)
        if message_ret is None:
            return
        result = await self._build_result(event, message_ret)
        yield result

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_voice_message(self, event: AstrMessageEvent):
        """语音消息 -> ASR -> 按当前模式处理(语音输入闭环)。"""
        try:
            if bot is None or not bot.is_running():
                return
            if VOICE_PRIVATE_ONLY and not _is_private_chat(event):
                return
            source = _extract_voice_source(event)
            if not source:
                return  # 非语音消息, 交给命令处理器
            # AstrBot STT 已转写时直接用转写文本
            text = (event.message_str or "").strip()
            if text:
                # 语音里带了唤醒词就去掉, 避免和命令处理器双重响应
                text = text.removeprefix("abot").strip() or text
            else:
                wav = await asyncio.to_thread(language.prepare_wav, source)
                if wav:
                    text = await asyncio.to_thread(
                        language.audio2text, wav, bot.language
                    )
                else:
                    logger.warning(f"voice prepare failed: {source}")
            if not text:
                result = event.plain_result("sorry, i can not understand the audio")
                event.stop_event()
                yield result
                return
            logger.info(f"voice recognized: {text}")
            message_ret = await asyncio.to_thread(process_event, text)
            if message_ret is None:
                return
            result = await self._build_result(event, message_ret)
            event.stop_event()  # 已处理, 阻止其他插件/LLM 重复响应
            yield result
        except Exception as e:
            logger.error(f"handle voice failed: {e}")

    async def _build_result(self, event, message_ret):
        """语音回复开关开启且 TTS 成功 -> 语音消息, 否则纯文本。"""
        if bot is not None and bot.voice_reply:
            path = await asyncio.to_thread(
                language.text2audio, str(message_ret), bot.language
            )
            if path:
                return event.chain_result([Comp.Record(file=path, url=path)])
            logger.warning("tts failed, fallback to plain text")
        return event.plain_result(message_ret)

    async def terminate(self):
        """插件被卸载/停用时调用: 停止并保存。"""
        global bot
        if bot is not None:
            bot.set_running(False)
            bot = None
        logger.info("abot plugin stopped")


if __name__ == "__main__":
    # 本地 CLI 调试: 在本目录的父目录下执行 `python -m ABot.main`
    print("abot (cli). type 'help' for commands, ctrl+c to exit.")
    while True:
        try:
            text = input("abot> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            break
        ret = process_event(text)
        if ret:
            print(ret)
