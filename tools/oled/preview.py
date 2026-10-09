#!/usr/bin/env python3
"""Render the keymap's OLED screens on a PC and save them as PNG files.

Compiles features/oled.c with small QMK stand-ins (tools/oled/sim), runs a set
of scenarios and writes docs/oled/*.png plus a combined overview, so OLED
changes can be checked without flashing the keyboard.

    python tools/oled/preview.py                    # needs gcc and a QMK checkout
    python tools/oled/preview.py --qmk ~/qmk_firmware

The QMK checkout is only used for the 6x8 font (drivers/oled/glcdfont.c). It is
found from --qmk, $QMK_HOME, `qmk env QMK_FIRMWARE`, or ~/qmk_firmware.
"""

from __future__ import annotations

import argparse
import os
import shutil
import struct
import subprocess
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FEATURES = ROOT / "keyboards/mechboards/sofle/pro/keymaps/jaakkolipp/features"
SIM = Path(__file__).resolve().parent / "sim"
OUT = ROOT / "docs/oled"

W, H = 32, 128
SCALE = 3
ON = (200, 230, 255)
OFF = (8, 10, 14)

# Layers: BASE=0 NUM=1 SYM=2 NAV=3 FUN=4 -> layer_state bitmask.
L = {"base": 0b1, "num": 0b11, "sym": 0b101, "nav": 0b1001, "fun": 0b11001}
SHIFT, CTRL, ALT, GUI = 0x02, 0x01, 0x04, 0x08

SCENARIOS: dict[str, list[str]] = {
    "left_base": ["side=left", f"layers={L['base']}", "wpm=0"],
    "left_sym_shift": ["side=left", f"layers={L['sym']}", f"mods={SHIFT}", "wpm=64", "caps_word=1"],
    "left_nav_locked": ["side=left", f"layers={L['nav']}", f"locked={1 << 3}", f"mods={CTRL | SHIFT}", "linux=1"],
    "left_num": ["side=left", f"layers={L['num']}", "numlock=1", "wpm=31"],
    "left_fun": ["side=left", f"layers={L['fun']}", f"mods={ALT}", "os_mode=1", "caps=1"],
    "right_sauna": ["side=right", "wpm=55", "clock=0942", "keys=12873", "time=0"],
    "right_loyly": ["side=right", "wpm=96", "clock=2115", "keys=48211", "time=400"],
    "right_think": ["side=right", "claude=2", "turn=47", "ctx=34", "clock=1408", "keys=5321", "time=300"],
    "right_tool": ["side=right", "claude=3", "tool=Bash", "turn=128", "ctx=61", "others=1", "clock=1409", "keys=5400"],
    "right_wait": ["side=right", "claude=4", "turn=312", "ctx=61", "clock=1411", "keys=5402", "time=500"],
    "right_done": ["side=right", "claude=5", "ctx=72", "clock=1415", "keys=5530"],
}


def find_qmk(explicit: str | None) -> Path:
    candidates = [explicit, os.environ.get("QMK_HOME")]
    if shutil.which("qmk"):
        try:
            out = subprocess.run(["qmk", "env", "QMK_FIRMWARE"], capture_output=True, text=True, check=False)
            candidates.append(out.stdout.strip())
        except OSError:
            pass
    candidates.append(str(Path.home() / "qmk_firmware"))
    for c in candidates:
        if c and (Path(c) / "drivers/oled/glcdfont.c").exists():
            return Path(c).resolve()
    raise SystemExit("QMK checkout not found; pass --qmk /path/to/qmk_firmware")


def build(qmk: Path, workdir: Path) -> Path:
    exe = workdir / "oled_sim"
    cmd = [
        "gcc", "-std=gnu11", "-O1", "-Wall", "-Werror",
        "-DQMK_KEYBOARD_H=\"qmk_stub.h\"",
        f"-DOLED_FONT_H=\"{qmk / 'drivers/oled/glcdfont.c'}\"",
        f"-I{SIM}", f"-I{FEATURES}",
        str(FEATURES / "oled.c"), str(SIM / "sim_main.c"),
        "-o", str(exe),
    ]  # fmt: skip
    subprocess.run(cmd, check=True)
    return exe


def render(exe: Path, args: list[str]) -> list[list[bool]]:
    out = subprocess.run([str(exe), *args], capture_output=True, text=True, check=True).stdout.strip()
    data = bytes.fromhex(out)
    return [[bool(data[x + (y // 8) * W] & (1 << (y % 8))) for x in range(W)] for y in range(H)]


def write_png(path: Path, pixels: list[list[tuple[int, int, int]]]) -> None:
    height, width = len(pixels), len(pixels[0])
    raw = b"".join(b"\x00" + b"".join(bytes(p) for p in row) for row in pixels)

    def chunk(tag: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    path.write_bytes(png)


def to_rgb(frame: list[list[bool]], scale: int) -> list[list[tuple[int, int, int]]]:
    rows = []
    for y in range(H * scale):
        rows.append([ON if frame[y // scale][x // scale] else OFF for x in range(W * scale)])
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--qmk", help="path to qmk_firmware")
    parser.add_argument("--ascii", action="store_true", help="print each screen as ASCII too")
    args = parser.parse_args()

    qmk = find_qmk(args.qmk)
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        exe = build(qmk, Path(tmp))
        frames = {name: render(exe, scenario) for name, scenario in SCENARIOS.items()}

    gap = 6 * SCALE
    sheet_w = len(frames) * (W * SCALE + gap) - gap
    sheet = [[(30, 32, 38)] * sheet_w for _ in range(H * SCALE)]
    for i, (name, frame) in enumerate(frames.items()):
        img = to_rgb(frame, SCALE)
        write_png(OUT / f"{name}.png", img)
        x0 = i * (W * SCALE + gap)
        for y, row in enumerate(img):
            sheet[y][x0 : x0 + W * SCALE] = row
        if args.ascii:
            print(name)
            print("\n".join("".join("#" if p else "." for p in row) for row in frame))
            print()
    write_png(OUT / "overview.png", sheet)
    print(f"wrote {len(frames)} screens + overview to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
