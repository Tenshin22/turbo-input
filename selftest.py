"""Автотест движка: серия нажатий на клавиатуру и на виртуальный геймпад."""

import ctypes
import json
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

BASE = Path(__file__).resolve().parent
TMP = Path(r"C:\Users\User\AppData\Local\Temp\opencode\turbo_test_config.json")
TMP_PAD = Path(r"C:\Users\User\AppData\Local\Temp\opencode\turbo_test_pad.json")

user32 = ctypes.WinDLL("user32", use_last_error=True)
xinput = ctypes.WinDLL("XInput1_4.dll")
ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

XUSB_GAMEPAD_A = 0x1000


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]


class _U(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _U)]


class XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ("wButtons", wintypes.WORD), ("bLeftTrigger", ctypes.c_ubyte),
        ("bRightTrigger", ctypes.c_ubyte), ("sThumbLX", ctypes.c_short),
        ("sThumbLY", ctypes.c_short), ("sThumbRX", ctypes.c_short),
        ("sThumbRY", ctypes.c_short),
    ]


class XINPUT_STATE(ctypes.Structure):
    _fields_ = [("dwPacketNumber", wintypes.DWORD), ("Gamepad", XINPUT_GAMEPAD)]


def send_scan(scan, up):
    inp = INPUT(type=1)
    inp.ki = KEYBDINPUT(0, scan, KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if up else 0), 0, 0)
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def down(vk):
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


def pad_button(mask):
    for slot in range(4):
        st = XINPUT_STATE()
        if xinput.XInputGetState(slot, ctypes.byref(st)) == 0 and (st.Gamepad.wButtons & mask):
            return True
    return False


def run_engine(cfg_path):
    return subprocess.Popen(
        [sys.executable, str(BASE / "turbo.py"), str(cfg_path)],
        cwd=str(BASE),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def count_presses(read_state, seconds=1.2):
    presses = 0
    prev = False
    send_scan(0x43, up=False)  # F9
    t_end = time.perf_counter() + seconds
    while time.perf_counter() < t_end:
        cur = read_state()
        if cur and not prev:
            presses += 1
        prev = cur
        time.sleep(0.001)
    send_scan(0x43, up=True)
    return presses


def test_keyboard():
    cfg = {
        "toggle_key": "f8",
        "bindings": [{
            "enabled": True,
            "trigger": {"type": "key", "key": "f9"},
            "output_type": "key",
            "output_key": "a",
            "mode": "hold",
            "rate_hz": 10,
            "press_ms": 20,
        }],
    }
    TMP.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    proc = run_engine(TMP)
    try:
        time.sleep(1.5)
        presses = count_presses(lambda: down(0x41))  # A
        print(f"клавиатура: нажатий за 1.2 с — {presses} (ожидание ~12)")
        return presses >= 8
    finally:
        stop(proc)


def test_pad():
    cfg = {
        "toggle_key": "f8",
        "bindings": [{
            "enabled": True,
            "trigger": {"type": "key", "key": "f9"},
            "output_type": "pad",
            "output_key": "a",
            "mode": "hold",
            "rate_hz": 10,
            "press_ms": 20,
        }],
    }
    TMP_PAD.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    proc = run_engine(TMP_PAD)
    try:
        time.sleep(2.0)  # виртуальный геймпад подключается не мгновенно
        presses = count_presses(lambda: pad_button(XUSB_GAMEPAD_A))
        print(f"геймпад:     нажатий за 1.2 с — {presses} (ожидание ~12)")
        return presses >= 8
    finally:
        stop(proc)


def tap_and_count(read_state, seconds=1.4):
    """Короткое нажатие F9 -> серия должна доиграть после отпускания."""
    presses = 0
    prev = read_state()
    send_scan(0x43, up=False)  # F9 вниз
    start = time.perf_counter()
    t_release = start + 0.12
    t_end = start + seconds
    released = False
    while time.perf_counter() < t_end:
        if not released and time.perf_counter() >= t_release:
            send_scan(0x43, up=True)   # и сразу отпускаем
            released = True
        cur = read_state()
        if cur and not prev:
            presses += 1
        prev = cur
        time.sleep(0.001)
    if not released:
        send_scan(0x43, up=True)
    return presses


def test_burst_pad():
    cfg = {
        "toggle_key": "f8",
        "bindings": [{
            "enabled": True,
            "trigger": {"type": "key", "key": "f9"},
            "output_type": "pad",
            "output_key": "a",
            "mode": "burst",
            "rate_hz": 10,
            "press_ms": 20,
            "burst_count": 6,
        }],
    }
    TMP_PAD.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    proc = run_engine(TMP_PAD)
    try:
        time.sleep(2.0)
        presses = tap_and_count(lambda: pad_button(XUSB_GAMEPAD_A), seconds=1.2)
        print(f"серия:       нажатий после короткого тапа — {presses} (ожидание 6)")
        return presses == 6
    finally:
        stop(proc)


def stop(proc):
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except Exception:
        proc.kill()


def main():
    ok = test_keyboard()
    time.sleep(0.5)
    ok = test_pad() and ok
    time.sleep(0.5)
    ok = test_burst_pad() and ok
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
