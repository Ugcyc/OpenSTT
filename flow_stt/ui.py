import tkinter as tk
from tkinter import ttk
from threading import Thread
from queue import Queue
from typing import Callable, Optional, Sequence

from .audio_capture import list_input_devices
from .config import ConfigManager


class StatusUI:
    """Lightweight overlay showing current dictation state."""

    def __init__(self, title: str = "Flow STT", on_settings_saved: Optional[Callable[[], None]] = None):
        self.title = title
        self._thread: Optional[Thread] = None
        self._root: Optional[tk.Tk] = None
        self._label: Optional[tk.Label] = None
        self._status_queue: "Queue[str]" = Queue()
        self._on_settings_saved = on_settings_saved

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = Thread(target=self._run, daemon=True)
        self._thread.start()

    def set_status(self, text: str) -> None:
        if self._status_queue is not None:
            self._status_queue.put(text)

    def _run(self) -> None:
        self._root = tk.Tk()
        self._root.title(self.title)
        self._root.geometry("260x120")
        self._root.resizable(False, False)
        self._label = tk.Label(self._root, text="Idle", font=("Segoe UI", 12))
        self._label.pack(padx=12, pady=12)
        ttk.Button(self._root, text="Settings", command=self._open_settings).pack(pady=4)
        ttk.Button(self._root, text="Exit", command=self._root.quit).pack()
        self._poll_status()
        self._root.mainloop()

    def _poll_status(self):
        if self._label is None or self._root is None:
            return
        while not self._status_queue.empty():
            status = self._status_queue.get()
            self._label.config(text=status)
        self._root.after(150, self._poll_status)

    def _open_settings(self):
        if self._root is None:
            return
        SettingsWindow(self._root, on_saved=self._on_settings_saved).open()


class SettingsWindow:
    """Tiny settings editor to update the JSON config file."""

    def __init__(self, root: tk.Tk, on_saved: Optional[Callable[[], None]] = None):
        self.root = root
        self.on_saved = on_saved
        self.cfg_manager = ConfigManager()
        self.window: Optional[tk.Toplevel] = None

    def open(self):
        if self.window:
            self.window.lift()
            return
        cfg = self.cfg_manager.config
        self.window = tk.Toplevel(self.root)
        self.window.title("Flow STT Settings")
        self.window.geometry("360x380")

        fields = ttk.Frame(self.window)
        fields.pack(fill="both", expand=True, padx=10, pady=10)

        self._hotkey = self._add_entry(fields, "Hotkey", cfg.hotkey)
        self._mode = self._add_combo(fields, "Mode", ["push_to_talk", "toggle"], cfg.mode)
        self._output_mode = self._add_combo(fields, "Output", ["type", "clipboard"], cfg.output_mode)
        self._model_size = self._add_combo(fields, "Model", ["tiny", "base", "small", "medium", "large"], cfg.model_size)
        self._language = self._add_entry(fields, "Language", cfg.language)
        self._mic_device = self._add_combo(fields, "Mic Device", self._mic_choices(), cfg.mic_device or "")
        self._spoken_punct = tk.BooleanVar(value=cfg.spoken_punctuation)
        self._auto_paste = tk.BooleanVar(value=cfg.auto_paste_clipboard)

        ttk.Checkbutton(fields, text="Spoken punctuation", variable=self._spoken_punct).pack(anchor="w", pady=3)
        ttk.Checkbutton(fields, text="Auto paste on clipboard mode", variable=self._auto_paste).pack(anchor="w", pady=3)

        btns = ttk.Frame(fields)
        btns.pack(fill="x", pady=8)
        ttk.Button(btns, text="Save", command=self._save).pack(side="left", padx=4)
        ttk.Button(btns, text="Close", command=self.window.destroy).pack(side="right", padx=4)

    def _add_entry(self, parent, label: str, value: str) -> tk.StringVar:
        var = tk.StringVar(value=value)
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text=label, width=14).pack(side="left")
        ttk.Entry(row, textvariable=var).pack(side="right", fill="x", expand=True)
        return var

    def _add_combo(self, parent, label: str, values: Sequence[str], current: str) -> tk.StringVar:
        var = tk.StringVar(value=current)
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text=label, width=14).pack(side="left")
        combo = ttk.Combobox(row, textvariable=var, values=list(values))
        combo.pack(side="right", fill="x", expand=True)
        return var

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
