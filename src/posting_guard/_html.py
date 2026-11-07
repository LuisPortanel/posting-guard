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
_NAMED = {"white": (255, 255, 255, 1.0), "transparent": (0, 0, 0, 0.0), "black": (0, 0, 0, 1.0),
          "snow": (255, 250, 250, 1.0), "ghostwhite": (248, 248, 255, 1.0), "whitesmoke": (245, 245, 245, 1.0),
          "ivory": (255, 255, 240, 1.0), "mintcream": (245, 255, 250, 1.0), "azure": (240, 255, 255, 1.0)}
_COLOR_TOKEN = re.compile(r"#[0-9a-f]{3,8}\b|(?:rgba?|hsla?)\([^)]*\)|\b[a-z]+\b")
NEAR_WHITE = 245          # every channel at or above this reads as white on a white page
_ALPHA_INVISIBLE = 0.05


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


def _channel(v: str, scale: float = 255) -> float:
    v = v.strip()
    return float(v[:-1]) * scale / 100 if v.endswith("%") else float(v)


def parse_color(value: str) -> Optional[Tuple[float, float, float, float]]:
    """(r, g, b, alpha) for #hex, rgb()/rgba(), hsl()/hsla() and a few named colors; None otherwise."""
    v = value.strip().lower()
    if v in _NAMED:
        return _NAMED[v]
    try:
        if v.startswith("#"):
            h = v[1:]
            if len(h) in (3, 4):
                h = "".join(c * 2 for c in h)
            if len(h) not in (6, 8):
                return None
            alpha = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
            return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha
        m = re.fullmatch(r"(rgba?|hsla?)\((.*)\)", v)
        if not m:
            return None
        parts = [p for p in re.split(r"[,\s/]+", m.group(2).strip()) if p]
        alpha = _channel(parts[3], 1) if len(parts) > 3 else 1.0
        if m.group(1).startswith("rgb"):
            return _channel(parts[0]), _channel(parts[1]), _channel(parts[2]), alpha
        # Saturation and lightness as fractions; a bare number means a percentage (CSS Color 4).
        saturation, lightness = (_channel(p, 1) if p.endswith("%") else float(p) / 100 for p in parts[1:3])
        # Only the lowest channel matters for "near white": it is l - s * min(l, 1 - l).
        low = 255 * (lightness - saturation * min(lightness, 1 - lightness))
        return low, low, low, alpha
    except (ValueError, IndexError):
        return None


def _invisible_color(value: str) -> bool:
    c = parse_color(value)
    if not c:
        return False
    r, g, b, alpha = c
    return alpha < _ALPHA_INVISIBLE or min(r, g, b) >= NEAR_WHITE


def _dark_background(value: str) -> bool:
    """True when a background declaration sets a color that white text would show up on."""
    for token in _COLOR_TOKEN.findall(value.lower()):
        c = parse_color(token)
        if c and c[3] >= 0.5:
            return min(c[0], c[1], c[2]) < NEAR_WHITE
    return False


def style_hides(style: str) -> bool:
    """True when an inline style hides its text from a human reader. White text counts as hidden
    unless the same style gives it a dark background."""
    declarations = []
    for declaration in style.split(";"):
        prop, sep, value = declaration.partition(":")
        if sep:
            declarations.append((prop.strip().lower(), value.lower().replace("!important", "").strip()))
    dark_background = any(prop in ("background", "background-color") and _dark_background(value)
                          for prop, value in declarations)
    for prop, value in declarations:
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
        if prop == "color" and _invisible_color(value) and not dark_background:
            return True
        if prop == "transform" and re.search(r"\bscale[xy]?\(\s*0*\.?0+\s*(?:[,)])", value):
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
