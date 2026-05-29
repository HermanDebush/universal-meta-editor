import io
import re
import zipfile
from pathlib import Path

from .models import AppMeta, CoreMeta, MetaBundle


# ── XML patch helpers ─────────────────────────────────────────────────────────

def _set_tag(xml: str, tag_pattern: str, value: str) -> str:
    """Replace inner text of the first matching tag. tag_pattern is a regex."""
    return re.sub(
        rf"(<{tag_pattern}(?:\s[^>]*)?>)[^<]*(</[^>]+>)",
        rf"\g<1>{value}\2",
        xml,
        count=1,
    )


def _patch_core(xml: str, meta: CoreMeta) -> str:
    pairs = [
        (r"dc:title",                    meta.title),
        (r"dc:subject",                  meta.subject),
        (r"dc:creator",                  meta.author),
        (r"cp:lastModifiedBy",           meta.last_modified_by),
        (r"cp:keywords",                 meta.keywords),
        (r"dc:description",              meta.description),
        (r"cp:category",                 meta.category),
        (r"cp:revision",                 meta.revision),
        (r"(?:[a-zA-Z]+:)?created",      meta.created),
        (r"(?:[a-zA-Z]+:)?modified",     meta.modified),
    ]
    for pattern, value in pairs:
        if value:
            xml = _set_tag(xml, pattern, value)
    return xml


def _patch_app(xml: str, meta: AppMeta, count_field: str | None) -> str:
    if not xml:
        return xml
    pairs = [
        (r"Application", meta.application),
        (r"Company",     meta.company),
        (r"TotalTime",   meta.total_time),
        (r"AppVersion",  meta.app_version),
    ]
    for pattern, value in pairs:
        if value:
            xml = _set_tag(xml, pattern, value)
    if count_field and meta.page_count:
        xml = _set_tag(xml, count_field, meta.page_count)
    return xml


# ── Public API ────────────────────────────────────────────────────────────────

def write_metadata(
    source_path: str | Path,
    bundle: MetaBundle,
    core: CoreMeta,
    app: AppMeta,
    output_path: str | Path,
) -> Path:
    """
    Write patched metadata into a clean copy of source_path saved at output_path.
    Rebuilds the zip from scratch to avoid duplicate entries.
    Returns the output path.
    """
    source_path = Path(source_path)
    output_path = Path(output_path)

    new_core = _patch_core(bundle._raw_core, core).encode("utf-8")
    new_app  = _patch_app(bundle._raw_app,  app, bundle.fmt.count_field).encode("utf-8") if bundle._raw_app else None

    # Read all original entries, then write a fresh zip replacing only what changed
    buf = io.BytesIO()
    with zipfile.ZipFile(source_path, "r") as src, \
         zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            if item.filename == "docProps/core.xml":
                dst.writestr(item, new_core)
            elif item.filename == "docProps/app.xml" and new_app is not None:
                dst.writestr(item, new_app)
            else:
                dst.writestr(item, src.read(item.filename))

    output_path.write_bytes(buf.getvalue())
    return output_path
