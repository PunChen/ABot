from enum import Enum


class Command(Enum):
    SWITCH = "switch"
    RECORDS = "records"
    STOP = "stop"
    HELP = "help"
    FORGET = "forget"
    SUMMARY = "summary"
    LANG = "lang"
    VOICE = "voice"
    CRAWL = "crawl"

    @staticmethod
    def values():
        return [c.value for c in Command]

    @staticmethod
    def match(text):
        """文本首词命中某命令时返回 (Command, 余下参数)，否则返回 (None, text)"""
        if not text:
            return None, text
        parts = text.split(None, 1)
        first = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""
        for cmd in Command:
            if cmd.value == first:
                return cmd, rest
        return None, text
