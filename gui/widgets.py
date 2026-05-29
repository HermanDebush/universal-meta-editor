import tkinter as tk
import customtkinter as ctk

# ── Palette ───────────────────────────────────────────────────────────────────
BG       = "#09090b"
CARD     = "#18181b"
BORDER   = "#27272a"
MUTED    = "#52525b"
MUTED2   = "#71717a"
TEXT     = "#fafafa"
ACCENT   = "#10b981"
ACCENT2  = "#059669"
ENTRY_BG = "#09090b"

ROW_H    = 48    # fixed height per field row


class SectionLabel(ctk.CTkFrame):
    """Uppercase section heading with a trailing rule."""

    def __init__(self, parent, text: str, **kw):
        super().__init__(parent, fg_color="transparent", height=28, **kw)
        self.pack_propagate(False)
        ctk.CTkLabel(
            self, text=text,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=MUTED2,
        ).pack(side="left", padx=(0, 10))
        ctk.CTkFrame(self, fg_color=BORDER, height=1).pack(side="left", fill="x", expand=True)


class Divider(ctk.CTkFrame):
    def __init__(self, parent, **kw):
        super().__init__(parent, fg_color=BORDER, height=1, **kw)


class FieldRow(ctk.CTkFrame):
    """
    Compact single-line field:  [Label / hint]  [Entry ............]  [right_tag?]

    Fixed height ROW_H so the list stays tight and predictable.
    """

    def __init__(
        self,
        parent,
        label: str,
        hint: str,
        var: tk.StringVar | None = None,
        *,
        width: int | None = None,          # fixed entry width; None → expand
        right_hint_var: tk.StringVar | None = None,
        placeholder: str = "",
        **kw,
    ):
        super().__init__(parent, fg_color="transparent", height=ROW_H, **kw)
        self.pack_propagate(False)

        if var is None:
            var = tk.StringVar()
        self.var = var

        # ── Left column: label + hint (fixed 160 px) ──────────────────────
        left = ctk.CTkFrame(self, fg_color="transparent", width=160)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        self._label_widget = ctk.CTkLabel(
            left, text=label,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=TEXT, anchor="w",
        )
        self._label_widget.pack(anchor="w", pady=(6, 0))

        ctk.CTkLabel(
            left, text=hint,
            font=ctk.CTkFont(size=10),
            text_color=MUTED, anchor="w",
        ).pack(anchor="w")

        # ── Entry ──────────────────────────────────────────────────────────
        entry_kw = dict(
            textvariable=var,
            fg_color=ENTRY_BG,
            border_color=BORDER,
            border_width=1,
            text_color=TEXT,
            placeholder_text=placeholder,
            placeholder_text_color=MUTED,
            corner_radius=8,
            height=32,
            font=ctk.CTkFont(size=12),
        )
        if width:
            entry_kw["width"] = width
            ctk.CTkEntry(self, **entry_kw).pack(
                side="left", padx=(10, 0), pady=8)
        else:
            ctk.CTkEntry(self, **entry_kw).pack(
                side="left", fill="x", expand=True, padx=(10, 0), pady=8)

        # ── Optional right label (e.g. "= 14h 3m") ────────────────────────
        if right_hint_var is not None:
            ctk.CTkLabel(
                self, textvariable=right_hint_var,
                font=ctk.CTkFont(size=11),
                text_color=ACCENT, width=72,
            ).pack(side="left", padx=(6, 0))

    def set_label(self, text: str):
        self._label_widget.configure(text=text)


class DateField(ctk.CTkFrame):
    """
    Compact date+time field:  Label | [ISO string entry] [📅 picker]

    The entry shows the raw ISO-8601 string (editable by hand).
    The calendar button opens CalendarPicker for visual selection.
    """

    def __init__(
        self,
        parent,
        label: str,
        hint: str,
        var: tk.StringVar | None = None,
        **kw,
    ):
        super().__init__(parent, fg_color="transparent", height=ROW_H, **kw)
        self.pack_propagate(False)

        if var is None:
            var = tk.StringVar()
        self.var = var

        # ── Left column: label + hint ──────────────────────────────────────
        left = ctk.CTkFrame(self, fg_color="transparent", width=160)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        ctk.CTkLabel(left, text=label,
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=TEXT, anchor="w").pack(anchor="w", pady=(6, 0))
        ctk.CTkLabel(left, text=hint,
                     font=ctk.CTkFont(size=10),
                     text_color=MUTED, anchor="w").pack(anchor="w")

        # ── Right: entry + calendar button ────────────────────────────────
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.pack(side="left", fill="x", expand=True, padx=(10, 0), pady=8)

        ctk.CTkEntry(
            right, textvariable=var,
            fg_color=ENTRY_BG, border_color=BORDER, border_width=1,
            text_color=TEXT,
            placeholder_text="YYYY-MM-DDTHH:MM:SSZ",
            placeholder_text_color=MUTED,
            corner_radius=8, height=32,
            font=ctk.CTkFont(size=12),
        ).pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            right, text="📅", width=34, height=32,
            fg_color=CARD, hover_color="#27272a",
            border_color=BORDER, border_width=1,
            text_color=TEXT, corner_radius=8,
            font=ctk.CTkFont(size=14),
            command=self._open_picker,
        ).pack(side="left", padx=(4, 0))

    def _open_picker(self):
        from .calendar_picker import CalendarPicker
        CalendarPicker(
            self.winfo_toplevel(),
            initial_iso=self.var.get(),
            on_select=self.var.set,
        )
