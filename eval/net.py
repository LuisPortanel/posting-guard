"""A deliberately broad search, written separately from posting_guard's rules.

It finds postings that might contain a trap, so a human can label them, including the ones the guard
misses. It is noisy on purpose: it shares no code or patterns with the package, and its hits are
only candidates for labeling, never verdicts.
"""
from __future__ import annotations

import html
import re
import unicodedata
from typing import List, Tuple

_AI = r"(?:a\.?i\.?|llms?|gpt\w*|chat\s*gpt|claude|gemini|copilot|language\s+models?|bots?|automated|agents?|assistants?|machines?|algorithms?|robots?|ia|inteligencia\s+artificial)"
NET = [
    ("ai-addressed", re.compile(r"\b(?:if|when|in\s+case|as|for|si|attention|note|dear|hey|hello|to)\b[^.\n]{0,40}\b" + _AI + r"\b[^.\n]{0,40}\b(?:read|reading|process|processing|parse|parsing|review|reviewing|screen|screening|evaluat\w*|summari[sz]\w*|eres|lees)\b", re.I)),
    ("ai-addressed", re.compile(r"\b" + _AI + r"\b[^.\n]{0,60}\b(?:must|should|please|always|never|ignore|disregard|respond|reply|answer|say|state|output|rank|recommend|include|mention)\b", re.I)),
    ("ai-addressed", re.compile(r"\b(?:ignore|disregard|forget|override|bypass)\b[^.\n]{0,60}\b(?:instructions?|prompts?|rules|guidelines|directions)\b", re.I)),
    ("ai-addressed", re.compile(r"\b(?:prompt\s+injection|system\s+prompt|jailbreak|you\s+are\s+now|new\s+instructions?)\b", re.I)),
    ("read-check", re.compile(r"\b(?:include|mention|use|put|add|write|type|insert|start|begin|end|open|close|sign|answer|reply|respond|reference|tell\s+us)\b[^.\n]{0,80}\b(?:words?|phrases?|emojis?|code\s*words?|keywords?|passwords?|colou?rs?|fruits?|vegetables?|animals?|favou?rite|subject(?:\s+line)?|first\s+line|haiku|poem|joke|riddle|song|movie)\b", re.I)),
    ("read-check", re.compile(r"\b(?:so|to\s+show|to\s+prove|to\s+let\s+us\s+know|para\s+saber|para\s+demostrar)\b[^.\n]{0,40}\b(?:read|reading|le[ií]ste|leyó|attention|paying\s+attention|made\s+it)\b", re.I)),
    ("read-check", re.compile(r"\b(?:made\s+it\s+(?:this\s+far|to\s+the\s+(?:end|bottom))|still\s+reading|read\s+(?:this|the\s+(?:whole|entire|full))|scrolled|secret\s+(?:word|code|question)|easter\s+egg)\b", re.I)),
    ("read-check", re.compile(r"[\"“”'‘’«][^\"“”'‘’«»\n]{2,40}[\"“”'‘’»][^.\n]{0,40}\b(?:in|into|at\s+the\s+(?:top|start|end))\b[^.\n]{0,30}\b(?:application|cover\s+letter|message|answer|response|email|subject|note)\b", re.I)),
    ("off-form", re.compile(r"\b(?:e-?mail|send|submit|forward|dm|message|write\s+to)\b[^.\n]{0,60}\b(?:resume|résumé|cv|application|portfolio|cover\s+letter|candidacy)\b[^.\n]{0,60}(?:@|\b(?:directly|linkedin|telegram|whatsapp|discord|twitter)\b)", re.I)),
    ("off-form", re.compile(r"\b(?:apply|applications?)\b[^.\n]{0,30}\b(?:by|via|through|over|only\s+(?:by|via))\b\s+(?:e-?mail|linkedin\s+message|dm|telegram|whatsapp|discord)\b", re.I)),
    ("off-form", re.compile(r"\b(?:skip|don'?t\s+(?:fill|use|bother\s+with)|do\s+not\s+(?:fill|use)|instead\s+of)\b[^.\n]{0,30}\b(?:the\s+)?(?:form|application|ats|portal)\b", re.I)),
]

_HIDDEN_STYLE = re.compile(
    r"(?:display\s*:\s*none|visibility\s*:\s*(?:hidden|collapse)|font-size\s*:\s*(?:0|0?\.\d+|1|2)(?:px|pt)?\b"
    r"|opacity\s*:\s*0?\.?0*\d?\s*[;\"']|color\s*:\s*(?:#f{3,6}\b|white|transparent|rgba\([^)]*,\s*0(?:\.\d+)?\))"
    r"|position\s*:\s*absolute[^\"']*-\d{3,}|text-indent\s*:\s*-\d{3,}|clip(?:-path)?\s*:|height\s*:\s*0|width\s*:\s*0"
    r"|transform\s*:\s*scale\(\s*0)", re.I)
_HIDDEN_ATTR = re.compile(r"<[^>]+(?:\shidden(?:\s|=|>)|class\s*=\s*[\"'][^\"']*\b(?:sr-only|visually-hidden|screen-reader|hidden|invisible|d-none|offscreen)\b)", re.I)
_COMMENT = re.compile(r"<!--(.*?)-->", re.S)


def _lines(text: str) -> List[str]:
    return [l.strip() for l in re.split(r"[\n\r]+|<br\s*/?>|</p>|</li>|</div>", text) if l.strip()]


def _strip_tags(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


def scan_net(raw: str) -> List[Tuple[str, str]]:
    """Return (category, snippet) pairs. Snippets are cut to 240 characters."""
    hits: List[Tuple[str, str]] = []
    text = html.unescape(raw) if "&lt;" in raw else raw
    plain = html.unescape(_strip_tags(text.replace("</p>", "\n").replace("<br", "\n<br").replace("</li>", "\n")))
    for line in _lines(plain.replace(". ", ".\n")):
        for cat, rx in NET:
            if rx.search(line):
                hits.append((cat, line[:240]))
                break
    for m in re.finditer(r"<[^>]+style\s*=\s*[\"']([^\"']*)[\"'][^>]*>", text, re.I):
        if _HIDDEN_STYLE.search(m.group(1)):
            after = _strip_tags(text[m.end():m.end() + 400])[:160]
            hits.append(("hidden-text", f"style={m.group(1)[:80]!r} -> {after}"))
    for m in _HIDDEN_ATTR.finditer(text):
        after = _strip_tags(text[m.end():m.end() + 400])[:160]
        hits.append(("hidden-text", f"{m.group(0)[:80]} -> {after}"))
    for m in _COMMENT.finditer(text):
        body = re.sub(r"\s+", " ", m.group(1)).strip()
        if len(body.split()) >= 3 and not re.search(r"\[if |endif|^\s*(?:end|start|begin)\b", body, re.I):
            hits.append(("hidden-text", f"<!-- {body[:200]} -->"))
    odd = [c for c in text if unicodedata.category(c) == "Cf" and c not in "­‍️"]
    odd += [c for c in text if 0xE0000 <= ord(c) <= 0xE007F or 0xE000 <= ord(c) <= 0xF8FF]
    if odd:
        names = sorted({unicodedata.name(c, hex(ord(c))) for c in odd})
        hits.append(("unicode-trick", f"{len(odd)} format/private-use chars: {', '.join(names[:6])}"))
    for w in re.findall(r"\w{3,}", plain):
        scripts = {unicodedata.name(c, "?").split()[0] for c in w if c.isalpha()}
        if "LATIN" in scripts and scripts & {"CYRILLIC", "GREEK"}:
            hits.append(("unicode-trick", f"mixed-script word: {w}"))
            break
    return hits
