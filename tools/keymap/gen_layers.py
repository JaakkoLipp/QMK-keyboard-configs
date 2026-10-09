#!/usr/bin/env python3
"""Generate layer data and images from the Sofle keymap.

Reads keyboards/mechboards/sofle/pro/keymaps/jaakkolipp/keymap.c (plus its
features/keycodes.h), evaluates every key to its 16-bit QMK keycode and writes:

  tools/layer_overlay/layer_overlay/data/layers.json    layout + per-layer codes
  tools/layer_overlay/layer_overlay/data/keycodes.json  code -> legend tables
  docs/layers/keymap.yaml                               keymap-drawer input
  docs/layers/*.svg                                     (with --draw)

Needs a qmk_firmware checkout for the keycode spec, keymap_finnish.h and the
keyboard's physical layout: --qmk, $QMK_HOME, `qmk env QMK_FIRMWARE` or
~/qmk_firmware. The Python packages from `pip install qmk` must be available.

    python tools/keymap/gen_layers.py --draw
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1].parent
KEYMAP_DIR = ROOT / "keyboards/mechboards/sofle/pro/keymaps/jaakkolipp"
KEYMAP_C = KEYMAP_DIR / "keymap.c"
KEYCODES_H = KEYMAP_DIR / "features/keycodes.h"
OVERLAY_DATA = ROOT / "tools/layer_overlay/layer_overlay/data"
DOCS = ROOT / "docs/layers"
INFO_JSON = Path(__file__).resolve().parent / "sofle_pro_info.json"
DRAWER_CONFIG = Path(__file__).resolve().parent / "drawer_config.yaml"
KEYBOARD = "mechboards/sofle/pro"

sys.path.insert(0, str(ROOT / "tools/layer_overlay"))
from layer_overlay.keycodes import Decoder  # noqa: E402

LAYER_COLORS = {
    "BASE": "#8a8f98",
    "NUM": "#3b82f6",
    "SYM": "#06b6d4",
    "NAV": "#22c55e",
    "FUN": "#a855f7",
}

# Short legends for plain QMK keycodes (by canonical or alias name).
NAME_LEGENDS: dict[str, str | list[str]] = {
    "KC_ESC": "Esc", "KC_TAB": "Tab", "KC_BSPC": "Bksp", "KC_ENT": "Enter", "KC_SPC": "Space",
    "KC_DEL": "Del", "KC_INS": "Ins", "KC_HOME": "Home", "KC_END": "End", "KC_PGUP": "PgUp", "KC_PGDN": "PgDn",
    "KC_LEFT": "←", "KC_RGHT": "→", "KC_UP": "↑", "KC_DOWN": "↓",
    "KC_LSFT": "Shift", "KC_RSFT": "Shift", "KC_LCTL": "Ctrl", "KC_RCTL": "Ctrl",
    "KC_LALT": "Alt", "KC_RALT": "AltGr", "KC_LGUI": "GUI", "KC_RGUI": "GUI",
    "KC_CAPS": "Caps", "KC_NUM": "NumLk", "KC_SCRL": "ScrLk", "KC_PAUS": "Pause", "KC_PSCR": "PrtSc", "KC_APP": "Menu",
    "KC_MUTE": "Mute", "KC_VOLU": "Vol+", "KC_VOLD": "Vol-", "KC_MPRV": "Prev", "KC_MNXT": "Next", "KC_MPLY": "Play",
    "KC_CALC": "Calc",
    "KC_PSLS": "/", "KC_PAST": "*", "KC_PMNS": "-", "KC_PPLS": "+", "KC_PENT": "Enter", "KC_PDOT": [",", "kp"],
    "QK_BOOT": "Boot", "QK_REBOOT": "Reboot", "EE_CLR": "EEClr", "QK_LLCK": "Lock", "CW_TOGG": ["Caps", "word"],
    "RM_TOGG": ["RGB", "on/off"], "RM_NEXT": ["RGB", "mode+"], "RM_PREV": ["RGB", "mode-"],
    "RM_VALU": ["RGB", "bri+"], "RM_VALD": ["RGB", "bri-"], "RM_HUEU": ["RGB", "hue+"], "RM_HUED": ["RGB", "hue-"],
    "MS_UP": "M↑", "MS_DOWN": "M↓", "MS_LEFT": "M←", "MS_RGHT": "M→",
    "MS_BTN1": "Click", "MS_BTN2": "RClick", "MS_BTN3": "MClick", "MS_WHLU": "Whl↑", "MS_WHLD": "Whl↓",
    **{f"KC_P{i}": str(i) for i in range(10)},
    **{f"KC_F{i}": f"F{i}" for i in range(1, 25)},
}  # fmt: skip

# Legends for key expressions as written in keymap.c.
EXPR_LEGENDS: dict[str, str | list[str]] = {
    "C(KC_Z)": "Undo", "C(KC_X)": "Cut", "C(KC_C)": "Copy", "C(KC_V)": "Paste",
    "C(KC_LEFT)": ["Word", "←"], "C(KC_RGHT)": ["Word", "→"],
    "C(KC_PGUP)": ["Tab", "←"], "C(KC_PGDN)": ["Tab", "→"],
    "C(KC_PMNS)": ["Zoom", "-"], "C(KC_PPLS)": ["Zoom", "+"],
    "A(KC_LEFT)": "Back", "A(KC_RGHT)": "Fwd", "G(KC_L)": ["Lock", "screen"],
    "CTL_ESC": ["Esc", "Ctrl"], "FI_EURE": "€",
}  # fmt: skip

CUSTOM_CATEGORIES = {
    "GRV_LIT": "symbol", "CIRC_LIT": "symbol", "TILD_LIT": "symbol",
    "TY_NDSH": "symbol", "TY_MDSH": "symbol", "TY_RDQU": "symbol", "TY_RSQU": "symbol", "TY_DEG": "symbol",
    "OS_REDO": "edit", "OS_SHOT": "system", "OS_DESKL": "nav", "OS_DESKR": "nav", "ALT_TAB": "nav",
    "OS_MODE": "system", "OLED_TOG": "system", "OVL_PIN": "system", "CLAUDE_ACK": "system",
}  # fmt: skip

FINNISH_COMMENT_FIXES = {"(backslash)": "\\"}


# --- QMK data -----------------------------------------------------------------


def find_qmk(explicit: str | None) -> Path:
    candidates = [explicit, os.environ.get("QMK_HOME")]
    if shutil.which("qmk"):
        out = subprocess.run(["qmk", "env", "QMK_FIRMWARE"], capture_output=True, text=True, check=False)
        candidates.append(out.stdout.strip())
    candidates.append(str(Path.home() / "qmk_firmware"))
    for c in candidates:
        if c and (Path(c) / "data/constants/keycodes").is_dir():
            return Path(c).resolve()
    raise SystemExit("qmk_firmware checkout not found; pass --qmk /path/to/qmk_firmware")


def load_spec(qmk: Path) -> dict[str, Any]:
    sys.path.insert(0, str(qmk / "lib/python"))
    cwd = os.getcwd()
    os.chdir(qmk)
    try:
        from qmk.keycodes import load_spec as qmk_load_spec

        return qmk_load_spec("latest")
    finally:
        os.chdir(cwd)


def load_layout(qmk: Path) -> list[dict[str, Any]]:
    import hjson

    info = hjson.loads((qmk / "keyboards" / KEYBOARD / "keyboard.json").read_text())
    return [dict(k) for k in info["layouts"]["LAYOUT"]["layout"]]


# --- Expression evaluation ------------------------------------------------------


def build_namespace(spec: dict[str, Any]) -> dict[str, Any]:
    ns: dict[str, Any] = {}
    for code, entry in spec["keycodes"].items():
        value = int(code, 16)
        ns[entry["key"]] = value
        for alias in entry.get("aliases", []):
            ns[alias] = value
    for span, entry in spec["ranges"].items():
        ns[entry["define"]] = int(span.split("/")[0], 16)

    def mod(m: int) -> Callable[[int], int]:
        return lambda kc: (m << 8) | kc

    mods = {"LCTL": 0x01, "LSFT": 0x02, "LALT": 0x04, "LGUI": 0x08, "RCTL": 0x11, "RSFT": 0x12, "RALT": 0x14, "RGUI": 0x18}
    for name, m in mods.items():
        ns[name] = mod(m)
        ns[f"MOD_{name}"] = m
        ns[f"{name}_T"] = (lambda mm: lambda kc: 0x2000 | (mm << 8) | kc)(m)
    ns.update(C=ns["LCTL"], S=ns["LSFT"], A=ns["LALT"], G=ns["LGUI"], ALGR=ns["RALT"])
    ns.update(
        MO=lambda layer: 0x5220 | layer,
        TG=lambda layer: 0x5260 | layer,
        TO=lambda layer: 0x5200 | layer,
        OSL=lambda layer: 0x5280 | layer,
        TT=lambda layer: 0x52C0 | layer,
        LT=lambda layer, kc: 0x4000 | (layer << 8) | kc,
        MT=lambda m, kc: 0x2000 | (m << 8) | kc,
    )
    return ns


def evaluate(expr: str, ns: dict[str, Any]) -> int:
    return int(eval(expr, {"__builtins__": {}}, ns))  # noqa: S307 - our own keymap source


def parse_defines(text: str) -> list[tuple[str, str, str]]:
    """#define NAME EXPR // comment  ->  (name, expr, comment)"""
    out = []
    for m in re.finditer(r"^#define\s+(\w+)\s+([^/\n]+?)\s*(?://\s*(.*))?$", text, re.M):
        out.append((m.group(1), m.group(2).strip(), (m.group(3) or "").strip()))
    return out


def load_finnish(qmk: Path, ns: dict[str, Any]) -> dict[int, list[str]]:
    legends: dict[int, list[str]] = {}
    header = (qmk / "quantum/keymap_extras/keymap_finnish.h").read_text(encoding="utf-8")
    for name, expr, comment in parse_defines(header):
        if not name.startswith("FI_"):
            continue
        ns[name] = evaluate(expr, ns)
        if not comment:
            continue
        legend = FINNISH_COMMENT_FIXES.get(comment, comment.split(" ")[0])
        legends[ns[name]] = [legend, "dead"] if "(dead)" in comment else [legend]
    return legends


def load_custom(ns: dict[str, Any]) -> tuple[list[str], dict[int, list[str]], dict[int, str]]:
    text = KEYCODES_H.read_text(encoding="utf-8")
    layers_body = re.search(r"enum layers \{(.*?)\};", text, re.S).group(1)
    layer_names = re.findall(r"_(\w+)", layers_body)
    for i, name in enumerate(layer_names):
        ns[f"_{name}"] = i

    legends: dict[int, list[str]] = {}
    categories: dict[int, str] = {}
    body = re.search(r"enum custom_keycodes \{(.*?)\};", text, re.S).group(1)
    index = 0
    for m in re.finditer(r"^\s*(\w+)(?:\s*=\s*QK_USER)?\s*,\s*//\s*legend:\s*(\S+)", body, re.M):
        code = ns["QK_USER"] + index
        ns[m.group(1)] = code
        legends[code] = [m.group(2)]
        if m.group(1) in CUSTOM_CATEGORIES:
            categories[code] = CUSTOM_CATEGORIES[m.group(1)]
        index += 1
    for name, expr, _ in parse_defines(text):
        if name not in ("QMK_KEYBOARD_H",):
            ns[name] = evaluate(expr, ns)
    return layer_names, legends, categories


def split_args(body: str) -> list[str]:
    """Split a LAYOUT( ... ) body on top-level commas."""
    out, depth, cur = [], 0, []
    for ch in body:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            out.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    if "".join(cur).strip():
        out.append("".join(cur).strip())
    return out


def parse_keymap(ns: dict[str, Any]) -> dict[str, list[str]]:
    text = KEYMAP_C.read_text(encoding="utf-8")
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    layers: dict[str, list[str]] = {}
    for m in re.finditer(r"\[\s*(_\w+)\s*\]\s*=\s*LAYOUT\(", text):
        depth, i = 1, m.end()
        while depth:
            depth += {"(": 1, ")": -1}.get(text[i], 0)
            i += 1
        layers[m.group(1)[1:]] = split_args(text[m.end() : i - 1])
    return layers


# --- Outputs --------------------------------------------------------------------


def build(qmk: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    spec = load_spec(qmk)
    ns = build_namespace(spec)
    legends = load_finnish(qmk, ns)
    layer_names, custom_legends, categories = load_custom(ns)
    legends.update(custom_legends)

    for name, legend in NAME_LEGENDS.items():
        if name in ns:
            legends[ns[name]] = legend if isinstance(legend, list) else [legend]
    for expr, legend in EXPR_LEGENDS.items():
        legends[evaluate(expr, ns)] = legend if isinstance(legend, list) else [legend]

    names = {}
    for code, entry in spec["keycodes"].items():
        names[f"0x{int(code, 16):04X}"] = entry["key"]
    ranges = {}
    for span, entry in spec["ranges"].items():
        start, size = (int(x, 16) for x in span.lower().split("/"))
        ranges[entry["define"]] = [start, start + size]

    keycodes = {
        "qmk_spec_version": spec["version"],
        "names": names,
        "legends": {f"0x{c:04X}": v for c, v in sorted(legends.items())},
        "categories": {f"0x{c:04X}": v for c, v in sorted(categories.items())},
        "ranges": ranges,
    }

    keymap = parse_keymap(ns)
    layout = load_layout(qmk)
    layers = []
    for name in layer_names:
        tokens = keymap[name]
        if len(tokens) != len(layout):
            raise SystemExit(f"layer {name}: {len(tokens)} keys, layout has {len(layout)}")
        layers.append({"name": name, "color": LAYER_COLORS.get(name, "#888888"), "codes": [evaluate(t, ns) for t in tokens]})

    layers_json = {
        "keyboard": KEYBOARD,
        "layout": [
            {"x": k["x"], "y": k["y"], "w": k.get("w", 1), "h": k.get("h", 1), "matrix": k["matrix"]} for k in layout
        ],
        "layers": layers,
    }
    return layers_json, keycodes


def drawer_yaml(layers_json: dict[str, Any], keycodes: dict[str, Any]) -> str:
    names = [layer["name"] for layer in layers_json["layers"]]
    decoder = Decoder(keycodes, names)
    base = layers_json["layers"][0]["codes"]

    def held_positions(index: int) -> set[int]:
        """Keys that must be held to reach this layer (MO keys on lower layers)."""
        held = set()
        for lower in layers_json["layers"][:index]:
            for pos, code in enumerate(lower["codes"]):
                key = decoder.decode(code)
                if key.layer == index and key.sub in ("hold", "toggle"):
                    held.add(pos)
        return held

    def quote(s: str) -> str:
        return json.dumps(s, ensure_ascii=False)

    lines = [
        "# Generated by tools/keymap/gen_layers.py - do not edit.",
        f"layout: {{qmk_info_json: {quote(str(INFO_JSON.relative_to(ROOT)))}}}",
        "layers:",
    ]
    for index, layer in enumerate(layers_json["layers"]):
        held = held_positions(index)
        lines.append(f"  {layer['name']}:")
        for pos, code in enumerate(layer["codes"]):
            if pos in held:
                lines.append(f"    - {{t: {quote(names[index])}, type: held}}")
                continue
            if code == 0x0001:
                lines.append("    - {type: trans}" if index else "    - ''")
                continue
            if code == 0x0000:
                lines.append("    - ''")
                continue
            key = decoder.decode(code)
            entry = f"t: {quote(key.legend)}"
            if key.sub:
                entry += f", s: {quote(key.sub)}"
            if key.category in ("mod", "layer"):
                entry += ", type: mod"
            lines.append(f"    - {{{entry}}}")
    del base
    return "\n".join(lines) + "\n"


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def draw(yaml_path: Path, layer_names: list[str]) -> None:
    keymap = shutil.which("keymap")
    if not keymap:
        raise SystemExit("keymap-drawer not installed: pip install keymap-drawer")
    cfg = ["-c", str(DRAWER_CONFIG)] if DRAWER_CONFIG.exists() else []
    targets = {"all": []} | {name.lower(): ["-s", name] for name in layer_names}
    for target, select in targets.items():
        with open(DOCS / f"{target}.svg", "w", encoding="utf-8") as out:
            subprocess.run([keymap, *cfg, "draw", str(yaml_path), *select], check=True, stdout=out, cwd=ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--qmk", help="path to qmk_firmware")
    parser.add_argument("--draw", action="store_true", help="also render docs/layers/*.svg with keymap-drawer")
    args = parser.parse_args()

    qmk = find_qmk(args.qmk)
    layers_json, keycodes = build(qmk)
    write_json(OVERLAY_DATA / "layers.json", layers_json)
    write_json(OVERLAY_DATA / "keycodes.json", keycodes)
    write_json(INFO_JSON, {"keyboard_name": "Sofle Pro", "layouts": {"LAYOUT": {"layout": layers_json["layout"]}}})
    DOCS.mkdir(parents=True, exist_ok=True)
    yaml_path = DOCS / "keymap.yaml"
    yaml_path.write_text(drawer_yaml(layers_json, keycodes), encoding="utf-8")
    print(f"wrote {len(layers_json['layers'])} layers, {len(keycodes['legends'])} legends")
    if args.draw:
        draw(yaml_path, [layer["name"] for layer in layers_json["layers"]])
        print(f"drew {DOCS.relative_to(ROOT)}/*.svg")


if __name__ == "__main__":
    main()
