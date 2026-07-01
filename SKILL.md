---
name: docx-to-md
description: 当用户需要将文档转换为适合 Obsidian、知识库入库、RAG 检索或模型阅读的干净 Markdown 时，应使用此 skill；支持 .docx（Pandoc）、.pdf、.pptx、.xlsx（MarkItDown）格式；具备单文件转换、批量转换、递归转换、默认图片提取、仅文本转换、Markdown 图片显示与可点击原图链接、内容清理、HTML 表格转 Markdown 表格、图片 alt 文本保留、链接文本提取和内联 HTML 清理等能力。
---

# 文档转 Markdown

## 概述

将单个或多个文档转换为适合 Obsidian 和知识库检索的干净 Markdown。

支持的文件格式：

| 格式 | 转换引擎 | 脚本 |
|------|----------|------|
| `.docx` | Pandoc | `scripts/convert_docx_to_md.py` |
| `.pdf` | MarkItDown (pdfminer.six)；`--vision` 模式使用 PyMuPDF + VLM | `scripts/convert_other_to_md.py` |
| `.pptx` | MarkItDown (python-pptx) | `scripts/convert_other_to_md.py` |
| `.xlsx` | MarkItDown (openpyxl) | `scripts/convert_other_to_md.py` |

- `.docx` 使用 `scripts/convert_docx_to_md.py` 执行 Pandoc 转换、提取图片并清理 Markdown；当用户明确要求"仅保留文本"时，使用 `scripts/convert_docx_to_md_text_only.py`。
- `.pdf`、`.pptx`、`.xlsx` 使用 `scripts/convert_other_to_md.py`，基于 MarkItDown 库转换，并经过与 docx 相同的后处理清理管道。

## 适用场景

在以下需求中使用此 skill：

- 将一个 Word 文档转换为 Markdown。
- 将 PDF 文档转换为 Markdown。
- 将 PowerPoint 演示文稿转换为 Markdown。
- 将 Excel 表格转换为 Markdown。
- 将一个文件夹中的多个文档批量转换为 `.md`。
- 递归转换多级目录中的文档文件。
- 从文档中提取图片，并在 Markdown 中同时保留图片显示和可点击原图链接。
- 仅保留文档中的文本内容，不提取图片。
- 清理转换工具生成的 Markdown 中残留的 HTML 表格、图片标签、链接或内联 HTML。
- 将文档整理为适合 Obsidian、知识库入库、RAG 检索或模型阅读的 Markdown。

不用于在文档内部直接编辑排版。

## 前置条件

### DOCX 转换依赖

转换 `.docx` 依赖 `pandoc`。执行转换前先检查：

```bash
pandoc --version
```

如果 macOS 环境缺少 `pandoc`，可安装：

```bash
brew install pandoc
```

### PDF / PPTX / XLSX 转换依赖

转换 `.pdf`、`.pptx`、`.xlsx` 依赖 `markitdown` Python 包。

**第一次使用前**，在用户级 Python 环境中执行一次安装即可，之后所有项目、所有会话都自动可用，不需要重新安装：

```bash
python3 -m pip install --user 'markitdown[pdf,pptx,xlsx]'
```

这会安装到当前用户的 site-packages 目录（macOS 通常是 `~/Library/Python/3.x/lib/python/site-packages/`），并自动带上子包依赖：
- `pdfminer.six`（PDF 文本提取）
- `python-pptx`（PowerPoint 解析）
- `openpyxl`（Excel 解析）

**为什么用 `--user`：**
- 不需要 sudo，不会污染系统 Python
- 装一次，所有项目、所有会话都生效
- Python 升级或重装时可能需要重装一次，但日常使用无影响

**如果执行时出现 `externally-managed-environment` 错误**（macOS Homebrew Python 常见），使用以下命令替代：

```bash
python3 -m pip install --user --break-system-packages 'markitdown[pdf,pptx,xlsx]'
```

除非用户明确要求安装依赖，否则不要自动安装依赖。

### Vision 模式额外依赖（可选）

当 PDF 中含有图表、架构图、流程图等以图片/矢量图形式传递信息的内容时，可启用 `--vision` 模式，使用多模态大模型（VLM）直接"看图"理解内容。

**额外依赖**：

```bash
# PyMuPDF：将 PDF 页面渲染为图片
python3 -m pip install --user pymupdf

# OpenAI Python SDK：调用多模态 API（兼容 OpenAI / Gemini / 智谱等）
python3 -m pip install --user openai
```

**环境变量配置（必须，只需配置一次）**：

Vision 模式需要调用支持图片理解的多模态 AI 模型。请在终端执行以下命令配置 API 密钥：

```bash
# 以 OpenAI (GPT-4o) 为例，将以下三行加入 ~/.zshrc：
echo 'export VISION_API_KEY="sk-你的密钥"' >> ~/.zshrc
echo 'export VISION_API_BASE="https://api.openai.com/v1"' >> ~/.zshrc
echo 'export VISION_MODEL="gpt-4o"' >> ~/.zshrc
source ~/.zshrc
```

支持的 Provider：

| Provider | VISION_API_BASE | VISION_MODEL | Key 获取 |
|----------|----------------|--------------|---------|
| OpenAI | `https://api.openai.com/v1` | `gpt-4o` | platform.openai.com |
| Google Gemini | `https://generativelanguage.googleapis.com/v1beta/openai` | `gemini-2.5-flash` | aistudio.google.com |
| 智谱 GLM-4V | `https://open.bigmodel.cn/api/paas/v4` | `glm-4v-plus` | open.bigmodel.cn |
| Anthropic | `https://api.anthropic.com/v1` | `claude-sonnet-4` | console.anthropic.com |

也可以直接设置 provider 专属变量（如 `OPENAI_API_KEY`），脚本会自动识别。

**Vision 模式前置条件**：
- `pymupdf` 已安装（用于 PDF → PNG 渲染）
- `openai` 已安装（用于调用 VLM API）
- 环境变量已配置（`VISION_API_KEY` 或 `OPENAI_API_KEY` 等）

**成本提示**：Vision 模式会对 PDF 每页调用一次 VLM。GPT-4o 约 $0.01-0.03/页，Gemini Flash 更便宜。建议仅对含图 PDF 使用。

## 快速开始

在 skill 目录中运行脚本。

### DOCX 转换

单文件转换，默认提取图片：

```bash
python3 scripts/convert_docx_to_md.py --input-file input.docx --output-file output.md
```

默认输出结构：

```text
当前目录/
├── output.md
└── output_images/
    ├── image1.png
    └── image2.jpeg
```

Markdown 中会生成同时支持显示和点击的图片语法：

```md
![图片说明](./output_images/image1.png)

[打开原图：图片说明](./output_images/image1.png)
```

批量转换目录，默认提取图片：

```bash
python3 scripts/convert_docx_to_md.py --input-dir ./docx --output-dir ./markdown
```

递归批量转换，并保留相对目录结构：

```bash
python3 scripts/convert_docx_to_md.py --input-dir ./docx --output-dir ./markdown --recursive
```

仅保留文本内容、不提取图片：

```bash
python3 scripts/convert_docx_to_md_text_only.py --input-file input.docx --output-file output.md
```

### PDF / PPTX / XLSX 转换

单文件转换：

```bash
python3 scripts/convert_other_to_md.py --input-file report.pdf --output-file report.md
python3 scripts/convert_other_to_md.py --input-file slides.pptx --output-file slides.md
python3 scripts/convert_other_to_md.py --input-file data.xlsx --output-file data.md
```

批量转换目录中所有支持的文件（PDF + PPTX + XLSX）：

```bash
python3 scripts/convert_other_to_md.py --input-dir ./docs --output-dir ./markdown
```

递归批量转换：

```bash
python3 scripts/convert_other_to_md.py --input-dir ./docs --output-dir ./markdown --recursive
```

不提取 base64 图片（保持内联）：

```bash
python3 scripts/convert_other_to_md.py --input-file slides.pptx --output-file slides.md --no-extract-images
```

保留 MarkItDown 原始输出用于排查：

```bash
python3 scripts/convert_other_to_md.py --input-file report.pdf --output-file report.md --keep-raw
```

### PDF Vision 模式（含图 PDF）

当 PDF 包含图表、架构图、流程图等视觉信息时，使用 `--vision` 让 VLM 直接看图理解：

```bash
python3 scripts/convert_other_to_md.py --input-file report.pdf --output-file report.md --vision
```

自定义渲染 DPI 和超时时间：

```bash
python3 scripts/convert_other_to_md.py --input-file report.pdf --output-file report.md --vision --vision-dpi 200 --vision-timeout 180
```

批量 vision 转换目录中的 PDF：

```bash
python3 scripts/convert_other_to_md.py --input-dir ./pdfs --output-dir ./markdown --vision
```

**注意**：`--vision` 仅对 PDF 文件生效。对 PPTX/XLSX 文件传入 `--vision` 会被忽略（PPTX/XLSX 仍走 MarkItDown）。

## 脚本选择逻辑

首先根据文件扩展名选择脚本：

- `.docx` 文件 → 使用 `scripts/convert_docx_to_md.py`（或纯文本变体）
- `.pdf`、`.pptx`、`.xlsx` 文件 → 使用 `scripts/convert_other_to_md.py`

对于 `.docx` 文件的进一步选择：

- 用户提到"保留图片""提取图片""图片也要保留""带图片转换"等需求时，使用 `scripts/convert_docx_to_md.py`。
- 用户没有说明是否保留图片时，默认使用 `scripts/convert_docx_to_md.py`，即保留图片并生成同级图片目录。
- 用户明确说"仅保留文本""不要图片""不提取图片""纯文本转换"时，使用 `scripts/convert_docx_to_md_text_only.py`。

对于混合目录（同时包含 .docx 和其他格式）：

- 分别调用两个脚本处理各自支持的格式，或者分两次 `--input-dir` 命令处理。

## 转换流程

1. 判断用户输入的是单个文件还是目录，以及文件扩展名。
2. 先按"脚本选择逻辑"根据扩展名选择转换脚本。
3. 选择对应转换模式：
   - 单文件：使用 `--input-file`，可选 `--output-file`。
   - 批量目录：使用 `--input-dir` 和 `--output-dir`。
   - 递归批量：在批量目录模式中增加 `--recursive`。
4. 尽量使用绝对路径执行脚本，避免工作目录不一致导致找不到文件。
5. 转换完成后确认生成的 `.md` 文件；如果使用保留图片脚本，还要确认同级图片目录。
6. 如果依赖缺失（`pandoc` 或 `markitdown`），说明安装方式，并在环境准备好后重新执行转换。
7. **【必须】对 PDF/PPTX 转换产物执行自检修复**（详见下方"产物自检修复"章节）。

## 产物自检修复（PDF / PPTX 必须执行）

### 触发条件

对所有 `.pdf` 和 `.pptx` 文件的转换产物，**必须**在脚本转换完成后执行此自检步骤。`.docx` 和 `.xlsx` 转换质量较高，可跳过此步骤（除非用户要求）。

### 自检流程

转换脚本输出 `.md` 文件后，执行以下步骤：

1. **阅读产物 Markdown 全文**：逐段阅读转换产物 `.md`，识别以下问题：
   - 句子被截断或不完整（如"用户偏好个体化表达，看到官号1秒"缺失后半句）
   - 同一句话被拆散到多行且语序混乱（PDF 多栏布局导致）
   - 表格行内容错位或列对不齐
   - 明显的 OCR 乱码或无意义字符碎片
   - 同一段落的内容被表格或空行打断

2. **对照原文档确认修复依据**：对于每个识别到的问题，必须回溯原文档（PDF/PPTX 原件）确认正确内容。如果原文档不可读取（如纯图片 PDF），则使用产物 `.md` 的上下文进行合理重组。

3. **执行修复**：直接编辑产物 `.md` 文件，修复上述问题。

4. **输出修复摘要**：修复完成后，简要告知用户修复了哪些内容。

### 严格约束（红线）

- **禁止猜测补充**：所有修复内容必须来自原文档或产物 `.md` 的上下文。绝对不允许模型自行编造、推测、扩写任何内容。
- **禁止改写语义**：修复仅限于重组散落文本的顺序、合并被截断的句子、去除乱码。不得改变原文的措辞、语气或观点。
- **禁止删除有效内容**：即使某段文字看起来突兀，只要它确实来自原文档，就必须保留。
- **无法确认时标注存疑**：如果某处文本无法通过原文档或上下文确认正确形式，用 `<!-- TODO: 此处原文不清晰，需人工确认 -->` 标注，不做修改。

### 常见修复模式

| 问题类型 | 修复方式 | 示例 |
|---------|---------|------|
| 多栏文本交错 | 根据语义将同一段落的碎片重新拼接为完整句子 | "企业影响力和信任构建迁移短视频 核心阵地：视频号" → 拆为两个独立要点 |
| 句子截断 | 在产物 md 上下文中寻找后半句，拼接还原 | "2B内容和官方身份的限制" + 下一行孤立文本 → 合并 |
| 表格行错位 | 对照原文档的表格结构重新对齐 | 把被错误拆分的行合并回正确的单元格 |
| OCR 乱码碎片 | 如果上下文可确认含义则修复，否则标注 `<!-- TODO -->` | — |
| 重复内容 | 删除明显因提取错误导致的重复段落 | — |

### 批量转换时的自检策略

- 批量转换时，对每个 PDF/PPTX 产物逐一执行自检。
- 如果文件数量过多（超过 5 个），优先自检前 5 个，其余告知用户可能需要人工复检。

## 脚本行为

### convert_docx_to_md.py（DOCX 专用）

分两步处理文档：

1. 使用 Pandoc 将 `.docx` 转换为原始 GitHub Flavored Markdown。
2. 对原始 Markdown 进行清理和增强：
   - 默认将 `.docx` 内嵌图片提取到 `<md文件名>_images/` 目录；目录名中的空格和特殊符号会自动替换为下划线。
   - 将图片引用转换为两行 Markdown：第一行直接显示图片，第二行提供可点击的"打开原图"链接。
   - 将 Pandoc 生成的 `media/` 子目录扁平化，图片统一放在 `<md文件名>_images/` 下。
   - `convert_docx_to_md_text_only.py` 不提取图片文件、不生成图片链接，只在有意义 alt 文本存在时保留 `图片：alt` 文本。
   - 将 `<table>...</table>` 转换为 Markdown pipe table。
   - 处理 HTML 表格中的 `rowspan` / `colspan`。
   - 默认使用中文分号 `；` 扁平化表格单元格内的多行内容。
   - 转义表格单元格中的竖线 `|`。
   - 移除泛化图片标签、将普通链接替换为可见链接文本。
   - 移除 `<br>`、段落标签和其他噪声内联 HTML。
   - 合并重复空行。

### convert_other_to_md.py（PDF / PPTX / XLSX）

分两步处理文档：

1. 使用 MarkItDown 库将文件转换为原始 Markdown。
2. 对原始 Markdown 进行清理和增强（与 docx 管道相同标准）：
   - 提取 base64 内联图片为本地文件（存入 `<md文件名>_images/` 目录）。
   - 将提取的图片引用转换为显示 + 打开原图的双链接格式。
   - 清理残留的 HTML 标签（`<a>`、`<br>`、`<p>` 等）。
   - 将普通链接替换为可见链接文本。
   - HTML 实体反转义。
   - 合并重复空行。
   - 保留 `--keep-raw` 用于排查原始输出。

## 常用参数

### convert_docx_to_md.py 参数

- `--cell-joiner "；"`：设置表格单元格内多行文本的连接符，默认是中文分号。
- `--recursive`：递归批量转换子目录中的 `.docx` 文件，并保留相对目录结构。
- `--keep-raw`：保留 Pandoc 生成的中间 Markdown，输出为 `*.raw.md`，便于排查格式问题。
- `--no-extract-images`：不提取图片；新任务中优先使用 `convert_docx_to_md_text_only.py`。
- `--image-dir-suffix "_images"`：设置同级图片目录后缀，默认 `<md文件名>_images/`。
- `--pandoc PATH`：指定 Pandoc 可执行文件路径。

### convert_other_to_md.py 参数

- `--input-file`：单个文件（PDF/PPTX/XLSX）。
- `--output-file`：输出 .md 路径，默认与输入同名改后缀。
- `--input-dir`：批量转换目录。
- `--output-dir`：批量输出目录。
- `--recursive`：递归转换子目录。
- `--keep-raw`：保留 MarkItDown 原始输出为 `*.raw.md`。
- `--no-extract-images`：不提取 base64 内联图片为本地文件。
- `--image-dir-suffix "_images"`：同级图片目录后缀。
- `--vision`：启用 VLM 视觉理解模式（仅 PDF）。将每页渲染为图片后由多模态模型识别，适合含图表/架构图/流程图的 PDF。
- `--vision-dpi 300`：Vision 模式下 PDF 页面渲染 DPI，默认 300。降低可加快速度但降低识别精度。
- `--vision-timeout 120`：Vision 模式下每页 VLM 处理超时秒数，默认 120。

## 图片保留规则

默认情况下，如果输出文件为：

```text
article.md
```

图片目录为：

```text
article_images/
```

Markdown 中每张图片会写成：

```md
![图片说明](./article_images/image1.png)

[打开原图：图片说明](./article_images/image1.png)
```

这样同时满足：

- 在 Obsidian、VS Code Markdown Preview、Typora、GitHub 等工具中直接显示图片。
- 点击"打开原图"链接跳转到图片文件。
- 移动或分享文档时，只需将 `.md` 文件和同级 `_images` 图片目录一起移动。

## 关于原始转换脚本的改动说明

skill 中没有直接修改用户原始文件，因为用户提供的是聊天中的脚本内容，而不是工作区内的现有脚本文件。实际处理方式是：基于用户提供的 Markdown 清理逻辑，新建并持续扩展了 skill 内的可复用脚本 `scripts/convert_docx_to_md.py`。

该脚本保留了用户原脚本中的核心清理思路，包括：

- `DEFAULT_CELL_JOINER = "；"`
- HTML 表格解析与 Markdown 表格输出
- 表格单元格内换行扁平化
- 图片 alt 文本过滤和保留
- 链接文本提取
- 内联 HTML 清理

同时做了面向 `.docx` 转 Markdown 场景的扩展：

- 新增 Pandoc 调用，将 `.docx` 先转换为原始 Markdown。
- 新增 `--input-file` / `--output-file` 单文件转换。
- 新增 `--input-dir` / `--output-dir` 批量转换。
- 新增 `--recursive` 递归批量转换。
- 新增默认图片提取能力。
- 新增 Markdown 图片显示语法和可点击原图链接的双输出。
- 新增 `--no-extract-images` 纯文本模式。
- 新增 `--image-dir-suffix` 自定义图片目录后缀。
- 新增 `--keep-raw` 保留 Pandoc 中间产物。
- 新增 `--pandoc` 指定 Pandoc 可执行文件。
- 新增 Markdown 图片语法和 Markdown 链接语法的清理。
- 新增对 Word 临时文件 `~$*.docx` 的跳过。
- 新增错误处理和更清晰的命令行提示。

因此，结论是：没有改动用户原始脚本文件；但 skill 内的转换脚本是在用户脚本基础上改写和扩展得到的。

## 注意事项

优先输出适合知识库入库和模型检索的干净 Markdown，同时保留图片的可读性和可访问性。该转换器更重视语义可读性、表格结构清晰度、图片路径稳定性和检索友好性，而不是追求与 Word 原始排版完全一致。
