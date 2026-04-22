from multiprocessing import Lock
from ..file_utils import FileUtils
import datetime
import os
from astrbot.api import logger

db_lock = Lock()
base_dir = os.path.dirname(os.path.abspath(__file__))
data_file_name = "data.json"
record_file_name = "record.json"


class DB:

    def __init__(self):
        self.data = {}
        self.record = []
        self.loaded = False
        self.data_file_path = os.path.join(base_dir, data_file_name)
        self.record_file_path = os.path.join(base_dir, record_file_name)
        self.load()

    def save(self):
        FileUtils.write_json(self.data_file_path, self.data)
        FileUtils.write_json(self.record_file_path, self.record)
        pass

    def load(self):
        global db_lock
        # read data file and record file
        dic_data = FileUtils.read_json(self.data_file_path, {})
        lst_record = FileUtils.read_json(self.record_file_path, [])
        # load to memory
        with db_lock:
            self.data.update(dic_data)
            self.record += lst_record
            self.loaded = True
        pass

    def find(self, text):
        if not self.loaded:
            self.load()
        # todo find optimization
        logger.warn(f"data:{self.data}")
        if self.data.__contains__(text):
            return self.data[text]
        return "sorry, i can not understand"

    def update(self, text):
        if not self.loaded:
            self.load()
        # todo update
        return None

    def insert(self, text):
        if not self.loaded:
            self.load()
        key = datetime.datetime.now()
        obj = {
            "time": str(key),
            "text": text
        }
        self.record.append(obj)
        return None
