from layer_overlay.keycodes import LAYER, MOD, Decoder

NAMES = ["BASE", "NUM", "SYM", "NAV", "FUN"]


def test_finnish_shifted_and_altgr():
    d = Decoder(layer_names=NAMES)
    assert d.decode(0x0225).legend == "("  # S(KC_8)
    assert d.decode(0x1424).legend == "{"  # ALGR(KC_7)
    assert d.decode(0x0033).legend == "Ö"  # KC_SCLN on a Finnish layout
    assert d.decode(0x002E).sub == "dead"  # ´ (KC_EQL)


def test_layer_and_mod_tap_keys():
    d = Decoder(layer_names=NAMES)
    nav = d.decode(0x5223)  # MO(3)
    assert (nav.legend, nav.category, nav.layer) == ("NAV", LAYER, 3)
    num = d.decode(0x5261)  # TG(1)
    assert (num.legend, num.sub) == ("NUM", "toggle")
    esc = d.decode(0x2129)  # LCTL_T(KC_ESC)
    assert esc.legend == "Esc" and esc.category == MOD


def test_unknown_codes_still_decode():
    d = Decoder(layer_names=NAMES)
    key = d.decode(0x0A04)  # LGUI(LSFT(KC_A)), not in the table
    assert key.legend == "A" and "GUI" in key.sub
    assert d.decode(0x7E5F).legend.startswith("U")  # unused QK_USER slot
