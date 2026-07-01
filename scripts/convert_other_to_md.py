#!/usr/bin/env python3
"""Convert PDF, PPTX, and XLSX files to clean Markdown using MarkItDown.

This script uses the MarkItDown library as the conversion backend for file types
that Pandoc does not handle well. The output goes through the same post-processing
pipeline as the docx-to-md converter (HTML cleanup, blank line merging, image
extraction from base64, table normalization, etc.).

Supported formats: .pdf, .pptx, .xlsx

Vision mode (--vision): For PDF files containing images, charts, or diagrams,
renders each page as a high-resolution PNG and uses a VLM (via claude-internal)
to produce structured Markdown that preserves visual semantics.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import unquote

SUPPORTED_EXTENSIONS = {".pdf", ".pptx", ".xlsx"}
DEFAULT_IMAGE_DIR_SUFFIX = "_images"
DEFAULT_CELL_JOINER = "；"
MEANINGLESS_ALT_VALUES = {"descript", "description", "image", "图片"}


# ---------------------------------------------------------------------------
# Utility functions (shared logic with convert_docx_to_md.py)
# ---------------------------------------------------------------------------

def is_meaningful_alt(value: str) -> bool:
    value = html.unescape(value).strip()
    return bool(value) and value.lower() not in MEANINGLESS_ALT_VALUES


def normalize_text(text: str, joiner: str = "\n") -> str:
    text = html.unescape(text).replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    lines = [line for line in lines if line]
    if joiner != "\n":
        lines = [line.rstrip("；;") for line in lines]
    return joiner.join(lines)


def safe_path_component(value: str) -> str:
    value = re.sub(r"\s+", "_", value.strip())
    value = re.sub(r"[^\w.-]+", "_", value, flags=re.UNICODE)
    value = re.sub(r"_+", "_", value).strip("._")
    return value or "images"


def escape_markdown_cell(text: str, cell_joiner: str) -> str:
    text = normalize_text(text, cell_joiner)
    return text.replace("|", "\\|")


def escape_markdown_label(text: str) -> str:
    return normalize_text(text, " ").replace("[", "\\[").replace("]", "\\]")


# ---------------------------------------------------------------------------
# Base64 image extraction
# ---------------------------------------------------------------------------

def extract_base64_images(markdown: str, image_dir: Path, image_dir_name: str) -> str:
    """Find base64-encoded images in Markdown and extract them as local files."""
    pattern = r"!\[([^\]]*)\]\(data:image/([a-zA-Z0-9+]+);base64,([A-Za-z0-9+/=\s]+)\)"

    counter = [0]

    def _replace_base64_image(match: re.Match[str]) -> str:
        alt_text = match.group(1)
        ext = match.group(2).lower()
        b64_data = match.group(3).strip()

        if ext == "jpeg":
            ext = "jpg"
        elif ext in ("svg+xml", "svg"):
            ext = "svg"

        try:
            image_data = base64.b64decode(b64_data)
        except Exception:
            return match.group(0)

        counter[0] += 1
        digest = hashlib.md5(image_data).hexdigest()[:8]
        filename = f"image{counter[0]}_{digest}.{ext}"

        image_dir.mkdir(parents=True, exist_ok=True)
        image_path = image_dir / filename
        image_path.write_bytes(image_data)

        rel_path = f"./{image_dir_name}/{filename}"
        label = escape_markdown_label(alt_text) if is_meaningful_alt(alt_text) else filename
        return f"![{label}]({rel_path})\n\n[打开原图：{label}]({rel_path})"

    return re.sub(pattern, _replace_base64_image, markdown)


# ---------------------------------------------------------------------------
# Post-processing pipeline (mirrors convert_docx_to_md.py logic)
# ---------------------------------------------------------------------------

def clean_markdown(text: str, image_dir_name: str | None) -> str:
    """Clean MarkItDown output to match docx-to-md quality standards."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Strip non-link Markdown links: [text](url) -> text (keep image links)
    text = re.sub(r"(?<!!)\[([^\]\n]+)\]\([^\)\n]+\)", lambda m: normalize_text(m.group(1), " "), text)

    # Clean HTML <a> tags to plain text
    text = re.sub(
        r"<a\b[^>]*>(.*?)</a>",
        lambda m: normalize_text(re.sub(r"<[^>]+>", "", m.group(1)), " "),
        text,
        flags=re.I | re.S,
    )

    # Replace <br> tags
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)

    # Replace <p> tags
    text = re.sub(r"</?p[^>]*>", "\n", text, flags=re.I)

    # Remove remaining HTML tags (but keep table content already parsed)
    text = re.sub(r"<[^>]+>", "", text, flags=re.I | re.S)

    # Unescape HTML entities
    text = html.unescape(text)

    # Normalize image references if we have an image directory
    if image_dir_name:
        def _fix_image_ref(m: re.Match[str]) -> str:
            alt = m.group(1)
            src = m.group(2)
            # Already local path reference — keep as is
            if src.startswith(f"./{image_dir_name}/") or src.startswith(f"{image_dir_name}/"):
                label = escape_markdown_label(alt) if is_meaningful_alt(alt) else Path(src).name
                return f"![{label}]({src})\n\n[打开原图：{label}]({src})"
            return m.group(0)

        text = re.sub(r"!\[([^\]]*)\]\(([^\)\n]+)\)", _fix_image_ref, text)

    # Merge consecutive blank lines
    lines: list[str] = []
    previous_blank = False
    for raw_line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        if not line:
            if not previous_blank:
                lines.append("")
            previous_blank = True
            continue
        lines.append(line)
        previous_blank = False

    return "\n".join(lines).strip() + "\n"


# ---------------------------------------------------------------------------
# Vision mode: VLM-based PDF conversion
# ---------------------------------------------------------------------------

VISION_PROMPT = """请将这张图片中的内容转换为结构化 Markdown 格式。

要求：
1. 完整保留所有可读文字（标题、正文、标注、图例、数据标签等）
2. 识别并保留视觉结构：
   - 层级关系用标题层级（# ## ###）表示
   - 并列内容用列表表示
   - 箭头/连线用文字描述流向关系
   - 时间线/时间节点用表格表示
3. 图表内容语义化描述：
   - 柱状图/饼图：描述类型、坐标轴、关键数据点
   - 流程图/架构图：描述节点和连接关系
   - 表格：转为 Markdown 表格
4. 图标/logo 仅简述文字（如"某品牌 logo"），不展开描述
5. 禁止编造图中未出现的任何内容
6. 直接输出 Markdown，不要添加解释性文字"""


def render_pdf_pages(source: Path, output_dir: Path, dpi: int = 300) -> list[Path]:
    """Render each page of a PDF to a PNG image using PyMuPDF.

    Returns a list of PNG file paths in page order.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print(
            "error: pymupdf is not installed. Install it with:\n"
            "  pip install pymupdf\n"
            "Required for --vision mode (PDF page rendering).",
            file=sys.stderr,
        )
        raise SystemExit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(source))
    pages: list[Path] = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(dpi=dpi)
        filename = f"page_{page_num + 1:04d}.png"
        out_path = output_dir / filename
        pix.save(str(out_path))
        pages.append(out_path)

    doc.close()
    return pages


def _check_vision_api_config() -> None:
    """Check that Vision API environment variables are properly configured.

    If not configured, prints a detailed setup guide and exits.
    """
    api_key = os.environ.get("VISION_API_KEY", "")
    if api_key:
        return

    # Also check common provider-specific keys as fallback
    for env_var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "ZHIPUAI_API_KEY"):
        if os.environ.get(env_var, ""):
            return

    print(
        "\n"
        "=" * 70 + "\n"
        "  ❌ Vision 模式需要配置多模态 API 密钥\n"
        "=" * 70 + "\n"
        "\n"
        "  --vision 模式需要调用支持图片理解的 AI 模型 API。\n"
        "  请按以下步骤配置（只需配置一次，永久生效）：\n"
        "\n"
        "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  步骤 1：获取 API Key（任选一个 provider）\n"
        "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "  • OpenAI (GPT-4o)     → https://platform.openai.com/api-keys\n"
        "  • Google Gemini       → https://aistudio.google.com/apikey\n"
        "  • 智谱 GLM-4V         → https://open.bigmodel.cn/usercenter/apikeys\n"
        "  • Anthropic Claude    → https://console.anthropic.com/settings/keys\n"
        "  • CodeBuddy 内网      → https://codebuddy.woa.com/settings/apikey\n"
        "\n"
        "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  步骤 2：配置环境变量\n"
        "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "  打开终端，执行以下命令（以 OpenAI 为例）：\n"
        "\n"
        '    echo \'export VISION_API_KEY="sk-你的密钥"\' >> ~/.zshrc\n'
        '    echo \'export VISION_API_BASE="https://api.openai.com/v1"\' >> ~/.zshrc\n'
        '    echo \'export VISION_MODEL="gpt-4o"\' >> ~/.zshrc\n'
        "    source ~/.zshrc\n"
        "\n"
        "  不同 provider 的配置示例：\n"
        "\n"
        "  ┌──────────────┬──────────────────────────────────────────┬────────────────────┐\n"
        "  │ Provider     │ VISION_API_BASE                          │ VISION_MODEL       │\n"
        "  ├──────────────┼──────────────────────────────────────────┼────────────────────┤\n"
        "  │ OpenAI       │ https://api.openai.com/v1                │ gpt-4o             │\n"
        "  │ Google       │ https://generativelanguage.googleapis.com│ gemini-2.5-flash   │\n"
        "  │ 智谱         │ https://open.bigmodel.cn/api/paas/v4     │ glm-4v-plus        │\n"
        "  │ Anthropic    │ https://api.anthropic.com/v1             │ claude-sonnet-4    │\n"
        "  └──────────────┴──────────────────────────────────────────┴────────────────────┘\n"
        "\n"
        "  也支持直接设置 provider 专属变量（无需 VISION_* 前缀）：\n"
        "    export OPENAI_API_KEY=\"sk-xxx\"   （自动使用 gpt-4o）\n"
        "\n"
        "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  步骤 3：验证配置\n"
        "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "    echo $VISION_API_KEY\n"
        "    # 应输出你的密钥（非空即成功）\n"
        "\n"
        "  配置完成后重新运行本命令即可。\n"
        "\n"
        "=" * 70 + "\n",
        file=sys.stderr,
    )
    raise SystemExit(1)


def _get_vision_api_config() -> tuple[str, str, str]:
    """Resolve Vision API configuration from environment variables.

    Returns (api_key, api_base, model) tuple.
    Priority: VISION_* env vars > provider-specific env vars (OPENAI > others).
    """
    # Explicit VISION_* config takes priority
    api_key = os.environ.get("VISION_API_KEY", "")
    api_base = os.environ.get("VISION_API_BASE", "https://api.openai.com/v1")
    model = os.environ.get("VISION_MODEL", "gpt-4o")

    if api_key:
        return api_key, api_base, model

    # Fallback to provider-specific keys
    if os.environ.get("OPENAI_API_KEY"):
        return os.environ["OPENAI_API_KEY"], "https://api.openai.com/v1", "gpt-4o"
    if os.environ.get("GOOGLE_API_KEY"):
        return os.environ["GOOGLE_API_KEY"], "https://generativelanguage.googleapis.com/v1beta/openai", "gemini-2.5-flash"
    if os.environ.get("ZHIPUAI_API_KEY"):
        return os.environ["ZHIPUAI_API_KEY"], "https://open.bigmodel.cn/api/paas/v4", "glm-4v-plus"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"], "https://api.anthropic.com/v1", "claude-sonnet-4"

    # Should not reach here if _check_vision_api_config passed
    raise RuntimeError("No Vision API key found in environment.")


def vision_convert_page(image_path: Path, timeout: int = 120) -> str:
    """Call a VLM via OpenAI-compatible API to recognize a single page image.

    Reads the image, encodes as base64, sends to the configured Vision API,
    and returns the Markdown text output.

    Requires: pip install openai
    Env vars: VISION_API_KEY, VISION_API_BASE, VISION_MODEL (or provider-specific keys)

    Returns the Markdown text output from the model.
    Raises RuntimeError on failure.
    """
    try:
        from openai import OpenAI
    except ImportError:
        print(
            "error: openai package is not installed. Install it with:\n"
            "  pip install openai\n"
            "Required for --vision mode (VLM API calls).",
            file=sys.stderr,
        )
        raise SystemExit(1)

    api_key, api_base, model = _get_vision_api_config()

    # Read and encode image as base64
    image_data = image_path.read_bytes()
    b64_image = base64.b64encode(image_data).decode("utf-8")

    client = OpenAI(api_key=api_key, base_url=api_base, timeout=timeout)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": VISION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64_image}",
                            },
                        },
                    ],
                }
            ],
            max_tokens=4096,
        )
    except Exception as e:
        raise RuntimeError(f"VLM API error for {image_path.name}: {e}")

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError(f"VLM returned empty response for {image_path.name}")

    return content.strip()


def convert_file_vision(
    source: Path,
    target: Path,
    dpi: int = 300,
    timeout: int = 120,
    keep_raw: bool = False,
) -> None:
    """Vision mode: render PDF pages as images and use VLM for conversion.

    Each page is rendered at the specified DPI, then fed to a multimodal model
    via OpenAI-compatible API. Pages are joined with a separator comment.
    On per-page failure, falls back to pdftotext for that page.
    """
    ext = source.suffix.lower()
    if ext != ".pdf":
        raise ValueError(f"Vision mode only supports PDF files, got: {ext}")

    # Check API configuration before starting (exits with guide if missing)
    _check_vision_api_config()

    # Create temp directory for page images
    tmp_dir = Path(tempfile.mkdtemp(prefix="d2m_vision_"))

    try:
        print(f"vision: rendering {source.name} at {dpi} DPI...")
        pages = render_pdf_pages(source, tmp_dir, dpi=dpi)
        print(f"vision: {len(pages)} pages rendered, starting VLM recognition...")

        page_markdowns: list[str] = []

        for i, page_path in enumerate(pages):
            page_num = i + 1
            print(f"  page {page_num}/{len(pages)}...", end=" ", flush=True)

            try:
                md = vision_convert_page(page_path, timeout=timeout)
                print("ok")
            except RuntimeError as e:
                print(f"FAILED ({e}), falling back to pdftotext")
                md = _fallback_pdftotext_page(source, page_num)

            page_markdowns.append(md)

            # Rate limiting between pages
            if i < len(pages) - 1:
                time.sleep(1)

        # Join all pages
        raw_output = "\n\n---\n\n".join(page_markdowns)

        target.parent.mkdir(parents=True, exist_ok=True)

        if keep_raw:
            raw_path = target.with_suffix(".raw.md")
            raw_path.write_text(raw_output, encoding="utf-8")

        # Post-process
        cleaned = clean_markdown(raw_output, None)
        target.write_text(cleaned, encoding="utf-8")

        print(f"converted (vision): {source} -> {target}")

    finally:
        # Cleanup temp images
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _fallback_pdftotext_page(source: Path, page_num: int) -> str:
    """Extract text for a single page using pdftotext as fallback."""
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", "-f", str(page_num), "-l", str(page_num), str(source), "-"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return f"<!-- Page {page_num}: VLM failed, pdftotext unavailable -->"


# ---------------------------------------------------------------------------
# Conversion core
# ---------------------------------------------------------------------------

def convert_file(
    source: Path,
    target: Path,
    extract_images: bool,
    image_dir_suffix: str,
    keep_raw: bool,
) -> None:
    """Convert a single PDF/PPTX/XLSX file to Markdown using MarkItDown."""
    ext = source.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")

    if source.name.startswith("~$"):
        return

    try:
        from markitdown import MarkItDown
    except ImportError:
        print(
            "error: markitdown is not installed. Install it with:\n"
            "  pip install 'markitdown[pdf,pptx,xlsx]'\n"
            "Required sub-packages: pdfminer.six, python-pptx, openpyxl",
            file=sys.stderr,
        )
        raise SystemExit(1)

    md = MarkItDown()
    result = md.convert(str(source))
    raw_markdown = result.text_content

    target.parent.mkdir(parents=True, exist_ok=True)

    # Save raw output if requested
    if keep_raw:
        raw_path = target.with_suffix(".raw.md")
        raw_path.write_text(raw_markdown, encoding="utf-8")

    # Extract base64 images if present and extraction is enabled
    image_dir_name = safe_path_component(f"{target.stem}{image_dir_suffix}") if extract_images else None
    image_dir = target.parent / image_dir_name if image_dir_name else None

    processed = raw_markdown
    if extract_images and image_dir_name and image_dir:
        processed = extract_base64_images(processed, image_dir, image_dir_name)

    # Post-process cleanup
    final_image_dir_name = image_dir.name if (image_dir and image_dir.exists()) else None
    cleaned = clean_markdown(processed, final_image_dir_name)

    target.write_text(cleaned, encoding="utf-8")

    print(f"converted: {source} -> {target}")
    if image_dir and image_dir.exists():
        image_count = len(list(image_dir.iterdir()))
        print(f"images: {image_dir} ({image_count} files)")


def iter_supported_files(input_dir: Path, recursive: bool) -> list[Path]:
    """Find all supported files in a directory."""
    files: list[Path] = []
    for ext in SUPPORTED_EXTENSIONS:
        pattern = f"**/*{ext}" if recursive else f"*{ext}"
        files.extend(
            path for path in input_dir.glob(pattern)
            if path.is_file() and not path.name.startswith("~$")
        )
    return sorted(files)


def convert_directory(
    input_dir: Path,
    output_dir: Path,
    recursive: bool,
    extract_images: bool,
    image_dir_suffix: str,
    keep_raw: bool,
) -> None:
    """Batch convert all supported files in a directory."""
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input directory does not exist: {input_dir}")

    sources = iter_supported_files(input_dir, recursive)
    if not sources:
        print(f"No supported files ({', '.join(sorted(SUPPORTED_EXTENSIONS))}) found in {input_dir}")
        return

    for source in sources:
        relative = source.relative_to(input_dir)
        target = output_dir / relative.with_suffix(".md")
        try:
            convert_file(source, target, extract_images, image_dir_suffix, keep_raw)
        except Exception as exc:
            print(f"error converting {source}: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert PDF, PPTX, and XLSX files to clean Markdown using MarkItDown."
    )
    parser.add_argument("--input-file", type=Path, help="Single file to convert (PDF, PPTX, or XLSX).")
    parser.add_argument("--output-file", type=Path, help="Output .md path. Defaults to input file with .md suffix.")
    parser.add_argument("--input-dir", type=Path, help="Directory containing files to convert.")
    parser.add_argument("--output-dir", type=Path, help="Directory for converted Markdown files.")
    parser.add_argument("--recursive", action="store_true", help="Recursively convert files in subdirectories.")
    parser.add_argument("--keep-raw", action="store_true", help="Keep MarkItDown raw output as *.raw.md.")
    parser.add_argument(
        "--no-extract-images",
        action="store_true",
        help="Do not extract base64-encoded images to local files.",
    )
    parser.add_argument(
        "--image-dir-suffix",
        default=DEFAULT_IMAGE_DIR_SUFFIX,
        help="Suffix for sibling image directories. Default: _images.",
    )

    # Vision mode arguments
    parser.add_argument(
        "--vision",
        action="store_true",
        help="Enable VLM vision mode for PDF: render pages as images and use "
             "claude-internal for visual understanding. Requires: pymupdf, claude-internal.",
    )
    parser.add_argument(
        "--vision-dpi",
        type=int,
        default=300,
        help="DPI for PDF page rendering in vision mode. Default: 300.",
    )
    parser.add_argument(
        "--vision-timeout",
        type=int,
        default=120,
        help="Timeout in seconds for VLM per-page processing. Default: 120.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    extract_images = not args.no_extract_images

    try:
        if args.input_file:
            target = args.output_file or args.input_file.with_suffix(".md")

            # Vision mode: PDF only
            if args.vision:
                if args.input_file.suffix.lower() != ".pdf":
                    raise ValueError("--vision mode only supports PDF files.")
                convert_file_vision(
                    args.input_file,
                    target,
                    dpi=args.vision_dpi,
                    timeout=args.vision_timeout,
                    keep_raw=args.keep_raw,
                )
                return 0

            convert_file(
                args.input_file,
                target,
                extract_images,
                args.image_dir_suffix,
                args.keep_raw,
            )
            return 0

        if args.input_dir:
            if not args.output_dir:
                raise ValueError("--output-dir is required when using --input-dir.")
            if args.vision:
                # Batch vision mode: process all PDFs in directory
                sources = iter_supported_files(args.input_dir, args.recursive)
                pdf_sources = [s for s in sources if s.suffix.lower() == ".pdf"]
                if not pdf_sources:
                    print(f"No PDF files found in {args.input_dir} for vision mode.")
                    return 0
                for source in pdf_sources:
                    relative = source.relative_to(args.input_dir)
                    t = args.output_dir / relative.with_suffix(".md")
                    try:
                        convert_file_vision(
                            source, t,
                            dpi=args.vision_dpi,
                            timeout=args.vision_timeout,
                            keep_raw=args.keep_raw,
                        )
                    except Exception as exc:
                        print(f"error converting {source}: {exc}", file=sys.stderr)
                return 0

            convert_directory(
                args.input_dir,
                args.output_dir,
                args.recursive,
                extract_images,
                args.image_dir_suffix,
                args.keep_raw,
            )
            return 0

        raise ValueError(
            "Use either --input-file [--output-file] or --input-dir --output-dir.\n"
            f"Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
