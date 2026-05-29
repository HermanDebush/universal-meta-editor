"""
Lightweight internationalization (RU / EN) for Universal Meta Editor.

- Language is auto-detected from the OS on first run (Russian Windows → RU,
  otherwise EN), then persisted in config.json next to the program.
- Use t("key") to fetch a translated string; t("key", name="x") formats it.
- months() / weekdays() return localized calendar labels.
No external dependencies.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

LANGUAGES = ("ru", "en")
DEFAULT_LANG = "en"

# config.json lives next to the executable (frozen) or the project root (source)
if getattr(sys, "frozen", False):
    _BASE = Path(sys.executable).parent
else:
    _BASE = Path(__file__).resolve().parent.parent
_CONFIG = _BASE / "config.json"

_lang: str | None = None


# ── Language detection / persistence ───────────────────────────────────────────

def _detect_system_lang() -> str:
    """Return 'ru' on a Russian-locale system, else 'en'."""
    # Windows: ask the OS for the UI language directly
    if sys.platform == "win32":
        try:
            import ctypes
            lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            if (lcid & 0x3FF) == 0x19:   # PRIMARYLANGID 0x19 = Russian
                return "ru"
            return "en"
        except Exception:
            pass
    # Fallback: standard library locale
    try:
        import locale
        loc = (locale.getdefaultlocale()[0] or "").lower()
        if loc.startswith("ru"):
            return "ru"
    except Exception:
        pass
    return DEFAULT_LANG


def _read_config() -> dict:
    try:
        if _CONFIG.exists():
            return json.loads(_CONFIG.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def load_language() -> str:
    """Resolve language: config.json → system → default. Caches the result."""
    global _lang
    cfg = _read_config().get("language")
    if cfg in LANGUAGES:
        _lang = cfg
    else:
        _lang = _detect_system_lang()
    return _lang


def get_language() -> str:
    return _lang if _lang is not None else load_language()


def set_language(lang: str) -> None:
    """Switch language and persist the choice to config.json."""
    global _lang
    if lang not in LANGUAGES:
        return
    _lang = lang
    try:
        data = _read_config()
        data["language"] = lang
        _CONFIG.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


# ── Lookup ──────────────────────────────────────────────────────────────────--

def t(key: str, **kwargs) -> str:
    """Translate *key* for the current language; format with kwargs if given."""
    lang = get_language()
    s = _STRINGS.get(lang, {}).get(key)
    if s is None:
        s = _STRINGS[DEFAULT_LANG].get(key, key)
    if kwargs:
        try:
            return s.format(**kwargs)
        except Exception:
            return s
    return s


def months() -> list[str]:
    return _MONTHS.get(get_language(), _MONTHS[DEFAULT_LANG])


def weekdays() -> list[str]:
    return _WEEKDAYS.get(get_language(), _WEEKDAYS[DEFAULT_LANG])


# ── Translation tables ──────────────────────────────────────────────────────--

_STRINGS: dict[str, dict[str, str]] = {
    "ru": {
        # Drop / welcome screen
        "drop.title":   "Перетащите файл или нажмите для выбора",
        "drop.formats": ".docx  .xlsx  .pptx  .html  .exe  .dll  .vsdx  .docm  …",
        "drop.choose":  "Выбрать файл",
        "drop.offline": "🔒  Файлы не загружаются — работает полностью оффлайн",
        # Editor shell
        "editor.save":        "⬇  Сохранить файл",
        "editor.change_file": "Сменить файл",
        # Core metadata (Office)
        "core.section":             "ОСНОВНЫЕ МЕТАДАННЫЕ",
        "field.author":             "Автор",
        "field.last_modified_by":   "Изменил",
        "field.title":              "Заголовок",
        "field.subject":            "Тема",
        "field.keywords":           "Ключевые слова",
        "field.category":           "Категория",
        "field.description":        "Описание",
        "field.created":            "Создан",
        "field.modified":           "Изменён",
        "field.revision":           "Ревизий",
        "ph.revision":              "напр. 47",
        # App metadata (Office)
        "app.section":        "МЕТАДАННЫЕ ПРИЛОЖЕНИЯ",
        "field.total_time":   "Время редактирования",
        "hint.minutes":       "минут",
        "ph.total_time":      "напр. 843",
        "field.application":  "Приложение",
        "hint.application":   "напр. Microsoft Office Word",
        "field.company":      "Организация",
        "hint.company":       "название компании",
        "field.app_version":  "Версия",
        "hint.app_version":   "напр. 16.0000",
        "hint.count":         "количество",
        "time.h_m":           "= {h}ч {m}м",
        "time.m":             "= {m}м",
        "count.Pages":        "Страниц",
        "count.Slides":       "Слайдов",
        "count.Sheets":       "Листов",
        # PE metadata
        "pe.section":               "ВЕРСИЯ И ОПИСАНИЕ ПРОГРАММЫ",
        "field.file_description":   "Описание",
        "field.file_version":       "Версия файла",
        "field.product_name":       "Продукт",
        "field.product_version":    "Версия продукта",
        "field.company_name":       "Компания",
        "field.legal_copyright":    "Авторские права",
        "field.original_filename":  "Имя файла",
        "field.internal_name":      "Внутреннее имя",
        "field.comments":           "Комментарии",
        "note.pe_copy":             "⚠  Редактирует копию файла — оригинал не изменяется. Только Windows.",
        "pe.manifest_section":      "МАНИФЕСТ ПРИЛОЖЕНИЯ  (XML)",
        "note.manifest":            "⚠  Редактирует копию файла — оригинал не изменяется. Пустое поле = не менять манифест.",
        # HTML metadata
        "html.section":       "МЕТАДАННЫЕ HTML",
        "field.html_title":   "Заголовок страницы",
        "field.viewport":     "Viewport",
        "og.title":           "OG: Заголовок",
        "og.description":     "OG: Описание",
        "og.type":            "OG: Тип",
        "hint.og_type":       "og:type  (напр. website, article)",
        "field.charset":      "Кодировка",
        "hint.charset":       "charset (только чтение)",
        # LNK shortcut
        "lnk.section":          "ПАРАМЕТРЫ ЯРЛЫКА  (Свойства → Ярлык)",
        "field.target_path":    "Объект",
        "hint.target_path":     "путь к программе, файлу или URL",
        "field.arguments":      "Аргументы",
        "hint.arguments":       "параметры командной строки",
        "field.working_dir":    "Рабочая папка",
        "hint.working_dir":     "каталог при запуске",
        "lnk.comment":          "Комментарий",
        "hint.lnk_comment":     "всплывающая подсказка",
        "field.icon_location":  "Значок",
        "hint.icon_location":   "путь,индекс  (напр. C:\\app.exe,0)",
        "lnk.window":           "Окно",
        "note.lnk_copy":        "⚠  Редактирует копию ярлыка — оригинал не изменяется.",
        "ws.normal":            "Обычное",
        "ws.maximized":         "Развёрнутое",
        "ws.minimized":         "Свёрнутое",
        # FS timestamps
        "fs.section":         "ВРЕМЕННЫЕ МЕТКИ ФАЙЛА  (Свойства → Подробно → Файл)",
        "field.fs_created":   "Дата создания",
        "field.fs_modified":  "Дата изменения",
        "field.fs_accessed":  "Дата доступа",
        "note.fs":            "⚠  Применяется через Windows API (kernel32.SetFileTime) — только Windows",
        # File dialogs
        "dlg.open_title":    "Открыть файл",
        "dlg.all_supported": "Все поддерживаемые файлы",
        "dlg.office_files":  "Файлы Office",
        "dlg.pe_files":      "Программы Windows",
        "dlg.html_files":    "HTML-страницы",
        "dlg.lnk_files":     "Ярлыки Windows",
        "dlg.all_files":     "Все файлы",
        "dlg.office_file":   "Файл Office (*{ext})",
        "dlg.generic_file":  "Файл (*{ext})",
        "dlg.html_file":     "HTML файл (*{ext})",
        "dlg.lnk_file":      "Ярлык Windows (*.lnk)",
        # Messages
        "err.open_failed":  "Не удалось открыть файл: {exc}",
        "err.unsupported":  "Формат {ext} не поддерживается.\nПоддерживаются: docx · xlsx · pptx · html · exe · dll и другие.",
        "err.read_failed":  "Не удалось прочитать файл: {exc}",
        "err.save_failed":  "Ошибка сохранения: {exc}",
        "info.no_changes":  "Поля не изменены — сохраняем файл без изменений",
        "ok.saved":         "Сохранено → {name}",
        "warn.fs_times":    "Временные метки не применены: {exc}",
        # Footer
        "footer.text": "Universal Meta Editor — открытый код, работает полностью оффлайн",
        # Dialog (error/warning/info)
        "dlg.error":      "Ошибка",
        "dlg.warning":    "Предупреждение",
        "dlg.info":       "Информация",
        "dlg.close_hint": "Enter / Esc — закрыть",
        "btn.copy":       "📋  Скопировать",
        "btn.close":      "Закрыть",
        # Calendar picker
        "cal.title":    "Выбор даты и времени",
        "cal.time_utc": "Время (UTC) ",
        "btn.cancel":   "Отмена",
        "btn.pick":     "Выбрать  ✓",
        # Format labels
        "fmt.docx":    "Документ Word",
        "fmt.docm":    "Документ Word (макросы)",
        "fmt.xlsx":    "Книга Excel",
        "fmt.xlsm":    "Книга Excel (макросы)",
        "fmt.pptx":    "Презентация PowerPoint",
        "fmt.pptm":    "Презентация PowerPoint (макросы)",
        "fmt.vsdx":    "Диаграмма Visio",
        "fmt.exe":     "Приложение Windows",
        "fmt.dll":     "Библиотека Windows",
        "fmt.sys":     "Драйвер Windows",
        "fmt.scr":     "Скринсейвер Windows",
        "fmt.html":    "HTML-страница",
        "fmt.htm":     "HTML-страница",
        "fmt.lnk":     "Ярлык Windows",
        "fmt.unknown": "Неизвестный формат",
    },
    "en": {
        # Drop / welcome screen
        "drop.title":   "Drop a file here or click to choose",
        "drop.formats": ".docx  .xlsx  .pptx  .html  .exe  .dll  .vsdx  .docm  …",
        "drop.choose":  "Choose file",
        "drop.offline": "🔒  Files are never uploaded — works fully offline",
        # Editor shell
        "editor.save":        "⬇  Save file",
        "editor.change_file": "Change file",
        # Core metadata (Office)
        "core.section":             "CORE METADATA",
        "field.author":             "Author",
        "field.last_modified_by":   "Last modified by",
        "field.title":              "Title",
        "field.subject":            "Subject",
        "field.keywords":           "Keywords",
        "field.category":           "Category",
        "field.description":        "Description",
        "field.created":            "Created",
        "field.modified":           "Modified",
        "field.revision":           "Revisions",
        "ph.revision":              "e.g. 47",
        # App metadata (Office)
        "app.section":        "APPLICATION METADATA",
        "field.total_time":   "Editing time",
        "hint.minutes":       "minutes",
        "ph.total_time":      "e.g. 843",
        "field.application":  "Application",
        "hint.application":   "e.g. Microsoft Office Word",
        "field.company":      "Company",
        "hint.company":       "company name",
        "field.app_version":  "Version",
        "hint.app_version":   "e.g. 16.0000",
        "hint.count":         "count",
        "time.h_m":           "= {h}h {m}m",
        "time.m":             "= {m}m",
        "count.Pages":        "Pages",
        "count.Slides":       "Slides",
        "count.Sheets":       "Sheets",
        # PE metadata
        "pe.section":               "VERSION & DESCRIPTION",
        "field.file_description":   "Description",
        "field.file_version":       "File version",
        "field.product_name":       "Product",
        "field.product_version":    "Product version",
        "field.company_name":       "Company",
        "field.legal_copyright":    "Copyright",
        "field.original_filename":  "Original filename",
        "field.internal_name":      "Internal name",
        "field.comments":           "Comments",
        "note.pe_copy":             "⚠  Edits a copy — the original is never modified. Windows only.",
        "pe.manifest_section":      "APPLICATION MANIFEST  (XML)",
        "note.manifest":            "⚠  Edits a copy — the original is never modified. Empty field = keep manifest unchanged.",
        # HTML metadata
        "html.section":       "HTML METADATA",
        "field.html_title":   "Page title",
        "field.viewport":     "Viewport",
        "og.title":           "OG: Title",
        "og.description":     "OG: Description",
        "og.type":            "OG: Type",
        "hint.og_type":       "og:type  (e.g. website, article)",
        "field.charset":      "Charset",
        "hint.charset":       "charset (read-only)",
        # LNK shortcut
        "lnk.section":          "SHORTCUT PROPERTIES  (Properties → Shortcut)",
        "field.target_path":    "Target",
        "hint.target_path":     "path to program, file or URL",
        "field.arguments":      "Arguments",
        "hint.arguments":       "command-line parameters",
        "field.working_dir":    "Start in",
        "hint.working_dir":     "working directory",
        "lnk.comment":          "Comment",
        "hint.lnk_comment":     "tooltip text",
        "field.icon_location":  "Icon",
        "hint.icon_location":   "path,index  (e.g. C:\\app.exe,0)",
        "lnk.window":           "Run",
        "note.lnk_copy":        "⚠  Edits a copy of the shortcut — the original is never modified.",
        "ws.normal":            "Normal",
        "ws.maximized":         "Maximized",
        "ws.minimized":         "Minimized",
        # FS timestamps
        "fs.section":         "FILE TIMESTAMPS  (Properties → Details → File)",
        "field.fs_created":   "Date created",
        "field.fs_modified":  "Date modified",
        "field.fs_accessed":  "Date accessed",
        "note.fs":            "⚠  Applied via Windows API (kernel32.SetFileTime) — Windows only",
        # File dialogs
        "dlg.open_title":    "Open file",
        "dlg.all_supported": "All supported files",
        "dlg.office_files":  "Office files",
        "dlg.pe_files":      "Windows programs",
        "dlg.html_files":    "HTML pages",
        "dlg.lnk_files":     "Windows shortcuts",
        "dlg.all_files":     "All files",
        "dlg.office_file":   "Office file (*{ext})",
        "dlg.generic_file":  "File (*{ext})",
        "dlg.html_file":     "HTML file (*{ext})",
        "dlg.lnk_file":      "Windows shortcut (*.lnk)",
        # Messages
        "err.open_failed":  "Could not open file: {exc}",
        "err.unsupported":  "Format {ext} is not supported.\nSupported: docx · xlsx · pptx · html · exe · dll and more.",
        "err.read_failed":  "Could not read file: {exc}",
        "err.save_failed":  "Save error: {exc}",
        "info.no_changes":  "No fields changed — saving the file unchanged",
        "ok.saved":         "Saved → {name}",
        "warn.fs_times":    "Timestamps not applied: {exc}",
        # Footer
        "footer.text": "Universal Meta Editor — open source, works fully offline",
        # Dialog (error/warning/info)
        "dlg.error":      "Error",
        "dlg.warning":    "Warning",
        "dlg.info":       "Info",
        "dlg.close_hint": "Enter / Esc — close",
        "btn.copy":       "📋  Copy",
        "btn.close":      "Close",
        # Calendar picker
        "cal.title":    "Pick date and time",
        "cal.time_utc": "Time (UTC) ",
        "btn.cancel":   "Cancel",
        "btn.pick":     "Select  ✓",
        # Format labels
        "fmt.docx":    "Word document",
        "fmt.docm":    "Word document (macros)",
        "fmt.xlsx":    "Excel workbook",
        "fmt.xlsm":    "Excel workbook (macros)",
        "fmt.pptx":    "PowerPoint presentation",
        "fmt.pptm":    "PowerPoint presentation (macros)",
        "fmt.vsdx":    "Visio diagram",
        "fmt.exe":     "Windows application",
        "fmt.dll":     "Windows library",
        "fmt.sys":     "Windows driver",
        "fmt.scr":     "Windows screensaver",
        "fmt.html":    "HTML page",
        "fmt.htm":     "HTML page",
        "fmt.lnk":     "Windows shortcut",
        "fmt.unknown": "Unknown format",
    },
}

_MONTHS: dict[str, list[str]] = {
    "ru": ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
           "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"],
    "en": ["January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December"],
}

_WEEKDAYS: dict[str, list[str]] = {
    "ru": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
    "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
}
