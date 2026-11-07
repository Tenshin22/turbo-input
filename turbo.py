#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
turbo.py — консольная версия Turbo Input.

Читает config.json, запускает движок из engine.py.
Для обычного использования удобнее app.py (окно) или TurboInput.exe.

Остановка: Ctrl+C. Пауза: клавиша toggle_key (по умолчанию F8).
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from engine import Binding, Engine, Trigger, resolve_vk

BASE = Path(__file__).resolve().parent


def _config_path() -> Path:
    """config.json рядом со скриптом; если папку писать нельзя — %APPDATA%\\TurboInput."""
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


def load_bindings(path: Path) -> tuple[dict, list[Binding]]:
    with open(path, encoding="utf-8-sig") as fh:
        cfg = json.load(fh)

    bindings: list[Binding] = []
    for raw in cfg.get("bindings", []):
        trig = raw.get("trigger", {})
        kind = str(trig.get("type", "key")).lower()
        if kind == "pad":
            trigger = Trigger("pad", str(trig.get("button", "a")).lower())
        elif kind == "key":
            name = str(trig.get("key", "f9")).lower()
            trigger = Trigger("key", name, resolve_vk(name))
        else:
            raise ValueError(f"trigger.type: ожидается 'pad' или 'key', а не {kind!r}")

        out_type = str(raw.get("output_type") or ("pad" if kind == "pad" else "key")).lower()
        out_key = str(raw.get("output_key", "a" if out_type == "pad" else "space")).lower()

        bindings.append(
            Binding(
                trigger=trigger,
                output_key=out_key,
                output_vk=resolve_vk(out_key) if out_type == "key" else 0,
                output_type=out_type,
                mode=str(raw.get("mode", "hold")).lower(),
                rate_hz=float(raw.get("rate_hz", 12)),
                press_ms=float(raw.get("press_ms", 50)),
                burst_count=int(raw.get("burst_count", 5)),
                enabled=bool(raw.get("enabled", True)),
            )
        )
    return cfg, bindings


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry_run = "--dry-run" in sys.argv
    path = Path(args[0]) if args else _config_path()

    try:
        cfg, bindings = load_bindings(path)
    except Exception as exc:
        print(f"Ошибка конфига {path}: {exc}")
        return 2

    active = [b for b in bindings if b.enabled]
    if not active:
        print("Нет включённых кнопок в конфиге.")
        return 2

    toggle_vk = resolve_vk(str(cfg.get("toggle_key", "f8")))
    engine = Engine(active, toggle_vk=toggle_vk, dry_run=dry_run)

    print("=" * 56)
    print(" Turbo Input (консольный режим)")
    print("=" * 56)
    for b in active:
        trig = f"геймпад:{b.trigger.name}" if b.trigger.kind == "pad" else f"клавиша:{b.trigger.name}"
        out = f"геймпад:{b.output_key}" if b.output_type == "pad" else f"клавиша:{b.output_key}"
        mode = "удержание" if b.mode == "hold" else f"серия x{b.burst_count}"
        print(f"  {trig} -> {out:<14} {mode}, {b.rate_hz:g} раз в секунду")
    print("-" * 56)
    print(f"Пауза: {cfg.get('toggle_key', 'f8').upper()} | Выход: Ctrl+C")
    if dry_run:
        print("[dry-run] клавиши не отправляются")
    print("-" * 56)

    engine.start()
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        engine.stop()
        print(f"\nОстановлено. Нажатий: {engine.presses}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
