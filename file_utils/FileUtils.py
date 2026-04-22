import json
import os
from astrbot.api import logger


def pre_check(path):
    if len(path) == 0:
        return
    try:
        ind = str(path).rfind(os.sep)
        if ind != -1:
            dirs = path[:ind]
            if not os.path.exists(dirs):
                os.makedirs(dirs)
        with open(path, "a+", encoding='utf-8') as f:
            pass
    except Exception as e:
        logger.error("pre_check fail: ", e)
    pass


def read_file(path):
    pre_check(path)
    lines = []
    try:
        with open(path, 'r', encoding='utf-8') as fp:
            lines += fp.readlines()
        return lines
    except Exception as e:
        logger.error("read_file fail: ", e)
    return lines


def write_json(path, data):
    pre_check(path)
    try:
        fp = open(path, 'w+', encoding='utf-8')
        json.dump(data, fp)
        return True
    except Exception as e:
        logger.error("write_json fail: ", e)
    return False


def read_json(path, default):
    pre_check(path)
    res = default
    try:
        fp = open(path, 'r', encoding='utf-8')
        res = json.load(fp)
        return res
    except Exception as e:
        logger.error("read_json fail: ", e)
    return res


def read_json_from_fp(fp, default):
    res = default
    try:
        res = json.load(fp)
        return res
    except Exception as e:
        logger.error("read_json_from_fp fail: ", e)
    return res


def get_write_file_pointer(path):
    pre_check(path)
    try:
        fp = open(path, 'w+', encoding='utf-8')
        return fp
    except Exception as e:
        logger.error("get_write_file_pointer fail: ", e)
    pass


def get_read_file_pointer(path):
    pre_check(path)
    try:
        fp = open(path, 'r', encoding='utf-8')
        return fp
    except Exception as e:
        logger.error("get_read_file_pointer fail: ", e)
    pass


def append_file_content(line, path):
    try:
        with open(path, 'a+', encoding='utf-8') as fp:
            fp.write(line)
        return True
    except Exception as e:
        logger.error("append_file_content fail: ", e)
    return False
