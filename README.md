# docx-to-md

A CodeBuddy skill for converting documents (`.docx`, `.pdf`, `.pptx`, `.xlsx`) into clean, AI-friendly Markdown for Obsidian, RAG, and knowledge bases. Includes a VLM vision mode for PDFs with charts, diagrams, and visual content.

一个用于将文档（`.docx`、`.pdf`、`.pptx`、`.xlsx`）转换为干净 Markdown 的 CodeBuddy Skill，支持批量转换、图片提取、表格清理和仅文本模式，适合 Obsidian、RAG 和知识库入库。新增 VLM 视觉模式，可处理含图表/架构图/流程图的 PDF。

---

## Features / 功能特性

### DOCX Conversion / DOCX 转换

- Convert single `.docx` files to `.md`  
  将单个 `.docx` 文件转换为 `.md`
- Batch convert all `.docx` files in a directory  
  批量转换目录中的 `.docx` 文件
- Recursively convert nested folders  
  支持递归转换多级目录
- Extract embedded images by default  
  默认提取 Word 文档中的内嵌图片
- Generate Markdown image syntax and original-image links  
  生成 Markdown 图片显示语法和可点击原图链接
- Provide a text-only mode for AI/RAG ingestion  
  提供仅文本模式，适合 AI / RAG 入库
- Convert Pandoc-generated HTML tables to Markdown pipe tables  
  将 Pandoc 生成的 HTML 表格转换为 Markdown 表格
- Handle `rowspan` / `colspan` in HTML tables  
  处理 HTML 表格中的 `rowspan` / `colspan` 合并单元格
- Flatten line breaks inside table cells with `；` by default  
  默认使用中文分号 `；` 扁平化表格单元格内换行
- Preserve meaningful image alt text  
  保留有意义的图片 alt 文本
- Remove noisy inline HTML, image tags, and link wrappers  
  清理噪声 HTML、图片标签和链接包装
- Skip temporary Word files such as `~$*.docx`  
  自动跳过 Word 临时文件，例如 `~$*.docx`

### PDF / PPTX / XLSX Conversion / PDF、PPTX、XLSX 转换

- Convert PDF, PPTX, XLSX to Markdown via MarkItDown  
  通过 MarkItDown 将 PDF、PPTX、XLSX 转换为 Markdown
- Extract base64-encoded images to local files  
  提取 base64 编码图片为本地文件
- HTML cleanup and blank line normalization  
  HTML 清理和空行规范化

### 🆕 Vision Mode (VLM) / 视觉模式

- Render PDF pages as high-resolution PNG images via PyMuPDF  
  使用 PyMuPDF 将 PDF 页面渲染为高清 PNG 图片
- Send page images to multimodal AI models for visual understanding  
  将页面图片发送给多模态 AI 模型进行视觉理解
- Support multiple VLM providers: OpenAI (GPT-4o), Google Gemini, Anthropic Claude, 智谱 GLM-4V  
  支持多种 VLM provider：OpenAI、Google Gemini、Anthropic Claude、智谱 GLM-4V
- Automatic fallback to pdftotext on per-page failure  
  单页 VLM 失败时自动 fallback 到 pdftotext
- Detailed setup guide when API key is missing  
  API Key 未配置时输出详细的配置教学

---

## Use Cases / 使用场景

Use this skill when you need to:  
当你需要以下能力时，可以使用这个 skill：

- Prepare Word documents for Obsidian notes  
  将 Word 文档整理为 Obsidian 笔记
- Convert Word documents into knowledge-base friendly Markdown  
  将 Word 文档转换为适合知识库入库的 Markdown
- Process documents before RAG indexing or vectorization  
  在 RAG 切片、索引、向量化前预处理文档
- Batch clean `.docx` files for AI reading  
  批量清理 `.docx` 文件，方便 AI 稳定读取
- Convert PR drafts, product docs, technical articles, or short-video scripts into structured Markdown  
  将 PR 稿、产品文档、技术文章、短视频脚本转换为结构化 Markdown
- Preserve document images while keeping Markdown portable  
  保留文档图片，并保持 Markdown 文件可迁移
- Generate text-only Markdown when images are not needed  
  在不需要图片时生成仅文本 Markdown

---

## Requirements / 依赖要求

### DOCX conversion / DOCX 转换依赖

[Pandoc](https://pandoc.org/) is required for `.docx` conversion.  
`.docx` 转换依赖 [Pandoc](https://pandoc.org/)。

```bash
# Check / 检查
pandoc --version

# Install on macOS / macOS 安装
brew install pandoc
```

### PDF / PPTX / XLSX conversion / PDF、PPTX、XLSX 转换依赖

```bash
# MarkItDown + pdfminer (text extraction)
pip install markitdown pdfminer.six
```

### Vision mode (optional) / 视觉模式依赖（可选）

Required only when using `--vision` for PDFs with charts/diagrams.  
仅在使用 `--vision` 处理含图表的 PDF 时需要。

```bash
# PyMuPDF: render PDF pages to images / 将 PDF 页面渲染为图片
pip install pymupdf

# OpenAI SDK: call VLM API / 调用多模态 API
pip install openai
```

**Environment variable setup / 环境变量配置**（choose one provider / 任选一个）：

```bash
# OpenAI (GPT-4o)
echo 'export VISION_API_KEY="sk-your-key"' >> ~/.zshrc
echo 'export VISION_API_BASE="https://api.openai.com/v1"' >> ~/.zshrc
echo 'export VISION_MODEL="gpt-4o"' >> ~/.zshrc
source ~/.zshrc
```

Supported providers / 支持的 Provider：

| Provider | VISION_API_BASE | VISION_MODEL | Get Key / 获取 Key |
|----------|----------------|--------------|-------------------|
| OpenAI | `https://api.openai.com/v1` | `gpt-4o` | platform.openai.com |
| Google Gemini | `https://generativelanguage.googleapis.com/v1beta/openai` | `gemini-2.5-flash` | aistudio.google.com |
| 智谱 GLM-4V | `https://open.bigmodel.cn/api/paas/v4` | `glm-4v-plus` | open.bigmodel.cn |
| Anthropic | `https://api.anthropic.com/v1` | `claude-sonnet-4` | console.anthropic.com |

You can also just set provider-specific keys (e.g. `OPENAI_API_KEY`), the script will auto-detect.  
也可以直接设置 provider 专属变量（如 `OPENAI_API_KEY`），脚本会自动识别。

---

## Installation / 安装方式

Copy this skill folder into your CodeBuddy user skills directory:  
将本 skill 文件夹复制到 CodeBuddy 用户 skill 目录：

```bash
mkdir -p ~/.codebuddy/skills
cp -R docx-to-md ~/.codebuddy/skills/docx-to-md
```

After installation, use it in CodeBuddy with:  
安装后，在 CodeBuddy 中这样调用：

```text
@skill://docx-to-md
```

---

## Script Selection Logic / 脚本选择逻辑

The skill includes three conversion scripts.  
本 skill 包含三个转换脚本。

| User intent / 用户意图 | Script / 使用脚本 |
|---|---|
| `.docx` with images / DOCX 保留图片 | `scripts/convert_docx_to_md.py` |
| `.docx` text only / DOCX 仅文本 | `scripts/convert_docx_to_md_text_only.py` |
| `.pdf` / `.pptx` / `.xlsx` (text extraction) / PDF、PPTX、XLSX 文本提取 | `scripts/convert_other_to_md.py` |
| `.pdf` with charts/diagrams (VLM) / 含图表的 PDF 视觉理解 | `scripts/convert_other_to_md.py --vision` |

Default behavior for DOCX is to keep images.  
DOCX 默认行为是保留图片。

---

## Usage / 使用方法

### 1. Convert a single DOCX file with images / 单文件转换，保留图片

```bash
python3 scripts/convert_docx_to_md.py \
  --input-file input.docx \
  --output-file output.md
```

Output structure / 输出结构：

```text
.
├── output.md
└── output_images/
    ├── image1.png
    └── image2.jpeg
```

Markdown image output example / Markdown 图片输出示例：

```md
![image1.png](./output_images/image1.png)

[打开原图：image1.png](./output_images/image1.png)
```

### 2. Convert a single DOCX file as text only / 单文件转换，仅保留文本

```bash
python3 scripts/convert_docx_to_md_text_only.py \
  --input-file input.docx \
  --output-file output.md
```

Text-only mode does not extract image files and does not write image links. If an image has meaningful alt text, it may be kept as plain text.  
仅文本模式不会提取图片文件，也不会写入图片链接。如果图片有有意义的 alt 文本，会保留为普通文本。

```md
图片：系统架构图
```

### 3. Batch convert a directory / 批量转换目录

```bash
python3 scripts/convert_docx_to_md.py \
  --input-dir ./docx \
  --output-dir ./markdown
```

### 4. Recursively batch convert subfolders / 递归批量转换子目录

```bash
python3 scripts/convert_docx_to_md.py \
  --input-dir ./docx \
  --output-dir ./markdown \
  --recursive
```

### 5. Batch convert as text only / 批量转换，仅保留文本

```bash
python3 scripts/convert_docx_to_md_text_only.py \
  --input-dir ./docx \
  --output-dir ./markdown \
  --recursive
```

### 6. Convert PDF / PPTX / XLSX (text extraction) / 转换 PDF、PPTX、XLSX

```bash
python3 scripts/convert_other_to_md.py \
  --input-file report.pdf \
  --output-file report.md
```

### 7. Convert PDF with Vision mode (VLM) / 使用视觉模式转换含图 PDF

```bash
python3 scripts/convert_other_to_md.py \
  --input-file report.pdf \
  --output-file report.md \
  --vision
```

Custom DPI and timeout / 自定义渲染精度和超时：

```bash
python3 scripts/convert_other_to_md.py \
  --input-file report.pdf \
  --output-file report.md \
  --vision --vision-dpi 200 --vision-timeout 180
```

Batch vision mode / 批量视觉转换：

```bash
python3 scripts/convert_other_to_md.py \
  --input-dir ./pdfs \
  --output-dir ./markdown \
  --vision
```

---

## Options / 参数说明

Common options / 通用参数：

| Option / 参数 | Description / 说明 |
|---|---|
| `--input-file` | Single `.docx` file to convert / 单个 `.docx` 输入文件 |
| `--output-file` | Output `.md` path for single-file conversion / 单文件转换的 `.md` 输出路径 |
| `--input-dir` | Directory containing `.docx` files / 包含 `.docx` 文件的目录 |
| `--output-dir` | Directory for generated Markdown files / Markdown 输出目录 |
| `--recursive` | Recursively convert `.docx` files in subdirectories / 递归转换子目录中的 `.docx` 文件 |
| `--keep-raw` | Keep Pandoc intermediate Markdown as `*.raw.md` / 保留 Pandoc 中间 Markdown 文件 |
| `--cell-joiner` | Text used to join multiple lines inside Markdown table cells; default is `；` / 表格单元格内多行文本连接符，默认是 `；` |
| `--pandoc` | Custom Pandoc executable path / 指定 Pandoc 可执行文件路径 |

Image mode only / 图片模式参数：

| Option / 参数 | Description / 说明 |
|---|---|
| `--no-extract-images` | Compatibility option in the main script; for new text-only tasks, prefer `convert_docx_to_md_text_only.py` / 主脚本兼容参数；新任务建议优先使用文本专用脚本 |
| `--image-dir-suffix` | Suffix for image directories; default is `_images` / 图片目录后缀，默认是 `_images` |

Vision mode options (`convert_other_to_md.py`) / 视觉模式参数：

| Option / 参数 | Description / 说明 |
|---|---|
| `--vision` | Enable VLM vision mode for PDF; renders pages as images and uses multimodal AI for recognition / 启用 VLM 视觉模式，将 PDF 页面渲染为图片后由多模态 AI 识别 |
| `--vision-dpi` | DPI for page rendering; default 300 / 页面渲染 DPI，默认 300 |
| `--vision-timeout` | Per-page VLM timeout in seconds; default 120 / 每页 VLM 超时秒数，默认 120 |

---

## How It Works / 工作原理

The converter runs in two phases.  
转换器分两步处理文档。

1. Use Pandoc to convert `.docx` into raw GitHub Flavored Markdown.  
   使用 Pandoc 将 `.docx` 转换为原始 GitHub Flavored Markdown。
2. Clean and normalize the raw Markdown.  
   对原始 Markdown 进行清理和规范化。

Cleanup includes:  
清理内容包括：

- Convert HTML tables to Markdown pipe tables  
  将 HTML 表格转换为 Markdown pipe table
- Handle merged cells from `rowspan` / `colspan`  
  处理 `rowspan` / `colspan` 产生的合并单元格
- Flatten line breaks inside table cells  
  扁平化表格单元格内换行
- Escape `|` inside table cells  
  转义表格单元格内的 `|`
- Extract images and rewrite image paths in image mode  
  在图片模式下提取图片并重写图片路径
- Keep useful image alt text in text-only mode  
  在仅文本模式下保留有意义的图片 alt 文本
- Replace links with visible text  
  将链接替换为可见文本
- Remove noisy inline HTML  
  移除噪声内联 HTML
- Collapse repeated blank lines  
  合并重复空行

---

## Notes on Images / 图片说明

Markdown itself does not embed image binary data. It references image files by path.  
Markdown 本身不嵌入图片二进制内容，而是通过路径引用图片文件。

When image extraction is enabled, the `.md` file and its sibling `_images` directory should be moved or shared together.  
启用图片提取时，`.md` 文件和同级 `_images` 图片目录需要一起移动或分享。

Some Markdown previewers may restrict clicking local file links inside preview mode due to WebView security rules. If preview clicking does not work, try opening the link from Markdown source mode, or use a Markdown editor such as Obsidian, Typora, or VS Code Markdown Preview.  
部分 Markdown 预览器会因为 WebView 安全策略限制预览模式中的本地文件跳转。如果预览中无法点击打开本地图片，可以尝试在 Markdown 源码模式中打开链接，或使用 Obsidian、Typora、VS Code Markdown Preview 等编辑器。

---

## Repository Structure / 仓库结构

```text
docx-to-md/
├── SKILL.md
├── README.md
├── LICENSE
└── scripts/
    ├── convert_docx_to_md.py           # DOCX → MD (with images)
    ├── convert_docx_to_md_text_only.py  # DOCX → MD (text only)
    └── convert_other_to_md.py           # PDF/PPTX/XLSX → MD (+ Vision mode)
```

---

## License / 开源协议

This project is licensed under the MIT License.  
本项目使用 MIT License。
