# Free ImageGen CLI

`free-imagegen` 是一个 LLM 驱动的端到端图片生成工具。输入一句话想法，大模型自动生成结构化提示词，本地渲染器输出 SVG / PNG 图片。

适合封面、知识卡、信息图、文章卡组和 OpenClaw 资产，不是写实扩散模型。

## 快速开始

### 1. 安装

```powershell
python -m pip install -e .
```

依赖 `openai>=1.0`，安装时自动拉取。

### 2. 配置 LLM

在项目根目录创建 `.env` 文件：

```ini
# OpenAI 兼容 API（必填）
BASE_URL=http://your-api-host/v1
MODEL=your-model-name
API_KEY=your-api-key

# 可选参数
TEMPERATURE=0.7
MAX_TOKENS=4096
TIMEOUT=90
MAX_RETRIES=3
```

支持所有 OpenAI 兼容 API：本地模型（vLLM / Ollama）、DeepInfra、xAI、OpenAI 官方等。

### 3. 生成图片

```powershell
# 一句话生成单张图片
free-imagegen create "AI 产品设计原则"

# 指定输出路径和格式
free-imagegen create "AI 产品设计原则" -o output/cover.png

# 生成多页卡组
free-imagegen create "AI 产品设计原则的五条核心原则" --mode story --output-dir output/cards

# 指定卡片数量
free-imagegen create "Python 入门教程" --mode story --cards 6 --output-dir output/tutorial
```

## CLI 命令

### `create` — 端到端生成（LLM + 渲染）

```powershell
free-imagegen create "你的想法" [选项]
```

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--mode` | `image`（单图）或 `story`（卡组） | `image` |
| `--cards` | 卡组模式的卡片数量 | 自动 |
| `-o` / `--output` | 单图输出文件路径 | 自动生成 |
| `--output-dir` | 卡组输出目录 | 自动生成 |
| `--format` | `png` 或 `svg` | `png` |
| `--keep-svg` | 同时保留 SVG 文件 | 关 |
| `--width` / `--height` | 画布尺寸 | 1024×1024（单图）/ 1080×1440（卡组） |
| `--theme` | `auto` / `light` / `dark` | `auto` |
| `--accent` | `auto` / `blue` / `green` / `warm` / `rose` | `auto` |
| `--tone` | `auto` / `calm` / `playful` / `bold` / `editorial` | `auto` |

### `generate` — 手动结构化提示词渲染

```powershell
free-imagegen generate --prompt "文字封面，标题：AI 产品设计原则，副标题：清晰层级与手机可读性" -o output/cover.png
free-imagegen generate --prompt-file prompt.txt --format svg -o output/cover.svg
```

### `story` — 渲染文章卡组

```powershell
free-imagegen story --prompt-file article.md --output-dir output/article
free-imagegen story --plan story-plan.json --output-dir output/story
```

### `assets` — 生成 OpenClaw 资产

```powershell
free-imagegen assets C:\path\to\project --prompt "space arcade game"
```

### `validate-plan` — 校验 story-plan JSON

```powershell
free-imagegen validate-plan story-plan.json
```

### `serve` — 启动本地 HTTP 服务

```powershell
free-imagegen serve --host 127.0.0.1 --port 8787
```

接口：`/health`、`/generate`、`/story`、`/assets`、`/validate-plan`。

## 项目结构

```text
src/free_imagegen/
  __init__.py      公开 API 导出
  api.py           公共 Python API
  cli.py           命令行入口
  llm.py           LLM 客户端（OpenAI 兼容）
  llm_prompts.py   LLM 系统提示词模板
  service.py       标准库 HTTP 服务
  _engine.py       内部 SVG 排版与 story 引擎
  resources/       story plan 契约与 agent 参考资料
tests/             API 和 CLI 测试
```

## Python API

```python
from free_imagegen import generate_image_from_idea, generate_story_from_idea

# 端到端：想法 → LLM → 渲染单图
result = generate_image_from_idea("AI 产品设计原则", "output/cover.png")

# 端到端：想法 → LLM → 渲染卡组
result = generate_story_from_idea("Python 入门五步", "output/tutorial/")
```

## PNG 导出

仅生成 SVG 不需要额外工具。PNG 导出需要系统安装以下任一：

- `rsvg-convert`
- `inkscape`
- `magick`（ImageMagick）
- macOS `sips`

## 测试

```powershell
python -m unittest discover -s tests -v
```
