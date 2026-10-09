"""Draws the Sofle and its legends with QPainter (used by every window)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from typing import Any

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen

from . import keycodes as kc

CATEGORY_FILL = {
    kc.NONE: None,
    kc.ALPHA: "#374151",
    kc.SYMBOL: "#0e7490",
    kc.DIGIT: "#52525b",
    kc.NAV: "#15803d",
    kc.EDIT: "#1d4ed8",
    kc.MOD: "#c2410c",
    kc.LAYER: "#a16207",
    kc.SYSTEM: "#7e22ce",
    kc.DANGER: "#b91c1c",
}
BACKGROUND = QColor(17, 20, 28, 232)
TEXT = QColor("#f8fafc")
SUBTEXT = QColor(248, 250, 252, 170)
EMPTY_BORDER = QColor(255, 255, 255, 40)


@dataclass
class KeymapData:
    layout: list[dict[str, Any]]
    names: list[str]
    colors: list[str]
    codes: list[list[int]]  # [layer][layout index]
    decoder: kc.Decoder
    live: bool = False  # codes came from the keyboard (VIA) instead of keymap.c

    @classmethod
    def bundled(cls) -> KeymapData:
        text = resources.files("layer_overlay").joinpath("data/layers.json").read_text(encoding="utf-8")
        data = json.loads(text)
        names = [layer["name"] for layer in data["layers"]]
        return cls(
            layout=data["layout"],
            names=names,
            colors=[layer["color"] for layer in data["layers"]],
            codes=[layer["codes"] for layer in data["layers"]],
            decoder=kc.Decoder(layer_names=names),
        )

    @property
    def matrix_size(self) -> tuple[int, int]:
        rows = max(k["matrix"][0] for k in self.layout) + 1
        cols = max(k["matrix"][1] for k in self.layout) + 1
        return rows, cols

    def with_live_keymap(self, matrix_codes: list[list[int]]) -> KeymapData:
        """Use codes read from the keyboard ([layer][row * cols + col])."""
        _, cols = self.matrix_size
        layers = []
        for layer in range(min(len(matrix_codes), len(self.names))):
            layers.append([matrix_codes[layer][k["matrix"][0] * cols + k["matrix"][1]] for k in self.layout])
        return KeymapData(self.layout, self.names, self.colors, layers, self.decoder, live=True)

    def differs_from(self, other: KeymapData) -> bool:
        return self.codes != other.codes[: len(self.codes)]

    def keys(self, layer: int) -> list[kc.Key]:
        return [self.decoder.decode(code) for code in self.codes[layer]]

    def held_positions(self, layer: int) -> set[int]:
        """Keys on lower layers that switch to this layer."""
        held = set()
        for lower in range(layer):
            for pos, code in enumerate(self.codes[lower]):
                if self.decoder.decode(code).layer == layer:
                    held.add(pos)
        return held

    def color(self, layer: int) -> QColor:
        return QColor(self.colors[layer] if layer < len(self.colors) else "#888888")

    def aspect(self) -> float:
        w = max(k["x"] + k.get("w", 1) for k in self.layout)
        h = max(k["y"] + k.get("h", 1) for k in self.layout)
        return w / h


def paint_layer(
    p: QPainter,
    rect: QRectF,
    data: KeymapData,
    layer: int,
    title: str | None = None,
    locked: bool = False,
    background: bool = True,
) -> None:
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    if background:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(BACKGROUND)
        p.drawRoundedRect(rect, 18, 18)

    accent = data.color(layer)
    pad = rect.height() * 0.06
    title_h = rect.height() * 0.12
    title_font = QFont()
    title_font.setBold(True)
    title_font.setPixelSize(max(10, int(title_h * 0.7)))
    p.setFont(title_font)
    p.setPen(accent)
    label = title or data.names[layer]
    if locked:
        label += "  (locked)"
    if data.live:
        label += "  · live"
    p.drawText(QRectF(rect.left() + pad, rect.top() + pad * 0.6, rect.width(), title_h), Qt.AlignmentFlag.AlignLeft, label)

    area = QRectF(rect.left() + pad, rect.top() + pad + title_h, rect.width() - 2 * pad, rect.height() - 2 * pad - title_h)
    units_w = max(k["x"] + k.get("w", 1) for k in data.layout)
    units_h = max(k["y"] + k.get("h", 1) for k in data.layout)
    unit = min(area.width() / units_w, area.height() / units_h)
    ox = area.left() + (area.width() - unit * units_w) / 2
    oy = area.top() + (area.height() - unit * units_h) / 2

    keys = data.keys(layer)
    held = data.held_positions(layer)
    legend_font = QFont()
    legend_font.setPixelSize(max(8, int(unit * 0.34)))
    sub_font = QFont()
    sub_font.setPixelSize(max(7, int(unit * 0.2)))
    inset = unit * 0.06

    for pos, (k, key) in enumerate(zip(data.layout, keys)):
        r = QRectF(ox + k["x"] * unit + inset, oy + k["y"] * unit + inset, k.get("w", 1) * unit - 2 * inset, k.get("h", 1) * unit - 2 * inset)
        empty = key.category == kc.NONE and pos not in held
        if pos in held:
            p.setBrush(accent)
            p.setPen(Qt.PenStyle.NoPen)
        elif empty:
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(EMPTY_BORDER, 1))
        else:
            p.setBrush(QColor(CATEGORY_FILL.get(key.category) or "#374151"))
            p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(r, unit * 0.12, unit * 0.12)
        if empty:
            continue
        legend = data.names[layer] if pos in held else key.legend
        sub = "held" if pos in held else key.sub
        p.setPen(TEXT)
        p.setFont(legend_font)
        main = QRectF(r.left(), r.top(), r.width(), r.height() * (0.72 if sub else 1.0))
        p.drawText(main, Qt.AlignmentFlag.AlignCenter, legend)
        if sub:
            p.setPen(SUBTEXT)
            p.setFont(sub_font)
            p.drawText(QRectF(r.left(), r.top() + r.height() * 0.62, r.width(), r.height() * 0.36), Qt.AlignmentFlag.AlignCenter, sub)
    p.restore()


def paint_sheet(p: QPainter, rect: QRectF, data: KeymapData) -> None:
    """All layers stacked vertically (cheat sheet)."""
    count = len(data.codes)
    gap = 10
    h = (rect.height() - gap * (count - 1)) / count
    for layer in range(count):
        paint_layer(p, QRectF(rect.left(), rect.top() + layer * (h + gap), rect.width(), h), data, layer)
