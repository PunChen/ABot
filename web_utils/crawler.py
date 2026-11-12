# -*- coding: utf-8 -*-
"""网页知识抓取(readme TODO #1/#2): 抓正文 -> 分词提名词 -> 递归补全定义。

依赖 requests + trafilatura(requirements.txt 提供), 缺失时降级:
- 无 requests: 拒绝抓取并提示
- 无 trafilatura: 正则粗抽正文
每次请求间隔限速, 词条总量设上限, 防止刷爆知识库。
"""
import re
import time
from urllib.parse import quote, unquote

from ..lang_utils import text as text_utils
from astrbot.api import logger

try:
    import requests

    _REQUESTS_AVAILABLE = True
except ImportError:  # pragma: no cover - 取决于运行环境
    _REQUESTS_AVAILABLE = False

# Wikipedia 官方 REST API(摘要), 适合"名词 -> 定义"的递归抓取
WIKI_API = "https://{lang}.wikipedia.org/api/rest_v1/page/summary/{term}"
USER_AGENT = "ABot/1.0 (https://github.com/PunChen/ABot)"
REQUEST_TIMEOUT = 10

_WIKI_PAGE_RE = re.compile(r"^https?://(\w+)\.wikipedia\.org/wiki/([^/?#]+)")


def is_available():
    return _REQUESTS_AVAILABLE


def fetch(url, timeout=REQUEST_TIMEOUT):
    """抓取网页并抽取正文文本, 失败返回 None。"""
    if not _REQUESTS_AVAILABLE:
        logger.warning("crawl requires requests: pip install requests")
        return None
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        return _extract_text(resp.text)
    except Exception as e:
        logger.error(f"fetch {url} failed: {e}")
        return None


def _extract_text(html):
    try:
        import trafilatura

        text = trafilatura.extract(html)
        if text:
            return text
    except ImportError:
        pass
    except Exception as e:  # trafilatura 抽取失败 -> 降级
        logger.warning(f"trafilatura extract failed: {e}")
    # 降级: 粗暴去标签
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-z]+;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def wiki_summary(term, lang="zh", timeout=REQUEST_TIMEOUT):
    """查 Wikipedia 摘要, 失败返回 None。"""
    if not _REQUESTS_AVAILABLE:
        return None
    url = WIKI_API.format(lang=lang, term=quote(term))
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
        if resp.status_code != 200:
            return None
        data = resp.json()
        return data.get("extract") or None
    except Exception as e:
        logger.error(f"wiki_summary({term}) failed: {e}")
        return None


def _first_sentence(text, limit=200):
    for sep in ("。", ". ", "！", "! ", "？", "? "):
        idx = text.find(sep)
        if 0 < idx < limit:
            return text[: idx + 1].strip()
    return text[:limit].strip()


def crawl(url, max_entries=30, depth=1, rate=1.0):
    """抓取 url: 正文提名词 -> 每个名词取 wiki 摘要首句为词条。

    depth=1: 页面名词 -> 定义; depth=2 会再对摘要提名词展开一层(慢, 慎用)。
    返回 [(term, summary), ...], 最多 max_entries 条。
    """
    if not _REQUESTS_AVAILABLE:
        logger.warning("crawl requires requests: pip install requests")
        return []
    if depth > 2:
        depth = 2  # 递归深度上限, 防止抓取失控
    page_text = fetch(url)
    if not page_text:
        return []
    entries = []
    seen = set()
    wiki_lang = "zh" if text_utils.looks_chinese(page_text) else "en"
    # url 本身是 wiki 页时, 页面主题直接成词条
    m = _WIKI_PAGE_RE.match(url)
    if m:
        lang_code, topic = m.group(1), unquote(m.group(2)).replace("_", " ")
        summary = wiki_summary(topic, lang=lang_code)
        if summary:
            entries.append((topic, _first_sentence(summary)))
            seen.add(text_utils.normalize(topic))
    frontier = text_utils.extract_nouns(page_text, top=max_entries * 2)
    for level in range(depth):
        next_frontier = []
        for term in frontier:
            if len(entries) >= max_entries:
                break
            norm = text_utils.normalize(term)
            if not norm or norm in seen:
                continue
            seen.add(norm)
            summary = wiki_summary(term, lang=wiki_lang)
            time.sleep(rate)  # 限速
            if summary:
                entries.append((term, _first_sentence(summary)))
                if level + 1 < depth:
                    next_frontier.extend(text_utils.extract_nouns(summary, top=5))
        frontier = next_frontier
    return entries
