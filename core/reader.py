import re
import zipfile
from pathlib import Path

from .formats import detect_format
from .models import AppMeta, CoreMeta, MetaBundle


# ── XML helpers ───────────────────────────────────────────────────────────────

def _get(xml: str, tag: str) -> str:
    """Return inner text of the first matching tag (namespace-aware)."""
    m = re.search(rf"<[^>]*{re.escape(tag)}[^>]*>([^<]*)</[^>]*{re.escape(tag)}>", xml)
    return m.group(1).strip() if m else ""


def _get_plain(xml: str, local: str) -> str:
    """Match a tag by its local name only (ignores namespace prefix)."""
    m = re.search(rf"<(?:[a-zA-Z]+:)?{re.escape(local)}(?:\s[^>]*)?>([^<]*)</(?:[a-zA-Z]+:)?{re.escape(local)}>", xml)
    return m.group(1).strip() if m else ""


# ── Parsers ───────────────────────────────────────────────────────────────────

def _parse_core(xml: str) -> CoreMeta:
    return CoreMeta(
        title            = _get_plain(xml, "title"),
        subject          = _get_plain(xml, "subject"),
        author           = _get(xml, "dc:creator"),
        last_modified_by = _get(xml, "cp:lastModifiedBy"),
        keywords         = _get(xml, "cp:keywords"),
        description      = _get_plain(xml, "description"),
        category         = _get(xml, "cp:category"),
        revision         = _get(xml, "cp:revision"),
        created          = _get_plain(xml, "created"),
        modified         = _get_plain(xml, "modified"),
    )


def _parse_app(xml: str, count_field: str | None) -> AppMeta:
    return AppMeta(
        application = _get_plain(xml, "Application"),
        company     = _get_plain(xml, "Company"),
        total_time  = _get_plain(xml, "TotalTime"),
        app_version = _get_plain(xml, "AppVersion"),
        page_count  = _get_plain(xml, count_field) if count_field else "",
    )


# ── Public API ────────────────────────────────────────────────────────────────

def read_metadata(path: str | Path) -> MetaBundle:
    path = Path(path)
    fmt  = detect_format(path.name)

    with zipfile.ZipFile(path, "r") as zf:
        names = zf.namelist()

        if "docProps/core.xml" not in names:
            raise ValueError("docProps/core.xml not found — is this a valid Office file?")

        raw_core = zf.read("docProps/core.xml").decode("utf-8")
        raw_app  = zf.read("docProps/app.xml").decode("utf-8") if "docProps/app.xml" in names else ""

    return MetaBundle(
        core      = _parse_core(raw_core),
        app       = _parse_app(raw_app, fmt.count_field),
        fmt       = fmt,
        _raw_core = raw_core,
        _raw_app  = raw_app,
    )
