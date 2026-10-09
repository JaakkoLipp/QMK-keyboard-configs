// Minimal stand-ins for the QMK APIs used by features/oled.c, so the OLED
// renderer can be compiled and run on a PC (tools/oled/preview.py).
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include "progmem.h"

typedef uint32_t layer_state_t;
typedef struct {
    struct {
        bool pressed;
    } event;
} keyrecord_t;
typedef union {
    uint8_t raw;
    struct {
        bool num_lock : 1;
        bool caps_lock : 1;
        bool scroll_lock : 1;
        bool compose : 1;
        bool kana : 1;
        uint8_t reserved : 3;
    };
} led_t;
typedef enum { OLED_ROTATION_0 = 0, OLED_ROTATION_90 = 1, OLED_ROTATION_180 = 2, OLED_ROTATION_270 = 3 } oled_rotation_t;

#define QK_USER 0x7E40
#define KC_ESC 0x29
#define KC_E 0x08
#define LCTL_T(kc) (0x2100 | (kc))
#define RALT(kc) (0x1400 | (kc))

#define MOD_MASK_CTRL 0x11
#define MOD_MASK_SHIFT 0x22
#define MOD_MASK_ALT 0x44
#define MOD_MASK_GUI 0x88
#define MIN(a, b) ((a) < (b) ? (a) : (b))

#define OLED_FONT_START 0
#define OLED_FONT_WIDTH 6
#define OLED_FONT_HEIGHT 8
#ifndef OLED_TIMEOUT
#    define OLED_TIMEOUT 60000
#endif

extern layer_state_t layer_state;
#define IS_LAYER_ON(layer) ((layer_state >> (layer)) & 1)

uint8_t  get_highest_layer(layer_state_t state);
uint8_t  get_mods(void);
uint8_t  get_oneshot_mods(void);
led_t    host_keyboard_led_state(void);
uint8_t  get_current_wpm(void);
uint32_t timer_read32(void);
uint32_t last_input_activity_elapsed(void);
bool     is_keyboard_left(void);
bool     is_oled_on(void);
bool     oled_off(void);
void     oled_clear(void);
void     oled_write_raw_byte(const char data, uint16_t index);
void     eeconfig_update_user(uint32_t val);
uint32_t eeconfig_read_user(void);
