---
name: docx-to-md
description: 当用户需要将一个或多个 Word .docx 文档转换为适合 Obsidian、知识库入库、RAG 检索或模型阅读的干净 Markdown 时，应使用此 skill；它支持单文件转换、批量转换、递归转换、默认图片提取、仅文本转换、Markdown 图片显示与可点击原图链接、Pandoc 生成内容清理、HTML 表格转 Markdown 表格、图片 alt 文本保留、链接文本提取和内联 HTML 清理。
---

# DOCX 转 Markdown

## 概述

将单个或多个 `.docx` 文档转换为适合 Obsidian 和知识库检索的干净 Markdown。默认使用 `scripts/convert_docx_to_md.py` 执行 Pandoc 转换、提取图片并清理 Markdown；当用户明确要求“仅保留文本”时，使用 `scripts/convert_docx_to_md_text_only.py`，不提取图片文件、不写入图片链接，只保留正文、表格、链接可见文本和有意义的图片 alt 文本。

## 适用场景

在以下需求中使用此 skill：

- 将一个 Word 文档转换为 Markdown。
- 将一个文件夹中的多个 `.docx` 批量转换为 `.md`。
- 递归转换多级目录中的 `.docx` 文件。
- 从 `.docx` 中提取图片，并在 Markdown 中同时保留图片显示和可点击原图链接。
- 仅保留 Word 文档中的文本内容，不提取图片。
- 清理 Pandoc 生成的 Markdown 中残留的 HTML 表格、图片标签、链接或内联 HTML。
- 将 Word 文档整理为适合 Obsidian、知识库入库、RAG 检索或模型阅读的 Markdown。

不用于 PDF 转换、表格文件转换，或在 Word 文档内部直接编辑排版。

## 前置条件

转换依赖 `pandoc`。执行转换前先检查：

```bash
pandoc --version
```

如果 macOS 环境缺少 `pandoc`，可安装：

```bash
brew install pandoc
```

除非用户明确要求安装依赖，否则不要自动安装依赖。

## 快速开始

在 skill 目录中运行脚本。

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

## 脚本选择逻辑

- 用户提到“保留图片”“提取图片”“图片也要保留”“带图片转换”等需求时，使用 `scripts/convert_docx_to_md.py`。
- 用户没有说明是否保留图片时，默认使用 `scripts/convert_docx_to_md.py`，即保留图片并生成同级图片目录。
- 用户明确说“仅保留文本”“不要图片”“不提取图片”“纯文本转换”时，使用 `scripts/convert_docx_to_md_text_only.py`。

## 转换流程

1. 判断用户输入的是单个 `.docx` 文件还是目录。
2. 先按“脚本选择逻辑”选择转换脚本。
3. 选择对应转换模式：
   - 单文件：使用 `--input-file`，可选 `--output-file`。
   - 批量目录：使用 `--input-dir` 和 `--output-dir`。
   - 递归批量：在批量目录模式中增加 `--recursive`。
4. 尽量使用绝对路径执行脚本，避免工作目录不一致导致找不到文件。
5. 转换完成后确认生成的 `.md` 文件；如果使用保留图片脚本，还要确认同级图片目录。
6. 如果 `pandoc` 缺失，说明安装方式，并在环境准备好后重新执行转换。

## 脚本行为

内置脚本分两步处理文档：

1. 使用 Pandoc 将 `.docx` 转换为原始 GitHub Flavored Markdown。
2. 对原始 Markdown 进行清理和增强：
   - `scripts/convert_docx_to_md.py` 默认将 `.docx` 内嵌图片提取到 `<md文件名>_images/` 目录；目录名中的空格和特殊符号会自动替换为下划线，提升本地 Markdown 预览兼容性。
   - 将图片引用转换为两行 Markdown：第一行直接显示图片，第二行提供可点击的“打开原图”链接。
   - 将 Pandoc 生成的 `media/` 子目录扁平化，图片统一放在 `<md文件名>_images/` 下。
   - `scripts/convert_docx_to_md_text_only.py` 不提取图片文件、不生成图片链接，只在有意义 alt 文本存在时保留 `图片：alt` 文本。
   - 将 `<table>...</table>` 转换为 Markdown pipe table。
   - 处理 HTML 表格中的 `rowspan` / `colspan`：只在合并区域第一个格子填入内容，其余被合并的占位格保持为空，避免 Markdown 表格列错位。
   - 默认使用中文分号 `；` 扁平化表格单元格内的多行内容。
   - 转义表格单元格中的竖线 `|`。
   - 移除 `image`、`description`、`descript`、`图片` 等泛化图片标签。
   - 将普通链接替换为可见链接文本。
   - 移除 `<br>`、段落标签和其他噪声内联 HTML。
   - 合并重复空行。

## 常用参数

- `--cell-joiner "；"`：设置表格单元格内多行文本的连接符，默认是中文分号。
- `--recursive`：递归批量转换子目录中的 `.docx` 文件，并保留相对目录结构。
- `--keep-raw`：保留 Pandoc 生成的中间 Markdown，输出为 `*.raw.md`，便于排查格式问题。
- `scripts/convert_docx_to_md_text_only.py`：仅保留文本内容，不提取真实图片文件，只在有意义 alt 文本存在时保留 `图片：alt` 文本。
- `--no-extract-images`：主脚本的兼容参数；新任务中优先使用文本专用脚本。
- `--image-dir-suffix "_images"`：设置同级图片目录后缀，默认生成安全化后的 `<md文件名>_images/`，其中空格和特殊符号会替换为下划线。
- `--pandoc PATH`：指定 Pandoc 可执行文件路径。

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
- 点击“打开原图”链接跳转到图片文件。
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
