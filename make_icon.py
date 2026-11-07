#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Генератор иконки Turbo Input: синее перо на тёмной плитке."""
from PIL import Image, ImageDraw

S = 1024  # мастер-размер

def bezier_q(p0, c, p1, n=240):
    pts = []
    for i in range(n + 1):
        t = i / n
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t ** 2 * p1[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t ** 2 * p1[1]
        pts.append((x, y))
    return pts


def make_master():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # тёмная плитка со скруглением (как в образце)
    d.rounded_rectangle([30, 30, S - 30, S - 30], radius=210,
                        fill=(14, 22, 38, 255),
                        outline=(40, 60, 92, 255), width=10)

    # перо: кончик вверху-справа, очин внизу-слева
    T = (760, 120)      # кончик пера
    P1 = (520, 700)     # низ опахала на стержне
    A = (392, 856)      # конец очина

    # опахало (vane): правый край + левый край (шире и длиннее)
    right = bezier_q(P1, (880, 452), T)
    left = bezier_q(P1, (500, 330), T)

    # вертикальный градиент для опахала
    grad = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    top_c, bot_c = (98, 172, 235), (40, 96, 176)
    for y in range(80, 760):
        t = (y - 80) / 680
        c = tuple(int(top_c[i] + (bot_c[i] - top_c[i]) * t) for i in range(3)) + (255,)
        gd.line([(0, y), (S, y)], fill=c)
    mask = Image.new("L", (S, S), 0)
    md = ImageDraw.Draw(mask)
    md.polygon(right + left[::-1], fill=255)
    img.paste(grad, (0, 0), mask)

    # бородки: от стержня к правому краю, чуть не доходя до края
    shaft_in = bezier_q(P1, (652, 400), T)  # ход стержня внутри опахала
    for i in range(2, 10):
        t = i / 11
        idx = int(t * (len(right) - 1))
        ex, ey = right[idx]
        sx, sy = shaft_in[int(t * (len(shaft_in) - 1))]
        ex = sx + (ex - sx) * 0.88
        ey = sy + (ey - sy) * 0.88
        d.line([(sx, sy), (ex, ey)], fill=(26, 72, 136, 200), width=7)

    # стержень (толстая линия со скруглением)
    shaft = bezier_q(A, (470, 780), P1, 60) + bezier_q(P1, (640, 420), T, 60)
    d.line(shaft, fill=(214, 228, 244, 255), width=24, joint="curve")
    d.ellipse([380, 844, 404, 868], fill=(214, 228, 244, 255))  # срез очина

    return img


master = make_master()
master.save("_icon_preview.png")

ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
master.save("icon.ico", format="ICO", sizes=ico_sizes)
print("OK: icon.ico + _icon_preview.png")
