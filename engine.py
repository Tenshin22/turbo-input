#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
engine.py — движок турбо-нажатий.

Читает клавиатуру (GetAsyncKeyState) и Xbox-геймпад (XInput),
отправляет клавиши через SendInput со скан-кодом.

Используется и консольной версией (turbo.py), и приложением (app.py).
"""

from __future__ import annotations

import ctypes
import sys
import threading
import time
from ctypes import wintypes
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# WinAPI
# ---------------------------------------------------------------------------

user32 = ctypes.WinDLL("user32", use_last_error=True)
winmm = ctypes.WinDLL("winmm")

ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
INPUT_KEYBOARD = 1
MAPVK_VK_TO_VSC = 0


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT
user32.MapVirtualKeyW.argtypes = [wintypes.UINT, wintypes.UINT]
user32.MapVirtualKeyW.restype = wintypes.UINT
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
winmm.timeBeginPeriod.argtypes = [wintypes.UINT]
winmm.timeEndPeriod.argtypes = [wintypes.UINT]


# ---------------------------------------------------------------------------
# Клавиши
# ---------------------------------------------------------------------------

NAMED_KEYS: dict[str, int] = {
    "space": 0x20,
    "enter": 0x0D,
    "tab": 0x09,
    "esc": 0x1B,
    "backspace": 0x08,
    "shift": 0xA0,
    "ctrl": 0xA2,
    "alt": 0xA4,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
    "insert": 0x2D,
    "delete": 0x2E,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
    "capslock": 0x14,
    "numlock": 0x90,
    "scrolllock": 0x91,
    "printscreen": 0x2C,
    "pause": 0x13,
    "`": 0xC0,
    "-": 0xBD,
    "=": 0xBB,
    "[": 0xDB,
    "]": 0xDD,
    ";": 0xBA,
    "'": 0xDE,
    ",": 0xBC,
    ".": 0xBE,
    "/": 0xBF,
}

EXTENDED_VKS = {
    0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x2D, 0x2E,
    0x5B, 0x5C, 0x5D, 0x6F, 0xA3, 0xA5,
}

# Человекочитаемые подписи для интерфейса
KEY_LABELS: dict[str, str] = {
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

# Подписи — по одной кнопке, в именах Xbox-контроллера: список должен читаться
# однозначно, без «A / ✕» и прочих двойных названий.
PAD_LABELS: dict[str, str] = {
    "a": "A",
    "b": "B",
    "x": "X",
    "y": "Y",
    "lb": "LB",
    "rb": "RB",
    "lt": "LT (триггер)",
    "rt": "RT (триггер)",
    "start": "Start",
    "back": "Back",
    "ls": "LS (стик)",
    "rs": "RS (стик)",
    "dpad_up": "D-Pad вверх",
    "dpad_down": "D-Pad вниз",
    "dpad_left": "D-Pad влево",
    "dpad_right": "D-Pad вправо",
}

PAD_BUTTONS = {
    "dpad_up": 0x0001,
    "dpad_down": 0x0002,
    "dpad_left": 0x0004,
    "dpad_right": 0x0008,
    "start": 0x0010,
    "back": 0x0020,
    "ls": 0x0040,
    "rs": 0x0080,
    "lb": 0x0100,
    "rb": 0x0200,
    "a": 0x1000,
    "b": 0x2000,
    "x": 0x4000,
    "y": 0x8000,
}

ANALOG_TRIGGERS = {"lt": "bLeftTrigger", "rt": "bRightTrigger"}
TRIGGER_THRESHOLD = 40


def output_key_names() -> list[str]:
    """Список ключей для выпадающего меню «какую клавишу жать»."""
    names = list("abcdefghijklmnopqrstuvwxyz") + list("0123456789")
    names += [f"f{i}" for i in range(1, 13)]
    names += list(NAMED_KEYS)
    return names


def resolve_vk(name: str) -> int:
    key = name.strip().lower()
    if key in NAMED_KEYS:
        return NAMED_KEYS[key]
    if len(key) == 1 and "a" <= key <= "z":
        return ord(key.upper())
    if len(key) == 1 and "0" <= key <= "9":
        return 0x30 + int(key)
    if key.startswith("f") and key[1:].isdigit():
        n = int(key[1:])
        if 1 <= n <= 24:
            return 0x70 + n - 1
    if key.startswith("numpad") and key[6:].isdigit():
        n = int(key[6:])
        if 0 <= n <= 9:
            return 0x60 + n
    raise ValueError(f"неизвестная клавиша: {name!r}")


_scan_cache: dict[int, int] = {}


def scan_of(vk: int) -> int:
    if vk not in _scan_cache:
        _scan_cache[vk] = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)
    return _scan_cache[vk]


def send_key(vk: int, up: bool) -> None:
    flags = KEYEVENTF_SCANCODE
    if vk in EXTENDED_VKS:
        flags |= KEYEVENTF_EXTENDEDKEY
    if up:
        flags |= KEYEVENTF_KEYUP
    inp = INPUT(type=INPUT_KEYBOARD)
    inp.ki = KEYBDINPUT(0, scan_of(vk), flags, 0, 0)
    if user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT)) != 1:
        raise OSError(ctypes.get_last_error(), "SendInput не сработал")


def tap(vk: int, press_ms: float) -> None:
    send_key(vk, up=False)
    time.sleep(max(press_ms, 1.0) / 1000.0)
    send_key(vk, up=True)


# ---------------------------------------------------------------------------
# Геймпад
# ---------------------------------------------------------------------------

class XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ("wButtons", wintypes.WORD),
        ("bLeftTrigger", ctypes.c_ubyte),
        ("bRightTrigger", ctypes.c_ubyte),
        ("sThumbLX", ctypes.c_short),
        ("sThumbLY", ctypes.c_short),
        ("sThumbRX", ctypes.c_short),
        ("sThumbRY", ctypes.c_short),
    ]


class XINPUT_STATE(ctypes.Structure):
    _fields_ = [("dwPacketNumber", wintypes.DWORD), ("Gamepad", XINPUT_GAMEPAD)]


def _load_xinput():
    for dll in ("XInput1_4.dll", "XInput1_3.dll", "XInput9_1_0.dll"):
        try:
            lib = ctypes.WinDLL(dll)
            lib.XInputGetState.argtypes = [wintypes.DWORD, ctypes.POINTER(XINPUT_STATE)]
            lib.XInputGetState.restype = wintypes.DWORD
            return lib
        except OSError:
            continue
    return None


xinput = _load_xinput()


class Pad:
    """Первый подключённый Xbox-контроллер."""

    def __init__(self) -> None:
        self.slot: int | None = None
        self.state = XINPUT_GAMEPAD()
        self.ignore: set[int] = set()   # слоты, которые нельзя читать (наш виртуальный геймпад)
        self._last_scan = 0.0

    def connected(self) -> set[int]:
        """Какие слоты XInput сейчас заняты (без учёта ignore)."""
        found: set[int] = set()
        if xinput is None:
            return found
        for slot in range(4):
            st = XINPUT_STATE()
            if xinput.XInputGetState(slot, ctypes.byref(st)) == 0:
                found.add(slot)
        return found

    def _scan(self) -> None:
        self.slot = None
        if xinput is None:
            return
        for slot in range(4):
            if slot in self.ignore:
                continue
            st = XINPUT_STATE()
            if xinput.XInputGetState(slot, ctypes.byref(st)) == 0:
                self.slot = slot
                break

    def update(self, now: float) -> None:
        if xinput is None:
            return
        if self.slot is None and now - self._last_scan > 2.0:
            self._last_scan = now
            self._scan()
        if self.slot is None:
            return
        st = XINPUT_STATE()
        if xinput.XInputGetState(self.slot, ctypes.byref(st)) != 0:
            self.slot = None
            return
        self.state = st.Gamepad

    def pressed(self, name: str) -> bool:
        key = name.strip().lower()
        if key in ANALOG_TRIGGERS:
            return getattr(self.state, ANALOG_TRIGGERS[key]) >= TRIGGER_THRESHOLD
        mask = PAD_BUTTONS.get(key)
        return bool(mask and (self.state.wButtons & mask))


# ---------------------------------------------------------------------------
# Виртуальный геймпад (ViGEmBus) — чтобы игра получала нажатия кнопок геймпада
# ---------------------------------------------------------------------------

VIGEM_ERROR_NONE = 0x20000000  # не 0: так в ViGEmClient.h


class XUSB_REPORT(ctypes.Structure):
    _fields_ = [
        ("wButtons", wintypes.WORD),
        ("bLeftTrigger", ctypes.c_ubyte),
        ("bRightTrigger", ctypes.c_ubyte),
        ("sThumbLX", ctypes.c_short),
        ("sThumbLY", ctypes.c_short),
        ("sThumbRX", ctypes.c_short),
        ("sThumbRY", ctypes.c_short),
    ]


def _vigem_candidates() -> list[Path]:
    here = Path(__file__).resolve().parent
    out = [here / "ViGEmClient.dll"]
    if getattr(sys, "frozen", False):
        out.insert(0, Path(sys.executable).resolve().parent / "ViGEmClient.dll")
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            out.insert(0, Path(meipass) / "ViGEmClient.dll")
    return out


def _load_vigem():
    for path in _vigem_candidates():
        if not path.exists():
            continue
        try:
            lib = ctypes.WinDLL(str(path))
        except OSError:
            continue

        lib.vigem_alloc.argtypes = []
        lib.vigem_alloc.restype = ctypes.c_void_p
        lib.vigem_free.argtypes = [ctypes.c_void_p]
        lib.vigem_free.restype = None
        lib.vigem_connect.argtypes = [ctypes.c_void_p]
        lib.vigem_connect.restype = wintypes.ULONG
        lib.vigem_disconnect.argtypes = [ctypes.c_void_p]
        lib.vigem_disconnect.restype = None
        lib.vigem_target_x360_alloc.argtypes = []
        lib.vigem_target_x360_alloc.restype = ctypes.c_void_p
        lib.vigem_target_free.argtypes = [ctypes.c_void_p]
        lib.vigem_target_free.restype = None
        lib.vigem_target_add.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        lib.vigem_target_add.restype = wintypes.ULONG
        lib.vigem_target_remove.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        lib.vigem_target_remove.restype = None
        lib.vigem_target_x360_update.argtypes = [ctypes.c_void_p, ctypes.c_void_p, XUSB_REPORT]
        lib.vigem_target_x360_update.restype = wintypes.ULONG
        return lib
    return None


vigem = _load_vigem()


def virtual_pad_status() -> str:
    """Короткое описание состояния вывода на геймпад для интерфейса."""
    if vigem is None:
        return "нет ViGEmClient.dll рядом с приложением"
    return ""


class VirtualPad:
    """Виртуальный Xbox 360-контроллер: игра видит его как обычный геймпад."""

    def __init__(self) -> None:
        if vigem is None:
            raise RuntimeError("не найден ViGEmClient.dll рядом с приложением")

        self._client = vigem.vigem_alloc()
        if not self._client:
            raise RuntimeError("не удалось создать клиент ViGEm")

        err = vigem.vigem_connect(self._client)
        if err != VIGEM_ERROR_NONE:
            vigem.vigem_free(self._client)
            self._client = None
            raise RuntimeError("ViGEmBus не установлен или не запущен")

        self._target = vigem.vigem_target_x360_alloc()
        err = vigem.vigem_target_add(self._client, self._target)
        if err != VIGEM_ERROR_NONE:
            vigem.vigem_target_free(self._target)
            vigem.vigem_disconnect(self._client)
            vigem.vigem_free(self._client)
            self._client = None
            raise RuntimeError("не удалось подключить виртуальный геймпад")

        self._lock = threading.Lock()

    def _send(self, key: str, down: bool) -> None:
        report = XUSB_REPORT()
        if key == "lt":
            report.bLeftTrigger = 255 if down else 0
        elif key == "rt":
            report.bRightTrigger = 255 if down else 0
        else:
            report.wButtons = PAD_BUTTONS.get(key, 0) if down else 0
        vigem.vigem_target_x360_update(self._client, self._target, report)

    def press(self, button: str, press_ms: float) -> None:
        key = button.strip().lower()
        with self._lock:
            self._send(key, True)
            time.sleep(max(press_ms, 1.0) / 1000.0)
            self._send(key, False)

    def close(self) -> None:
        if not self._client:
            return
        try:
            vigem.vigem_target_remove(self._client, self._target)
        finally:
            vigem.vigem_target_free(self._target)
            vigem.vigem_disconnect(self._client)
            vigem.vigem_free(self._client)
            self._client = None


# ---------------------------------------------------------------------------
# Биндинги
# ---------------------------------------------------------------------------

@dataclass
class Trigger:
    kind: str          # "pad" или "key"
    name: str          # кнопка геймпада или имя клавиши
    vk: int | None = None


@dataclass
class Binding:
    trigger: Trigger
    output_key: str
    output_vk: int
    output_type: str = "key"  # "key" — SendInput, "pad" — виртуальный геймпад
    mode: str = "hold"       # "hold" | "burst"
    rate_hz: float = 12.0
    press_ms: float = 50.0
    burst_count: int = 5
    enabled: bool = True

    _prev: bool = field(default=False, init=False)
    _next: float = field(default=0.0, init=False)
    _queue: list[float] = field(default_factory=list, init=False)

    @property
    def interval(self) -> float:
        return 1.0 / max(self.rate_hz, 0.5)

    def effective_press_ms(self) -> float:
        """Сколько держать кнопку.

        Игры читают геймпад раз в кадр (30–60 раз в секунду), поэтому слишком
        короткий импульс (20 мс) они просто не видят: счётчик нажатий растёт,
        а в игре ничего не происходит. Для геймпада держим не меньше половины
        интервала, но не дольше 50 мс — так нажатия не слипаются в удержание.
        """
        if self.output_type != "pad":
            return self.press_ms
        return max(self.press_ms, min(50.0, self.interval * 0.5))

    def reset(self) -> None:
        self._prev = False
        self._next = 0.0
        self._queue.clear()

    def update(self, now: float, active: bool, tap_fn) -> None:
        if not self.enabled:
            return

        if active and not self._prev:      # фронт нажатия
            self._prev = True
            self._next = now
            if self.mode == "burst":
                self._queue = [now + i * self.interval for i in range(self.burst_count)]
        elif not active and self._prev:
            self._prev = False
            self._next = 0.0

        if self.mode == "burst":
            # Серия уже запущена — она доигрывает до конца, даже если кнопку
            # отпустили. Иначе короткое нажатие давало бы только один повтор.
            while self._queue and self._queue[0] <= now:
                self._queue.pop(0)
                tap_fn()
        elif active and now >= self._next:
            self._next = now + self.interval
            tap_fn()


# ---------------------------------------------------------------------------
# Движок
# ---------------------------------------------------------------------------

class Engine:
    """Фоновый поток: читает ввод и отправляет нажатия."""

    def __init__(
        self,
        bindings: list[Binding],
        toggle_vk: int = 0x77,          # F8
        on_pause: callable | None = None,
        on_press: callable | None = None,
        dry_run: bool = False,
    ) -> None:
        self.bindings = bindings
        self.toggle_vk = toggle_vk
        self.on_pause = on_pause
        self.on_press = on_press
        self.dry_run = dry_run

        self.paused = False
        self.presses = 0
        self.running = False
        self.pad_slot: int | None = None
        self.virtual_ready = False
        self.pad_error = ""

        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._virt: VirtualPad | None = None

    # --- управление ---

    def start(self) -> None:
        if self.running:
            return
        self._stop.clear()
        self.paused = False
        self.presses = 0
        self.running = True
        self._thread = threading.Thread(target=self._run, name="turbo-engine", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._thread = None
        self.running = False

    def toggle_pause(self) -> None:
        self.paused = not self.paused
        with self._lock:
            for b in self.bindings:
                b.reset()
        if self.on_pause:
            self.on_pause(self.paused)

    def set_bindings(self, bindings: list[Binding]) -> None:
        with self._lock:
            for b in bindings:
                b.reset()
            self.bindings = bindings

    # --- поток ---

    def _fire(self, binding: Binding) -> None:
        self.presses += 1
        if not self.dry_run:
            if binding.output_type == "pad":
                virt = self._virt
                if virt is not None:
                    try:
                        virt.press(binding.output_key, binding.effective_press_ms())
                    except Exception:
                        pass
            else:
                try:
                    tap(binding.output_vk, binding.press_ms)
                except OSError:
                    pass
        if self.on_press:
            self.on_press(self.presses)

    def _start_virtual_pad(self) -> None:
        """Создаёт виртуальный геймпад, если он нужен хотя бы одной кнопке."""
        needs = any(b.enabled and b.output_type == "pad" for b in self.bindings)
        if not needs:
            return
        try:
            self._virt = VirtualPad()
            self.virtual_ready = True
        except Exception as exc:
            self.pad_error = str(exc)

    def _run(self) -> None:
        winmm.timeBeginPeriod(1)
        pad = Pad()
        pad.update(time.perf_counter())
        real_slots = pad.connected()

        self._start_virtual_pad()
        if self._virt is not None:
            # Свой виртуальный геймпад нельзя читать как источник нажатий,
            # иначе он будет нажимать сам себя.
            pad.ignore = pad.connected() - real_slots
            pad._scan()
            pad.update(time.perf_counter())

        self.pad_slot = pad.slot
        toggle_prev = False
        try:
            while not self._stop.is_set():
                now = time.perf_counter()

                toggle_now = bool(user32.GetAsyncKeyState(self.toggle_vk) & 0x8000)
                if toggle_now and not toggle_prev:
                    self.paused = not self.paused
                    with self._lock:
                        for b in self.bindings:
                            b.reset()
                    if self.on_pause:
                        self.on_pause(self.paused)
                toggle_prev = toggle_now

                pad.update(now)
                self.pad_slot = pad.slot

                if not self.paused:
                    with self._lock:
                        bindings = list(self.bindings)
                    for b in bindings:
                        if b.trigger.kind == "pad":
                            active = pad.pressed(b.trigger.name)
                        else:
                            active = bool(user32.GetAsyncKeyState(b.trigger.vk or 0) & 0x8000)
                        b.update(now, active, lambda b=b: self._fire(b))

                time.sleep(0.001)
        finally:
            if self._virt is not None:
                try:
                    self._virt.close()
                except Exception:
                    pass
                self._virt = None
                self.virtual_ready = False
            winmm.timeEndPeriod(1)
            self.running = False
