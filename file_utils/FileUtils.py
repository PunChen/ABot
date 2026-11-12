import json
import os
from astrbot.api import logger


def pre_check(path):
    if len(path) == 0:
        return
    try:
        if not os.path.exists(path):
            with open(path, "a+", encoding='utf-8') as f:
                pass
    except Exception as e:
        logger.error(f"pre_check fail: {e}")


def read_file(path):
    pre_check(path)
    lines = []
    try:
        with open(path, 'r', encoding='utf-8') as fp:
            lines += fp.readlines()
        return lines
    except Exception as e:
        logger.error(f"read_file fail: {e}")
    return lines


def write_json(path, data):
    """原子写入: 先写临时文件再替换, 避免进程中断留下半个 json。"""
    pre_check(path)
    tmp_path = f"{path}.tmp"
    try:
        with open(tmp_path, 'w', encoding='utf-8') as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
        return True
    except Exception as e:
        logger.error(f"write_json fail: {e}")
    return False


def read_json(path, default):
    pre_check(path)
    try:
        with open(path, 'r', encoding='utf-8') as fp:
            content = fp.read().strip()
            if not content:
                return default
            return json.loads(content)
    except Exception as e:
        logger.error(f"read_json fail: {e}")
    return default


def read_json_from_fp(fp, default):
    res = default
    try:
        res = json.load(fp)
        return res
    except Exception as e:
        logger.error(f"read_json_from_fp fail: {e}")
    return res


def get_write_file_pointer(path):
    pre_check(path)
    try:
        fp = open(path, 'w+', encoding='utf-8')
        return fp
    except Exception as e:
        logger.error(f"get_write_file_pointer fail: {e}")
    return None


def get_read_file_pointer(path):
    pre_check(path)
    try:
        fp = open(path, 'r', encoding='utf-8')
        return fp
    except Exception as e:
        logger.error(f"get_read_file_pointer fail: {e}")
    return None


def append_file_content(line, path):
    try:
        with open(path, 'a+', encoding='utf-8') as fp:
            fp.write(line)
        return True
    except Exception as e:
        logger.error(f"append_file_content fail: {e}")
    return False
