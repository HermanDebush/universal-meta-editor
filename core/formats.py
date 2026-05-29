from .models import FormatInfo

_FORMATS: dict[str, FormatInfo] = {
    # ── Office Open XML ───────────────────────────────────────────────────────
    "docx": FormatInfo("docx", "Документ Word",                  "📝", "Pages"),
    "docm": FormatInfo("docm", "Документ Word (макросы)",        "📝", "Pages"),
    "xlsx": FormatInfo("xlsx", "Книга Excel",                    "📊", "Sheets"),
    "xlsm": FormatInfo("xlsm", "Книга Excel (макросы)",          "📊", "Sheets"),
    "pptx": FormatInfo("pptx", "Презентация PowerPoint",         "📽", "Slides"),
    "pptm": FormatInfo("pptm", "Презентация PowerPoint (макросы)","📽", "Slides"),
    "vsdx": FormatInfo("vsdx", "Диаграмма Visio",                "📐", None),
    # ── Windows PE ────────────────────────────────────────────────────────────
    "exe":  FormatInfo("exe",  "Приложение Windows",             "⚙",  None),
    "dll":  FormatInfo("dll",  "Библиотека Windows",             "📦", None),
    "sys":  FormatInfo("sys",  "Драйвер Windows",                "⚙",  None),
    "scr":  FormatInfo("scr",  "Скринсейвер Windows",            "🖥",  None),
    # ── Web ───────────────────────────────────────────────────────────────────
    "html": FormatInfo("html", "HTML-страница",                  "🌐", None),
    "htm":  FormatInfo("htm",  "HTML-страница",                  "🌐", None),
    # ── Ярлыки Windows ────────────────────────────────────────────────────────
    "lnk":  FormatInfo("lnk",  "Ярлык Windows",                  "🔗", None),
}

_OFFICE_EXTS = {"docx", "docm", "xlsx", "xlsm", "pptx", "pptm", "vsdx"}
_PE_EXTS     = {"exe", "dll", "sys", "scr"}
_HTML_EXTS   = {"html", "htm"}
_LNK_EXTS    = {"lnk"}

_FALLBACK = FormatInfo("?", "Неизвестный формат", "📄", None)


def detect_format(filename: str) -> FormatInfo:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return _FORMATS.get(ext, _FALLBACK)


def is_office_ext(filename: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in _OFFICE_EXTS


def is_pe_ext(filename: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in _PE_EXTS


def is_html_ext(filename: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in _HTML_EXTS


def supported_extensions() -> list[str]:
    return [f"*.{ext}" for ext in _FORMATS]


def office_extensions() -> list[str]:
    return [f"*.{ext}" for ext in _OFFICE_EXTS]


def pe_extensions() -> list[str]:
    return [f"*.{ext}" for ext in _PE_EXTS]


def html_extensions() -> list[str]:
    return [f"*.{ext}" for ext in _HTML_EXTS]


def is_lnk_ext(filename: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in _LNK_EXTS


def lnk_extensions() -> list[str]:
    return [f"*.{ext}" for ext in _LNK_EXTS]
