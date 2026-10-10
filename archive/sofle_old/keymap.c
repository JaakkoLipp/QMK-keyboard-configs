// Copyright 2025 Dasky (@daskygit)
// SPDX-License-Identifier: GPL-2.0-or-later

#include QMK_KEYBOARD_H

// clang-format off










const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {
  [0] = LAYOUT(
    KC_GRV,  KC_1,    KC_2,    KC_3,    KC_4,    KC_5,                             KC_6,    KC_7,    KC_8,    KC_9,   KC_0,    KC_MINS,
    KC_ESC,  KC_Q,    KC_W,    KC_E,    KC_R,    KC_T,                             KC_Y,    KC_U,    KC_I,    KC_O,   KC_P,    KC_BSPC,
    KC_TAB,  KC_A,    KC_S,    KC_D,    KC_F,    KC_G,                             KC_H,    KC_J,    KC_K,    KC_L,   KC_SCLN, KC_QUOT,
    KC_LSFT, KC_Z,    KC_X,    KC_C,    KC_V,    KC_B,    KC_MUTE,        KC_MPLY, KC_N,    KC_M,    KC_COMM, KC_DOT, KC_SLSH, KC_RSFT,
                      KC_LGUI, KC_LALT, KC_LCTL, KC_SPC,   MO(1),         MO(2),   KC_ENT,  KC_RGUI, KC_ALGR, KC_RCTL
  ),
  [1] = LAYOUT(
    KC_F1,   KC_F2,   KC_F3,   KC_F4,   KC_F5,   KC_F6,                            KC_F7,   KC_F8,   KC_F9,   KC_F10,  KC_F11,  KC_F12,
    _______, S(KC_1), S(KC_2), S(KC_3), S(KC_4), S(KC_5),                          S(KC_6), S(KC_7), S(KC_8), S(KC_9), S(KC_0), KC_DEL,
    KC_CAPS, KC_WBAK, KC_WSCH, KC_WFWD, RALT(KC_COMM), RALT(KC_DOT),               KC_PIPE, RALT(KC_8), RALT(KC_9), RALT(KC_7), RALT(KC_0), KC_LBRC,
    _______, KC_WREF,  KC_CUT, KC_COPY, KC_PSTE, KC_EQL, _______,        _______, KC_QUOT, KC_RBRC, KC_SCLN, KC_COLN, RALT(KC_MINS), _______,
                      _______, _______, _______, _______, _______,        MO(3),   _______ ,   _______, _______, _______
  ),
  [2] = LAYOUT(
     KC_F13, KC_F14,  KC_F15,  KC_F16,  KC_F17,  KC_F18,                        KC_F19,  KC_F20,  KC_F21,  KC_F22,  KC_F23, KC_F24,
    _______, KC_NUM,  KC_KP_7, KC_KP_8, KC_KP_9, KC_PMNS,                       KC_PGUP, KC_HOME, KC_UP,   KC_PSCR, MS_BTN6, _______,
    _______, KC_PSLS, KC_P4,   KC_P5,   KC_P6,   KC_PPLS,                       KC_PGDN, KC_LEFT, KC_DOWN, KC_RGHT, MS_BTN7, XXXXXXX,
    _______, KC_PAST, KC_P1,   KC_P2,   KC_P3,   KC_PCMM, _______,      _______, KC_INS,  KC_END,  KC_APP,  KC_DEL, MS_BTN8, _______,
                      KC_P0,   KC_PDOT, KC_PENT, _______, MO(3),        _______, _______, _______,  _______, _______
  ),
    [3] = LAYOUT(
    QK_REBOOT, PB_1,    PB_2 ,   PB_3,    PB_4,    PB_5,                             XXXXXXX, XXXXXXX, XXXXXXX, XXXXXXX, XXXXXXX, XXXXXXX,
    EE_CLR, XXXXXXX, MS_BTN1, MS_UP,   MS_BTN2, MS_WHLU,                            XXXXXXX, XXXXXXX, XXXXXXX, XXXXXXX, XXXXXXX, XXXXXXX,
    QK_BOOT , XXXXXXX, MS_LEFT, MS_DOWN, MS_RGHT, MS_WHLD,                          XXXXXXX, XXXXXXX, XXXXXXX, XXXXXXX, XXXXXXX, XXXXXXX,
    XXXXXXX, XXXXXXX, MS_WHLL, MS_BTN3, MS_WHLR, XXXXXXX, XXXXXXX,        XXXXXXX, XXXXXXX, XXXXXXX, XXXXXXX, XXXXXXX, XXXXXXX, XXXXXXX,
                      _______, _______, _______, _______, _______,        _______, _______, _______, _______, _______
  )
};


// TODO: midi layer


#ifdef ENCODER_MAP_ENABLE
const uint16_t PROGMEM encoder_map[][NUM_ENCODERS][NUM_DIRECTIONS] = {
[0] = { ENCODER_CCW_CW(KC_VOLD, KC_VOLU), ENCODER_CCW_CW(KC_MPRV, KC_MNXT)},
[1] = { ENCODER_CCW_CW(KC_TRNS, KC_TRNS), ENCODER_CCW_CW(KC_TRNS, KC_TRNS)},
[2] = { ENCODER_CCW_CW(KC_TRNS, KC_TRNS), ENCODER_CCW_CW(KC_TRNS, KC_TRNS)},
[3] = { ENCODER_CCW_CW(KC_TRNS, KC_TRNS), ENCODER_CCW_CW(KC_TRNS, KC_TRNS)}
};
#endif
// clang-format on
