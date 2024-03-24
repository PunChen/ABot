from multiprocessing import Lock
from file_utils import FileUtils
import datetime

db_lock = Lock()

data_file_name = "db_utils/data.txt"
record_file_name = "db_utils/record.txt"


class DB:

    def __init__(self):
        self.data = {}
        self.record = []
        self.data_fp = None
        self.record_fp = None
        self.loaded = False
        self.load()

    def load(self):
        global db_lock
        # read data file and record file
        lst_data = FileUtils.read_file(data_file_name)
        lst_record = FileUtils.read_file(record_file_name)
        # load to memory
        with db_lock:
            self.data['hello'] = "hi"
            self.data['hi'] = "helo"
            self.data['who are you'] = "I am Abot, an AGI bot designed for instant conversation"
            self.data['what can you help'] = "I can help you with talking and recording"
            for line in lst_data:
                arr = line.split("\t")
                if len(arr) == 2:
                    self.data[arr[0]] = arr[1]
            self.record += lst_record
            self.loaded = True
        pass

    def find(self, text):
        if not self.loaded:
            return text
        # todo find optimization
        if self.data.__contains__(text):
            return self.data[text]
        return None

    def update(self, text):
        if not self.loaded:
            self.load()
        # todo update
        return None

    def insert(self, text):
        if not self.loaded:
            self.load()
        key = datetime.datetime.now()
        line = "{}\t{}\n".format(key, text)
        self.record.append(line)
        res = FileUtils.append_file_content(line, record_file_name)
        print("insert : {}".format(res))
        return None
