from dataclasses import dataclass, field
from typing import Optional


# ── Format info ───────────────────────────────────────────────────────────────

@dataclass
class FormatInfo:
    ext:         str
    label:       str
    icon:        str
    count_field: Optional[str]   # "Pages" | "Slides" | "Sheets" | None


# ── Core metadata  (docProps/core.xml) ────────────────────────────────────────

@dataclass
class CoreMeta:
    title:            str = ""
    subject:          str = ""
    author:           str = ""   # dc:creator
    last_modified_by: str = ""   # cp:lastModifiedBy
    keywords:         str = ""
    description:      str = ""
    category:         str = ""
    revision:         str = ""   # cp:revision  — save count
    created:          str = ""   # dcterms:created  ISO-8601
    modified:         str = ""   # dcterms:modified ISO-8601


# ── App metadata  (docProps/app.xml) ──────────────────────────────────────────

@dataclass
class AppMeta:
    application: str = ""
    company:     str = ""
    total_time:  str = ""   # minutes
    app_version: str = ""
    page_count:  str = ""   # Pages / Slides / Sheets — depends on format


# ── Bundle returned by reader ─────────────────────────────────────────────────

@dataclass
class MetaBundle:
    core:      CoreMeta
    app:       AppMeta
    fmt:       FormatInfo
    _raw_core: str = field(repr=False)
    _raw_app:  str = field(repr=False, default="")
