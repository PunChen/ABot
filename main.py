from bot_utils.bot import Bot
from command_utils.Command import Command
if __name__ == '__main__':
    bot = Bot()
    running = True
    while running:
        text = input()
        if len(text) == 0:
            continue
        elif text == Command.STOP.value:
            running = False
            break
        elif text.startswith(Command.SWITCH.value):
            value_str = text.split(" ")[-1]
            value = int(value_str)
            bot.switch_status(value)
            continue
        ret = bot.on_text(text)
        print("Abot: {}".format(ret))
