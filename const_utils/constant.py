from enum import Enum


def contains_value(clazz, value):
    for key in clazz.__members__.keys():
        if clazz.__getitem__(key).value == value:
            return True
    return False


def contains_name(clazz, name=str):
    return clazz.__members__.keys().__contains__(name)


def name2value(clazz, name=str):
    if clazz.__members__.keys().__contains__(name):
        return clazz.__getitem__(name)
    return None


def value2name(clazz, value):
    for key in clazz.__members__.keys():
        if clazz.__getitem__(key).value == value:
            return True
    return False


class Language(Enum):
    CHINESE = "chinese"
    ENGLISH = "english"


class BotStatus(Enum):
    INIT = 0
    TALK = 1
    LEARN = 2
    RECORD = 3
