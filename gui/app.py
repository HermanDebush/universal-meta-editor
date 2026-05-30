import dataclasses
import sys
import tkinter as tk
import zipfile
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD

from core.file_times import read_file_times, write_file_times
from core.formats import (detect_format, html_extensions, is_html_ext,
                          is_lnk_ext, is_office_ext, is_pe_ext,
                          lnk_extensions, office_extensions,
                          pe_extensions, supported_extensions)
from core.html_meta import HTMLMeta, read_html_meta, write_html_meta
from core.i18n import LANGUAGES, get_language, set_language, t
from core.lnk_meta import (WINDOW_STYLE_KEYS, WINDOW_STYLE_ORDER, LnkMeta,
                            is_lnk_file, read_lnk_meta, write_lnk_meta)
from core.models import AppMeta, CoreMeta, MetaBundle
from core.pe_meta import (PEMeta, is_pe_file, patch_pe_resource,
                           read_pe_manifest, read_pe_meta, write_pe_meta)
from core.reader import read_metadata
from core.writer import write_metadata
from .toast import ToastManager
from .widgets import (ACCENT, ACCENT2, BG, BORDER, CARD, MUTED, MUTED2, TEXT,
                      DateField, Divider, FieldRow, SectionLabel)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

ACCENT2 = "#059669"


class App(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.title("Universal Meta Editor")
        self.geometry("820x700")
        self.minsize(700, 560)
        self.configure(fg_color=BG)
        self._apply_icon()

        self._mode:             str               = ""    # "office"|"pe"|"html"|"lnk"
        self._bundle:           MetaBundle | None = None
        self._pe_meta:          PEMeta | None     = None
        self._html_meta:        HTMLMeta | None   = None
        self._lnk_meta:         LnkMeta | None    = None
        self._source_path:      Path | None       = None
        self._field_vars:       dict[str, tk.StringVar] = {}
        self._manifest_textbox: ctk.CTkTextbox | None   = None
        self._ws_var:           tk.StringVar | None      = None
        self._ws_label_to_int:  dict[str, int]           = {}

        self._build_header()
        self._build_drop_area()
        self._build_editor()
        self._build_footer()

        self.toast = ToastManager(self)

        self._setup_dnd()

    # ── Иконка окна ───────────────────────────────────────────────────────────

    def _apply_icon(self):
        """Set the window icon from assets/icon.ico (title bar + taskbar)."""
        # Windows: явный AppUserModelID — таскбар берёт иконку окна,
        # а не группирует приложение под python.exe.
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    "SNNProject.UniversalMetaEditor")
            except Exception:
                pass
        ico = Path(__file__).parent.parent / "assets" / "icon.ico"
        if not ico.exists():
            return
        try:
            self.wm_iconbitmap(str(ico))
        except Exception:
            pass
        # CTk иногда сбрасывает иконку через ~200 мс после инициализации —
        # применяем повторно.
        def _reapply():
            try:
                self.iconbitmap(str(ico))
            except Exception:
                pass
        self.after(300, _reapply)

    # ── Переключение языка ─────────────────────────────────────────────────────

    def _on_lang_change(self, lang_code: str):
        """Persist the new language and rebuild the whole UI in place."""
        new_lang = lang_code.lower()
        if new_lang == get_language():
            return
        set_language(new_lang)
        self._relocalize()

    def _relocalize(self):
        """Tear down and rebuild all UI, preserving the loaded file & field values."""
        # 1. Capture current state
        editor_visible = self._editor_frame.winfo_ismapped()
        values = {k: v.get() for k, v in self._field_vars.items()}
        manifest_text = ""
        if self._manifest_textbox is not None:
            manifest_text = self._manifest_textbox.get("0.0", "end").rstrip("\n")
        ws_int = None
        if self._ws_var is not None:
            ws_int = self._ws_label_to_int.get(self._ws_var.get(), 1)

        # 2. Destroy the four shell frames
        for frame in (self._header, self._drop_frame,
                      self._editor_frame, self._footer):
            try:
                frame.destroy()
            except Exception:
                pass

        # 3. Rebuild shell
        self._field_vars = {}
        self._manifest_textbox = None
        self._ws_var = None
        self._ws_label_to_int = {}
        self._build_header()
        self._build_drop_area()
        self._build_editor()
        self._build_footer()

        # 4. Restore loaded file (if any)
        if editor_visible and self._mode and self._source_path:
            self._rebuild_cards(self._mode)
            for k, val in values.items():
                if k in self._field_vars:
                    self._field_vars[k].set(val)
            if self._manifest_textbox is not None and manifest_text:
                self._manifest_textbox.delete("0.0", "end")
                self._manifest_textbox.insert("0.0", manifest_text)
            if self._ws_var is not None and ws_int is not None:
                self._ws_var.set(t(WINDOW_STYLE_KEYS.get(ws_int, "ws.normal")))
            if self._mode == "office" and self._bundle is not None:
                cf = self._bundle.fmt.count_field or "Pages"
                self._page_row.set_label(t(f"count.{cf}"))
            self._update_badge(self._source_path)
            self._drop_frame.pack_forget()
            self._editor_frame.pack(fill="both", expand=True)

    def _update_badge(self, path: Path):
        """Set the file-badge icon, name and localized format label."""
        fmt = detect_format(path.name)
        try:
            self._file_icon_lbl.configure(text=fmt.icon)
        except Exception:
            self._file_icon_lbl.configure(text="*")
        ext = fmt.ext if fmt.ext and fmt.ext != "?" else "unknown"
        self._file_name_lbl.configure(text=path.name)
        self._file_fmt_lbl.configure(text=t(f"fmt.{ext}"))

    # ── Шапка ─────────────────────────────────────────────────────────────────

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=CARD, corner_radius=0, height=52)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)
        self._header = hdr

        inner = ctk.CTkFrame(hdr, fg_color="transparent")
        inner.place(relx=0, rely=0.5, anchor="w", x=20)

        ctk.CTkLabel(inner, text="Universal Meta Editor",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=TEXT).pack(side="left", padx=(0, 6))

        ctk.CTkLabel(inner, text="docx · xlsx · pptx · html · exe · dll",
                     font=ctk.CTkFont(size=11),
                     text_color=MUTED2).pack(side="left")

        # Right side: language switcher + version
        right = ctk.CTkFrame(hdr, fg_color="transparent")
        right.place(relx=1, rely=0.5, anchor="e", x=-20)

        self._lang_var = tk.StringVar(value=get_language().upper())
        ctk.CTkSegmentedButton(
            right,
            values=[code.upper() for code in LANGUAGES],
            variable=self._lang_var,
            command=self._on_lang_change,
            font=ctk.CTkFont(size=11, weight="bold"),
            height=26, width=92,
            selected_color=ACCENT, selected_hover_color=ACCENT2,
            unselected_color=CARD, unselected_hover_color="#27272a",
            text_color=TEXT,
        ).pack(side="left", padx=(0, 12))

        ctk.CTkLabel(right, text="v1.2",
                     font=ctk.CTkFont(size=11),
                     text_color=MUTED).pack(side="left")

    # ── Экран приветствия / открытия файла ────────────────────────────────────

    def _build_drop_area(self):
        self._drop_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._drop_frame.pack(fill="both", expand=True, padx=24, pady=24)

        card = ctk.CTkFrame(self._drop_frame, fg_color=CARD,
                            corner_radius=20, border_width=2,
                            border_color=BORDER)
        card.pack(expand=True, fill="both")

        center = ctk.CTkFrame(card, fg_color="transparent")
        center.place(relx=0.5, rely=0.5, anchor="center")

        icon_box = ctk.CTkFrame(center, width=72, height=72,
                                fg_color="#052e16", corner_radius=16,
                                border_width=1, border_color="#14532d")
        icon_box.pack()
        icon_box.pack_propagate(False)
        ctk.CTkLabel(icon_box, text="↑",
                     font=ctk.CTkFont(size=30, weight="bold"),
                     text_color=ACCENT).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(center, text=t("drop.title"),
                     font=ctk.CTkFont(size=17, weight="bold"),
                     text_color=TEXT).pack(pady=(18, 4))

        ctk.CTkLabel(center,
                     text=t("drop.formats"),
                     font=ctk.CTkFont(size=12, family="Courier"),
                     text_color=MUTED2).pack()

        ctk.CTkButton(
            center, text=t("drop.choose"),
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=ACCENT, hover_color=ACCENT2,
            text_color="#000", corner_radius=10,
            height=40, width=180,
            command=self._browse,
        ).pack(pady=(22, 0))

        ctk.CTkLabel(center,
                     text=t("drop.offline"),
                     font=ctk.CTkFont(size=11), text_color=MUTED).pack(pady=(10, 0))

    # ── Редактор (оболочка) ───────────────────────────────────────────────────

    def _build_editor(self):
        self._editor_frame = ctk.CTkFrame(self, fg_color="transparent")

        self._scroll = ctk.CTkScrollableFrame(
            self._editor_frame, fg_color="transparent",
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color=MUTED,
        )
        self._scroll.pack(fill="both", expand=True, padx=24, pady=(14, 0))

        # Плашка с именем файла (статичная)
        self._build_file_badge(self._scroll)

        # Зона для динамических карточек — перестраивается при каждом открытии файла
        self._cards_area = ctk.CTkFrame(self._scroll, fg_color="transparent")
        self._cards_area.pack(fill="x")

        btn_wrap = ctk.CTkFrame(self._editor_frame, fg_color="transparent")
        btn_wrap.pack(fill="x", padx=24, pady=10)

        ctk.CTkButton(
            btn_wrap,
            text=t("editor.save"),
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=ACCENT, hover_color=ACCENT2,
            text_color="#000", corner_radius=12, height=46,
            command=self._save,
        ).pack(fill="x")

    def _build_file_badge(self, parent):
        badge = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=12,
                             border_width=1, border_color=BORDER, height=54)
        badge.pack(fill="x", pady=(0, 14))
        badge.pack_propagate(False)

        self._file_icon_lbl = ctk.CTkLabel(badge, text="📄",
                                           font=ctk.CTkFont(size=22))
        self._file_icon_lbl.place(relx=0, rely=0.5, anchor="w", x=14)

        info = ctk.CTkFrame(badge, fg_color="transparent")
        info.place(relx=0, rely=0.5, anchor="w", x=52)
        self._file_name_lbl = ctk.CTkLabel(info, text="",
                                           font=ctk.CTkFont(size=13, weight="bold"),
                                           text_color=TEXT)
        self._file_name_lbl.pack(anchor="w")
        self._file_fmt_lbl = ctk.CTkLabel(info, text="",
                                          font=ctk.CTkFont(size=11),
                                          text_color=MUTED2)
        self._file_fmt_lbl.pack(anchor="w")

        ctk.CTkButton(badge, text=t("editor.change_file"), width=110, height=28,
                      fg_color="transparent", border_width=1,
                      border_color=BORDER, text_color=MUTED,
                      hover_color="#27272a", corner_radius=8,
                      font=ctk.CTkFont(size=11),
                      command=self._browse).place(relx=1, rely=0.5,
                                                   anchor="e", x=-14)

    # ── Динамические карточки ─────────────────────────────────────────────────

    def _rebuild_cards(self, mode: str):
        """Уничтожает старые карточки и строит новые под нужный режим."""
        for w in self._cards_area.winfo_children():
            w.destroy()
        self._field_vars.clear()
        self._manifest_textbox = None
        self._ws_var           = None

        if mode == "office":
            self._make_core_card(self._cards_area)
            self._make_app_card(self._cards_area)
        elif mode == "pe":
            self._make_pe_card(self._cards_area)
            self._make_pe_manifest_card(self._cards_area)
        elif mode == "html":
            self._make_html_card(self._cards_area)
        elif mode == "lnk":
            self._make_lnk_card(self._cards_area)

        self._make_fs_card(self._cards_area)

    # ── Карточка: основные метаданные (Office) ────────────────────────────────

    def _make_core_card(self, parent):
        card = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=14,
                            border_width=1, border_color=BORDER)
        card.pack(fill="x", pady=(0, 10))

        SectionLabel(card, t("core.section")).pack(fill="x", padx=16, pady=(14, 8))

        for key, hint in [
            ("author",           "dc:creator"),
            ("last_modified_by", "cp:lastModifiedBy"),
            ("title",            "dc:title"),
            ("subject",          "dc:subject"),
            ("keywords",         "cp:keywords"),
            ("category",         "cp:category"),
            ("description",      "dc:description"),
        ]:
            var = tk.StringVar()
            self._field_vars[key] = var
            FieldRow(card, t(f"field.{key}"), hint, var).pack(fill="x", padx=16)

        Divider(card).pack(fill="x", padx=16, pady=8)

        for key, hint in [
            ("created",  "dcterms:created"),
            ("modified", "dcterms:modified"),
        ]:
            var = tk.StringVar()
            self._field_vars[key] = var
            DateField(card, t(f"field.{key}"), hint, var).pack(fill="x", padx=16)

        v_rev = tk.StringVar()
        self._field_vars["revision"] = v_rev
        FieldRow(card, t("field.revision"), "cp:revision", v_rev,
                 width=90, placeholder=t("ph.revision")).pack(fill="x", padx=16)

        ctk.CTkFrame(card, height=10, fg_color="transparent").pack()

    # ── Карточка: метаданные приложения (Office) ──────────────────────────────

    def _make_app_card(self, parent):
        card = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=14,
                            border_width=1, border_color=BORDER)
        card.pack(fill="x", pady=(0, 10))

        SectionLabel(card, t("app.section")).pack(fill="x", padx=16, pady=(14, 8))

        self._time_hint = tk.StringVar()
        v_tt = tk.StringVar()
        self._field_vars["total_time"] = v_tt
        v_tt.trace_add("write", self._update_time_hint)
        FieldRow(card, t("field.total_time"), t("hint.minutes"), v_tt,
                 width=90, placeholder=t("ph.total_time"),
                 right_hint_var=self._time_hint).pack(fill="x", padx=16)

        for key in ("application", "company", "app_version"):
            var = tk.StringVar()
            self._field_vars[key] = var
            FieldRow(card, t(f"field.{key}"), t(f"hint.{key}"), var).pack(
                fill="x", padx=16)

        v_pc = tk.StringVar()
        self._field_vars["page_count"] = v_pc
        self._page_row = FieldRow(card, t("count.Pages"), t("hint.count"),
                                  v_pc, width=90)
        self._page_row.pack(fill="x", padx=16)

        ctk.CTkFrame(card, height=10, fg_color="transparent").pack()

    # ── Карточка: метаданные PE (EXE / DLL) ──────────────────────────────────

    def _make_pe_card(self, parent):
        card = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=14,
                            border_width=1, border_color=BORDER)
        card.pack(fill="x", pady=(0, 10))

        SectionLabel(card, t("pe.section")).pack(
            fill="x", padx=16, pady=(14, 8))

        for key, hint in [
            ("file_description",  "FileDescription"),
            ("file_version",      "FileVersion"),
            ("product_name",      "ProductName"),
            ("product_version",   "ProductVersion"),
            ("company_name",      "CompanyName"),
            ("legal_copyright",   "LegalCopyright"),
            ("original_filename", "OriginalFilename"),
            ("internal_name",     "InternalName"),
            ("comments",          "Comments"),
        ]:
            var = tk.StringVar()
            self._field_vars[key] = var
            FieldRow(card, t(f"field.{key}"), hint, var).pack(fill="x", padx=16)

        note = ctk.CTkFrame(card, fg_color="transparent")
        note.pack(fill="x", padx=16, pady=(4, 0))
        ctk.CTkLabel(
            note,
            text=t("note.pe_copy"),
            font=ctk.CTkFont(size=10), text_color=MUTED,
        ).pack(anchor="w")
        ctk.CTkFrame(card, height=10, fg_color="transparent").pack()

    # ── Карточка: манифест приложения (EXE / DLL) ─────────────────────────────

    def _make_pe_manifest_card(self, parent):
        card = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=14,
                            border_width=1, border_color=BORDER)
        card.pack(fill="x", pady=(0, 10))

        SectionLabel(card, t("pe.manifest_section")).pack(
            fill="x", padx=16, pady=(14, 4))

        # Подсказка о ключевых полях
        hint_frame = ctk.CTkFrame(card, fg_color="transparent")
        hint_frame.pack(fill="x", padx=16, pady=(0, 6))
        ctk.CTkLabel(
            hint_frame,
            text=(
                "requestedExecutionLevel:  asInvoker  |  highestAvailable  |  requireAdministrator\n"
                "dpiAware:  true  |  false      dpiAwareness:  PerMonitorV2  |  PerMonitor  |  System"
            ),
            font=ctk.CTkFont(size=10, family="Courier"),
            text_color=MUTED2, justify="left",
        ).pack(anchor="w")

        self._manifest_textbox = ctk.CTkTextbox(
            card,
            height=190,
            font=ctk.CTkFont(size=11, family="Courier"),
            fg_color="#0f172a",
            text_color="#94a3b8",
            border_width=1,
            border_color=BORDER,
            corner_radius=8,
            wrap="none",
        )
        self._manifest_textbox.pack(fill="x", padx=16, pady=(0, 6))
        self._fix_textbox_scroll(self._manifest_textbox)

        note = ctk.CTkFrame(card, fg_color="transparent")
        note.pack(fill="x", padx=16, pady=(0, 0))
        ctk.CTkLabel(
            note,
            text=t("note.manifest"),
            font=ctk.CTkFont(size=10), text_color=MUTED,
        ).pack(anchor="w")
        ctk.CTkFrame(card, height=10, fg_color="transparent").pack()

    # ── Карточка: метаданные HTML ─────────────────────────────────────────────

    def _make_html_card(self, parent):
        card = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=14,
                            border_width=1, border_color=BORDER)
        card.pack(fill="x", pady=(0, 10))

        SectionLabel(card, t("html.section")).pack(fill="x", padx=16, pady=(14, 8))

        for key, lbl_key, hint in [
            ("title",       "field.html_title",  "<title>"),
            ("description", "field.description", 'name="description"'),
            ("keywords",    "field.keywords",    'name="keywords"'),
            ("author",      "field.author",      'name="author"'),
            ("viewport",    "field.viewport",    'name="viewport"'),
        ]:
            var = tk.StringVar()
            self._field_vars[key] = var
            FieldRow(card, t(lbl_key), hint, var).pack(fill="x", padx=16)

        Divider(card).pack(fill="x", padx=16, pady=(10, 4))

        ctk.CTkLabel(card, text="  OPEN GRAPH",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=MUTED2).pack(anchor="w", padx=16, pady=(0, 6))

        for key, lbl_key, hint in [
            ("og_title",       "og.title",       "og:title"),
            ("og_description", "og.description",  "og:description"),
            ("og_type",        "og.type",         t("hint.og_type")),
        ]:
            var = tk.StringVar()
            self._field_vars[key] = var
            FieldRow(card, t(lbl_key), hint, var).pack(fill="x", padx=16)

        # Кодировка — только для информации (не редактируется)
        v_cs = tk.StringVar()
        self._field_vars["charset"] = v_cs
        cs_row = FieldRow(card, t("field.charset"), t("hint.charset"), v_cs)
        cs_row.pack(fill="x", padx=16)
        # Делаем поле нередактируемым
        try:
            for child in cs_row.winfo_children():
                if hasattr(child, "configure") and "state" in child.keys():
                    child.configure(state="disabled")
        except Exception:
            pass

        ctk.CTkFrame(card, height=10, fg_color="transparent").pack()

    # ── Карточка: ярлык Windows (.lnk) ───────────────────────────────────────

    def _make_lnk_card(self, parent):
        card = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=14,
                            border_width=1, border_color=BORDER)
        card.pack(fill="x", pady=(0, 10))

        SectionLabel(card, t("lnk.section")).pack(
            fill="x", padx=16, pady=(14, 8))

        for key, lbl_key, hint_key in [
            ("target_path",   "field.target_path",   "hint.target_path"),
            ("arguments",     "field.arguments",     "hint.arguments"),
            ("working_dir",   "field.working_dir",   "hint.working_dir"),
            ("description",   "lnk.comment",         "hint.lnk_comment"),
            ("icon_location", "field.icon_location", "hint.icon_location"),
        ]:
            var = tk.StringVar()
            self._field_vars[key] = var
            FieldRow(card, t(lbl_key), t(hint_key), var).pack(fill="x", padx=16)

        # Окно (WindowStyle) — сегментированная кнопка
        ws_row = ctk.CTkFrame(card, fg_color="transparent")
        ws_row.pack(fill="x", padx=16, pady=(6, 0))
        ctk.CTkLabel(ws_row, text=t("lnk.window"),
                     font=ctk.CTkFont(size=12), text_color=TEXT,
                     width=140, anchor="w").pack(side="left")

        ws_labels = [t(WINDOW_STYLE_KEYS[i]) for i in WINDOW_STYLE_ORDER]
        self._ws_label_to_int = {
            t(WINDOW_STYLE_KEYS[i]): i for i in WINDOW_STYLE_ORDER
        }
        self._ws_var = tk.StringVar(value=ws_labels[0])
        ctk.CTkSegmentedButton(
            ws_row,
            values=ws_labels,
            variable=self._ws_var,
            font=ctk.CTkFont(size=11),
            selected_color=ACCENT, selected_hover_color=ACCENT2,
            unselected_color=CARD, unselected_hover_color="#27272a",
            text_color=TEXT,
        ).pack(side="left")

        note = ctk.CTkFrame(card, fg_color="transparent")
        note.pack(fill="x", padx=16, pady=(10, 0))
        ctk.CTkLabel(
            note,
            text=t("note.lnk_copy"),
            font=ctk.CTkFont(size=10), text_color=MUTED,
        ).pack(anchor="w")
        ctk.CTkFrame(card, height=10, fg_color="transparent").pack()

    # ── Фикс скролла внутри CTkScrollableFrame ────────────────────────────────

    @staticmethod
    def _fix_textbox_scroll(tb: ctk.CTkTextbox) -> None:
        """
        CTkScrollableFrame binds <MouseWheel> on all children via bind_all.
        This overrides it so the textbox scrolls its own content only when
        the mouse is actually hovering over it; otherwise the frame scrolls.
        """
        inner = tb._textbox   # underlying tk.Text

        def _wheel_self(e):
            inner.yview_scroll(int(-1 * (e.delta / 120)), "units")
            return "break"   # stop bind_all → frame doesn't also scroll

        def _on_enter(_e=None):
            inner.bind("<MouseWheel>", _wheel_self)

        def _on_leave(_e=None):
            inner.unbind("<MouseWheel>")

        inner.bind("<Enter>", _on_enter)
        inner.bind("<Leave>", _on_leave)
        tb.bind("<Enter>",    _on_enter)
        tb.bind("<Leave>",    _on_leave)
        inner.unbind("<MouseWheel>")   # not hovered by default

    # ── Карточка: временные метки файловой системы (всегда) ──────────────────

    def _make_fs_card(self, parent):
        card = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=14,
                            border_width=1, border_color=BORDER)
        card.pack(fill="x", pady=(0, 10))

        SectionLabel(card, t("fs.section")).pack(
            fill="x", padx=16, pady=(14, 8))

        for key, hint in [
            ("fs_created",  "st_ctime — Windows Explorer"),
            ("fs_modified", "st_mtime — Windows Explorer"),
            ("fs_accessed", "st_atime — Windows Explorer"),
        ]:
            var = tk.StringVar()
            self._field_vars[key] = var
            DateField(card, t(f"field.{key}"), hint, var).pack(fill="x", padx=16)

        note = ctk.CTkFrame(card, fg_color="transparent")
        note.pack(fill="x", padx=16, pady=(4, 0))
        ctk.CTkLabel(
            note,
            text=t("note.fs"),
            font=ctk.CTkFont(size=10), text_color=MUTED,
        ).pack(anchor="w")
        ctk.CTkFrame(card, height=10, fg_color="transparent").pack()

    # ── Drag-and-drop (tkinterdnd2 / нативное расширение tkdnd) ────────────────

    def _setup_dnd(self):
        """Регистрирует drag-and-drop файлов на всё окно через tkinterdnd2.

        Использует нативное Tcl-расширение tkdnd, интегрированное в цикл
        событий Tk — без ctypes-перехвата оконной процедуры (который
        нестабилен на Python 3.14).
        """
        try:
            self.TkdndVersion = TkinterDnD._require(self)
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self._on_drop)
        except Exception:
            pass

    def _on_drop(self, event):
        """Обработка брошенных файлов: берём первый существующий файл."""
        try:
            files = self.tk.splitlist(event.data)
        except Exception:
            files = [event.data]
        for f in files:
            p = Path(str(f).strip("{}"))
            if p.is_file():
                self._load_file(p)
                break

    # ── Выбор файла ───────────────────────────────────────────────────────────

    def _browse(self):
        path = filedialog.askopenfilename(
            title=t("dlg.open_title"),
            filetypes=[
                (t("dlg.all_supported"), " ".join(supported_extensions())),
                (t("dlg.office_files"),  " ".join(office_extensions())),
                (t("dlg.pe_files"),      " ".join(pe_extensions())),
                (t("dlg.html_files"),    " ".join(html_extensions())),
                (t("dlg.lnk_files"),     " ".join(lnk_extensions())),
                (t("dlg.all_files"),     "*.*"),
            ],
        )
        if path:
            self._load_file(Path(path))

    # ── Загрузка файла ────────────────────────────────────────────────────────

    def _load_file(self, path: Path):
        """Публичный метод — всегда перехватывает любые исключения."""
        try:
            self._load_file_impl(path)
        except Exception as exc:
            self.toast.error(t("err.open_failed", exc=exc))

    def _load_file_impl(self, path: Path):
        """Внутренняя реализация: определяет тип, читает данные, затем обновляет UI."""
        fmt = detect_format(path.name)

        # ── 1. Определяем тип и читаем данные (до изменений в UI) ────────────
        if is_pe_file(path):
            mode      = "pe"
            pe_meta   = read_pe_meta(path)
            manifest  = read_pe_manifest(path)
            bundle    = None
            html_meta = None
            lnk_meta  = None

        elif is_html_ext(path.name):
            mode      = "html"
            html_meta = read_html_meta(path)
            bundle    = None
            pe_meta   = None
            manifest  = ""
            lnk_meta  = None

        elif is_lnk_file(path):
            mode      = "lnk"
            lnk_meta  = read_lnk_meta(path)
            bundle    = None
            pe_meta   = None
            html_meta = None
            manifest  = ""

        else:
            # Офис (ZIP + XML) — для любых расширений, в т.ч. неизвестных
            try:
                bundle    = read_metadata(path)
                mode      = "office"
                pe_meta   = None
                html_meta = None
                lnk_meta  = None
                manifest  = ""
            except zipfile.BadZipFile:
                ext = path.suffix.upper() if path.suffix else path.name
                self.toast.error(t("err.unsupported", ext=ext))
                return
            except Exception as exc:
                self.toast.error(t("err.read_failed", exc=exc))
                return

        # ── 2. Данные получены — обновляем состояние и UI ─────────────────────
        self._mode        = mode
        self._source_path = path
        self._bundle      = bundle
        self._pe_meta     = pe_meta
        self._html_meta   = html_meta
        self._lnk_meta    = lnk_meta

        self._rebuild_cards(mode)

        # ── 3. Заполняем поля ─────────────────────────────────────────────────
        if mode == "office":
            core_map = dataclasses.asdict(bundle.core)
            app_map  = {
                "total_time":  bundle.app.total_time,
                "application": bundle.app.application,
                "company":     bundle.app.company,
                "app_version": bundle.app.app_version,
                "page_count":  bundle.app.page_count,
            }
            for key, var in self._field_vars.items():
                val = core_map.get(key) or app_map.get(key) or ""
                var.set(val)

            cf = bundle.fmt.count_field or "Pages"
            self._page_row.set_label(t(f"count.{cf}"))
            self._page_row.var.set(bundle.app.page_count)

        elif mode == "pe":
            for key in ("file_description", "file_version", "product_name",
                        "product_version", "company_name", "legal_copyright",
                        "original_filename", "internal_name", "comments"):
                if key in self._field_vars:
                    self._field_vars[key].set(getattr(pe_meta, key, ""))
            # Заполняем textbox манифеста
            if self._manifest_textbox and manifest:
                self._manifest_textbox.delete("0.0", "end")
                self._manifest_textbox.insert("0.0", manifest)

        elif mode == "html":
            for key in ("title", "description", "keywords", "author",
                        "viewport", "og_title", "og_description", "og_type", "charset"):
                if key in self._field_vars:
                    self._field_vars[key].set(getattr(html_meta, key, ""))

        elif mode == "lnk":
            for key in ("target_path", "arguments", "working_dir",
                        "description", "icon_location"):
                if key in self._field_vars:
                    self._field_vars[key].set(getattr(lnk_meta, key, ""))
            if self._ws_var is not None:
                key = WINDOW_STYLE_KEYS.get(lnk_meta.window_style, "ws.normal")
                self._ws_var.set(t(key))

        # Временные метки ФС — для любого типа файла
        try:
            for key, val in read_file_times(path).items():
                if key in self._field_vars:
                    self._field_vars[key].set(val)
        except Exception:
            pass

        # ── 4. Обновляем плашку файла ─────────────────────────────────────────
        self._update_badge(path)

        # ── 5. Показываем редактор ────────────────────────────────────────────
        self._drop_frame.pack_forget()
        self._editor_frame.pack(fill="both", expand=True)

    # ── Подсказка времени редактирования ─────────────────────────────────────

    def _update_time_hint(self, *_):
        var = self._field_vars.get("total_time")
        if var is None:
            return
        try:
            n = int(var.get())
            h, m = divmod(n, 60)
            self._time_hint.set(t("time.h_m", h=h, m=m) if h else t("time.m", m=m))
        except (ValueError, AttributeError):
            try:
                self._time_hint.set("")
            except Exception:
                pass

    # ── Сохранение ────────────────────────────────────────────────────────────

    def _save(self):
        if self._mode == "office":
            self._save_office()
        elif self._mode == "pe":
            self._save_pe()
        elif self._mode == "html":
            self._save_html()
        elif self._mode == "lnk":
            self._save_lnk()

    def _get_var(self, key: str) -> str:
        v = self._field_vars.get(key)
        return v.get() if v else ""

    def _save_office(self):
        if not self._bundle or not self._source_path:
            return

        new_core = CoreMeta(
            title            = self._get_var("title"),
            subject          = self._get_var("subject"),
            author           = self._get_var("author"),
            last_modified_by = self._get_var("last_modified_by"),
            keywords         = self._get_var("keywords"),
            description      = self._get_var("description"),
            category         = self._get_var("category"),
            revision         = self._get_var("revision"),
            created          = self._get_var("created"),
            modified         = self._get_var("modified"),
        )
        new_app = AppMeta(
            application = self._get_var("application"),
            company     = self._get_var("company"),
            total_time  = self._get_var("total_time"),
            app_version = self._get_var("app_version"),
            page_count  = self._get_var("page_count"),
        )

        if (dataclasses.asdict(new_core) == dataclasses.asdict(self._bundle.core) and
                dataclasses.asdict(new_app)  == dataclasses.asdict(self._bundle.app)):
            self.toast.info(t("info.no_changes"))

        ext = self._source_path.suffix
        out = filedialog.asksaveasfilename(
            defaultextension=ext,
            initialfile=f"{self._source_path.stem}{ext}",
            filetypes=[(t("dlg.office_file", ext=ext), f"*{ext}"),
                       (t("dlg.all_files"), "*.*")],
        )
        if not out:
            return

        try:
            write_metadata(self._source_path, self._bundle, new_core, new_app, out)
            self._apply_fs_times(out)
            self.toast.success(t("ok.saved", name=Path(out).name))
        except Exception as exc:
            self.toast.error(t("err.save_failed", exc=exc))

    def _save_pe(self):
        if not self._pe_meta or not self._source_path:
            return

        new_meta = PEMeta(
            file_description  = self._get_var("file_description"),
            file_version      = self._get_var("file_version"),
            product_name      = self._get_var("product_name"),
            product_version   = self._get_var("product_version"),
            company_name      = self._get_var("company_name"),
            legal_copyright   = self._get_var("legal_copyright"),
            original_filename = self._get_var("original_filename"),
            internal_name     = self._get_var("internal_name"),
            comments          = self._get_var("comments"),
        )

        if dataclasses.asdict(new_meta) == dataclasses.asdict(self._pe_meta):
            self.toast.info(t("info.no_changes"))

        ext = self._source_path.suffix
        out = filedialog.asksaveasfilename(
            defaultextension=ext,
            initialfile=f"{self._source_path.stem}{ext}",
            filetypes=[(t("dlg.generic_file", ext=ext), f"*{ext}"),
                       (t("dlg.all_files"), "*.*")],
        )
        if not out:
            return

        out_path = Path(out)
        try:
            # Шаг 1: копируем + обновляем VERSIONINFO
            write_pe_meta(self._source_path, out_path, new_meta)

            # Шаг 2: обновляем манифест прямо в готовой копии (без доп. копирования)
            new_manifest = ""
            if self._manifest_textbox is not None:
                new_manifest = self._manifest_textbox.get("0.0", "end").strip()
            if new_manifest:
                patch_pe_resource(out_path, 24, 1, new_manifest.encode("utf-8"))

            self._apply_fs_times(out)
            self.toast.success(t("ok.saved", name=out_path.name))
        except Exception as exc:
            self.toast.error(t("err.save_failed", exc=exc))

    def _save_html(self):
        if not self._source_path:
            return

        new_meta = HTMLMeta(
            title          = self._get_var("title"),
            description    = self._get_var("description"),
            keywords       = self._get_var("keywords"),
            author         = self._get_var("author"),
            viewport       = self._get_var("viewport"),
            og_title       = self._get_var("og_title"),
            og_description = self._get_var("og_description"),
            og_type        = self._get_var("og_type"),
        )

        ext = self._source_path.suffix
        out = filedialog.asksaveasfilename(
            defaultextension=ext,
            initialfile=f"{self._source_path.stem}{ext}",
            filetypes=[(t("dlg.html_file", ext=ext), f"*{ext}"),
                       (t("dlg.all_files"), "*.*")],
        )
        if not out:
            return

        try:
            write_html_meta(self._source_path, out, new_meta)
            self._apply_fs_times(out)
            self.toast.success(t("ok.saved", name=Path(out).name))
        except Exception as exc:
            self.toast.error(t("err.save_failed", exc=exc))

    def _save_lnk(self):
        if not self._source_path:
            return

        # Reverse-map window style label → int
        ws_label = self._ws_var.get() if self._ws_var else ""
        ws_int = self._ws_label_to_int.get(ws_label, 1)

        new_meta = LnkMeta(
            target_path   = self._get_var("target_path"),
            arguments     = self._get_var("arguments"),
            working_dir   = self._get_var("working_dir"),
            description   = self._get_var("description"),
            icon_location = self._get_var("icon_location"),
            window_style  = ws_int,
        )

        out = filedialog.asksaveasfilename(
            defaultextension=".lnk",
            initialfile=f"{self._source_path.stem}.lnk",
            filetypes=[(t("dlg.lnk_file"), "*.lnk"), (t("dlg.all_files"), "*.*")],
        )
        if not out:
            return

        try:
            write_lnk_meta(self._source_path, out, new_meta)
            self._apply_fs_times(out)
            self.toast.success(t("ok.saved", name=Path(out).name))
        except Exception as exc:
            self.toast.error(t("err.save_failed", exc=exc))

    def _apply_fs_times(self, out: str):
        """Применяет временные метки ФС к сохранённому файлу (если заданы)."""
        fc = self._get_var("fs_created")
        fm = self._get_var("fs_modified")
        fa = self._get_var("fs_accessed")
        if any([fc, fm, fa]):
            try:
                write_file_times(Path(out), fc, fm, fa)
            except Exception as exc:
                self.toast.warning(t("warn.fs_times", exc=exc))

    # ── Подвал ────────────────────────────────────────────────────────────────

    def _build_footer(self):
        footer = ctk.CTkFrame(self, fg_color=CARD, corner_radius=0, height=36)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        self._footer = footer
        ctk.CTkLabel(
            footer,
            text=t("footer.text"),
            font=ctk.CTkFont(size=10), text_color=MUTED,
        ).place(relx=0.5, rely=0.5, anchor="center")
