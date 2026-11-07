"""Plain-text helpers: invisible characters, mixed scripts, whitespace."""
from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Optional, Tuple

INVISIBLE_RANGES = {
    "zero-width": [(0x200B, 0x200D), (0x2060, 0x2064), (0xFEFF, 0xFEFF), (0x00AD, 0x00AD),
                   (0x180E, 0x180E), (0x034F, 0x034F)],
    "bidi-control": [(0x200E, 0x200F), (0x202A, 0x202E), (0x2066, 0x2069), (0x061C, 0x061C)],
    "unicode-tag": [(0xE0000, 0xE007F)],
    "variation-selector": [(0xFE00, 0xFE0F), (0xE0100, 0xE01EF)],
}

# Zero-width characters wedged between two word characters: a common way to break keyword filters.
INSIDE_WORD = re.compile(r"\w[​-‍⁠-⁤﻿­]+\w")

_BLACK_FLAG = 0x1F3F4
_CANCEL_TAG = 0xE007F
_FLAG_PAYLOAD = re.compile(r"[a-z]{2}[a-z0-9]{1,5}")
_SYMBOL_CATEGORIES = ("So", "Sm", "Sk")


def invisible_kind(ch: str) -> Optional[str]:
    o = ord(ch)
    for kind, ranges in INVISIBLE_RANGES.items():
        for a, b in ranges:
            if a <= o <= b:
                return kind
    return None


def _flag_sequence_end(text: str, i: int) -> int:
    """If text[i] starts a subdivision flag emoji (black flag + tag letters + cancel tag), return the
    index just past it; otherwise return -1. These flags (England, Scotland, Wales) legitimately use
    Unicode tag characters."""
    j = i + 1
    while j < len(text) and 0xE0020 <= ord(text[j]) <= 0xE007E:
        j += 1
    if j < len(text) and ord(text[j]) == _CANCEL_TAG:
        payload = "".join(chr(ord(c) - 0xE0000) for c in text[i + 1:j])
        if _FLAG_PAYLOAD.fullmatch(payload):
            return j + 1
    return -1


def strip_invisibles(text: str) -> Tuple[str, Dict[str, int], List[str]]:
    """Remove invisible characters. Returns (clean text, counts by kind, ASCII text decoded from
    Unicode tag characters). Keeps the ones emoji need: a variation selector after a symbol, a
    zero-width joiner between two emoji, and the tag sequence of a subdivision flag."""
    counts: Dict[str, int] = {}
    smuggled: List[str] = []
    out: List[str] = []
    run: List[str] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        o = ord(ch)
        if o == _BLACK_FLAG:
            end = _flag_sequence_end(text, i)
            if end > 0:
                if run:
                    smuggled.append("".join(run))
                    run = []
                out.append(text[i:end])
                i = end
                continue
        kind = invisible_kind(ch)
        prev = out[-1][-1] if out else ""
        if kind == "variation-selector" and 0xFE00 <= o <= 0xFE0F and prev \
                and (unicodedata.category(prev) in _SYMBOL_CATEGORIES or prev in "0123456789#*"):
            out.append(ch)       # emoji or symbol followed by its selector, e.g. U+26A0 U+FE0F
            i += 1
            continue
        if ch == "‍" and prev and i + 1 < n \
                and (unicodedata.category(prev) in ("So", "Sk") or prev == "️") \
                and unicodedata.category(text[i + 1]) == "So":
            out.append(ch)       # zero-width joiner inside an emoji sequence
            i += 1
            continue
        if kind:
            counts[kind] = counts.get(kind, 0) + 1
            if kind == "unicode-tag" and 0xE0020 <= o <= 0xE007E:
                run.append(chr(o - 0xE0000))
            i += 1
            continue
        if run:
            smuggled.append("".join(run))
            run = []
        out.append(ch)
        i += 1
    if run:
        smuggled.append("".join(run))
    return "".join(out), counts, smuggled


def _script_of(ch: str) -> Optional[str]:
    if not ch.isalpha():
        return None
    name = unicodedata.name(ch, "")
    for script in ("LATIN", "CYRILLIC", "GREEK"):
        if name.startswith(script):
            return script
    return "OTHER"


def mixed_script_words(text: str) -> List[str]:
    """Words that mix Latin letters with Cyrillic or Greek look-alikes (homoglyphs)."""
    found = set()
    for word in re.findall(r"\w{2,}", text):
        scripts = {_script_of(c) for c in word} - {None, "OTHER"}
        if "LATIN" in scripts and len(scripts) > 1:
            found.add(word)
    return sorted(found)


def tidy(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()
