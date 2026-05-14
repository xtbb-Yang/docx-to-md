#!/usr/bin/env python3
"""Convert DOCX files to text-only clean Markdown.

This wrapper uses the main docx-to-md converter with image extraction disabled.
It keeps document text, tables, links as visible text, and meaningful image alt
text as plain text, but does not extract image files or write image links.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from convert_docx_to_md import DEFAULT_CELL_JOINER, convert_docx_directory, convert_docx_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert DOCX files to text-only clean Markdown.")
    parser.add_argument("--input-file", type=Path, help="Single .docx file to convert.")
    parser.add_argument("--output-file", type=Path, help="Output .md path. Defaults to input file with .md suffix.")
    parser.add_argument("--input-dir", type=Path, help="Directory containing .docx files.")
    parser.add_argument("--output-dir", type=Path, help="Directory for converted Markdown files.")
    parser.add_argument("--recursive", action="store_true", help="Recursively convert .docx files in subdirectories.")
    parser.add_argument("--keep-raw", action="store_true", help="Keep Pandoc intermediate Markdown as *.raw.md next to the cleaned output.")
    parser.add_argument(
        "--cell-joiner",
        default=DEFAULT_CELL_JOINER,
        help="Text used to join multiple lines inside a Markdown table cell. Default: Chinese semicolon.",
    )
    parser.add_argument("--pandoc", default="pandoc", help="Pandoc executable path. Default: pandoc from PATH.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        if args.input_file:
            target = args.output_file or args.input_file.with_suffix(".md")
            convert_docx_file(
                args.input_file,
                target,
                args.cell_joiner,
                args.pandoc,
                args.keep_raw,
                False,
                "_images",
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
                False,
                "_images",
            )
            return 0

        raise ValueError("Use either --input-file [--output-file] or --input-dir --output-dir.")
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
