// Copyright 2026 Jaakko Lipponen
// SPDX-License-Identifier: GPL-2.0-or-later

#include "fi_keys.h"
#include "keycodes.h"
#include "keymap_finnish.h"
#include "os_detection.h"

#ifndef ALT_TAB_TIMEOUT
#    define ALT_TAB_TIMEOUT 1000
#endif
#ifndef NUMLOCK_CHECK_DELAY
#    define NUMLOCK_CHECK_DELAY 50
#endif

user_config_t user_config;

void user_config_load(void) {
    user_config.raw = eeconfig_read_user();
}

void user_config_save(void) {
    eeconfig_update_user(user_config.raw);
}

void eeconfig_init_user(void) {
    user_config.raw = 0;
    user_config_save();
}

bool os_is_windows(void) {
    switch (user_config.os_mode) {
        case OSM_WINDOWS:
            return true;
        case OSM_LINUX:
            return false;
        default: {
            // Unknown hosts get the Windows variants.
            os_variant_t os = detected_host_os();
            return os != OS_LINUX && os != OS_MACOS && os != OS_IOS;
        }
    }
}

// Run fn with all modifiers released, then restore them.
static void tap_clean(void (*fn)(void)) {
    const uint8_t mods = get_mods();
    const uint8_t weak = get_weak_mods();
    const uint8_t osm  = get_oneshot_mods();
    clear_mods();
    clear_weak_mods();
    clear_oneshot_mods();
    send_keyboard_report();
    fn();
    set_mods(mods);
    set_weak_mods(weak);
    set_oneshot_mods(osm);
    send_keyboard_report();
}

// Literal dead keys: dead key followed by Space types the bare character on
// both Windows and Linux Finnish layouts.
static uint16_t dead_key;
static void     tap_dead_literal(void) {
    tap_code16(dead_key);
    tap_code(KC_SPC);
}

// Windows Alt+numpad code, e.g. "0150" for an en dash. Needs NumLock on, so it
// is switched on for the duration if needed.
static const char *alt_code;
static void        tap_alt_code(void) {
    const bool numlock = host_keyboard_led_state().num_lock;
    if (!numlock) {
        tap_code(KC_NUM);
    }
    register_code(KC_LALT);
    for (const char *p = alt_code; *p; ++p) {
        tap_code(*p == '0' ? KC_P0 : KC_P1 + (*p - '1'));
    }
    unregister_code(KC_LALT);
    if (!numlock) {
        tap_code(KC_NUM);
    }
}

static uint16_t linux_combo;
static void     tap_linux_combo(void) {
    tap_code16(linux_combo);
}

// Linux Finnish (kotoistus) has these on AltGr; Windows needs Alt codes.
static void send_typography(uint16_t linux, const char *windows) {
    if (os_is_windows()) {
        alt_code = windows;
        tap_clean(tap_alt_code);
    } else {
        linux_combo = linux;
        tap_clean(tap_linux_combo);
    }
}

static bool     alt_tab_active = false;
static uint16_t alt_tab_timer  = 0;

static void alt_tab_release(void) {
    if (alt_tab_active) {
        unregister_code(KC_LALT);
        alt_tab_active = false;
    }
}

static uint16_t desktop_switch(bool right) {
    const uint16_t arrow = right ? KC_RGHT : KC_LEFT;
#ifdef DESKTOP_GNOME
    if (!os_is_windows()) {
        return LCTL(LALT(arrow));
    }
#endif
    // Windows and KDE Plasma.
    return LCTL(LGUI(arrow));
}

bool process_fi_keys(uint16_t keycode, keyrecord_t *record) {
    if (keycode == ALT_TAB) {
        if (record->event.pressed) {
            if (!alt_tab_active) {
                alt_tab_active = true;
                register_code(KC_LALT);
            }
            alt_tab_timer = timer_read();
            register_code(KC_TAB);
        } else {
            unregister_code(KC_TAB);
        }
        return false;
    }

    if (!record->event.pressed) {
        return true;
    }

    switch (keycode) {
        case GRV_LIT:
            dead_key = FI_GRV;
            tap_clean(tap_dead_literal);
            return false;
        case CIRC_LIT:
            dead_key = FI_CIRC;
            tap_clean(tap_dead_literal);
            return false;
        case TILD_LIT:
            dead_key = FI_TILD;
            tap_clean(tap_dead_literal);
            return false;

        case TY_NDSH: // – AltGr+-
            send_typography(RALT(KC_SLSH), "0150");
            return false;
        case TY_MDSH: // — AltGr+Shift+M
            send_typography(RALT(RSFT(KC_M)), "0151");
            return false;
        case TY_RDQU: // ” AltGr+Shift+2
            send_typography(RALT(RSFT(KC_2)), "0148");
            return false;
        case TY_RSQU: // ’ AltGr+,
            send_typography(RALT(KC_COMM), "0146");
            return false;
        case TY_DEG: // ° AltGr+Shift+0
            send_typography(RALT(RSFT(KC_0)), "0176");
            return false;

        case OS_REDO:
            tap_code16(os_is_windows() ? LCTL(KC_Y) : LCTL(LSFT(KC_Z)));
            return false;
        case OS_SHOT:
            tap_code16(os_is_windows() ? LGUI(LSFT(KC_S)) : KC_PSCR);
            return false;
        case OS_DESKL:
            tap_code16(desktop_switch(false));
            return false;
        case OS_DESKR:
            tap_code16(desktop_switch(true));
            return false;
        case OS_MODE:
            user_config.os_mode = (user_config.os_mode + 1) % 3;
            user_config_save();
            return false;
    }
    return true;
}

static uint32_t numlock_check(uint32_t trigger_time, void *cb_arg) {
    if (IS_LAYER_ON(_NUM) && !host_keyboard_led_state().num_lock) {
        tap_code(KC_NUM);
    }
    return 0;
}

layer_state_t fi_keys_layer_state(layer_state_t state) {
    static bool num_was_on = false;
    const bool  num_on     = layer_state_cmp(state, _NUM);
    // Keypad keys act as arrows with NumLock off; make sure it is on. Checked
    // a little later so a quick NUM on/off does not toggle NumLock twice.
    if (num_on && !num_was_on && is_keyboard_master()) {
        defer_exec(NUMLOCK_CHECK_DELAY, numlock_check, NULL);
    }
    num_was_on = num_on;

    // Leaving NAV finishes an Alt-Tab chain immediately.
    if (!layer_state_cmp(state, _NAV)) {
        alt_tab_release();
    }
    return state;
}

void fi_keys_housekeeping(void) {
    if (alt_tab_active && timer_elapsed(alt_tab_timer) > ALT_TAB_TIMEOUT) {
        alt_tab_release();
    }
}

// Finnish Caps Word: Ö Ä Å are letters, "-" ends the word (EU-maa) and "_"
// continues it. KC_MINS is "+" on Finnish and must never be shifted ("?").
bool caps_word_press_user(uint16_t keycode) {
    switch (keycode) {
        case KC_A ... KC_Z:
        case FI_ODIA:
        case FI_ADIA:
        case FI_ARNG:
            add_weak_mods(MOD_BIT(KC_LSFT));
            return true;

        case KC_1 ... KC_0:
        case KC_P1 ... KC_P0:
        case KC_BSPC:
        case KC_DEL:
        case FI_UNDS:
            return true;

        default:
            return false;
    }
}

// Ctrl/Esc: any other key pressed while it is down makes it Ctrl at once, so
// quick Ctrl+C is never typed as Esc, c.
bool get_hold_on_other_key_press(uint16_t keycode, keyrecord_t *record) {
    return keycode == CTL_ESC;
}
