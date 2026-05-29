"""
Dark-themed date + time picker — v2
Fixes:
  - No-flicker grid: 42 buttons created once, only .configure() on nav
  - Editable year entry + ‹/› year buttons
  - Mousewheel scrolls months anywhere over the popup
"""

import calendar as _cal
from datetime import datetime, timezone

import customtkinter as ctk

from core.i18n import months as _i18n_months
from core.i18n import t
from core.i18n import weekdays as _i18n_weekdays

# ── Palette ───────────────────────────────────────────────────────────────────
_BG       = "#09090b"
_CARD     = "#18181b"
_BORDER   = "#27272a"
_MUTED    = "#52525b"
_MUTED2   = "#71717a"
_TEXT     = "#fafafa"
_ACCENT   = "#10b981"
_ACCENT2  = "#059669"
_DAY_BG   = "#27272a"
_DAY_HVR  = "#3f3f46"
_TODAY_BG = "#052e16"
_SEL_BG   = "#10b981"
_SEL_TEXT = "#000000"
_DISABLED = "#09090b"   # invisible "empty" cells

_ROWS, _COLS = 6, 7   # fixed 6-week grid


class CalendarPicker(ctk.CTkToplevel):
    """
    Modal date+time picker. Returns ISO-8601 UTC string via on_select callback.

    Navigation:
      ‹ ›      — previous / next month
      ‹‹ ││ ›› — previous / next year  (buttons next to year entry)
      [year]   — editable entry, press Enter or click away to jump
      scroll   — mousewheel anywhere on the popup scrolls months
    """

    def __init__(self, parent: ctk.CTk, initial_iso: str = "", on_select=None):
        super().__init__(parent)
        self.title(t("cal.title"))
        self.resizable(False, False)
        self.configure(fg_color=_CARD)
        self.grab_set()
        self.lift()
        self.focus_force()

        self._on_select = on_select
        self._now = datetime.now(timezone.utc).replace(second=0, microsecond=0)

        dt = self._parse(initial_iso) or self._now
        self._sel_year   = dt.year
        self._sel_month  = dt.month
        self._sel_day    = dt.day
        self._view_year  = dt.year
        self._view_month = dt.month
        self._hour       = dt.hour
        self._minute     = dt.minute

        # Pre-created button pool — never destroyed, only .configure()d
        self._slots: list[ctk.CTkButton] = []

        self._build()
        self._render_grid()      # first paint
        self._bind_scroll()      # mousewheel after all widgets exist
        self._center(parent)

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self):
        wrap = ctk.CTkFrame(self, fg_color="transparent")
        wrap.pack(padx=14, pady=12, fill="both", expand=True)

        self._build_nav(wrap)
        self._build_day_headers(wrap)
        self._build_grid(wrap)
        self._build_time(wrap)
        self._build_actions(wrap)

    # ── Navigation row ────────────────────────────────────────────────────────

    def _build_nav(self, parent):
        nav = ctk.CTkFrame(parent, fg_color="transparent")
        nav.pack(fill="x", pady=(0, 8))

        # Month: ‹ [Name] ›
        _btn(nav, "‹", 30, self._prev_month, font_size=16).pack(side="left")

        self._month_lbl = ctk.CTkLabel(
            nav, text="", width=94,
            font=ctk.CTkFont(size=13, weight="bold"), text_color=_TEXT,
        )
        self._month_lbl.pack(side="left", padx=2)

        _btn(nav, "›", 30, self._next_month, font_size=16).pack(side="left")

        # Divider
        ctk.CTkFrame(nav, fg_color=_BORDER, width=1, height=22).pack(
            side="left", padx=10)

        # Year: ‹ [entry] ›
        _btn(nav, "‹", 26, self._prev_year,
             fg=_DAY_BG, font_size=13).pack(side="left")

        self._year_var = ctk.StringVar()
        year_entry = ctk.CTkEntry(
            nav, textvariable=self._year_var,
            width=54, height=26,
            fg_color=_BG, border_color=_BORDER, border_width=1,
            text_color=_TEXT, justify="center",
            font=ctk.CTkFont(size=12, weight="bold"),
            corner_radius=6,
        )
        year_entry.pack(side="left", padx=3)
        year_entry.bind("<Return>",   self._apply_year)
        year_entry.bind("<FocusOut>", self._apply_year)

        _btn(nav, "›", 26, self._next_year,
             fg=_DAY_BG, font_size=13).pack(side="left")

    # ── Day-of-week header ────────────────────────────────────────────────────

    def _build_day_headers(self, parent):
        hdr = ctk.CTkFrame(parent, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 3))
        for d in _i18n_weekdays():
            ctk.CTkLabel(hdr, text=d, width=36,
                         font=ctk.CTkFont(size=10),
                         text_color=_MUTED2).pack(side="left")

    # ── Pre-created 6×7 button grid ───────────────────────────────────────────

    def _build_grid(self, parent):
        self._grid_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self._grid_frame.pack()

        for r in range(_ROWS):
            for c in range(_COLS):
                btn = ctk.CTkButton(
                    self._grid_frame, text="",
                    width=36, height=30,
                    fg_color=_DISABLED,
                    hover_color=_DISABLED,
                    text_color=_DISABLED,
                    corner_radius=6,
                    font=ctk.CTkFont(size=12),
                    state="disabled",
                    command=lambda: None,
                )
                btn.grid(row=r, column=c, padx=1, pady=1)
                self._slots.append(btn)

    # ── Time row ──────────────────────────────────────────────────────────────

    def _build_time(self, parent):
        ctk.CTkFrame(parent, fg_color=_BORDER, height=1).pack(fill="x", pady=10)

        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x")

        ctk.CTkLabel(row, text=t("cal.time_utc"),
                     font=ctk.CTkFont(size=12),
                     text_color=_MUTED2).pack(side="left")

        self._hour_var   = ctk.StringVar(value=f"{self._hour:02d}")
        self._minute_var = ctk.StringVar(value=f"{self._minute:02d}")

        self._spin(row, self._hour_var,   "hour")
        ctk.CTkLabel(row, text=" : ",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=_TEXT).pack(side="left")
        self._spin(row, self._minute_var, "minute")

    def _spin(self, parent, var: ctk.StringVar, field: str):
        _btn(parent, "−", 24, lambda: self._adjust(field, -1),
             fg=_DAY_BG, h=26).pack(side="left", padx=(0, 2))
        ctk.CTkEntry(parent, textvariable=var,
                     width=40, height=26,
                     fg_color=_BG, border_color=_BORDER, border_width=1,
                     text_color=_TEXT, justify="center",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     corner_radius=5).pack(side="left")
        _btn(parent, "+", 24, lambda: self._adjust(field, +1),
             fg=_DAY_BG, h=26).pack(side="left", padx=(2, 0))

    # ── Action buttons ────────────────────────────────────────────────────────

    def _build_actions(self, parent):
        ctk.CTkFrame(parent, fg_color=_BORDER, height=1).pack(fill="x", pady=10)

        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x")

        ctk.CTkButton(row, text=t("btn.cancel"),
                      fg_color="transparent", border_width=1, border_color=_BORDER,
                      text_color=_MUTED2, hover_color=_DAY_HVR,
                      corner_radius=8, height=36,
                      command=self.destroy
                      ).pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(row, text=t("btn.pick"),
                      fg_color=_ACCENT, hover_color=_ACCENT2,
                      text_color=_SEL_TEXT,
                      corner_radius=8, height=36,
                      font=ctk.CTkFont(size=12, weight="bold"),
                      command=self._confirm
                      ).pack(side="left", fill="x", expand=True)

    # ── Grid render — only .configure(), never destroy ────────────────────────

    def _render_grid(self):
        self._month_lbl.configure(text=_i18n_months()[self._view_month - 1])
        self._year_var.set(str(self._view_year))

        weeks = _cal.monthcalendar(self._view_year, self._view_month)
        days  = [d for week in weeks for d in week]
        days += [0] * (_ROWS * _COLS - len(days))   # pad to 42

        for btn, day in zip(self._slots, days):
            if day == 0:
                btn.configure(
                    text="", state="disabled",
                    fg_color=_DISABLED, hover_color=_DISABLED,
                    text_color=_DISABLED,
                    command=lambda: None,
                )
            else:
                selected = (
                    day == self._sel_day and
                    self._view_year  == self._sel_year and
                    self._view_month == self._sel_month
                )
                today = (
                    day == self._now.day and
                    self._view_year  == self._now.year and
                    self._view_month == self._now.month
                )

                if selected:
                    fg, tc, hv = _SEL_BG,   _SEL_TEXT, _ACCENT2
                elif today:
                    fg, tc, hv = _TODAY_BG, _ACCENT,   _DAY_HVR
                else:
                    fg, tc, hv = _DAY_BG,   _TEXT,     _DAY_HVR

                btn.configure(
                    text=str(day), state="normal",
                    fg_color=fg, text_color=tc, hover_color=hv,
                    command=lambda d=day: self._select_day(d),
                )

    # ── Mousewheel — bound recursively after all widgets exist ────────────────

    def _bind_scroll(self):
        def on_scroll(event):
            if event.delta > 0:
                self._prev_month()
            else:
                self._next_month()

        def bind_tree(w):
            try:
                w.bind("<MouseWheel>", on_scroll)
            except Exception:
                pass
            for child in w.winfo_children():
                bind_tree(child)

        bind_tree(self)

    # ── Navigation actions ────────────────────────────────────────────────────

    def _prev_month(self):
        if self._view_month == 1:
            self._view_month, self._view_year = 12, self._view_year - 1
        else:
            self._view_month -= 1
        self._render_grid()

    def _next_month(self):
        if self._view_month == 12:
            self._view_month, self._view_year = 1, self._view_year + 1
        else:
            self._view_month += 1
        self._render_grid()

    def _prev_year(self):
        self._view_year -= 1
        self._render_grid()

    def _next_year(self):
        self._view_year += 1
        self._render_grid()

    def _apply_year(self, _event=None):
        try:
            y = int(self._year_var.get())
            if 1900 <= y <= 2200:
                self._view_year = y
                self._render_grid()
            else:
                self._year_var.set(str(self._view_year))
        except ValueError:
            self._year_var.set(str(self._view_year))

    def _select_day(self, day: int):
        self._sel_year, self._sel_month, self._sel_day = (
            self._view_year, self._view_month, day)
        self._render_grid()

    def _adjust(self, field: str, delta: int):
        if field == "hour":
            self._hour = (self._hour + delta) % 24
            self._hour_var.set(f"{self._hour:02d}")
        else:
            self._minute = (self._minute + delta) % 60
            self._minute_var.set(f"{self._minute:02d}")

    # ── Confirm ───────────────────────────────────────────────────────────────

    def _confirm(self):
        try:
            h = max(0, min(23, int(self._hour_var.get())))
            m = max(0, min(59, int(self._minute_var.get())))
        except ValueError:
            h, m = self._hour, self._minute

        max_day = _cal.monthrange(self._sel_year, self._sel_month)[1]
        day = min(self._sel_day, max_day)
        dt  = datetime(self._sel_year, self._sel_month, day, h, m, 0,
                       tzinfo=timezone.utc)
        iso = dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        if self._on_select:
            self._on_select(iso)
        self.destroy()

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _parse(iso: str) -> datetime | None:
        if not iso:
            return None
        try:
            return datetime.fromisoformat(
                iso.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            return None

    def _center(self, parent: ctk.CTk):
        self.update_idletasks()
        pw, ph = parent.winfo_width(),  parent.winfo_height()
        px, py = parent.winfo_x(),      parent.winfo_y()
        w,  h  = self.winfo_reqwidth(), self.winfo_reqheight()
        self.geometry(f"+{px + (pw - w) // 2}+{py + (ph - h) // 2}")


# ── Helper: compact button factory ───────────────────────────────────────────

def _btn(
    parent, text: str, w: int, cmd,
    fg: str = "transparent",
    font_size: int = 13,
    h: int = 28,
) -> ctk.CTkButton:
    return ctk.CTkButton(
        parent, text=text, width=w, height=h,
        fg_color=fg, hover_color=_DAY_HVR,
        text_color=_TEXT, corner_radius=6,
        font=ctk.CTkFont(size=font_size),
        command=cmd,
    )
