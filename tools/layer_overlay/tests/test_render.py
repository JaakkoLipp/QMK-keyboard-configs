import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    import PySide6.QtGui  # noqa: F401
except ImportError as exc:  # PySide6 or its system libraries missing
    pytest.skip(f"Qt not available: {exc}", allow_module_level=True)

from layer_overlay.__main__ import render_demo
from layer_overlay.render import KeymapData


def test_demo_renders_every_layer(tmp_path):
    render_demo(tmp_path)
    data = KeymapData.bundled()
    for name in data.names:
        assert (tmp_path / f"overlay_{name.lower()}.png").stat().st_size > 2000
    assert (tmp_path / "overlay_sheet.png").exists()


def test_live_keymap_mapping_and_held_keys():
    data = KeymapData.bundled()
    rows, cols = data.matrix_size
    matrix = []
    for layer in data.codes:
        flat = [0] * (rows * cols)
        for k, code in zip(data.layout, layer):
            flat[k["matrix"][0] * cols + k["matrix"][1]] = code
        matrix.append(flat)
    live = data.with_live_keymap(matrix)
    assert not live.differs_from(data)
    sym = data.names.index("SYM")
    assert len(data.held_positions(sym)) == 1  # the SYM thumb key on BASE
