import tkinter as tk
from queue import Queue
from threading import Thread
from tkinter import ttk
from typing import Callable, Optional, Sequence
import ctypes

# Keep your existing imports
from .audio_capture import list_input_devices
from .config import ConfigManager

# Enable High DPI on Windows
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# --- Modern Palette ---
PALETTE = {
    "bg": "#1e293b",          # Slate 800
    "card": "#0f172a",        # Slate 900
    "header": "#020617",      # Slate 950
    "text": "#f8fafc",        # Slate 50 (Brighter text)
    "muted": "#94a3b8",       # Slate 400
    "border": "#334155",      # Slate 700
    "input_bg": "#1e293b",    # Specific darker bg for inputs
    "accent": "#38bdf8",      # Sky 400
    "accent_hover": "#0ea5e9",# Sky 500
    "danger": "#ef4444",      # Red 500
    "badge_idle": "#334155",
    "badge_listen": "#0ea5e9",
    "badge_transcribe": "#8b5cf6",
}

# --- Windows Rounded Corners Helper ---
def apply_rounded_corners(window_handle, width, height, radius=20):
    """Uses Windows API to clip the window into a rounded rectangle."""
    try:
        # Create a rounded region
        # CreateRoundRectRgn(x1, y1, x2, y2, width_ellipse, height_ellipse)
        rgn = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, width, height, radius, radius)
        # Set the window region
        ctypes.windll.user32.SetWindowRgn(window_handle, rgn, True)
    except Exception:
        pass # Linux/Mac fallbacks usually ignore this safely

class ModernButton(tk.Label):
    """A custom flat button."""
    def __init__(self, parent, text, command, bg=PALETTE["card"], fg=PALETTE["text"], 
                 hover_bg=PALETTE["border"], width=None, font=("Segoe UI", 10)):
        super().__init__(parent, text=text, bg=bg, fg=fg, font=font, cursor="hand2", padx=14, pady=8)
        self.command = command
        self.default_bg = bg
        self.hover_bg = hover_bg
        if width: self.configure(width=width)
        self.bind("<Enter>", lambda e: self.configure(bg=self.hover_bg))
        self.bind("<Leave>", lambda e: self.configure(bg=self.default_bg))
        self.bind("<Button-1>", lambda e: self.command() if self.command else None)

class ResizeGrip(tk.Label):
    """A draggable handle to resize the window."""
    def __init__(self, parent, target_window):
        super().__init__(parent, text="⛲", bg=PALETTE["bg"], fg=PALETTE["muted"], 
                         font=("Segoe UI Symbol", 10), cursor="size_nw_se")
        self.target = target_window
        self.bind("<ButtonPress-1>", self._start_resize)
        self.bind("<B1-Motion>", self._on_resize)
        self.bind("<ButtonRelease-1>", self._end_resize)
        
    def _start_resize(self, event):
        self.start_x = event.x_root
        self.start_y = event.y_root
        self.start_w = self.target.winfo_width()
        self.start_h = self.target.winfo_height()

    def _on_resize(self, event):
        dx = event.x_root - self.start_x
        dy = event.y_root - self.start_y
        new_w = max(300, self.start_w + dx)
        new_h = max(300, self.start_h + dy)
        self.target.geometry(f"{new_w}x{new_h}")
        
    def _end_resize(self, event):
        # Re-apply rounded corners to the new size
        apply_rounded_corners(self.target.winfo_id(), self.target.winfo_width(), self.target.winfo_height())

class TitleBar(tk.Frame):
    """Custom draggable title bar."""
    def __init__(self, parent, title, on_close, on_settings=None):
        super().__init__(parent, bg=PALETTE["header"], height=38)
        self.parent = parent
        self.pack(fill="x", side="top")
        self.pack_propagate(False)

        self.bind("<ButtonPress-1>", self._start_move)
        self.bind("<B1-Motion>", self._on_move)

        tk.Label(self, text=title, bg=PALETTE["header"], fg=PALETTE["muted"], 
                 font=("Segoe UI Semibold", 11)).pack(side="left", padx=15)

        close_btn = tk.Label(self, text="✕", bg=PALETTE["header"], fg=PALETTE["muted"], 
                             font=("Segoe UI", 11), cursor="hand2", width=5)
        close_btn.pack(side="right", fill="y")
        close_btn.bind("<Enter>", lambda e: close_btn.configure(bg=PALETTE["danger"], fg="white"))
        close_btn.bind("<Leave>", lambda e: close_btn.configure(bg=PALETTE["header"], fg=PALETTE["muted"]))
        close_btn.bind("<Button-1>", lambda e: on_close())

        if on_settings:
            settings_btn = tk.Label(self, text="⚙", bg=PALETTE["header"], fg=PALETTE["muted"], 
                                    font=("Segoe UI", 13), cursor="hand2", width=5)
            settings_btn.pack(side="right", fill="y")
            settings_btn.bind("<Enter>", lambda e: settings_btn.configure(bg=PALETTE["border"], fg="white"))
            settings_btn.bind("<Leave>", lambda e: settings_btn.configure(bg=PALETTE["header"], fg=PALETTE["muted"]))
            settings_btn.bind("<Button-1>", lambda e: on_settings())

    def _start_move(self, event):
        self.parent._drag_start = (event.x, event.y)

    def _on_move(self, event):
        x = event.x_root - self.parent._drag_start[0]
        y = event.y_root - self.parent._drag_start[1]
        self.parent.geometry(f"+{x}+{y}")

def _apply_theme(root: tk.Misc):
    style = ttk.Style(root)
    style.theme_use("clam")
    
    # Fix Combobox Dropdown colors
    root.option_add('*TCombobox*Listbox.background', PALETTE['card'])
    root.option_add('*TCombobox*Listbox.foreground', PALETTE['text'])
    root.option_add('*TCombobox*Listbox.selectBackground', PALETTE['accent'])
    root.option_add('*TCombobox*Listbox.selectForeground', PALETTE['header'])

    style.configure("TFrame", background=PALETTE["bg"])
    style.configure("Card.TFrame", background=PALETTE["card"])
    
    # Configure Combobox to look flat and dark
    style.map("TCombobox", fieldbackground=[("readonly", PALETTE["card"])],
                           selectbackground=[("readonly", PALETTE["card"])],
                           selectforeground=[("readonly", PALETTE["text"])])
    style.configure("TCombobox", 
                    background=PALETTE["bg"], 
                    foreground=PALETTE["text"], 
                    arrowcolor=PALETTE["text"],
                    borderwidth=0)


class StatusUI:
    def __init__(self, title: str = "Flow STT", on_settings_saved: Optional[Callable[[], None]] = None):
        self.title = title
        self._thread: Optional[Thread] = None
        self._root: Optional[tk.Tk] = None
        self._status_label: Optional[tk.Label] = None
        self._status_queue: "Queue[str]" = Queue()
        self._on_settings_saved = on_settings_saved
        self._drag_start = (0, 0)
        self._canvas: Optional[tk.Canvas] = None
        self._dots: list[int] = []
        self._dot_step = 0
        self._current_status = "Idle"

    def start(self) -> None:
        if self._thread and self._thread.is_alive(): return
        self._thread = Thread(target=self._run, daemon=True)
        self._thread.start()

    def set_status(self, text: str) -> None:
        if self._status_queue is not None: self._status_queue.put(text)

    def _run(self) -> None:
        self._root = tk.Tk()
        self._root.title(self.title)
        w, h = 380, 250
        self._root.geometry(f"{w}x{h}")
        self._root.configure(bg=PALETTE["bg"])
        self._root.overrideredirect(True)
        self._root.wm_attributes("-topmost", True)
        self._root.config(highlightbackground=PALETTE["border"], highlightthickness=1)
        
        _apply_theme(self._root)

        # Round Corners after window is created
        self._root.update_idletasks()
        apply_rounded_corners(self._root.winfo_id(), w, h, radius=25)

        TitleBar(self._root, "Flow STT", self._root.quit, self._open_settings)

        content = tk.Frame(self._root, bg=PALETTE["bg"])
        content.pack(fill="both", expand=True, padx=20, pady=10)

        self._canvas = tk.Canvas(content, width=220, height=40, bg=PALETTE["bg"], bd=0, highlightthickness=0)
        self._canvas.pack(pady=(10, 5))
        
        start_x = 80
        self._dots = []
        for i in range(3):
            x = start_x + i * 30
            dot = self._canvas.create_oval(x, 12, x + 16, 28, fill=PALETTE["badge_idle"], outline="")
            self._dots.append(dot)

        self._status_label = tk.Label(content, text="Idle", font=("Segoe UI Semibold", 20), bg=PALETTE["bg"], fg=PALETTE["muted"])
        self._status_label.pack(pady=(0, 5))

        tk.Label(content, text="Hold hotkey to dictate.\nRelease to transcribe.", font=("Segoe UI", 10), bg=PALETTE["bg"], fg=PALETTE["muted"], justify="center").pack(side="bottom", pady=(0, 10))

        self._poll_status()
        self._animate_dots()
        self._root.mainloop()

    def _poll_status(self):
        if self._status_label is None or self._root is None: return
        while not self._status_queue.empty():
            status = self._status_queue.get()
            self._update_status(status)
        self._root.after(150, self._poll_status)

    def _update_status(self, status: str) -> None:
        self._current_status = status
        colors = self._badge_colors(status)
        self._status_label.config(text=status, fg=colors["fg"])
        if self._dots and self._canvas:
            for dot in self._dots: self._canvas.itemconfig(dot, fill=colors["bg"])

    def _badge_colors(self, status: str):
        lowered = status.lower()
        if "listen" in lowered: return {"bg": PALETTE["badge_listen"], "fg": PALETTE["text"]}
        if "transcrib" in lowered: return {"bg": PALETTE["badge_transcribe"], "fg": PALETTE["text"]}
        return {"bg": PALETTE["badge_idle"], "fg": PALETTE["muted"]}

    def _animate_dots(self):
        if not self._dots or self._canvas is None or self._root is None: return
        colors = self._badge_colors(self._current_status)
        base_color = colors["bg"]
        for idx, dot in enumerate(self._dots):
            phase = (self._dot_step + idx * 4) % 30
            intensity = 0.4 + 0.6 * (1 - abs(15 - phase) / 15) 
            if self._current_status == "Idle":
                fill = _mix_hex(base_color, PALETTE["bg"], 0.5)
            else:
                fill = _mix_hex(base_color, PALETTE["text"], intensity * 0.5)
            self._canvas.itemconfig(dot, fill=fill)
        self._dot_step = (self._dot_step + 1) % 30
        self._root.after(50, self._animate_dots)

    def _open_settings(self):
        if self._root is None: return
        SettingsWindow(self._root, on_saved=self._on_settings_saved).open()


class SettingsWindow:
    def __init__(self, root: tk.Tk, on_saved: Optional[Callable[[], None]] = None):
        self.root = root
        self.on_saved = on_saved
        self.cfg_manager = ConfigManager()
        self.window: Optional[tk.Toplevel] = None
        self._drag_start = (0, 0)

    def open(self):
        if self.window:
            self.window.lift()
            return
            
        cfg = self.cfg_manager.config
        self.window = tk.Toplevel(self.root)
        self.window.title("Settings")
        w, h = 500, 680
        self.window.geometry(f"{w}x{h}")
        self.window.configure(bg=PALETTE["bg"])
        self.window.overrideredirect(True)
        self.window.config(highlightbackground=PALETTE["border"], highlightthickness=1)
        
        _apply_theme(self.window)
        
        # Round corners initially
        self.window.update_idletasks()
        apply_rounded_corners(self.window.winfo_id(), w, h, radius=25)

        TitleBar(self.window, "Settings", self.window.destroy)

        container = tk.Frame(self.window, bg=PALETTE["bg"])
        container.pack(fill="both", expand=True, padx=30, pady=20)

        # --- INPUT FIELDS ---
        self._hotkey = self._add_entry(container, "Hotkey", cfg.hotkey)
        self._mode = self._add_combo(container, "Mode", ["push_to_talk", "toggle"], cfg.mode)
        self._output_mode = self._add_combo(container, "Output", ["type", "clipboard"], cfg.output_mode)
        self._model_size = self._add_combo(container, "Model", ["tiny", "base", "small", "medium", "large"], cfg.model_size)
        self._language = self._add_entry(container, "Language", cfg.language)
        self._mic_device = self._add_combo(container, "Microphone", self._mic_choices(), cfg.mic_device or "")
        
        # --- CHECKBOXES (Using standard tk.Checkbutton for color control) ---
        chk_frame = tk.Frame(container, bg=PALETTE["bg"])
        chk_frame.pack(fill="x", pady=15)
        
        self._spoken_punct = tk.BooleanVar(value=cfg.spoken_punctuation)
        self._auto_paste = tk.BooleanVar(value=cfg.auto_paste_clipboard)

        self._make_checkbox(chk_frame, "Parse spoken punctuation", self._spoken_punct)
        self._make_checkbox(chk_frame, "Auto-paste from clipboard", self._auto_paste)

        # --- BOTTOM ACTIONS ---
        btn_frame = tk.Frame(self.window, bg=PALETTE["bg"])
        btn_frame.pack(side="bottom", fill="x", padx=30, pady=(0, 25))

        # Resize Grip
        ResizeGrip(btn_frame, self.window).pack(side="right", anchor="se")

        ModernButton(btn_frame, "Save", self._save, 
                     bg=PALETTE["accent"], hover_bg=PALETTE["accent_hover"], fg="#0f172a", width=12).pack(side="right", padx=10)
        
        ModernButton(btn_frame, "Cancel", self.window.destroy, 
                     bg=PALETTE["card"], hover_bg=PALETTE["border"], width=10).pack(side="right", padx=10)

    def _make_checkbox(self, parent, text, var):
        # Using standard tk.Checkbutton because ttk is buggy with background colors on Windows
        cb = tk.Checkbutton(parent, text=text, variable=var, 
                            bg=PALETTE["bg"], fg=PALETTE["text"], 
                            selectcolor=PALETTE["card"], # Color of the box when checked/unchecked
                            activebackground=PALETTE["bg"], activeforeground=PALETTE["text"],
                            font=("Segoe UI", 10), bd=0, highlightthickness=0)
        cb.pack(anchor="w", pady=4)

    def _add_entry(self, parent, label: str, value: str) -> tk.StringVar:
        var = tk.StringVar(value=value)
        self._create_field_label(parent, label)
        
        # Use a Frame to create a "border"
        wrapper = tk.Frame(parent, bg=PALETTE["card"], pady=1, padx=1)
        wrapper.pack(fill="x", pady=(0, 12))
        
        # Use STANDARD tk.Entry to ensure background color works
        entry = tk.Entry(wrapper, textvariable=var, font=("Segoe UI", 11),
                         bg=PALETTE["card"], fg=PALETTE["text"], 
                         insertbackground=PALETTE["text"], # Cursor color
                         bd=0, highlightthickness=5, highlightbackground=PALETTE["card"], highlightcolor=PALETTE["card"])
        entry.pack(fill="x", ipady=3)
        return var

    def _add_combo(self, parent, label: str, values: Sequence[str], current: str) -> tk.StringVar:
        var = tk.StringVar(value=current)
        self._create_field_label(parent, label)
        
        # ttk.Combobox is tricky, but we styled it in _apply_theme
        combo = ttk.Combobox(parent, textvariable=var, values=list(values), state="readonly", font=("Segoe UI", 11))
        combo.pack(fill="x", pady=(0, 12), ipady=4) 
        return var
        
    def _create_field_label(self, parent, text):
        tk.Label(parent, text=text, bg=PALETTE["bg"], fg=PALETTE["muted"], 
                 font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x", pady=(0, 2))

    def _mic_choices(self) -> Sequence[str]:
        devices = list_input_devices()
        return devices or ["Default"]

    def _save(self):
        cfg = {
            "hotkey": self._hotkey.get(),
            "mode": self._mode.get(),
            "output_mode": self._output_mode.get(),
            "model_size": self._model_size.get(),
            "language": self._language.get(),
            "mic_device": self._mic_device.get() or None,
            "spoken_punctuation": self._spoken_punct.get(),
            "auto_paste_clipboard": self._auto_paste.get(),
        }
        self.cfg_manager.update(**cfg)
        if self.on_saved:
            self.on_saved()
        self.window.destroy()


def _mix_hex(base: str, target: str, t: float) -> str:
    def hex_to_rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))
    br, bg, bb = hex_to_rgb(base)
    tr, tg, tb = hex_to_rgb(target)
    r = int(br + (tr - br) * t)
    g = int(bg + (tg - bg) * t)
    b = int(bb + (tb - bb) * t)
    return f"#{r:02x}{g:02x}{b:02x}"