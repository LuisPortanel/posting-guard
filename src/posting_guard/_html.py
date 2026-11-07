"""HTML handling: split visible text from hidden text."""
from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from typing import Dict, List, Optional, Set, Tuple

DROP_TAGS = {"script", "style", "noscript", "template", "head"}
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
             "source", "track", "wbr"}
BLOCK_TAGS = {"p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr",
              "table", "section", "article", "header", "footer", "blockquote", "pre", "hr"}

HIDDEN_CLASS = re.compile(
    r"^(sr-only|visually-hidden|screen-reader-text|screenreader|d-none|hidden|invisible)$", re.I)
# A responsive variant that shows the element again ("hidden md:block", "d-none d-lg-flex").
REVEAL_CLASS = re.compile(
    r"^((sm|md|lg|xl|2xl):(block|inline|inline-block|flex|inline-flex|grid|inline-grid|table|contents|visible"
    r"|not-sr-only)|d-(sm|md|lg|xl|xxl)-(block|inline|inline-block|flex|inline-flex|grid|table))$", re.I)

_NUMBER = re.compile(r"^(-?\d*\.?\d+)\s*([a-z%]*)$")
_INVISIBLE_COLORS = {"#fff", "#ffffff", "white", "transparent"}


def _number(value: str) -> Optional[Tuple[float, str]]:
    m = _NUMBER.match(value)
    return (float(m.group(1)), m.group(2)) if m else None


def _tiny_font(value: str) -> bool:
    parsed = _number(value)
    if not parsed:
        return False                      # keywords such as "small" or "inherit"
    size, unit = parsed
    if unit in ("px", "pt"):
        return size <= 1
    if unit in ("em", "rem"):
        return size < 0.25
    if unit == "%":
        return size < 25
    return size == 0


def _invisible_color(value: str) -> bool:
    v = value.replace(" ", "")
    if v in _INVISIBLE_COLORS or re.fullmatch(r"#(fff0|ffffff00)", v):
        return True
    return bool(re.fullmatch(r"(rgba|hsla)\(.*,(0|0?\.0+)\)", v))


def style_hides(style: str) -> bool:
    """True when an inline style hides its text from a human reader."""
    for declaration in style.split(";"):
        prop, sep, value = declaration.partition(":")
        if not sep:
            continue
        prop = prop.strip().lower()
        value = value.lower().replace("!important", "").strip()
        if prop.startswith("--"):
            continue                      # CSS custom property, e.g. --link-color
        if prop == "display" and value == "none":
            return True
        if prop == "visibility" and value in ("hidden", "collapse"):
            return True
        if prop == "font-size" and _tiny_font(value):
            return True
        if prop == "opacity":
            parsed = _number(value)
            if parsed and not parsed[1] and parsed[0] < 0.05:
                return True
        if prop == "color" and _invisible_color(value):
            return True
        if prop in ("left", "top", "right", "text-indent", "margin-left") and re.match(r"-\d{3,}", value):
            return True
        if prop == "clip" and re.match(r"rect\(\s*0", value):
            return True
        if prop in ("height", "max-height") and value in ("0", "0px"):
            return True
    return False


def class_hides(classes: str) -> bool:
    tokens = classes.split()
    return any(HIDDEN_CLASS.match(t) for t in tokens) and not any(REVEAL_CLASS.match(t) for t in tokens)


class HiddenTextParser(HTMLParser):
    """Separates visible text from hidden text.

    "style" hidden: inline style, the `hidden` attribute or a hidden input. Always reported.
    "class" hidden: classes such as sr-only or Tailwind's `hidden`. Pages use them for short
    accessibility labels, so the caller decides whether the amount of text is worth reporting.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: List[Tuple[str, Optional[str], bool]] = []   # (tag, hidden kind, dropped)
        self.visible: List[str] = []
        self.hidden: List[str] = []
        self.class_hidden: List[str] = []
        self.comments: List[str] = []
        self.hidden_blocks = 0
        self.visible_urls: Set[str] = set()
        self.hidden_urls: Set[str] = set()

    def _kind(self) -> Optional[str]:
        kinds = {k for _, k, _ in self.stack if k}
        return "style" if "style" in kinds else ("class" if kinds else None)

    def _dropped(self) -> bool:
        return any(d for _, _, d in self.stack)

    def _sink(self, kind: Optional[str]) -> List[str]:
        return {"style": self.hidden, "class": self.class_hidden}.get(kind or "", self.visible)

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        a: Dict[str, str] = {k.lower(): (v or "") for k, v in attrs}
        kind = None
        if "hidden" in a or style_hides(a.get("style", "")) or a.get("type", "").lower() == "hidden":
            kind = "style"
        elif class_hides(a.get("class", "")):
            kind = "class"
        if kind == "style" and self._kind() != "style" and tag not in VOID_TAGS:
            self.hidden_blocks += 1
        effective = "style" if "style" in (kind, self._kind()) else (kind or self._kind())
        href = a.get("href") or ""
        if href.startswith("http"):
            (self.hidden_urls if effective == "style" else self.visible_urls).add(href)
        if tag in BLOCK_TAGS:
            self._sink(effective).append("\n")
        if tag == "li" and not effective:
            self.visible.append("- ")
        if tag not in VOID_TAGS:
            self.stack.append((tag, kind, tag in DROP_TAGS))

    def handle_startendtag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS and self.stack and self.stack[-1][0] == tag:
            self.stack.pop()

    def handle_endtag(self, tag: str) -> None:
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break
        if tag in BLOCK_TAGS:
            self._sink(self._kind()).append("\n")

    def handle_data(self, data: str) -> None:
        if not self._dropped():
            self._sink(self._kind()).append(data)

    def handle_comment(self, data: str) -> None:
        if data.strip():
            self.comments.append(data.strip())


def linkedin_description(raw: str) -> Optional[str]:
    """On a public LinkedIn job page only the description matters; the rest is menus and hidden
    modals. Returns the inner HTML of the description element, keeping nested elements."""
    m = re.search(r'<(\w+)\b[^>]*class="[^"]*show-more-less-html__markup[^"]*"[^>]*>', raw)
    if not m:
        return None
    tag, start, depth = m.group(1).lower(), m.end(), 1
    for t in re.finditer(r"<(/?)%s\b[^>]*>" % re.escape(tag), raw[start:], re.I):
        depth += -1 if t.group(1) else 1
        if depth == 0:
            return raw[start:start + t.start()]
    return raw[start:]


def unescape_if_escaped(raw: str) -> str:
    """Some ATS APIs (Greenhouse) return the description as escaped HTML: &lt;p&gt;."""
    if re.search(r"&lt;\s*/?\s*[a-zA-Z]", raw) and not re.search(r"<\s*/?\s*(p|div|li|ul|br|span)\b", raw[:2000], re.I):
        return html.unescape(raw)
    return raw


def looks_like_html(raw: str) -> bool:
    return bool(re.search(r"<\s*/?\s*(p|div|li|ul|ol|br|span|h\d|strong|em|a|table|section)\b[^>]*>", raw, re.I))
