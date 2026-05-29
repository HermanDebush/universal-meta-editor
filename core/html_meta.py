"""
HTML file metadata — read and write <title> and <meta> tags.
No external dependencies (regex only). Preserves original encoding.
"""
from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass
class HTMLMeta:
    title:          str = ""
    description:    str = ""
    keywords:       str = ""
    author:         str = ""
    viewport:       str = ""
    og_title:       str = ""
    og_description: str = ""
    og_type:        str = ""
    charset:        str = ""   # informational; not edited directly


# ── HTML helpers ──────────────────────────────────────────────────────────────

def _unescape(s: str) -> str:
    return (s.replace("&amp;", "&").replace("&lt;", "<")
             .replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'"))

def _escape(s: str) -> str:
    return s.replace("&", "&amp;").replace('"', "&quot;")


# ── Reader ────────────────────────────────────────────────────────────────────

def _title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    return _unescape(m.group(1).strip()) if m else ""

def _meta_name(html: str, name: str) -> str:
    """<meta name="X" content="Y"> or reversed attribute order."""
    n = re.escape(name)
    for pat in (
        rf'<meta\b[^>]*\bname=["\']?{n}["\']?[^>]*\bcontent=["\']([^"\']*)["\'][^>]*/?>',
        rf'<meta\b[^>]*\bcontent=["\']([^"\']*)["\'][^>]*\bname=["\']?{n}["\']?[^>]*/?>',
    ):
        m = re.search(pat, html, re.I)
        if m:
            return _unescape(m.group(1))
    return ""

def _meta_prop(html: str, prop: str) -> str:
    """<meta property="og:X" content="Y"> or reversed."""
    p = re.escape(prop)
    for pat in (
        rf'<meta\b[^>]*\bproperty=["\']?{p}["\']?[^>]*\bcontent=["\']([^"\']*)["\'][^>]*/?>',
        rf'<meta\b[^>]*\bcontent=["\']([^"\']*)["\'][^>]*\bproperty=["\']?{p}["\']?[^>]*/?>',
    ):
        m = re.search(pat, html, re.I)
        if m:
            return _unescape(m.group(1))
    return ""

def _charset(html: str) -> str:
    m = re.search(r'<meta\b[^>]*\bcharset=["\']?([^"\'\s>]+)', html[:4096], re.I)
    return m.group(1) if m else ""


def read_html_meta(path: str | Path) -> HTMLMeta:
    raw = Path(path).read_bytes()
    enc = "utf-8"
    m = re.search(rb'charset=["\']?([^"\'\s>]+)', raw[:2048], re.I)
    if m:
        try:
            enc = m.group(1).decode("ascii")
        except Exception:
            pass
    html = raw.decode(enc, errors="replace")
    return HTMLMeta(
        title          = _title(html),
        description    = _meta_name(html, "description"),
        keywords       = _meta_name(html, "keywords"),
        author         = _meta_name(html, "author"),
        viewport       = _meta_name(html, "viewport"),
        og_title       = _meta_prop(html, "og:title"),
        og_description = _meta_prop(html, "og:description"),
        og_type        = _meta_prop(html, "og:type"),
        charset        = _charset(html),
    )


# ── Writer ────────────────────────────────────────────────────────────────────

def _insert_in_head(html: str, tag: str) -> str:
    if re.search(r"</head>", html, re.I):
        return re.sub(r"(</head>)", rf"  {tag}\n\1", html, count=1, flags=re.I)
    if re.search(r"<body\b", html, re.I):
        return re.sub(r"(<body\b)", rf"{tag}\n\1", html, count=1, flags=re.I)
    return html + f"\n{tag}"

def _set_title(html: str, value: str) -> str:
    esc = _escape(value)
    if re.search(r"<title[^>]*>", html, re.I):
        return re.sub(r"(<title[^>]*>).*?(</title>)", rf"\g<1>{esc}\2",
                      html, count=1, flags=re.I | re.S)
    return _insert_in_head(html, f"<title>{esc}</title>")

def _set_meta_name(html: str, name: str, value: str) -> str:
    esc = _escape(value)
    n   = re.escape(name)
    pat1 = rf'(<meta\b[^>]*\bname=["\']?{n}["\']?[^>]*\bcontent=["\'])([^"\']*?)(["\'][^>]*/?>)'
    pat2 = rf'(<meta\b[^>]*\bcontent=["\'])([^"\']*?)(["\'][^>]*\bname=["\']?{n}["\']?[^>]*/?>)'
    if re.search(pat1, html, re.I):
        return re.sub(pat1, rf'\g<1>{esc}\g<3>', html, count=1, flags=re.I)
    if re.search(pat2, html, re.I):
        return re.sub(pat2, rf'\g<1>{esc}\g<3>', html, count=1, flags=re.I)
    return _insert_in_head(html, f'<meta name="{name}" content="{esc}">')

def _set_meta_prop(html: str, prop: str, value: str) -> str:
    esc = _escape(value)
    p   = re.escape(prop)
    pat1 = rf'(<meta\b[^>]*\bproperty=["\']?{p}["\']?[^>]*\bcontent=["\'])([^"\']*?)(["\'][^>]*/?>)'
    pat2 = rf'(<meta\b[^>]*\bcontent=["\'])([^"\']*?)(["\'][^>]*\bproperty=["\']?{p}["\']?[^>]*/?>)'
    if re.search(pat1, html, re.I):
        return re.sub(pat1, rf'\g<1>{esc}\g<3>', html, count=1, flags=re.I)
    if re.search(pat2, html, re.I):
        return re.sub(pat2, rf'\g<1>{esc}\g<3>', html, count=1, flags=re.I)
    return _insert_in_head(html, f'<meta property="{prop}" content="{esc}">')


def write_html_meta(source: str | Path, dest: str | Path, meta: HTMLMeta) -> Path:
    """Patch HTML meta tags; write result to dest. Source is never modified."""
    src, dst = Path(source), Path(dest)
    raw = src.read_bytes()
    enc = "utf-8"
    m = re.search(rb'charset=["\']?([^"\'\s>]+)', raw[:2048], re.I)
    if m:
        try:
            enc = m.group(1).decode("ascii")
        except Exception:
            pass

    html = raw.decode(enc, errors="replace")

    if meta.title:          html = _set_title(html, meta.title)
    if meta.description:    html = _set_meta_name(html, "description",    meta.description)
    if meta.keywords:       html = _set_meta_name(html, "keywords",       meta.keywords)
    if meta.author:         html = _set_meta_name(html, "author",         meta.author)
    if meta.viewport:       html = _set_meta_name(html, "viewport",       meta.viewport)
    if meta.og_title:       html = _set_meta_prop(html, "og:title",       meta.og_title)
    if meta.og_description: html = _set_meta_prop(html, "og:description", meta.og_description)
    if meta.og_type:        html = _set_meta_prop(html, "og:type",        meta.og_type)

    dst.write_text(html, encoding=enc, errors="replace")
    return dst
