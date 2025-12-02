#include QMK_KEYBOARD_H
#include "keymap_finnish.h"

enum layers {
    _BASE = 0,
    _SYM,
    _EXTRA
};


// Convenience macros
// These assume Windows Finnish / Nordic layout.
// #define FI_LCBR      RALT(KC_7)      // {


const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {

    /* BASE (Finnish header definitions) */
    [_BASE] = LAYOUT(
    FI_SECT, FI_1,    FI_2,    FI_3,    FI_4,    FI_5,                                FI_6,    FI_7,    FI_8,    FI_9,    FI_0,     FI_PLUS,
    KC_ESC,  FI_Q,    FI_W,    FI_E,    FI_R,    FI_T,                                FI_Y,    FI_U,    FI_I,    FI_O,    FI_P,     KC_BSPC,
    KC_TAB,  FI_A,    FI_S,    FI_D,    FI_F,    FI_G,                                FI_H,    FI_J,    FI_K,    FI_L,    FI_ODIA,  FI_ADIA,
    KC_LSFT, FI_Z,    FI_X,    FI_C,    FI_V,    FI_B,    KC_MUTE,          KC_MPLY,  FI_N,    FI_M,    FI_COMM, FI_DOT,  FI_MINS,  KC_RSFT,
                        KC_LGUI, KC_LALT, KC_LCTL, KC_SPC,  MO(1),           MO(2),   KC_ENT, KC_RCTL, KC_ALGR, KC_RGUI
    ),

    /* SYMBOL LAYER */
    [_SYM] = LAYOUT(
    KC_F1,   KC_F2,   KC_F2,   KC_F4,   KC_F5,   KC_F6,                                KC_F7,   KC_F8,   KC_F9,   KC_F10,  KC_F11,   KC_F12,
    _______, FI_HASH, FI_LBRC, FI_RBRC, FI_EQL, FI_QUOT,                               KC_PGUP, KC_HOME, KC_END, KC_PSCR, KC_INS,  KC_DEL,
    KC_CAPS, FI_LCBR, FI_LPRN, FI_RPRN, FI_RCBR, FI_UNDS,                              KC_APP, KC_LEFT, KC_UP,   KC_DOWN, KC_RGHT,  FI_ARNG,
    _______, FI_PIPE, FI_LABK, FI_RABK, FI_SLSH, FI_BSLS,   _______,          _______, KC_PGDN, KC_MPRV, KC_MPLY, KC_MNXT, FI_GRV,  _______,
                       _______, _______, _______, _______, _______,          QK_LLCK, _______, _______, _______, _______
    ),

    /* EXTRA LAYER */
    [_EXTRA] = LAYOUT(
    KC_F13, KC_F14,  KC_F15,  KC_F16,  KC_F17,  KC_F18,                                 KC_F19,  KC_F20,  KC_F21,  KC_F22,  KC_F23, KC_F24,
    PB_1, PB_2, MS_BTN1, MS_UP,   MS_BTN2, MS_WHLU,                                     KC_NUM,  KC_KP_7, KC_KP_8, KC_KP_9, KC_PMNS, _______,
    PB_3 , PB_4, MS_LEFT, MS_DOWN, MS_RGHT, MS_WHLD,                                    KC_PSLS, KC_P4,   KC_P5,   KC_P6,   KC_PPLS, XXXXXXX,
    PB_5, PB_6, MS_WHLL, MS_BTN3, MS_WHLR, MS_BTN5, _______,                   _______, KC_PAST, KC_P1,   KC_P2,   KC_P3,   KC_PCMM, _______,
                _______, _______, _______, _______, QK_LLCK,                   _______, _______, KC_P0,   KC_PDOT, KC_PENT
    )
};



/* EXTRA LAYER
    [_EXTRA] = LAYOUT(
    _______, _______, _______, _______, _______, _______,                             _______, _______, _______, _______, _______, _______,
    _______, _______, _______, _______, _______, _______,                             _______, _______, _______, _______, _______, _______,
    _______, _______, _______, _______, _______, _______,                             _______, _______, _______, _______, _______, _______,
    _______, _______, _______, _______, _______, _______, _______,          _______, _______, _______, _______, _______, _______, _______,
                      _______, _______, _______, _______, _______,          _______, _______, _______, _______, _______
    )
*/


#ifdef ENCODER_MAP_ENABLE
const uint16_t PROGMEM encoder_map[][NUM_ENCODERS][NUM_DIRECTIONS] = {
[_BASE] = { ENCODER_CCW_CW(KC_VOLD, KC_VOLU), ENCODER_CCW_CW(KC_MPRV, KC_MNXT)},
[_SYM] = { ENCODER_CCW_CW(KC_TRNS, KC_TRNS), ENCODER_CCW_CW(KC_TRNS, KC_TRNS)},
[_EXTRA] = { ENCODER_CCW_CW(KC_TRNS, KC_TRNS), ENCODER_CCW_CW(KC_TRNS, KC_TRNS)},
};
#endif
// clang-format on
