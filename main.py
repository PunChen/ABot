from .bot_utils.bot import Bot
from .command_utils.Command import Command
from .lang_utils import language
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger  # 使用 astrbot 提供的 logger 接口

bot = None


def process_event(text):
    global bot
    if bot is None:
        bot = Bot()
        bot.set_running(True)
    if len(text) == 0:
        return None
    elif text.startswith(Command.SWITCH.value):
        value_str = text.split(" ")[-1]
        value = int(value_str)
        ret = bot.switch_status(value)
        return ret
    else:
        ret = bot.on_text(text)
        logger.warning("process_event return :{}".format(ret))
        # filename = language.text2audio(ret)
        # language.play_audio(filename)
        return ret


class ABot(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    # 注册指令的装饰器。指令名为 helloworld。注册成功后，发送 `/helloworld` 就会触发这个指令，并回复 `你好, {user_name}!`
    @filter.command("abot")
    async def abot(self, event: AstrMessageEvent):
        """abot 命令接文本消息"""  # 这是 handler 的描述，将会被解析方便用户了解插件内容。非常建议填写。
        user_name = event.get_sender_name()
        message_str = event.message_str.removeprefix('abot ')  # abot+空格
        message_ret = process_event(message_str)
        if message_ret is None:
            return
        yield event.plain_result(f"received: {message_str}\nsender: {user_name}\nresponse: {message_ret}")  # 发送一条纯文本消息

    async def terminate(self):
        """可选择实现 terminate 函数，当插件被卸载/停用时会调用。"""
        logger.info("abot plugin stopped")


if __name__ == '__main__':
    text = input()
    process_event(text)
