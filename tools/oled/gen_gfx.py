#!/usr/bin/env python3
"""Generate the OLED bitmaps used by the Sofle keymap.

Shapes are drawn procedurally or from small ASCII-art strings and written to
keyboards/mechboards/sofle/pro/keymaps/jaakkolipp/features/oled_gfx.h.

Bitmap format: {width, height, rows...}; each row is ceil(width / 8) bytes,
most significant bit = leftmost pixel.

    python tools/oled/gen_gfx.py            # write the header
    python tools/oled/gen_gfx.py --preview  # also print every bitmap
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "keyboards/mechboards/sofle/pro/keymaps/jaakkolipp/features/oled_gfx.h"


class Canvas:
    def __init__(self, w: int, h: int) -> None:
        self.w, self.h = w, h
        self.px = [[False] * w for _ in range(h)]

    def set(self, x: int, y: int, on: bool = True) -> None:
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y][x] = on

    def rect(self, x: int, y: int, w: int, h: int, on: bool = True) -> None:
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.set(xx, yy, on)

    def outline(self, x: int, y: int, w: int, h: int) -> None:
        self.rect(x, y, w, 1)
        self.rect(x, y + h - 1, w, 1)
        self.rect(x, y, 1, h)
        self.rect(x + w - 1, y, 1, h)

    def art(self, x: int, y: int, rows: list[str]) -> None:
        for dy, row in enumerate(rows):
            for dx, ch in enumerate(row):
                if ch == "#":
                    self.set(x + dx, y + dy)

    def line(self, x0: float, y0: float, x1: float, y1: float, thick: float = 1.0) -> None:
        steps = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1
        r = thick / 2
        for i in range(steps + 1):
            t = i / steps
            cx, cy = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            for yy in range(int(cy - r - 1), int(cy + r + 2)):
                for xx in range(int(cx - r - 1), int(cx + r + 2)):
                    if (xx + 0.5 - cx) ** 2 + (yy + 0.5 - cy) ** 2 <= r * r:
                        self.set(xx, yy)

    def rows(self) -> list[str]:
        return ["".join("#" if p else "." for p in row) for row in self.px]


def from_art(rows: list[str]) -> Canvas:
    c = Canvas(max(len(r) for r in rows), len(rows))
    c.art(0, 0, rows)
    return c


def mirror(c: Canvas) -> Canvas:
    m = Canvas(c.w, c.h)
    for y in range(c.h):
        for x in range(c.w):
            m.px[y][c.w - 1 - x] = c.px[y][x]
    return m


# --- Layer icons -------------------------------------------------------------


def icon_base() -> Canvas:
    """A small keyboard."""
    c = Canvas(30, 20)
    c.outline(0, 0, 30, 20)
    c.set(0, 0, False), c.set(29, 0, False), c.set(0, 19, False), c.set(29, 19, False)
    for row, offset in ((3, 3), (7, 5), (11, 3)):
        for i in range(6):
            c.rect(offset + i * 4, row, 3, 3)
    c.rect(8, 15, 14, 2)  # space bar
    return c


def icon_num() -> Canvas:
    """A numpad: 3x3 keys plus a wide zero."""
    c = Canvas(26, 30)
    for r in range(3):
        for k in range(3):
            c.outline(k * 9, r * 7, 8, 6)
    c.outline(0, 21, 17, 6)
    c.outline(18, 21, 8, 6)
    return c


BRACE = [
    "....####",
    "...##...",
    "..##....",
    "..##....",
    "..##....",
    "..##....",
    "..##....",
    "..##....",
    ".##.....",
    "##......",
    ".##.....",
    "..##....",
    "..##....",
    "..##....",
    "..##....",
    "..##....",
    "..##....",
    "...##...",
    "....####",
]


def icon_sym() -> Canvas:
    """Curly braces with a dot between them: { · }."""
    c = Canvas(28, len(BRACE))
    c.art(0, 0, BRACE)
    c.art(20, 0, mirror(from_art(BRACE)).rows())
    c.rect(13, 8, 2, 2)
    return c


def icon_nav() -> Canvas:
    """Four arrows around a centre dot."""
    n = 29
    c = Canvas(n, n)
    m = n // 2
    for i in range(6):  # arrow heads
        c.rect(m - i, i, 2 * i + 1, 1)  # up
        c.rect(m - i, n - 1 - i, 2 * i + 1, 1)  # down
        c.rect(i, m - i, 1, 2 * i + 1)  # left
        c.rect(n - 1 - i, m - i, 1, 2 * i + 1)  # right
    c.rect(m - 1, 6, 3, 6)
    c.rect(m - 1, n - 12, 3, 6)
    c.rect(6, m - 1, 6, 3)
    c.rect(n - 12, m - 1, 6, 3)
    c.rect(m - 1, m - 1, 3, 3)
    return c


def icon_fun() -> Canvas:
    """A gear."""
    n = 29
    c = Canvas(n, n)
    m = (n - 1) / 2
    for y in range(n):
        for x in range(n):
            dx, dy = x - m, y - m
            r = math.hypot(dx, dy)
            a = (math.atan2(dy, dx) + math.pi) / (2 * math.pi) * 8
            tooth = ((a + 0.25) % 1.0) < 0.5
            outer = 13.6 if tooth else 10.2
            if 4.6 < r <= outer:
                c.set(x, y)
    return c


# --- Claude panel ------------------------------------------------------------


def draw_sparkle(c: Canvas, cx: float, cy: float, radius: float) -> None:
    """Four-point star: |dx|^p + |dy|^p <= R^p with p < 1."""
    p = 0.5
    for y in range(c.h):
        for x in range(c.w):
            if abs(x - cx) ** p + abs(y - cy) ** p <= radius**p:
                c.set(x, y)


def sparkle(frame: int, size: int = 31) -> Canvas:
    """Twinkle animation: the big star pulses while small ones blink."""
    c = Canvas(size, size)
    m = (size - 1) / 2
    big = (15, 12, 10)[frame]
    draw_sparkle(c, m, m, big)
    if frame >= 1:
        draw_sparkle(c, 25, 5, 4.5)
    if frame == 2:
        draw_sparkle(c, 5, 25, 4.5)
    return c


def icon_check() -> Canvas:
    c = Canvas(26, 22)
    c.line(2, 12, 9, 19, 3.5)
    c.line(9, 19, 23, 3, 3.5)
    return c


def icon_cross() -> Canvas:
    c = Canvas(22, 22)
    c.line(3, 3, 18, 18, 3.5)
    c.line(18, 3, 3, 18, 3.5)
    return c


# --- Modifiers (13 px wide) -------------------------------------------------

MOD_SHIFT = [
    "......#......",
    ".....#.#.....",
    "....#...#....",
    "...#.....#...",
    "..#.......#..",
    ".#.........#.",
    "####.....####",
    "...#.....#...",
    "...#.....#...",
    "...#######...",
]
MOD_CTRL = [
    "......#......",
    ".....###.....",
    "....##.##....",
    "...##...##...",
    "..##.....##..",
    ".##.......##.",
    "##.........##",
]
MOD_ALT = [
    "####....#####",
    "...#.........",
    "....#........",
    ".....#.......",
    "......#......",
    ".......######",
]

# --- Sauna -------------------------------------------------------------------


def thermometer() -> Canvas:
    """Tube outline 9x52 above a filled bulb; mercury is drawn at runtime."""
    c = Canvas(13, 64)
    c.outline(2, 0, 9, 53)
    c.set(2, 0, False), c.set(10, 0, False)
    for y in range(64):
        for x in range(13):
            if math.hypot(x - 6, y - 57) <= 6.2:
                c.set(x, y)
    c.rect(3, 50, 7, 4, False)
    c.rect(4, 50, 5, 7)  # neck into the bulb
    return c


def steam(phase: int) -> Canvas:
    """Three wavy wisps rising; phase 0..2 shifts the wave."""
    c = Canvas(30, 14)
    for i, x0 in enumerate((5, 15, 25)):
        for y in range(14):
            shift = phase * 2.1 + i * 1.7
            x = x0 + 2.2 * math.sin((y + shift) / 2.2)
            if (y + phase + i) % 7 < 5:  # gaps make it look like puffs
                c.set(int(round(x)), 13 - y)
    return c


BITMAPS: dict[str, Canvas] = {}


def build() -> None:
    BITMAPS.update(
        {
            "icon_base": icon_base(),
            "icon_num": icon_num(),
            "icon_sym": icon_sym(),
            "icon_nav": icon_nav(),
            "icon_fun": icon_fun(),
            "sparkle_0": sparkle(0),
            "sparkle_1": sparkle(1),
            "sparkle_2": sparkle(2),
            "icon_check": icon_check(),
            "icon_cross": icon_cross(),
            "mod_shift": from_art(MOD_SHIFT),
            "mod_ctrl": from_art(MOD_CTRL),
            "mod_alt": from_art(MOD_ALT),
            "thermometer": thermometer(),
            "steam_0": steam(0),
            "steam_1": steam(1),
            "steam_2": steam(2),
        }
    )


def encode(c: Canvas) -> list[int]:
    data = [c.w, c.h]
    for row in c.px:
        for byte in range(0, c.w, 8):
            v = 0
            for bit in range(8):
                x = byte + bit
                if x < c.w and row[x]:
                    v |= 0x80 >> bit
            data.append(v)
    return data


def render_header() -> str:
    out = [
        "// Copyright 2026 Jaakko Lipponen",
        "// SPDX-License-Identifier: GPL-2.0-or-later",
        "//",
        "// Generated by tools/oled/gen_gfx.py - edit that script, not this file.",
        "// Format: {width, height, rows...}, MSB = leftmost pixel.",
        "#pragma once",
        "",
        "#include <stdint.h>",
        '#include "progmem.h"',
        "",
    ]
    for name, canvas in BITMAPS.items():
        data = encode(canvas)
        out.append(f"// {name}: {canvas.w}x{canvas.h}")
        out.append(f"static const uint8_t PROGMEM gfx_{name}[] = {{")
        for i in range(0, len(data), 16):
            out.append("    " + ", ".join(f"0x{b:02X}" for b in data[i : i + 16]) + ",")
        out.append("};")
        out.append("")
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true", help="print every bitmap as ASCII")
    parser.add_argument("--check", action="store_true", help="fail if the header is out of date")
    args = parser.parse_args()
    build()
    if args.preview:
        for name, canvas in BITMAPS.items():
            print(f"{name} ({canvas.w}x{canvas.h})")
            print("\n".join(canvas.rows()))
            print()
    header = render_header()
    if args.check:
        if not OUT.exists() or OUT.read_text() != header:
            raise SystemExit(f"{OUT} is out of date; run tools/oled/gen_gfx.py")
        return
    OUT.write_text(header)
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
