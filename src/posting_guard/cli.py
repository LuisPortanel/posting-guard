"""Command line: posting-guard FILE|- [--out CLEAN.txt] [--json] [--strict]"""
from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from . import __version__
from .core import REVIEW, scan


def _print_report(report) -> None:
    print(report.summary)
    for f in report.instructions:
        print(f"  > line {f.line} ({f.kind}): {f.text}")
    for f in report.hidden_instructions:
        print(f"  > IN HIDDEN TEXT ({f.kind}): {f.text}")
    if report.hidden_text and not report.minor_hidden_text:
        print("  hidden text:", report.hidden_text[:400].replace("\n", " | "))
    for c in report.suspicious_comments[:5]:
        print("  suspicious comment:", c[:160])
    if report.invisible_chars:
        print("  invisible characters:", ", ".join(f"{k}={v}" for k, v in report.invisible_chars.items()))
    for s in report.tag_smuggled_text:
        print("  hidden in Unicode tags:", s[:200])
    if report.mixed_script_words:
        print("  mixed alphabets:", ", ".join(report.mixed_script_words))
    for u in report.hidden_only_urls:
        print("  URL only in hidden text:", u[:160])


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="posting-guard",
        description="Flag hidden text, invisible characters and prompt-injection lines in a job posting "
                    "before an LLM reads it. Warns, never blocks.")
    ap.add_argument("file", help="HTML (escaped HTML too), Markdown or plain text; '-' reads stdin")
    ap.add_argument("--out", metavar="PATH",
                    help="write the visible, cleaned text (instruction lines marked) to PATH")
    ap.add_argument("--json", action="store_true", help="print the full report as JSON")
    ap.add_argument("--strict", action="store_true", help="exit with status 2 when the verdict is REVIEW")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = ap.parse_args(argv)

    if args.file == "-":
        raw = sys.stdin.read()
    else:
        with open(args.file, encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
    report = scan(raw)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(report.clean_text + "\n")
    if args.json:
        print(json.dumps(report.to_dict(include_text=False), ensure_ascii=False, indent=1))
    else:
        _print_report(report)
    return 2 if args.strict and report.verdict == REVIEW else 0
