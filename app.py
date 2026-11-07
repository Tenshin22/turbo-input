#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py — графическое приложение Turbo Input.

Одно нажатие геймпада/клавиатуры превращается в серию нажатий.
Окно с карточками кнопок, частота, режимы, сохранение настроек.
"""

from __future__ import annotations

import ctypes
import json
import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from engine import (
    PAD_LABELS,
    Engine,
    Binding,
    Trigger,
    output_key_names,
    resolve_vk,
)

BASE = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent


def _config_path() -> Path:
    """config.json рядом с .exe, если папку можно писать (портативный режим).

    Иначе (установка в Program Files) — %APPDATA%\\TurboInput\\config.json.
    """
    local = BASE / "config.json"
    try:
        probe = local.parent / ".write_test"
        probe.write_bytes(b"")
        probe.unlink()
        return local
    except OSError:
        cfg_dir = Path(os.environ.get("APPDATA", str(Path.home()))) / "TurboInput"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        return cfg_dir / "config.json"


CONFIG = _config_path()

# --- палитра ---------------------------------------------------------------

BG = "#1b1d21"
CARD = "#262a30"
CARD2 = "#33383f"
FG = "#e9ecf1"
MUTED = "#9ba1ab"
ACCENT = "#4f8cff"
ACCENT_HI = "#6ea1ff"
OK = "#3ddc84"
WARN = "#ffb020"
DANGER = "#ff5d5d"

FONT = "Segoe UI"

# --- языки -------------------------------------------------------------------

LANG = "ru"

_T: dict[str, dict[str, str]] = {
    "ru": {
        "title": "Turbo Input — нажатия без долбёжки",
        "subtitle": "Одно нажатие — серия нажатий. Для игр, где нужно быстро жать.",
        "stopped": "Остановлено",
        "running": "Работает",
        "paused": "Пауза",
        "btn_start": "▶  Запустить",
        "btn_stop": "■  Остановить",
        "enabled": "Включено",
        "delete": "Удалить",
        "btn_label": "Кнопка",
        "press_label": "Жать",
        "mode_label": "Режим",
        "rate_label": "Частота",
        "per_sec": "раз в секунду",
        "in_burst": "В серии",
        "add_btn": "+  Добавить кнопку",
        "pause_label": "Пауза:",
        "topmost": "Поверх окон",
        "presses": "Нажатий: {n}",
        "note": "Только для одиночных игр. В онлайн-играх с античитом не использовать.",
        "saved": "Сохранено",
        "started": "Запущено. Сверни окно и играй. F8 — пауза.",
        "stopped_note": "Остановлено.",
        "check": "Проверь настройки: {e}",
        "min_one": "Должна остаться хотя бы одна кнопка",
        "pad_err": "Вывод на геймпад недоступен: {e}",
        "hint_burst": "Одно нажатие = несколько нажатий подряд",
        "hint_hold": "Держи кнопку — нажатия идут с выбранной скоростью",
        "hint_pad": "в игру уйдут нажатия кнопки геймпада",
        "hint_key": "в игру уйдут нажатия клавиши",
    },
    "en": {
        "title": "Turbo Input — no more mashing",
        "subtitle": "One press — a burst of presses. For games that make you mash.",
        "stopped": "Stopped",
        "running": "Running",
        "paused": "Paused",
        "btn_start": "▶  Start",
        "btn_stop": "■  Stop",
        "enabled": "Enabled",
        "delete": "Delete",
        "btn_label": "Button",
        "press_label": "Press",
        "mode_label": "Mode",
        "rate_label": "Rate",
        "per_sec": "per second",
        "in_burst": "In burst",
        "add_btn": "+  Add button",
        "pause_label": "Pause:",
        "topmost": "Always on top",
        "presses": "Presses: {n}",
        "note": "Single-player only. Never use in online games with anti-cheat.",
        "saved": "Saved",
        "started": "Running. Minimize the window and play. F8 to pause.",
        "stopped_note": "Stopped.",
        "check": "Check the settings: {e}",
        "min_one": "At least one button must remain",
        "pad_err": "Gamepad output unavailable: {e}",
        "hint_burst": "One press = several presses in a row",
        "hint_hold": "Hold the button — presses repeat at the chosen rate",
        "hint_pad": "gamepad button presses go to the game",
        "hint_key": "key presses go to the game",
    },
}

LANG_DISPLAY = {"Русский": "ru", "English": "en"}


def t(key: str, **kw) -> str:
    text = _T.get(LANG, _T["ru"]).get(key) or _T["ru"].get(key, key)
    return text.format(**kw) if kw else text


def set_lang(code: str) -> None:
    global LANG
    LANG = code if code in _T else "ru"


def mode_labels() -> dict:
    return {"hold": "Удержание", "burst": "Серия"} if LANG == "ru" else {"hold": "Hold", "burst": "Burst"}


def mode_by_label() -> dict:
    return {v: k for k, v in mode_labels().items()}


def type_labels() -> dict:
    return (
        {"pad": "Геймпад (Xbox)", "key": "Клавиатура"}
        if LANG == "ru"
        else {"pad": "Gamepad (Xbox)", "key": "Keyboard"}
    )


def type_by_label() -> dict:
    return {v: k for k, v in type_labels().items()}


_EN_PAD = {
    "lt": "LT (trigger)",
    "rt": "RT (trigger)",
    "ls": "LS (stick)",
    "rs": "RS (stick)",
    "dpad_up": "D-Pad up",
    "dpad_down": "D-Pad down",
    "dpad_left": "D-Pad left",
    "dpad_right": "D-Pad right",
}


def pad_labels() -> dict:
    if LANG == "ru":
        return dict(PAD_LABELS)
    return {k: _EN_PAD.get(k, v) for k, v in PAD_LABELS.items()}


KEY_DISPLAY = {
    "space": "Пробел",
    "enter": "Enter",
    "tab": "Tab",
    "esc": "Esc",
    "backspace": "Backspace",
    "shift": "Shift",
    "ctrl": "Ctrl",
    "alt": "Alt",
    "up": "Вверх",
    "down": "Вниз",
    "left": "Влево",
    "right": "Вправо",
    "insert": "Insert",
    "delete": "Delete",
    "home": "Home",
    "end": "End",
    "pageup": "Page Up",
    "pagedown": "Page Down",
    "capslock": "Caps Lock",
    "numlock": "Num Lock",
    "scrolllock": "Scroll Lock",
    "printscreen": "Print Screen",
    "pause": "Pause",
}

_KEY_DISPLAY_EN = {
    "space": "Space",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
}


def display_key(name: str) -> str:
    m = KEY_DISPLAY if LANG == "ru" else {**KEY_DISPLAY, **_KEY_DISPLAY_EN}
    return m.get(name, name.upper() if len(name) == 1 else name.capitalize())


def output_labels() -> dict:
    return {display_key(k): k for k in output_key_names()}


class ToggleSwitch(tk.Canvas):
    """Аккуратный переключатель вместо системного чекбокса."""

    def __init__(self, master: tk.Misc, variable: tk.BooleanVar, command=None,
                 bg: str = CARD, width: int = 46, height: int = 26):
        super().__init__(master, width=width, height=height, bg=bg,
                         highlightthickness=0, cursor="hand2", takefocus=1)
        self.var = variable
        self.command = command
        self._sw, self._sh = width, height
        self.bind("<Button-1>", self._toggle)
        self.bind("<space>", self._toggle)
        variable.trace_add("write", lambda *_: self._draw())
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        on = bool(self.var.get())
        track = ACCENT if on else "#3b414a"
        r = self._sh / 2
        self.create_oval(1, 1, self._sh - 1, self._sh - 1, fill=track, outline=track)
        self.create_oval(self._sw - self._sh + 1, 1, self._sw - 1, self._sh - 1, fill=track, outline=track)
        self.create_rectangle(r, 1, self._sw - r, self._sh - 1, fill=track, outline=track)
        pad = 3
        d = self._sh - 2 * pad
        x = (self._sw - pad - d) if on else pad
        self.create_oval(x, pad, x + d, pad + d, fill="#ffffff", outline="")

    def _toggle(self, _event=None) -> None:
        self.var.set(not self.var.get())
        if self.command:
            self.command()


# --- конфиг ----------------------------------------------------------------

def default_config() -> dict:
    return {
        "language": "ru",
        "toggle_key": "f8",
        "bindings": [
            {
                "enabled": True,
                "trigger": {"type": "pad", "button": "a"},
                "output_type": "pad",
                "output_key": "a",
                "mode": "hold",
                "rate_hz": 12,
                "press_ms": 50,
            }
        ],
    }


def load_config() -> dict:
    if not CONFIG.exists():
        return default_config()
    try:
        with open(CONFIG, encoding="utf-8-sig") as fh:
            cfg = json.load(fh)
        if not isinstance(cfg.get("bindings"), list) or not cfg["bindings"]:
            raise ValueError("пустой список bindings")
        return cfg
    except Exception:
        return default_config()


def save_config(cfg: dict) -> None:
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


# --- карточка биндинга -----------------------------------------------------

class BindingCard(ttk.Frame):
    def __init__(self, master: tk.Misc, app: "App", data: dict):
        super().__init__(master, style="Card.TFrame", padding=14)
        self.app = app

        trig = data.get("trigger", {})
        kind = str(trig.get("type", "key")).lower()
        out_key = str(data.get("output_key", "a" if kind == "pad" else "space"))

        self.type_var = tk.StringVar(value=type_labels().get(kind, type_labels()["key"]))
        self.trig_var = tk.StringVar()
        self.out_var = tk.StringVar(
            value=pad_labels().get(out_key.lower(), pad_labels()["a"]) if kind == "pad" else display_key(out_key)
        )
        self.mode_var = tk.StringVar(
            value=mode_labels().get(str(data.get("mode", "hold")), mode_labels()["hold"])
        )
        self.rate_var = tk.IntVar(value=int(round(float(data.get("rate_hz", 12)))))
        self.count_var = tk.IntVar(value=int(data.get("burst_count", 5)))
        self.enabled_var = tk.BooleanVar(value=bool(data.get("enabled", True)))

        self.press_ms = float(data.get("press_ms", 50))

        # верхняя строка: включено + удалить
        top = ttk.Frame(self, style="Card.TFrame")
        top.pack(fill="x")
        ToggleSwitch(top, self.enabled_var, command=self.app.on_change).pack(side="left")
        ttk.Label(top, text=t("enabled"), style="Card.TLabel").pack(side="left", padx=(10, 0))
        ttk.Button(
            top, text=t("delete"), style="Ghost.TButton", width=8, command=self.app.remove_card_cb(self)
        ).pack(side="right")

        # строка 1: триггер -> клавиша
        line1 = ttk.Frame(self, style="Card.TFrame")
        line1.pack(fill="x", pady=(10, 6))

        ttk.Label(line1, text=t("btn_label"), style="CardMuted.TLabel").pack(side="left")
        self.type_box = ttk.Combobox(
            line1, textvariable=self.type_var, values=list(type_labels().values()),
            state="readonly", width=16, font=(FONT, 10),
        )
        self.type_box.pack(side="left", padx=(6, 4))
        self.type_box.bind("<<ComboboxSelected>>", self._on_type_change)

        self.trig_box = ttk.Combobox(line1, textvariable=self.trig_var, state="readonly", width=16, font=(FONT, 10))
        self.trig_box.pack(side="left", padx=(0, 8))

        ttk.Label(line1, text="→", style="Arrow.TLabel").pack(side="left", padx=4)

        ttk.Label(line1, text=t("press_label"), style="CardMuted.TLabel").pack(side="left", padx=(10, 0))
        self.out_box = ttk.Combobox(
            line1, textvariable=self.out_var, values=[],
            state="readonly", width=16, font=(FONT, 10),
        )
        self.out_box.pack(side="left", padx=6)

        # строка 2: режим, частота, серия
        line2 = ttk.Frame(self, style="Card.TFrame")
        line2.pack(fill="x", pady=(2, 0))

        ttk.Label(line2, text=t("mode_label"), style="CardMuted.TLabel").pack(side="left")
        self.mode_box = ttk.Combobox(
            line2, textvariable=self.mode_var, values=list(mode_labels().values()),
            state="readonly", width=11, font=(FONT, 10),
        )
        self.mode_box.pack(side="left", padx=6)
        self.mode_box.bind("<<ComboboxSelected>>", self._on_mode_change)

        ttk.Label(line2, text=t("rate_label"), style="CardMuted.TLabel").pack(side="left", padx=(18, 0))
        ttk.Spinbox(
            line2, from_=1, to=30, textvariable=self.rate_var, width=4,
            font=(FONT, 10), justify="center", command=self.app.on_change,
        ).pack(side="left", padx=6)
        ttk.Label(line2, text=t("per_sec"), style="CardMuted.TLabel").pack(side="left")

        ttk.Label(line2, text=t("in_burst"), style="CardMuted.TLabel").pack(side="left", padx=(18, 0))
        self.count_spin = ttk.Spinbox(
            line2, from_=2, to=20, textvariable=self.count_var, width=4,
            font=(FONT, 10), justify="center", command=self.app.on_change,
        )
        self.count_spin.pack(side="left", padx=6)

        # подсказка
        self.hint = ttk.Label(self, text="", style="CardMuted.TLabel")
        self.hint.pack(fill="x", pady=(8, 0))

        # значения триггера и вывода
        self._fill_triggers(preselect=str(trig.get("button") or trig.get("key") or ""))
        self._fill_outputs(preselect=out_key)

        for var in (self.type_var, self.trig_var, self.out_var, self.mode_var,
                    self.rate_var, self.count_var, self.enabled_var):
            var.trace_add("write", lambda *_: self.app.on_change())
        self._update_mode_state()

    # --- значения ---

    def _fill_triggers(self, preselect: str = "") -> None:
        if self.trigger_kind() == "pad":
            values = list(pad_labels().values())
            current = pad_labels().get(preselect.lower(), values[0])
        else:
            values = [display_key(k) for k in output_key_names()]
            current = display_key(preselect) if preselect else "F9"
        self.trig_box.configure(values=values)
        self.trig_var.set(current if current in values else values[0])

    def _fill_outputs(self, preselect: str = "") -> None:
        """Список «Жать» повторяет тип слева: кнопки геймпада или клавиши."""
        if self.trigger_kind() == "pad":
            values = list(pad_labels().values())
            current = pad_labels().get(preselect.lower(), values[0])
        else:
            values = [display_key(k) for k in output_key_names()]
            current = display_key(preselect) if preselect else "E"
        self.out_box.configure(values=values)
        self.out_var.set(current if current in values else values[0])

    def _on_type_change(self, _event=None) -> None:
        self._fill_triggers()
        self._fill_outputs()
        self._update_mode_state()
        self.app.on_change()

    def _on_mode_change(self, _event=None) -> None:
        self._update_mode_state()
        self.app.on_change()

    def _update_mode_state(self) -> None:
        burst = self.mode_var.get() == mode_labels()["burst"]
        state = "normal" if burst else "disabled"
        try:
            self.count_spin.configure(state=state)
        except tk.TclError:
            pass
        if burst:
            text = t("hint_burst")
        else:
            text = t("hint_hold")
        if self.trigger_kind() == "pad":
            text += "  ·  " + t("hint_pad")
        else:
            text += "  ·  " + t("hint_key")
        self.hint.configure(text=text)

    # --- данные ---

    def trigger_kind(self) -> str:
        return type_by_label()[self.type_var.get()]

    def trigger_name(self) -> str:
        if self.trigger_kind() == "pad":
            rev = {v: k for k, v in pad_labels().items()}
            return rev.get(self.trig_var.get(), "a")
        rev = {display_key(k): k for k in output_key_names()}
        return rev.get(self.trig_var.get(), self.trig_var.get().lower())

    def output_key(self) -> str:
        raw = self.out_var.get().strip()
        if self.trigger_kind() == "pad":
            rev = {v: k for k, v in pad_labels().items()}
            return rev.get(raw, "a")
        return output_labels().get(raw, raw.lower())

    def to_dict(self) -> dict:
        kind = self.trigger_kind()
        trig = (
            {"type": "pad", "button": self.trigger_name()}
            if kind == "pad"
            else {"type": "key", "key": self.trigger_name()}
        )
        data = {
            "enabled": bool(self.enabled_var.get()),
            "trigger": trig,
            "output_type": kind,
            "output_key": self.output_key(),
            "mode": mode_by_label().get(self.mode_var.get(), "hold"),
            "rate_hz": max(1, int(self.rate_var.get())),
            "press_ms": self.press_ms,
        }
        if data["mode"] == "burst":
            data["burst_count"] = max(1, int(self.count_var.get()))
        return data

    def to_binding(self) -> Binding:
        kind = self.trigger_kind()
        name = self.trigger_name()
        out = self.output_key()
        trigger = Trigger(kind, name, resolve_vk(name) if kind == "key" else None)
        return Binding(
            trigger=trigger,
            output_key=out,
            output_vk=resolve_vk(out) if kind == "key" else 0,
            output_type=kind,
            mode=mode_by_label().get(self.mode_var.get(), "hold"),
            rate_hz=max(1, int(self.rate_var.get())),
            press_ms=self.press_ms,
            burst_count=max(1, int(self.count_var.get())),
            enabled=bool(self.enabled_var.get()),
        )


# --- приложение ------------------------------------------------------------

class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.engine: Engine | None = None
        self.cards: list[BindingCard] = []
        self._save_job = None
        self._note_job = None
        self._pad_error_shown = False

        self._cfg = load_config()
        set_lang(str(self._cfg.get("language", "ru")))

        root.title(t("title"))
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        w, h = min(1000, sw - 80), min(760, sh - 120)
        root.geometry(f"{w}x{h}")
        root.minsize(min(860, sw - 40), min(560, sh - 80))
        root.configure(bg=BG)

        self._init_style()
        self._build_header()
        self._build_body()
        self._build_footer()

        self.load_from_disk()
        self._poll()
        root.protocol("WM_DELETE_WINDOW", self.on_close)

    # --- стили ---

    def _init_style(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure(".", background=BG, foreground=FG, fieldbackground=CARD2,
                        font=(FONT, 11))
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=CARD)
        style.configure("TLabel", background=BG, foreground=FG)
        style.configure("Card.TLabel", background=CARD, foreground=FG)
        style.configure("CardMuted.TLabel", background=CARD, foreground=MUTED, font=(FONT, 9))
        style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=(FONT, 10))
        style.configure("Ok.TLabel", background=BG, foreground=OK, font=(FONT, 10))
        style.configure("Err.TLabel", background=BG, foreground=DANGER, font=(FONT, 10))
        style.configure("Title.TLabel", background=BG, foreground=FG, font=(FONT, 20, "bold"))
        style.configure("Sub.TLabel", background=BG, foreground=MUTED, font=(FONT, 10))
        style.configure("Arrow.TLabel", background=CARD, foreground=ACCENT, font=(FONT, 15, "bold"))
        style.configure("Status.TLabel", background=BG, foreground=MUTED, font=(FONT, 11, "bold"))

        style.configure("TCombobox", fieldbackground=CARD2, background=CARD2,
                        foreground=FG, arrowcolor=FG, padding=5)
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", CARD2)],
            foreground=[("readonly", FG)],
            selectbackground=[("readonly", CARD2)],
            selectforeground=[("readonly", FG)],
            background=[("active", CARD2)],
        )

        style.configure("TSpinbox", fieldbackground=CARD2, background=CARD2,
                        foreground=FG, arrowcolor=FG, padding=4)
        style.configure("TCheckbutton", background=CARD, foreground=FG,
                        font=(FONT, 10))
        style.map("TCheckbutton", background=[("active", CARD)],
                  foreground=[("active", FG)])

        style.configure("Accent.TButton", background=ACCENT, foreground="#ffffff",
                        font=(FONT, 12, "bold"), padding=(18, 10), borderwidth=0)
        style.map("Accent.TButton",
                  background=[("active", ACCENT_HI), ("pressed", "#3c74d6")])
        style.configure("Danger.TButton", background=DANGER, foreground="#ffffff",
                        font=(FONT, 12, "bold"), padding=(18, 10), borderwidth=0)
        style.map("Danger.TButton",
                  background=[("active", "#ff7a7a"), ("pressed", "#e04a4a")])
        style.configure("Ghost.TButton", background=CARD2, foreground=MUTED,
                        font=(FONT, 9), padding=(10, 5), borderwidth=0)
        style.map("Ghost.TButton", background=[("active", "#40464f")],
                  foreground=[("active", FG)])
        style.configure("Add.TButton", background=CARD, foreground=FG,
                        font=(FONT, 11, "bold"), padding=(18, 10), borderwidth=0)
        style.map("Add.TButton", background=[("active", CARD2)])

        style.configure("Vertical.TScrollbar", background=CARD2, troughcolor=BG,
                        bordercolor=BG, arrowcolor=MUTED, borderwidth=0)

        self.root.option_add("*TCombobox*Listbox.background", CARD2)
        self.root.option_add("*TCombobox*Listbox.foreground", FG)
        self.root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
        self.root.option_add("*TCombobox*Listbox.font", (FONT, 11))

    # --- интерфейс ---

    def _build_header(self) -> None:
        head = ttk.Frame(self.root, padding=(22, 18, 22, 10))
        head.pack(fill="x")

        # правая часть пакуется первой: на узком окне сжимается подпись слева,
        # а не кнопка «Запустить»
        right = ttk.Frame(head)
        right.pack(side="right")

        self.lang_var = tk.StringVar(value="Русский" if LANG == "ru" else "English")
        lang_box = ttk.Combobox(
            right, textvariable=self.lang_var, values=list(LANG_DISPLAY),
            state="readonly", width=9, font=(FONT, 10),
        )
        lang_box.pack(side="left", padx=(0, 14))
        lang_box.bind("<<ComboboxSelected>>", self._on_lang_change)

        status = ttk.Frame(right)
        status.pack(side="left", padx=(0, 14))
        self.dot = tk.Canvas(status, width=12, height=12, bg=BG, highlightthickness=0)
        self.dot.pack(side="left", padx=(0, 8))
        self.dot_id = self.dot.create_oval(2, 2, 10, 10, fill=MUTED, outline="")
        self.status_var = tk.StringVar(value=t("stopped"))
        ttk.Label(status, textvariable=self.status_var, style="Status.TLabel").pack(side="left")

        self.toggle_btn = ttk.Button(
            right, text=t("btn_start"), style="Accent.TButton", command=self.toggle_engine
        )
        self.toggle_btn.pack(side="left")

        left = ttk.Frame(head)
        left.pack(side="left", fill="x", expand=True)
        ttk.Label(left, text="Turbo Input", style="Title.TLabel").pack(anchor="w")
        self.sub_label = ttk.Label(left, text=t("subtitle"), style="Sub.TLabel")
        self.sub_label.pack(anchor="w", pady=(2, 0))

    def _build_body(self) -> None:
        body = ttk.Frame(self.root, padding=(22, 8, 22, 8))
        body.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(body, bg=BG, highlightthickness=0)
        scroll = ttk.Scrollbar(body, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.inner = ttk.Frame(self.canvas)
        self.inner_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>",
                        lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfigure(self.inner_id, width=e.width))
        self.root.bind_all("<MouseWheel>", self._on_wheel)

    def _build_footer(self) -> None:
        foot = ttk.Frame(self.root, padding=(22, 8, 22, 16))
        foot.pack(fill="x")

        row = ttk.Frame(foot)
        row.pack(fill="x")

        self.add_btn = ttk.Button(row, text=t("add_btn"), style="Add.TButton",
                                  command=self.add_card)
        self.add_btn.pack(side="left")

        self.pause_label = ttk.Label(row, text=t("pause_label"), style="Muted.TLabel")
        self.pause_label.pack(side="left", padx=(22, 6))
        self.toggle_key_var = tk.StringVar(value="F8")
        self.toggle_box = ttk.Combobox(
            row, textvariable=self.toggle_key_var, values=[f"F{i}" for i in range(1, 13)],
            state="readonly", width=5, font=(FONT, 10),
        )
        self.toggle_box.pack(side="left")
        self.toggle_box.bind("<<ComboboxSelected>>", lambda e: self.on_change())

        self.topmost_var = tk.BooleanVar(value=False)
        topmost_box = ttk.Frame(row)
        topmost_box.pack(side="left", padx=(22, 0))
        ToggleSwitch(topmost_box, self.topmost_var, command=self._apply_topmost,
                     bg=BG, width=40, height=22).pack(side="left")
        self.topmost_label = ttk.Label(topmost_box, text=t("topmost"), style="Muted.TLabel")
        self.topmost_label.pack(side="left", padx=(8, 0))

        self.count_var = tk.StringVar(value=t("presses", n=0))
        ttk.Label(row, textvariable=self.count_var, style="Muted.TLabel").pack(side="right")

        self.note_var = tk.StringVar(value=t("note"))
        self.note = ttk.Label(foot, textvariable=self.note_var, style="Muted.TLabel")
        self.note.pack(anchor="w", pady=(10, 0))

    # --- карточки ---

    def load_from_disk(self) -> None:
        cfg = load_config()
        self.toggle_key_var.set(str(cfg.get("toggle_key", "f8")).upper())
        for b in cfg.get("bindings", []):
            self.add_card(b, notify=False)

    def add_card(self, data: dict | None = None, notify: bool = True) -> None:
        data = data or {
            "enabled": True,
            "trigger": {"type": "pad", "button": "a"},
            "output_type": "pad",
            "output_key": "a",
            "mode": "hold",
            "rate_hz": 12,
            "press_ms": 50,
        }
        card = BindingCard(self.inner, self, data)
        card.pack(fill="x", pady=(0, 10))
        self.cards.append(card)
        if notify:
            self.on_change()
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def remove_card_cb(self, card: BindingCard):
        def _remove() -> None:
            if len(self.cards) == 1:
                self.note_err(t("min_one"))
                return
            card.destroy()
            self.cards.remove(card)
            self.on_change()
        return _remove

    # --- изменения ---

    def collect(self) -> list[Binding]:
        return [c.to_binding() for c in self.cards]

    def config_dict(self) -> dict:
        return {
            "language": LANG,
            "toggle_key": self.toggle_key_var.get().lower(),
            "bindings": [c.to_dict() for c in self.cards],
        }

    def on_change(self) -> None:
        if self._save_job:
            self.root.after_cancel(self._save_job)
        self._save_job = self.root.after(450, self.apply_changes)

    def apply_changes(self) -> None:
        self._save_job = None
        try:
            bindings = self.collect()
            cfg = self.config_dict()
            save_config(cfg)
        except (ValueError, tk.TclError) as exc:
            self.note_err(t("check", e=exc))
            return

        if self.engine and self.engine.running:
            self.engine.set_bindings(bindings)
            self.engine.toggle_vk = resolve_vk(self.toggle_key_var.get())
        self.note_ok(t("saved"))

    # --- запуск ---

    def toggle_engine(self) -> None:
        if self.engine and self.engine.running:
            self.stop_engine()
        else:
            self.start_engine()

    def start_engine(self) -> None:
        try:
            bindings = self.collect()
            toggle_vk = resolve_vk(self.toggle_key_var.get())
        except ValueError as exc:
            self.note_err(t("check", e=exc))
            return
        save_config(self.config_dict())
        self._pad_error_shown = False
        self.engine = Engine(bindings, toggle_vk=toggle_vk)
        self.engine.start()
        self.toggle_btn.configure(text=t("btn_stop"), style="Danger.TButton")
        self.note_ok(t("started"))

    def stop_engine(self) -> None:
        if self.engine:
            self.engine.stop()
        self.toggle_btn.configure(text=t("btn_start"), style="Accent.TButton")
        self.note_var.set(t("stopped_note"))
        self._set_status(t("stopped"), MUTED)

    def _apply_topmost(self) -> None:
        self.root.attributes("-topmost", bool(self.topmost_var.get()))

    # --- язык ---

    def _on_lang_change(self, _event=None) -> None:
        code = LANG_DISPLAY.get(self.lang_var.get(), "ru")
        if code == LANG:
            return
        # подписи в переменных — на старом языке: собираем данные ДО смены языка
        datas = [c.to_dict() for c in self.cards]
        for card in self.cards:
            card.destroy()
        self.cards.clear()
        set_lang(code)
        for d in datas:
            self.add_card(d, notify=False)
        save_config(self.config_dict())
        self._retranslate()

    def _retranslate(self) -> None:
        self.root.title(t("title"))
        self.sub_label.configure(text=t("subtitle"))
        self.lang_var.set("Русский" if LANG == "ru" else "English")
        if self.engine and self.engine.running:
            self.toggle_btn.configure(text=t("btn_stop"), style="Danger.TButton")
        else:
            self.toggle_btn.configure(text=t("btn_start"), style="Accent.TButton")
        self.add_btn.configure(text=t("add_btn"))
        self.pause_label.configure(text=t("pause_label"))
        self.topmost_label.configure(text=t("topmost"))
        self._note_reset()

    # --- статус ---

    def _set_status(self, text: str, color: str) -> None:
        self.status_var.set(text)
        self.dot.itemconfigure(self.dot_id, fill=color)

    def _poll(self) -> None:
        eng = self.engine
        if eng and eng.running:
            if eng.paused:
                self._set_status(t("paused"), WARN)
            else:
                self._set_status(t("running"), OK)
            self.count_var.set(t("presses", n=eng.presses))
            if eng.pad_error and not self._pad_error_shown:
                self._pad_error_shown = True
                self.note_err(t("pad_err", e=eng.pad_error))
        else:
            self._set_status(t("stopped"), MUTED)
            self.count_var.set(t("presses", n=0))
        self.root.after(200, self._poll)

    def note_ok(self, text: str) -> None:
        self.note_var.set(text)
        self.note.configure(style="Ok.TLabel")
        if self._note_job:
            self.root.after_cancel(self._note_job)
        self._note_job = self.root.after(2500, self._note_reset)

    def note_err(self, text: str) -> None:
        self.note_var.set(text)
        self.note.configure(style="Err.TLabel")
        if self._note_job:
            self.root.after_cancel(self._note_job)
        self._note_job = self.root.after(4000, self._note_reset)

    def _note_reset(self) -> None:
        self._note_job = None
        self.note_var.set(t("note"))
        self.note.configure(style="Muted.TLabel")

    def _on_wheel(self, event) -> None:
        widget = self.root.winfo_containing(event.x_root, event.y_root)
        if isinstance(widget, (ttk.Combobox, ttk.Spinbox)):
            return
        self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def on_close(self) -> None:
        try:
            save_config(self.config_dict())
        except Exception:
            pass
        if self.engine:
            self.engine.stop()
        self.root.destroy()


def main() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()

