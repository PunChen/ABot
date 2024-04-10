from bot_utils.bot import Bot
from command_utils.Command import Command
from lang_utils import language
if __name__ == '__main__':
    bot = Bot()
    bot.set_running(True)
    while bot.is_running():
        text = input()
        if len(text) == 0:
            continue
        elif text == Command.STOP.value:
            bot.set_running(False)
            continue
        elif text.startswith(Command.SWITCH.value):
            value_str = text.split(" ")[-1]
            value = int(value_str)
            bot.switch_status(value)
            continue
        ret = bot.on_text(text)
        print("{}".format(ret))
        filename = language.text2audio(ret)
        language.play_audio(filename)

