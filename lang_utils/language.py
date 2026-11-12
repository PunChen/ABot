# -*- coding: utf-8 -*-
"""语音能力: 语音识别(ASR)与语音合成(TTS)。

- ASR: 装有 faster-whisper 时中英文都用它(本地离线);
  否则英文退回 Sphinx(SpeechRecognition), 中文提示安装指引。
- TTS: pyttsx4(系统语音, 输出 wav, AstrBot Record 组件只收 wav),
  按语言选择音色(Windows SAPI5 自带中文音色, Linux 需 espeak)。
- prepare_wav: 把收到的语音(URL/本地文件, QQ silk 格式)转成可识别的 wav。
所有重依赖均为可选导入, 缺失时降级并给出日志指引。
"""
import os
import re
import tempfile
import threading
import time
import urllib.request
import wave
from urllib.parse import unquote

from ..const_utils.constant import Language
from astrbot.api import logger

# 语音文件统一放插件根目录 audios/ 下(绝对路径, 不随工作目录漂移)
AUDIO_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "audios"
)
USER_AGENT = "ABot/1.0 (https://github.com/PunChen/ABot)"
DOWNLOAD_TIMEOUT = 30
# QQ(silk) 语音常见采样率
SILK_SAMPLE_RATE = 24000

_engine = None
_engine_lock = threading.Lock()
_whisper_model = None

# 本地 ASR 可选引擎: faster-whisper(中英文, 需 pip install faster-whisper)
WHISPER_MODEL_SIZE = "base"


def _log_and_return_none(message):
    logger.warning(message)
    return None


def _get_engine():
    global _engine
    if _engine is None:
        import pyttsx4

        _engine = pyttsx4.Engine()
    return _engine


def _select_voice(engine, lang):
    """按语言挑选系统音色(zh/en)。"""
    want = "zh" if lang == Language.CHINESE else "en"
    try:
        voices = engine.getProperty("voices") or []
    except Exception:
        return None
    for voice in voices:
        voice_id = str(getattr(voice, "id", "") or "").lower()
        langs = getattr(voice, "languages", None) or []
        langs = [
            item.decode(errors="ignore") if isinstance(item, bytes) else str(item)
            for item in langs
        ]
        for tag in [voice_id] + [str(x).lower() for x in langs]:
            if want in tag:
                return voice
    return None


def _whisper_available():
    try:
        import faster_whisper  # noqa: F401

        return True
    except ImportError:
        return False


def _asr_whisper(audio_file, lang):
    global _whisper_model
    try:
        from faster_whisper import WhisperModel

        if _whisper_model is None:
            _whisper_model = WhisperModel(WHISPER_MODEL_SIZE)
        language = "zh" if lang == Language.CHINESE else "en"
        segments, _info = _whisper_model.transcribe(audio_file, language=language)
        return "".join(seg.text for seg in segments).strip() or None
    except Exception as e:
        logger.error(f"whisper asr failed: {e}")
        return None


def _asr_sphinx(audio_file):
    import speech_recognition as sr

    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_file) as source:
        audio = recognizer.record(source)  # read the entire audio file
    # recognize speech using Sphinx(仅英文, 离线)
    try:
        return recognizer.recognize_sphinx(audio)
    except sr.UnknownValueError:
        logger.error("Sphinx could not understand audio")
    except sr.RequestError as e:
        logger.error(f"Sphinx error; {e}")
    return None


def audio2text(audio_file, lang=Language.ENGLISH):
    """语音转文本。whisper 可用时中英文通用, 否则仅英文(Sphinx)。"""
    if not audio_file or not os.path.exists(audio_file):
        return None
    if _whisper_available():
        return _asr_whisper(audio_file, lang)
    if lang == Language.ENGLISH:
        return _asr_sphinx(audio_file)
    return _log_and_return_none(
        "chinese asr needs faster-whisper (pip install faster-whisper) "
        "or AstrBot provider STT"
    )


def text2audio(text, lang=Language.ENGLISH):
    """文本转语音(wav)。失败返回 None(调用方回退纯文本)。"""
    if not text:
        return None
    try:
        os.makedirs(AUDIO_DIR, exist_ok=True)
        filename = os.path.join(AUDIO_DIR, f"{int(time.time() * 1000)}.wav")
        with _engine_lock:
            engine = _get_engine()
            voice = _select_voice(engine, lang)
            if voice is not None:
                engine.setProperty("voice", voice.id)
            engine.save_to_file(text, filename)
            engine.runAndWait()
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            return filename
        logger.error(f"text2audio produced empty file for: {text}")
    except Exception as e:
        logger.error(f"text2audio failed for: {text}, error: {e}")
    return None


# ---------- 收到语音的预处理 ----------

def _download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT) as resp, open(
        dest, "wb"
    ) as fp:
        fp.write(resp.read())
    return dest


def _silk_to_wav(src, dest):
    """QQ silk 语音 -> wav(经 pilk 解码为 pcm 后封装)。"""
    import pilk

    with tempfile.NamedTemporaryFile(suffix=".pcm", delete=False) as tmp:
        pcm_path = tmp.name
    try:
        pilk.decode(src, pcm_path, sample_rate=SILK_SAMPLE_RATE)
        with open(pcm_path, "rb") as pcm_fp:
            pcm_data = pcm_fp.read()
        with wave.open(dest, "wb") as wav_fp:
            wav_fp.setnchannels(1)
            wav_fp.setsampwidth(2)
            wav_fp.setframerate(SILK_SAMPLE_RATE)
            wav_fp.writeframes(pcm_data)
        return dest
    finally:
        try:
            os.remove(pcm_path)
        except OSError:
            pass


def prepare_wav(source):
    """把语音来源(URL 或本地路径)整理成 wav 本地文件, 失败返回 None。

    支持直接 wav 与 QQ silk(pilk 转码); 其他格式给出日志指引。
    """
    if not source:
        return None
    try:
        os.makedirs(AUDIO_DIR, exist_ok=True)
        local = source
        if local.startswith("file://"):
            # Lagrange 等适配器会给出 file:///D:/xx.amr 形式
            local = unquote(local[len("file://"):])
            local = re.sub(r"^/(?=[A-Za-z]:)", "", local)  # Windows 盘符前多余斜杠
        if re.match(r"^https?://", local):
            dest = os.path.join(AUDIO_DIR, f"inbox_{int(time.time() * 1000)}.bin")
            local = _download(local, dest)
        if not local or not os.path.exists(local):
            return None
        lower = local.lower()
        if lower.endswith(".wav"):
            return local
        silk_like = lower.endswith((".silk", ".slk")) or _is_silk(local)
        if silk_like:
            wav_path = re.sub(r"\.[^.]+$", "", local) + ".wav"
            return _silk_to_wav(local, wav_path)
        return _log_and_return_none(
            f"unsupported voice format: {local} "
            "(expect wav/silk; configure platform to output wav or install pilk)"
        )
    except ImportError:
        return _log_and_return_none(
            "silk voice needs pilk: pip install pilk"
        )
    except Exception as e:
        logger.error(f"prepare_wav failed for {source}: {e}")
        return None


def _is_silk(path):
    """silk v3 文件以 \\x02 ( PAT 块)开头且含 '#!SILK' 头。"""
    try:
        with open(path, "rb") as fp:
            head = fp.read(10)
        return b"#!SILK" in head or head[:1] == b"\x02"
    except OSError:
        return False


if __name__ == "__main__":
    # lyric = "冷咖啡离开乐杯垫，我忍住的情绪在很后面"
    # lyric = "hello from the other side, i wish i could never die"
    lyric = "it has been a long day without you my friend, i will tell you all about it when i see you again"
    filepath = text2audio(lyric)
    logger.info(f"tts output: {filepath}")
