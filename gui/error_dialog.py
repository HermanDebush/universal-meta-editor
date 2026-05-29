"""
Beautiful modal error/warning/info dialog.
No OS title bar — custom dark card with fade-in animation and drag support.
"""
from __future__ import annotations

import tkinter as tk
import customtkinter as ctk

from core.i18n import t
from .widgets import BORDER, CARD, MUTED, TEXT

_KINDS: dict[str, dict] = {
    "error":   {"icon": "✕", "color": "#f87171", "icon_bg": "#450a0a", "label_key": "dlg.error"},
    "warning": {"icon": "⚠", "color": "#fbbf24", "icon_bg": "#431407", "label_key": "dlg.warning"},
    "info":    {"icon": "i", "color": "#60a5fa", "icon_bg": "#0c1a2e", "label_key": "dlg.info"},
}

_FADE_STEPS = 12
_FADE_MS    = 16   # ~192 ms total


class ErrorDialog(ctk.CTkToplevel):
    def __init__(
        self,
        parent: ctk.CTk,
        message: str,
        kind:    str = "error",
        title:   str = "",
    ):
        super().__init__(parent)
        k = _KINDS.get(kind, _KINDS["error"])

        self._parent   = parent
        self._message  = message
        self._drag_ox  = 0
        self._drag_oy  = 0

        self.withdraw()
        self.overrideredirect(True)          # no OS chrome
        self.configure(fg_color="#09090b")   # thin outer border colour
        self.resizable(False, False)
        if hasattr(self, "wm_attributes"):
            try:
                self.wm_attributes("-topmost", True)
            except Exception:
                pass

        self._build(message, k, title or t(k["label_key"]))

        # Centre on parent
        self.update_idletasks()
        pw, ph = parent.winfo_width(),  parent.winfo_height()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        dw, dh = self.winfo_reqwidth(), self.winfo_reqheight()
        x = px + (pw - dw) // 2
        y = py + (ph - dh) // 3
        self.geometry(f"+{x}+{y}")

        # Fade in
        self.wm_attributes("-alpha", 0.0)
        self.deiconify()
        self.lift()
        self.focus_force()
        self.grab_set()
        self._fade_in(0)

        self.bind("<Escape>", lambda _: self._close())
        self.bind("<Return>", lambda _: self._close())

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _build(self, message: str, k: dict, label: str):
        # Outer card with 2 px gap from window edge → acts as border
        card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=16,
                            border_width=1, border_color=BORDER)
        card.pack(padx=2, pady=2)

        # ── Header (draggable) ────────────────────────────────────────────────
        hdr = ctk.CTkFrame(card, fg_color="transparent", height=60)
        hdr.pack(fill="x", padx=20, pady=(18, 0))
        hdr.pack_propagate(False)
        for w in (hdr,):
            w.bind("<ButtonPress-1>", self._drag_start)
            w.bind("<B1-Motion>",     self._drag_move)

        # Coloured circle icon
        icon_wrap = ctk.CTkFrame(hdr, width=44, height=44,
                                 fg_color=k["icon_bg"], corner_radius=22)
        icon_wrap.pack(side="left")
        icon_wrap.pack_propagate(False)
        ctk.CTkLabel(icon_wrap, text=k["icon"],
                     font=ctk.CTkFont(size=17, weight="bold"),
                     text_color=k["color"]).place(relx=0.5, rely=0.5, anchor="center")

        # Title + hint
        txt_col = ctk.CTkFrame(hdr, fg_color="transparent")
        txt_col.pack(side="left", padx=(14, 48), fill="y")
        ctk.CTkLabel(txt_col, text=label,
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=TEXT).pack(anchor="w", pady=(10, 0))
        ctk.CTkLabel(txt_col, text=t("dlg.close_hint"),
                     font=ctk.CTkFont(size=10),
                     text_color=MUTED).pack(anchor="w")

        # ✕ close button (top-right corner of card)
        ctk.CTkButton(
            card, text="✕", width=26, height=26,
            font=ctk.CTkFont(size=11),
            fg_color="transparent", hover_color="#27272a",
            text_color=MUTED, corner_radius=6,
            command=self._close,
        ).place(relx=1.0, rely=0.0, anchor="ne", x=-12, y=12)

        # ── Message box ───────────────────────────────────────────────────────
        msg_outer = ctk.CTkFrame(card, fg_color="#0f172a", corner_radius=10,
                                 border_width=1, border_color=BORDER)
        msg_outer.pack(fill="x", padx=20, pady=(14, 0))

        line_count = min(8, message.count("\n") + 2)

        txt = tk.Text(
            msg_outer,
            wrap="word",
            bg="#0f172a", fg="#94a3b8",
            font=("Consolas", 10),
            relief="flat", borderwidth=0,
            padx=14, pady=10,
            height=line_count, width=52,
            cursor="arrow",
            selectbackground="#1e293b",
            selectforeground="#e2e8f0",
        )
        txt.insert("1.0", message)
        txt.configure(state="disabled")
        txt.pack(fill="x", expand=False)

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(14, 20))

        ctk.CTkButton(
            btn_row, text=t("btn.copy"),
            font=ctk.CTkFont(size=12),
            fg_color="transparent", border_width=1,
            border_color=BORDER, text_color=MUTED,
            hover_color="#27272a", corner_radius=8,
            height=36, width=155,
            command=self._copy,
        ).pack(side="left")

        ctk.CTkButton(
            btn_row, text=t("btn.close"),
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=k["icon_bg"], hover_color="#18181b",
            text_color=k["color"],
            border_width=1, border_color=BORDER,
            corner_radius=8, height=36, width=120,
            command=self._close,
        ).pack(side="right")

    # ── Behaviour ──────────────────────────────────────────────────────────────

    def _fade_in(self, step: int):
        self.wm_attributes("-alpha", min(step / _FADE_STEPS, 1.0))
        if step < _FADE_STEPS:
            self.after(_FADE_MS, lambda: self._fade_in(step + 1))

    def _close(self):
        try:
            self.grab_release()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass

    def _copy(self):
        try:
            self.clipboard_clear()
            self.clipboard_append(self._message)
        except Exception:
            pass

    def _drag_start(self, event: tk.Event):
        self._drag_ox = event.x_root - self.winfo_x()
        self._drag_oy = event.y_root - self.winfo_y()

    def _drag_move(self, event: tk.Event):
        self.geometry(f"+{event.x_root - self._drag_ox}+{event.y_root - self._drag_oy}")


# ── Convenience helpers ────────────────────────────────────────────────────────

def show_error(parent: ctk.CTk, message: str, title: str = "") -> None:
    ErrorDialog(parent, message, "error", title)

def show_warning(parent: ctk.CTk, message: str, title: str = "") -> None:
    ErrorDialog(parent, message, "warning", title)

def show_info(parent: ctk.CTk, message: str, title: str = "") -> None:
    ErrorDialog(parent, message, "info", title)
