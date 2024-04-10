from multiprocessing import Lock

from const_utils import constant
from const_utils.constant import BotStatus
from db_utils import database
from lang_utils import language

status_lock = Lock()


class Bot:
    def __init__(self):
        self.status = BotStatus.INIT
        self.db_inst = database.DB()
        self.status = BotStatus.TALK
        self.running = False

    def is_running(self):
        return self.running

    def set_running(self, running):
        self.running = running
        text = "hello, what can i help?"
        print(text)
        filename = language.text2audio(text)
        language.play_audio(filename)
        pass

    def switch_status(self, status_value):
        with status_lock:
            if constant.contains_value(BotStatus, status_value):
                tgt_status = BotStatus(status_value)
                print("try switch status: {} -> {}".format(self.status, tgt_status))
                self.status = tgt_status
                print("switch to status: {} success".format(status_value))
            else:
                print("switch to status: {} failed".format(status_value))

    def on_text(self, text):
        res = None
        if self.status == BotStatus.INIT:
            res = "init: bot not ready!"
        elif self.status == BotStatus.TALK:
            # talk mode : search and react using database
            res = self.db_inst.find(text)

        elif self.status == BotStatus.LEARN:
            # learn mode : learn every sentence and try update database
            res = self.db_inst.update(text)

        elif self.status == BotStatus.RECORD:
            # record mode : record every word you said to Abot
            res = self.db_inst.insert(text)
        return res

    def on_voice(self, audio):
        print("on_voice try parse audio...")
        text = language.audio2text(audio)
        res = self.on_text(text)
        return res

    pass
