// Copyright 2026 Jaakko Lipponen
// SPDX-License-Identifier: GPL-2.0-or-later
//
// Per-key RGB as a layer guide: on any layer above BASE only the keys that do
// something on that layer light up, coloured by what they do. The underglow
// takes the layer colour. Caps Lock / Caps Word light the Shift keys, and a
// Claude Code session waiting for permission makes the underglow breathe
// amber (even after the idle timeout). Normal RGB effects run on BASE.

#include QMK_KEYBOARD_H
#include "lib/lib8tion/lib8tion.h"
#include "keycodes.h"
#include "fi_keys.h"
#include "shared.h"

#ifndef RGB_IDLE_TIMEOUT
#    define RGB_IDLE_TIMEOUT (5UL * 60 * 1000)
#endif

enum key_category {
    CAT_NONE,
    CAT_SYMBOL,
    CAT_DIGIT, // digits, keypad, F-keys
    CAT_NAV,
    CAT_EDIT,
    CAT_MOD,
    CAT_LAYER,
    CAT_SYSTEM, // media, mouse, RGB, OS utilities
    CAT_DANGER, // bootloader, EEPROM clear
};

static const hsv_t category_hsv[] = {
    [CAT_NONE]   = {0, 0, 0},
    [CAT_SYMBOL] = {128, 255, 255}, // cyan
    [CAT_DIGIT]  = {0, 0, 255},     // white
    [CAT_NAV]    = {85, 255, 255},  // green
    [CAT_EDIT]   = {170, 255, 255}, // blue
    [CAT_MOD]    = {21, 255, 255},  // orange
    [CAT_LAYER]  = {43, 255, 255},  // yellow
    [CAT_SYSTEM] = {191, 255, 255}, // purple
    [CAT_DANGER] = {0, 255, 255},   // red
};

static const hsv_t layer_hsv[] = {
    [_BASE] = {0, 0, 0},
    [_NUM]  = {170, 255, 255}, // blue
    [_SYM]  = {128, 255, 255}, // cyan
    [_NAV]  = {85, 255, 255},  // green
    [_FUN]  = {191, 255, 255}, // purple
};

static const hsv_t amber = {24, 255, 255};
static const hsv_t red   = {0, 255, 255};

static uint8_t key_category(uint16_t kc) {
    switch (kc) {
        case KC_TRNS:
        case KC_NO:
            return CAT_NONE;
        case QK_BOOT:
        case QK_REBOOT:
        case EE_CLR:
            return CAT_DANGER;
        case QK_LAYER_LOCK:
            return CAT_LAYER;
        case KC_LCTL ... KC_RGUI:
        case CW_TOGG:
        case KC_CAPS:
            return CAT_MOD;
        case KC_1 ... KC_0:
        case KC_F1 ... KC_F12:
        case KC_F13 ... KC_F24:
        case KC_NUM:
        case KC_PSLS ... KC_PDOT:
            return CAT_DIGIT;
        case KC_RGHT ... KC_UP:
        case KC_HOME:
        case KC_END:
        case KC_PGUP:
        case KC_PGDN:
        case C(KC_LEFT):
        case C(KC_RGHT):
        case C(KC_PGUP):
        case C(KC_PGDN):
        case A(KC_LEFT):
        case A(KC_RGHT):
        case OS_DESKL:
        case OS_DESKR:
        case ALT_TAB:
            return CAT_NAV;
        case KC_BSPC:
        case KC_DEL:
        case KC_INS:
        case KC_ENT:
        case KC_TAB:
        case KC_ESC:
        case C(KC_Z):
        case C(KC_X):
        case C(KC_C):
        case C(KC_V):
        case OS_REDO:
            return CAT_EDIT;
        case KC_CALC:
        case KC_SCRL:
        case KC_PAUS:
        case G(KC_L):
        case OS_SHOT:
        case OS_MODE:
        case OLED_TOG:
        case OVL_PIN:
        case CLAUDE_ACK:
            return CAT_SYSTEM;
    }
    if (IS_QK_MOMENTARY(kc) || IS_QK_TOGGLE_LAYER(kc)) {
        return CAT_LAYER;
    }
    if (IS_CONSUMER_KEYCODE(kc) || IS_SYSTEM_KEYCODE(kc) || IS_MOUSE_KEYCODE(kc) || IS_QK_LIGHTING(kc)) {
        return CAT_SYSTEM;
    }
    return CAT_SYMBOL; // letters on SYM, shifted/AltGr characters, typography
}

static void set_hsv(uint8_t index, hsv_t hsv, uint8_t brightness) {
    hsv.v       = scale8(hsv.v, brightness);
    const rgb_t rgb = hsv_to_rgb(hsv);
    rgb_matrix_set_color(index, rgb.r, rgb.g, rgb.b);
}

static void set_matrix_key(uint8_t row, uint8_t col, uint8_t led_min, uint8_t led_max, hsv_t hsv, uint8_t brightness) {
    const uint8_t index = g_led_config.matrix_co[row][col];
    if (index != NO_LED && index >= led_min && index < led_max) {
        set_hsv(index, hsv, brightness);
    }
}

bool rgb_matrix_indicators_advanced_user(uint8_t led_min, uint8_t led_max) {
    const bool claude_wait = g_shared.claude_state == CLAUDE_WAIT && !user_config.nudge_off;

    if (!claude_wait && last_input_activity_elapsed() > RGB_IDLE_TIMEOUT) {
        for (uint8_t i = led_min; i < led_max; i++) {
            rgb_matrix_set_color(i, 0, 0, 0);
        }
        return false;
    }

    const uint8_t brightness = rgb_matrix_get_val();
    uint8_t       layer      = get_highest_layer(layer_state);
    if (layer > _FUN) {
        layer = _FUN;
    }

    if (layer != _BASE) {
        for (uint8_t row = 0; row < MATRIX_ROWS; row++) {
            for (uint8_t col = 0; col < MATRIX_COLS; col++) {
                const uint16_t kc = keymap_key_to_keycode(layer, (keypos_t){.row = row, .col = col});
                set_matrix_key(row, col, led_min, led_max, category_hsv[key_category(kc)], brightness);
            }
        }
        for (uint8_t i = led_min; i < led_max; i++) {
            if (HAS_FLAGS(g_led_config.flags[i], LED_FLAG_UNDERGLOW)) {
                set_hsv(i, layer_hsv[layer], brightness);
            }
        }
    }

    // Shift keys: left [3,0], right [8,0].
    if (host_keyboard_led_state().caps_lock || shared_caps_word()) {
        set_matrix_key(3, 0, led_min, led_max, red, brightness);
        set_matrix_key(8, 0, led_min, led_max, red, brightness);
    }

    if (claude_wait) {
        const uint8_t breath = sin8((timer_read32() / 8) & 0xFF);
        for (uint8_t i = led_min; i < led_max; i++) {
            if (HAS_FLAGS(g_led_config.flags[i], LED_FLAG_UNDERGLOW)) {
                set_hsv(i, amber, scale8(breath, brightness));
            } else if (last_input_activity_elapsed() > RGB_IDLE_TIMEOUT) {
                rgb_matrix_set_color(i, 0, 0, 0);
            }
        }
    }
    return false;
}
