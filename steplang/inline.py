from __future__ import annotations

import html
import re
from urllib.parse import urlsplit

from .model import StepSyntaxError

_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_INLINE = re.compile(r"`([^`]+)`|\[([^\]]+)\]\(([^)\s]+)\)|\*\*(.+?)\*\*")


def escape(text: str) -> str:
    return html.escape(text, quote=True)


def _check_url(url: str, *, kind: str, source: str, line: int, text: str) -> None:
    value = url.strip()
    if not value:
        raise StepSyntaxError("empty URL", line=line, source=source, text=text)
    if any(ord(ch) < 0x20 for ch in value):
        raise StepSyntaxError("URL contains control characters", line=line, source=source, text=text)

    scheme = ""
    if value.startswith("//"):
        scheme = "//"
    else:
        match = _SCHEME.match(value)
        if match:
            scheme = match.group(0)[:-1].lower()

    allowed = {"http", "https", "mailto", "tel"} if kind == "link" else {"http", "https"}
    if scheme and scheme != "//" and scheme not in allowed:
        raise StepSyntaxError(
            f"unsupported URL scheme '{scheme}:' for {kind}",
            line=line,
            source=source,
            text=text,
        )
    if scheme == "//" and kind == "image":
        raise StepSyntaxError(
            "protocol-relative image URLs are not supported; use https://",
            line=line,
            source=source,
            text=text,
        )


def _external(url: str) -> bool:
    value = url.strip()
    return value.startswith("//") or bool(re.match(r"^https?://", value, re.IGNORECASE))


def render_inline(text: str, *, source: str = "", line: int = 0) -> str:
    """Escape text and render a deliberately small inline markup subset."""
    out: list[str] = []
    pos = 0

    for match in _INLINE.finditer(text):
        out.append(escape(text[pos : match.start()]))
        code, label, url, bold = match.groups()

        if code is not None:
            out.append(f"<code>{escape(code)}</code>")
        elif label is not None and url is not None:
            _check_url(url, kind="link", source=source, line=line, text=text)
            attrs = f'href="{escape(url)}"'
            if _external(url):
                attrs += ' target="_blank" rel="noopener noreferrer"'
            out.append(f"<a {attrs}>{escape(label)}</a>")
        elif bold is not None:
            out.append(f"<strong>{escape(bold)}</strong>")

        pos = match.end()

    out.append(escape(text[pos:]))
    return "".join(out)


def validate_url(url: str, *, kind: str, source: str = "", line: int = 0, text: str = "") -> str:
    _check_url(url, kind=kind, source=source, line=line, text=text)
    return url.strip()


def url_host(url: str) -> str:
    try:
        return urlsplit(url).hostname or ""
    except ValueError:
        return ""
