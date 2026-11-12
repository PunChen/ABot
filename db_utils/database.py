# -*- coding: utf-8 -*-
import datetime
import difflib
import os
import random
import re
import threading

from ..file_utils import FileUtils
from ..lang_utils import text as text_utils
from astrbot.api import logger

db_lock = threading.Lock()
base_dir = os.path.dirname(os.path.abspath(__file__))
data_file_name = "data.json"
record_file_name = "record.json"

# 学习语法分隔符: "问题 => 回答"; 多答案用 "|" 分隔
LEARN_SEP = "=>"
ANSWER_SEP = "|"

# L2 分词重合度阈值(Jaccard)
TOKEN_MATCH_THRESHOLD = 0.4


class DB:
    """对话知识库: data.json 为词条, record.json 为语录记录。"""

    def __init__(self, data_file_path=None, record_file_path=None):
        self.data = {}
        self.record = []
        self.loaded = False
        self.data_file_path = data_file_path or os.path.join(base_dir, data_file_name)
        self.record_file_path = record_file_path or os.path.join(base_dir, record_file_name)
        # 检索索引: 规范化key -> 原key; 原key -> token集合
        self._norm_keys = {}
        self._key_words = {}
        self.load()

    # ---------- 持久化 ----------

    def save(self):
        with db_lock:
            FileUtils.write_json(self.data_file_path, self.data)
            FileUtils.write_json(self.record_file_path, self.record)

    def load(self):
        dic_data = FileUtils.read_json(self.data_file_path, {})
        lst_record = FileUtils.read_json(self.record_file_path, [])
        with db_lock:
            # 覆盖式加载, 保证幂等
            self.data = dic_data if isinstance(dic_data, dict) else {}
            self.record = lst_record if isinstance(lst_record, list) else []
            self.loaded = True
            self._rebuild_index()

    def _rebuild_index(self):
        self._norm_keys = {}
        self._key_words = {}
        for key in self.data:
            self._index_key(key)

    def _index_key(self, key):
        norm = text_utils.normalize(key)
        if norm:
            self._norm_keys[norm] = key
        self._key_words[key] = text_utils.tokenize(norm or key)

    # ---------- 检索(三层) ----------

    def find(self, text):
        """三层检索: 规范化精确 -> 分词重合度 -> 编辑距离近似。"""
        if not self.loaded:
            self.load()
        q = text_utils.normalize(text)
        if not q:
            return None
        # L1: 规范化精确(大小写/标点/全半角差异均可命中)
        key = self._norm_keys.get(q)
        if key is not None:
            return self._answer(key)
        # L2: 分词重合度
        q_words = text_utils.tokenize(q)
        best, best_score = None, 0.0
        if q_words:
            for k, k_words in self._key_words.items():
                if not k_words:
                    continue
                score = len(q_words & k_words) / len(q_words | k_words)
                if score > best_score:
                    best, best_score = k, score
        if best is not None and best_score >= TOKEN_MATCH_THRESHOLD:
            return self._answer(best)
        # L3: 编辑距离兜底
        close = difflib.get_close_matches(q, list(self._norm_keys), n=3, cutoff=0.6)
        if close:
            originals = [self._norm_keys[c] for c in close]
            if len(originals) == 1:
                return self._answer(originals[0])
            return "did you mean: " + " / ".join(originals)
        return "sorry, i can not understand"

    def _answer(self, key):
        value = self.data.get(key)
        if isinstance(value, list):
            return random.choice(value) if value else None
        return value

    # ---------- 学习(LEARN 模式) ----------

    def update(self, text):
        """学习词条: "问题 => 回答" 或 "问题 => 回答1 | 回答2"。

        已存在的问题会合并新答案。返回给用户的反馈文本。
        """
        if not self.loaded:
            self.load()
        if LEARN_SEP not in text:
            return "learn usage: <question> => <answer>"
        key, _, value = text.partition(LEARN_SEP)
        key = key.strip()
        answers = [a.strip() for a in value.split(ANSWER_SEP) if a.strip()]
        if not key or not answers:
            return "learn usage: <question> => <answer>"
        norm = text_utils.normalize(key)
        existing = self._norm_keys.get(norm)
        if existing is not None:
            cur = self.data[existing]
            cur_list = cur if isinstance(cur, list) else [cur]
            new = [a for a in answers if a not in cur_list]
            if not new:
                return f"already known: {existing} => {cur_list}"
            self.data[existing] = cur_list + new
            self.save()
            return f"updated: {existing} => {self.data[existing]}"
        self.data[key] = answers[0] if len(answers) == 1 else answers
        self._index_key(key)
        self.save()
        return f"learned: {key} => {self.data[key]}"

    def forget(self, key):
        if not self.loaded:
            self.load()
        key = key.strip()
        if not key:
            return "usage: forget <question>"
        norm = text_utils.normalize(key)
        existing = self._norm_keys.get(norm)
        if existing is None:
            return f"no entry for: {key}"
        self.data.pop(existing, None)
        self._norm_keys.pop(norm, None)
        self._key_words.pop(existing, None)
        self.save()
        return f"forgot: {existing}"

    def learn_url(self, url, max_entries=30):
        """从网页学习: 抓正文 -> 提名词 -> 补全定义后入库。"""
        if not url:
            return "usage: crawl <url>"
        if not re.match(r"^https?://\S+$", url.strip()):
            return f"invalid url: {url}"
        from ..web_utils import crawler
        try:
            entries = crawler.crawl(url.strip(), max_entries=max_entries)
        except Exception as e:
            logger.error(f"learn_url failed: {e}")
            return f"crawl {url} failed: {e}"
        if not entries:
            return f"learned nothing from {url}"
        added = 0
        for term, summary in entries:
            norm = text_utils.normalize(term)
            if norm and norm not in self._norm_keys:
                self.data[term] = summary
                self._index_key(term)
                added += 1
        self.save()
        return f"learned {added}/{len(entries)} entries from {url}"

    # ---------- 记录(RECORD 模式) ----------

    def insert(self, text):
        """记录一句话并即时落盘。"""
        if not self.loaded:
            self.load()
        obj = {
            "time": str(datetime.datetime.now()),
            "text": text,
        }
        self.record.append(obj)
        self.save()
        return f"recorded: {text}"

    def clear_records(self):
        if not self.loaded:
            self.load()
        count = len(self.record)
        self.record = []
        self.save()
        return f"cleared {count} records"

    def records_text(self):
        if not self.loaded:
            self.load()
        if not self.record:
            return "(no records yet)"
        return "\n".join(f"{item.get('time')} {item.get('text')}" for item in self.record)

    # ---------- 汇总(record -> 知识) ----------

    _RE_IS = re.compile(r"^(.{1,30}?)\s+is\s+(.{1,200})$", re.I)
    _RE_ZH_IS = re.compile(r"^(.{1,30}?)\s*是\s*(.{1,200})$")
    _RE_MY_NAME = re.compile(r"^my name is\s+(\S.{0,29})$", re.I)
    _RE_ZH_NAME = re.compile(r"^(?:我叫|我的名字是)\s*(\S.{0,29})$")

    def _pattern_entry(self, raw):
        """从语句中抽取结构化词条, 无匹配返回 (None, None)。"""
        m = self._RE_MY_NAME.match(raw)
        if m:
            return "name", m.group(1).strip()
        m = self._RE_ZH_NAME.match(raw)
        if m:
            return "名字", m.group(1).strip()
        m = self._RE_IS.match(raw)
        if m:
            return m.group(1).strip(), m.group(2).strip()
        m = self._RE_ZH_IS.match(raw)
        if m:
            return m.group(1).strip(), m.group(2).strip()
        return None, None

    def summarize_records(self, keep=False):
        """把 record 汇总入知识集合(readme TODO #3)。

        规则: 结构化句式("X is Y"/"X 是 Y"/"my name is X"...)抽为词条;
        其余取首个名词 => 原句。默认清空已汇总的记录, keep=True 保留。
        """
        if not self.loaded:
            self.load()
        imported, empty = 0, 0
        for item in list(self.record):
            raw = str(item.get("text") or "").strip()
            if not raw:
                empty += 1
                continue
            key, value = self._pattern_entry(raw)
            if key is None:
                nouns = text_utils.extract_nouns(raw, top=1)
                if nouns:
                    key, value = nouns[0], raw
            if key is None:
                continue
            norm = text_utils.normalize(key)
            if not norm or norm in self._norm_keys:
                continue
            self.data[key] = value
            self._index_key(key)
            imported += 1
        if imported:
            self.save()
        if not keep:
            self.record = []
            self.save()
        return f"imported {imported} entries, {len(self.record)} records left"
