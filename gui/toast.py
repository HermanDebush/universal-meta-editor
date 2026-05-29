"""
Bottom toast notifications — no modal dialogs.
Usage:
    toast = ToastManager(root_window)
    toast.success("File saved successfully")
    toast.warning("No changes detected")
    toast.error("Could not read file: ...")
"""

import customtkinter as ctk

_STYLES = {
    "success": {"fg": "#10b981", "bg": "#052e16", "border": "#065f46", "icon": "✓"},
    "warning": {"fg": "#f59e0b", "bg": "#1c1000", "border": "#78350f", "icon": "⚠"},
    "error":   {"fg": "#f87171", "bg": "#1c0000", "border": "#7f1d1d", "icon": "✕"},
    "info":    {"fg": "#94a3b8", "bg": "#0f172a", "border": "#1e293b", "icon": "i"},
}

_DURATION_MS = 3500
_SLIDE_STEPS = 12
_SLIDE_MS    = 15


class _Toast(ctk.CTkFrame):
    """One toast message. Self-destructs after _DURATION_MS ms."""

    def __init__(self, manager: "ToastManager", message: str, kind: str):
        s = _STYLES.get(kind, _STYLES["info"])
        super().__init__(
            manager.root,
            fg_color=s["bg"],
            border_color=s["border"],
            border_width=1,
            corner_radius=10,
        )

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(padx=14, pady=10)

        ctk.CTkLabel(
            inner, text=s["icon"],
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=s["fg"], width=20,
        ).pack(side="left")

        ctk.CTkLabel(
            inner, text=message,
            font=ctk.CTkFont(size=12),
            text_color=s["fg"],
            wraplength=380,
        ).pack(side="left", padx=(6, 0))

        self._manager  = manager
        self._start_y  = 0   # set by manager
        self._target_y = 0
        self._alive    = True

    def slide_in(self, target_y: int, start_y: int):
        self._target_y = target_y
        self._start_y  = start_y
        self._step     = 0
        self._animate()

    def _animate(self):
        if not self._alive:
            return
        progress = self._step / _SLIDE_STEPS
        ease     = 1 - (1 - progress) ** 3          # ease-out cubic
        current  = self._start_y + (self._target_y - self._start_y) * ease
        self.place(relx=0.5, anchor="n", y=int(current))
        self._step += 1
        if self._step <= _SLIDE_STEPS:
            self.after(_SLIDE_MS, self._animate)
        else:
            self.after(_DURATION_MS, self._dismiss)

    def _dismiss(self):
        self._alive = False
        self.place_forget()
        self.destroy()
        self._manager._on_dismiss(self)


class ToastManager:
    """
    Attach one ToastManager to the root CTk window.
    All toasts stack above the bottom footer.
    """

    FOOTER_H = 40   # height of the app footer — toasts appear above it

    def __init__(self, root: ctk.CTk):
        self.root    = root
        self._stack: list[_Toast] = []

    # ── Public helpers ─────────────────────────────────────────────────────

    def success(self, msg: str): self._show(msg, "success")
    def info(self,    msg: str): self._show(msg, "info")

    def error(self, msg: str):
        from .error_dialog import ErrorDialog
        ErrorDialog(self.root, msg, "error")

    def warning(self, msg: str):
        from .error_dialog import ErrorDialog
        ErrorDialog(self.root, msg, "warning")

    # ── Internal ───────────────────────────────────────────────────────────

    def _show(self, message: str, kind: str):
        toast = _Toast(self, message, kind)
        toast.update_idletasks()

        # Measure toast height after rendering
        w_width  = self.root.winfo_width()
        toast_w  = min(440, w_width - 48)
        toast.configure(width=toast_w)

        self.root.update_idletasks()
        toast_h = max(44, toast.winfo_reqheight())

        # Calculate vertical position (stack from bottom up)
        base_y   = self.root.winfo_height() - self.FOOTER_H - 8
        slot_y   = base_y - sum(
            max(44, t.winfo_reqheight()) + 8 for t in self._stack
        )
        start_y  = base_y + 60           # start below the window
        target_y = slot_y - toast_h

        self._stack.append(toast)
        toast.slide_in(target_y, start_y)

    def _on_dismiss(self, toast: _Toast):
        if toast in self._stack:
            self._stack.remove(toast)
