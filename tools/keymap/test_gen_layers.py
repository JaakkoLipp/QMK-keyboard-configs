"""Tests for tools/keymap/gen_layers.py (need a qmk_firmware checkout)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_layers  # noqa: E402


@pytest.fixture(scope="module")
def generated():
    try:
        qmk = gen_layers.find_qmk(os.environ.get("QMK_HOME"))
    except SystemExit:
        pytest.skip("no qmk_firmware checkout")
    return gen_layers.build(qmk)


def test_five_layers_of_sixty_keys(generated):
    layers, _ = generated
    assert [layer["name"] for layer in layers["layers"]] == ["BASE", "NUM", "SYM", "NAV", "FUN"]
    assert len(layers["layout"]) == 60
    for layer in layers["layers"]:
        assert len(layer["codes"]) == 60


def test_every_key_has_a_real_legend(generated):
    layers, keycodes = generated
    decoder = gen_layers.Decoder(keycodes, [layer["name"] for layer in layers["layers"]])
    for layer in layers["layers"]:
        for code in layer["codes"]:
            if code in (0, 1):
                continue
            key = decoder.decode(code)
            assert key.legend and key.legend != f"{code:04X}", (layer["name"], hex(code))


def test_sym_brackets_are_mirrored(generated):
    layers, keycodes = generated
    decoder = gen_layers.Decoder(keycodes)
    sym = next(layer for layer in layers["layers"] if layer["name"] == "SYM")
    legends = [decoder.decode(c).legend for c in sym["codes"]]
    row = legends[24:36]  # home row: 6 left keys, then right keys inner -> outer
    assert row[2:5] == ["{", "(", "["]
    assert row[7:10] == ["]", ")", "}"]


def test_committed_data_is_up_to_date(generated):
    layers, keycodes = generated
    data = gen_layers.OVERLAY_DATA
    assert json.loads((data / "layers.json").read_text(encoding="utf-8")) == layers, "run tools/keymap/gen_layers.py"
    assert json.loads((data / "keycodes.json").read_text(encoding="utf-8")) == keycodes, "run tools/keymap/gen_layers.py"
