import datetime as dt

from layer_overlay import protocol as p


def test_parse_state_report():
    report = bytearray(32)
    report[0:3] = bytes([p.CMD, p.GET_STATE, p.VERSION])
    report[3:7] = (0b1101).to_bytes(4, "little")  # BASE, SYM, NAV on
    report[8] = 1 << 3  # NAV locked
    report[9] = 0x02  # shift
    report[10] = 0b0110  # num lock + caps word
    report[13] = 1
    report[14] = 7
    report[15] = 88
    st = p.parse_state(bytes(report))
    assert st.highest_layer == 3 and st.locked(3) and st.layer_on(2)
    assert st.num_lock and st.caps_word and not st.caps_lock
    assert st.windows and st.pin_count == 7 and st.wpm == 88


def test_parse_rejects_foreign_reports():
    assert p.parse_state(bytes([0x11]) + bytes(31)) is None


def test_set_time_and_claude_packing():
    t = p.set_time(dt.datetime(2026, 10, 9, 14, 5, 59))
    assert len(t) == 32 and t[:5] == bytes([p.CMD, p.SET_TIME, 14, 5, 59])
    c = p.set_claude(p.ClaudeStatus(p.ClaudeState.TOOL, "Bash", 300, 42, 2))
    assert c[:3] == bytes([p.CMD, p.SET_CLAUDE, 3])
    assert c[3:8] == b"Bash "
    assert int.from_bytes(c[8:10], "little") == 300 and c[10] == 42 and c[11] == 2
    assert p.set_claude(p.ClaudeStatus())[10] == 0xFF  # unknown context


def test_keymap_from_via_buffer():
    rows, cols = 2, 3
    codes = list(range(1, 2 * rows * cols + 1))
    buffer = b"".join(c.to_bytes(2, "big") for c in codes)
    layers = p.keymap_from_buffer(buffer, 2, rows, cols)
    assert layers[0] == codes[:6] and layers[1] == codes[6:]
