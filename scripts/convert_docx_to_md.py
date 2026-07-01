#!/usr/bin/env python3
"""Convert DOCX files to clean Markdown for Obsidian knowledge bases.

The converter runs Pandoc first, then cleans Pandoc-generated Markdown that may
contain HTML tables, image tags, links, and inline HTML. It supports single-file
and batch conversion. By default, embedded DOCX images are extracted to a sibling
image directory and each image is rendered with both Markdown display syntax and
a clickable original-image link.
"""

from __future__ import annotations

import argparse
import html
import re
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

DEFAULT_CELL_JOINER = "；"
DEFAULT_IMAGE_DIR_SUFFIX = "_images"
MEANINGLESS_ALT_VALUES = {"descript", "description", "image", "图片"}


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


def escape_markdown_cell(text: str, cell_joiner: str) -> str:
    text = normalize_text(text, cell_joiner)
    return text.replace("|", "\\|")


def escape_markdown_label(text: str) -> str:
    return normalize_text(text, " ").replace("[", "\\[").replace("]", "\\]")


def extract_link_target(value: str) -> str:
    value = html.unescape(value).strip()
    if value.startswith("<") and ">" in value:
        return value[1 : value.index(">")]
    for suffix in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff", ".svg", ".emf"):
        match = re.search(rf".*?{re.escape(suffix)}(?=\s+[\"']|$)", value, flags=re.I)
        if match:
            return match.group(0).strip('"')
    return value.strip('"') if value else ""


def image_filename_from_src(src: str) -> str:
    target = extract_link_target(src)
    target = target.split("?", 1)[0].split("#", 1)[0]
    return Path(unquote(target)).name


def safe_path_component(value: str) -> str:
    value = re.sub(r"\s+", "_", value.strip())
    value = re.sub(r"[^\w.-]+", "_", value, flags=re.UNICODE)
    value = re.sub(r"_+", "_", value).strip("._")
    return value or "images"


def format_image_reference(alt: str, src: str, image_dir_name: str | None, inline: bool = False) -> str:
    alt_text = normalize_text(alt, " ")
    filename = image_filename_from_src(src)

    if image_dir_name and filename:
        image_path = f"./{image_dir_name}/{filename}"
        label = escape_markdown_label(alt_text if is_meaningful_alt(alt_text) else filename)
        if inline:
            return f"![{label}]({image_path}) [打开原图]({image_path})"
        return f"![{label}]({image_path})\n\n[打开原图：{label}]({image_path})"

    if is_meaningful_alt(alt_text):
        return "图片：" + alt_text
    return ""


class TableParser(HTMLParser):
    def __init__(self, image_dir_name: str | None = None) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self.current_row: list[str] | None = None
        self.current_cell: list[str] | None = None
        self.current_col = 0
        self.current_cell_colspan = 1
        self.current_cell_rowspan = 1
        self.rowspans: dict[int, list[object]] = {}
        self.image_dir_name = image_dir_name

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr_map = {key.lower(): value or "" for key, value in attrs}

        if tag == "tr":
            self.current_row = []
            self.current_col = 0
            return

        if tag in {"td", "th"} and self.current_row is not None:
            self._fill_pending_rowspans_before_cell()
            self.current_cell = []
            self.current_cell_colspan = self._parse_span(attr_map.get("colspan", "1"))
            self.current_cell_rowspan = self._parse_span(attr_map.get("rowspan", "1"))
            return

        if self.current_cell is None:
            return

        if tag in {"p", "div", "li"}:
            self._append_break()
        elif tag == "br":
            self._append_break()
        elif tag == "img":
            image_text = format_image_reference(
                attr_map.get("alt", ""),
                attr_map.get("src", ""),
                self.image_dir_name,
                inline=True,
            )
            if image_text:
                self.current_cell.append(image_text)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()

        if self.current_cell is not None and tag in {"p", "div", "li"}:
            self._append_break()
            return

        if tag in {"td", "th"} and self.current_row is not None and self.current_cell is not None:
            cell_text = "".join(self.current_cell)
            for offset in range(self.current_cell_colspan):
                text = cell_text if offset == 0 else ""
                self.current_row.append(text)
                if self.current_cell_rowspan > 1:
                    self.rowspans[self.current_col + offset] = [self.current_cell_rowspan - 1, ""]
            self.current_col += self.current_cell_colspan
            self.current_cell = None
            self.current_cell_colspan = 1
            self.current_cell_rowspan = 1
            return

        if tag == "tr" and self.current_row is not None:
            self._fill_pending_rowspans_to_row_end()
            if any(normalize_text(cell) for cell in self.current_row):
                self.rows.append(self.current_row)
            self.current_row = None

    def handle_data(self, data: str) -> None:
        if self.current_cell is not None:
            self.current_cell.append(data)

    def _append_break(self) -> None:
        if self.current_cell is not None and self.current_cell and self.current_cell[-1] != "\n":
            self.current_cell.append("\n")

    @staticmethod
    def _parse_span(value: str) -> int:
        try:
            return max(1, int(value))
        except ValueError:
            return 1

    def _append_pending_rowspan(self) -> None:
        remaining, text = self.rowspans[self.current_col]
        self.current_row.append(str(text))
        if int(remaining) <= 1:
            del self.rowspans[self.current_col]
        else:
            self.rowspans[self.current_col] = [int(remaining) - 1, text]
        self.current_col += 1

    def _fill_pending_rowspans_before_cell(self) -> None:
        while self.current_col in self.rowspans:
            self._append_pending_rowspan()

    def _fill_pending_rowspans_to_row_end(self) -> None:
        while self.rowspans and self.current_col <= max(self.rowspans):
            if self.current_col in self.rowspans:
                self._append_pending_rowspan()
            else:
                self.current_row.append("")
                self.current_col += 1


def html_table_to_markdown(table_html: str, cell_joiner: str, image_dir_name: str | None) -> str:
    parser = TableParser(image_dir_name)
    parser.feed(table_html)
    rows = parser.rows
    if not rows:
        return ""

    col_count = max(len(row) for row in rows)
    normalized_rows = [row + [""] * (col_count - len(row)) for row in rows]

    header = [
        escape_markdown_cell(cell, cell_joiner) or f"列{i + 1}"
        for i, cell in enumerate(normalized_rows[0])
    ]
    body = [[escape_markdown_cell(cell, cell_joiner) for cell in row] for row in normalized_rows[1:]]

    output = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * col_count) + " |",
    ]
    output.extend("| " + " | ".join(row) + " |" for row in body)
    return "\n".join(output)


def get_html_attr(tag_html: str, attr_name: str) -> str:
    match = re.search(rf"\b{re.escape(attr_name)}\s*=\s*([\"'])(.*?)\1", tag_html, re.I | re.S)
    return match.group(2) if match else ""


def replace_html_img_tag(match: re.Match[str], image_dir_name: str | None) -> str:
    tag_html = match.group(0)
    return format_image_reference(
        get_html_attr(tag_html, "alt"),
        get_html_attr(tag_html, "src"),
        image_dir_name,
    )


def replace_markdown_image(match: re.Match[str], image_dir_name: str | None) -> str:
    return format_image_reference(match.group(1), match.group(2), image_dir_name)


def strip_markdown_link(match: re.Match[str]) -> str:
    return normalize_text(match.group(1), " ")


def clean_non_table(text: str, image_dir_name: str | None) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"(?<!!)\[([^\]\n]+)\]\([^\)\n]+\)", strip_markdown_link, text)
    text = re.sub(
        r"!\[([^\]]*)\]\(([^\)\n]+)\)(?:\{[^\n]*\})?",
        lambda match: replace_markdown_image(match, image_dir_name),
        text,
    )
    text = re.sub(
        r"<a\b[^>]*>(.*?)</a>",
        lambda match: normalize_text(re.sub(r"<[^>]+>", "", match.group(1)), " "),
        text,
        flags=re.I | re.S,
    )
    text = re.sub(
        r"<img\b[^>]*>",
        lambda match: replace_html_img_tag(match, image_dir_name),
        text,
        flags=re.I | re.S,
    )
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</?p[^>]*>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text, flags=re.I | re.S)
    text = html.unescape(text)

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

    return "\n".join(lines).strip()


def convert_document(text: str, cell_joiner: str, image_dir_name: str | None) -> str:
    parts: list[str] = []
    last = 0

    for match in re.finditer(r"<table\b.*?</table>", text, flags=re.I | re.S):
        before = clean_non_table(text[last : match.start()], image_dir_name)
        table = html_table_to_markdown(match.group(0), cell_joiner, image_dir_name)
        if before:
            parts.append(before)
        if table:
            parts.append(table)
        last = match.end()

    after = clean_non_table(text[last:], image_dir_name)
    if after:
        parts.append(after)

    return "\n\n".join(parts).strip() + "\n"


def run_pandoc(source: Path, raw_markdown: Path, pandoc: str, extract_media_dir: Path | None, cwd: Path) -> None:
    command = [
        pandoc,
        str(source),
        "--from=docx",
        "--to=gfm",
        "--wrap=none",
        "--markdown-headings=atx",
        "--output",
        str(raw_markdown),
    ]
    if extract_media_dir is not None:
        command.append(f"--extract-media={extract_media_dir}")

    try:
        subprocess.run(command, check=True, text=True, capture_output=True, cwd=cwd)
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Pandoc is not installed or not found in PATH.\n"
            "Install options:\n"
            "  brew install pandoc          # recommended on macOS\n"
            "  sudo apt install pandoc      # Ubuntu/Debian\n"
            "If already installed but not found, add it to PATH:\n"
            "  export PATH=\"/opt/homebrew/bin:$PATH\"\n"
            "Then rerun conversion."
        ) from exc
    except subprocess.CalledProcessError as exc:
        details = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        raise RuntimeError(f"Pandoc failed for {source}: {details}") from exc


def flatten_extracted_images(image_dir: Path) -> list[Path]:
    if not image_dir.exists():
        return []

    source_root = image_dir / "media" if (image_dir / "media").exists() else image_dir
    extracted: list[Path] = []
    for image_file in sorted(path for path in source_root.rglob("*") if path.is_file()):
        destination = image_dir / image_file.name
        if image_file.resolve() != destination.resolve():
            if destination.exists():
                destination.unlink()
            shutil.move(str(image_file), str(destination))
        extracted.append(destination)

    media_dir = image_dir / "media"
    if media_dir.exists():
        shutil.rmtree(media_dir)

    for child in sorted(image_dir.rglob("*"), reverse=True):
        if child.is_dir():
            try:
                child.rmdir()
            except OSError:
                pass

    return sorted(set(extracted))


def convert_docx_file(
    source: Path,
    target: Path,
    cell_joiner: str,
    pandoc: str,
    keep_raw: bool,
    extract_images: bool,
    image_dir_suffix: str,
) -> None:
    if source.suffix.lower() != ".docx":
        raise ValueError(f"Input file is not a .docx file: {source}")
    if source.name.startswith("~$"):
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    image_dir_name = safe_path_component(f"{target.stem}{image_dir_suffix}") if extract_images else None
    image_dir = target.parent / image_dir_name if image_dir_name else None
    extract_media_dir = Path(image_dir.name) if image_dir is not None else None

    with tempfile.TemporaryDirectory(prefix="docx-to-md-") as tmp_dir:
        raw_markdown = Path(tmp_dir) / f"{source.stem}.raw.md"
        run_pandoc(source, raw_markdown, pandoc, extract_media_dir, target.parent)
        if image_dir is not None:
            flatten_extracted_images(image_dir)
        image_dir_name = image_dir.name if image_dir is not None and image_dir.exists() else None
        cleaned = convert_document(raw_markdown.read_text(encoding="utf-8", errors="ignore"), cell_joiner, image_dir_name)
        target.write_text(cleaned, encoding="utf-8")
        if keep_raw:
            shutil.copyfile(raw_markdown, target.with_suffix(".raw.md"))

    print(f"converted: {source} -> {target}")
    if image_dir is not None and image_dir.exists():
        print(f"images: {image_dir}")


def iter_docx_files(input_dir: Path, recursive: bool) -> list[Path]:
    pattern = "**/*.docx" if recursive else "*.docx"
    return sorted(path for path in input_dir.glob(pattern) if path.is_file() and not path.name.startswith("~$"))


def convert_docx_directory(
    input_dir: Path,
    output_dir: Path,
    cell_joiner: str,
    pandoc: str,
    recursive: bool,
    keep_raw: bool,
    extract_images: bool,
    image_dir_suffix: str,
) -> None:
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input directory does not exist: {input_dir}")

    sources = iter_docx_files(input_dir, recursive)
    if not sources:
        print(f"No .docx files found in {input_dir}")
        return

    for source in sources:
        relative = source.relative_to(input_dir)
        target = output_dir / relative.with_suffix(".md")
        convert_docx_file(source, target, cell_joiner, pandoc, keep_raw, extract_images, image_dir_suffix)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert DOCX files to clean Markdown for Obsidian and model retrieval.")
    parser.add_argument("--input-file", type=Path, help="Single .docx file to convert.")
    parser.add_argument("--output-file", type=Path, help="Output .md path. Defaults to input file with .md suffix.")
    parser.add_argument("--input-dir", type=Path, help="Directory containing .docx files.")
    parser.add_argument("--output-dir", type=Path, help="Directory for converted Markdown files.")
    parser.add_argument("--recursive", action="store_true", help="Recursively convert .docx files in subdirectories.")
    parser.add_argument("--keep-raw", action="store_true", help="Keep Pandoc intermediate Markdown as *.raw.md next to the cleaned output.")
    parser.add_argument("--no-extract-images", action="store_true", help="Do not extract embedded images; keep only meaningful alt text as plain text.")
    parser.add_argument(
        "--image-dir-suffix",
        default=DEFAULT_IMAGE_DIR_SUFFIX,
        help="Suffix for sibling image directories. Default: _images, producing <markdown-stem>_images/.",
    )
    parser.add_argument(
        "--cell-joiner",
        default=DEFAULT_CELL_JOINER,
        help="Text used to join multiple lines inside a Markdown table cell. Default: Chinese semicolon.",
    )
    parser.add_argument("--pandoc", default="pandoc", help="Pandoc executable path. Default: pandoc from PATH.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    extract_images = not args.no_extract_images

    try:
        if args.input_file:
            target = args.output_file or args.input_file.with_suffix(".md")
            convert_docx_file(
                args.input_file,
                target,
                args.cell_joiner,
                args.pandoc,
                args.keep_raw,
                extract_images,
                args.image_dir_suffix,
            )
            return 0

        if args.input_dir:
            if not args.output_dir:
                raise ValueError("--output-dir is required when using --input-dir.")
            convert_docx_directory(
                args.input_dir,
                args.output_dir,
                args.cell_joiner,
                args.pandoc,
                args.recursive,
                args.keep_raw,
                extract_images,
                args.image_dir_suffix,
            )
            return 0

        raise ValueError("Use either --input-file [--output-file] or --input-dir --output-dir.")
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
