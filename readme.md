# ABot

> 一个用数据库检索驱动的对话机器人，AstrBot 插件（`>=4.17.0`）。

## 功能

| 能力 | 说明 |
|---|---|
| 对话 TALK | 三层检索知识库：规范化精确匹配 → jieba 分词重合度 → 编辑距离近似 |
| 学习 LEARN | `问题 => 回答`（多答案用 `|` 分隔）；支持从网页/维基百科递归抓取词条 |
| 记录 RECORD | 记录用户语录，`summary` 命令把记录汇总进知识库 |
| 语音 | 语音输入（Record/silk → wav → ASR）、语音回复（TTS，`voice on` 开启） |
| 多语言 | `lang chinese|english` 控制识别语言与 TTS 音色 |

## 快速开始

```
abot hello                       # 对话
abot switch 3                    # 进入学习模式
abot 你好 => 嗨，很高兴见到你     # 学习词条
abot switch 1                    # 回到对话模式
abot 你好                        # -> 嗨，很高兴见到你
```

## 命令

```
abot <text>                  在当前模式下对话/学习/记录
abot switch <0-3>            切换模式: 0=init 1=talk 2=record 3=learn
abot records [clear]         查看/清空记录
abot summary [keep]          把记录汇总进知识库（keep 保留记录）
abot forget <question>       删除一个已学习的词条
abot crawl <url>             从网页学习（抓正文→提名词→维基百科补定义）
abot lang <chinese|english>  设置语音语言
abot voice <on|off>          开启/关闭语音回复
abot voice <private|group>   语音输入作用域（默认仅私聊）
abot stop                    停止并保存
abot help                    显示帮助
```

学习模式里直接发送 URL 也会触发抓取学习。

## 语音说明

- **语音输入**：收到语音后自动转写并按当前模式处理（默认仅私聊响应，避免群聊刷屏）。
- **识别引擎**：装有 `faster-whisper` 时中英文通用（本地离线）；
  否则英文回退 Sphinx，中文需安装 `pip install faster-whisper`
  或开启 AstrBot 自带 STT（转写文本会直接复用）。
- **语音回复**：`abot voice on` 后回复语音（pyttsx4 系统语音，输出 wav，
  单条回复最多朗读 200 字，超出部分只朗读开头）。
  Windows 自带中文音色（如 Huihui）；Linux 需安装 espeak-ng。
- **QQ 语音格式**：aiocqhttp 收到的语音常为 silk，需 `pip install pilk` 转码；
  装有 ffmpeg 时 amr/mp3 等格式也能自动转换。

## 可选依赖

```
pip install pilk            # QQ silk 语音转码（Python<=3.11 的预编译包）
pip install faster-whisper  # 本地中英文语音识别（首次运行会下载模型）
```

## 开发与测试

```
# 端到端冒烟（无需安装 AstrBot）
python tests/smoke_repl.py

# 单元测试（pytest 可用时）
python -m pytest tests -q
# 或纯 Python 运行
python tests/run_tests.py
```

## 数据文件

- `db_utils/data.json`：知识词条（`问题: 回答`，回答可为字符串或多答案数组）
- `db_utils/record.json`：语录记录

---

### 历史 Todo（已在 v1.1.0 完成）

1. ~~添加自动抓取网页内容机制~~（`web_utils/crawler.py`，`abot crawl <url>`）
2. ~~文本分词、提名词并递归抓取~~（jieba 分词 + 维基百科递归补定义，递归深度≤2）
3. ~~record 模式切换与汇总入数据集合~~（`abot summary`）
