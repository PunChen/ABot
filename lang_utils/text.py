# -*- coding: utf-8 -*-
"""文本处理工具: 规范化、分词、名词提取。

被三处复用:
- db_utils.database  的三层检索(find)
- db_utils.database  的 record 汇总(summarize)
- web_utils.crawler  的网页名词提取

jieba 缺失时自动降级(空格切分), 不影响插件加载。
"""
import re
import unicodedata

try:
    import jieba
    import jieba.posseg

    _JIEBA_AVAILABLE = True
except ImportError:  # pragma: no cover - 取决于运行环境
    _JIEBA_AVAILABLE = False

# 中英文常见停用词
STOPWORDS = {
    # english
    "the", "a", "an", "is", "are", "am", "was", "were", "be", "been",
    "of", "to", "in", "on", "at", "for", "and", "or", "but", "if",
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her",
    "my", "your", "his", "its", "our", "their", "this", "that",
    "what", "which", "who", "whom", "how", "when", "where", "why",
    "can", "could", "will", "would", "shall", "should", "may", "might",
    "do", "does", "did", "not", "no", "yes", "so", "as", "by", "with",
    "from", "about", "into", "than", "then", "there", "here", "up", "down",
    "please", "tell", "say", "said", "just", "very", "also", "some",
    # chinese
    "的", "了", "是", "在", "我", "你", "他", "她", "它", "们",
    "和", "与", "就", "也", "都", "而", "及", "着", "或", "一个",
    "没有", "我们", "你们", "他们", "什么", "怎么", "哪", "谁",
    "吗", "呢", "啊", "吧", "呀", "哦", "嗯", "这", "那", "些",
    "有", "人", "去", "来", "说", "要", "会", "能", "好", "很",
}

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_WORD_RE = re.compile(r"[\w\u4e00-\u9fff]+")


def is_jieba_available():
    return _JIEBA_AVAILABLE


def normalize(text):
    """规范化: 全角->半角(NFKC) + 小写 + 去标点 + 压缩空白。

    "Ｈｅｌｌｏ, World!" -> "hello world"; "什么是时间？" -> "什么是时间"
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", str(text)).lower()
    words = _WORD_RE.findall(text)
    return " ".join(words)


def tokenize(text):
    """分词并去停用词, 返回 token 集合。中文依赖 jieba, 英文按空格。"""
    if not text:
        return set()
    text = str(text)
    if _CJK_RE.search(text) and _JIEBA_AVAILABLE:
        raw_tokens = jieba.lcut(text)
    else:
        raw_tokens = text.split()
    tokens = set()
    for token in raw_tokens:
        token = token.strip().lower()
        if not token or token in STOPWORDS:
            continue
        tokens.add(token)
    return tokens


def extract_nouns(text, top=20):
    """提取名词(词条候选), 顺序去重, 最多 top 个。

    jieba 可用时按词性标注取 n* 开头的词;
    否则降级为"长度>=2 的非停用词"。
    """
    if not text:
        return []
    text = str(text)
    if _CJK_RE.search(text) and _JIEBA_AVAILABLE:
        nouns = [w for w, flag in jieba.posseg.lcut(text) if flag.startswith("n")]
    else:
        nouns = [w for w in tokenize(text) if len(w) >= 2]
    return list(dict.fromkeys(nouns))[:top]


def looks_chinese(text):
    """文本是否以中文为主(用于选择 wiki 语言)。"""
    if not text:
        return False
    cjk = len(_CJK_RE.findall(text))
    return cjk * 2 >= len(text)
