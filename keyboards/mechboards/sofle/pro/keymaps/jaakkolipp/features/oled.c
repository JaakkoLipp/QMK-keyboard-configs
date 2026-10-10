// Copyright 2026 Jaakko Lipponen
// SPDX-License-Identifier: GPL-2.0-or-later
//
// Both OLEDs are portrait, 32x128 px (5 text columns x 16 rows).
// Left half:  status - layer icon, lock, mods, Caps / Caps Word / NUM, WPM.
// Right half: fun    - clock, Claude Code status or the WPM sauna, keystrokes.
//
// Everything is drawn into a local frame buffer and copied to the driver with
// oled_write_raw_byte(), which only marks bytes that really changed as dirty,
// so redrawing every frame costs almost no I2C traffic.

#include "oled.h"
#include <stdio.h>
#include <string.h>
#include "keycodes.h"
#include "fi_keys.h"
#include "shared.h"
#include "oled_gfx.h"
#include OLED_FONT_H // static font[]: a private copy for our own text drawing

#define W 32
#define H 128

static uint8_t fb[W * H / 8];

typedef enum { DRAW_ON, DRAW_OFF, DRAW_DIM } draw_mode_t;

static void px(int16_t x, int16_t y, bool on) {
    if (x < 0 || y < 0 || x >= W || y >= H) {
        return;
    }
    const uint16_t i = x + (y / 8) * W;
    if (on) {
        fb[i] |= 1 << (y % 8);
    } else {
        fb[i] &= ~(1 << (y % 8));
    }
}

static void plot(int16_t x, int16_t y, draw_mode_t mode) {
    switch (mode) {
        case DRAW_ON:
            px(x, y, true);
            break;
        case DRAW_OFF:
            px(x, y, false);
            break;
        case DRAW_DIM: // checkerboard: reads as "inactive"
            if (((x + y) & 1) == 0) px(x, y, true);
            break;
    }
}

static void fill(int16_t x, int16_t y, int16_t w, int16_t h, bool on) {
    for (int16_t yy = y; yy < y + h; yy++) {
        for (int16_t xx = x; xx < x + w; xx++) {
            px(xx, yy, on);
        }
    }
}

static void invert(int16_t x, int16_t y, int16_t w, int16_t h) {
    for (int16_t yy = y; yy < y + h; yy++) {
        for (int16_t xx = x; xx < x + w; xx++) {
            if (xx >= 0 && yy >= 0 && xx < W && yy < H) {
                fb[xx + (yy / 8) * W] ^= 1 << (yy % 8);
            }
        }
    }
}

static uint8_t bm_w(const uint8_t *bm) {
    return pgm_read_byte(&bm[0]);
}

static uint8_t bm_h(const uint8_t *bm) {
    return pgm_read_byte(&bm[1]);
}

static void bitmap(const uint8_t *bm, int16_t x, int16_t y, draw_mode_t mode) {
    const uint8_t w = bm_w(bm), h = bm_h(bm), stride = (w + 7) / 8;
    for (uint8_t yy = 0; yy < h; yy++) {
        for (uint8_t xx = 0; xx < w; xx++) {
            if (pgm_read_byte(&bm[2 + yy * stride + xx / 8]) & (0x80 >> (xx % 8))) {
                plot(x + xx, y + yy, mode);
            }
        }
    }
}

static void bitmap_c(const uint8_t *bm, int16_t y, draw_mode_t mode) {
    bitmap(bm, (W - bm_w(bm)) / 2, y, mode);
}

static void glyph(int16_t x, int16_t y, uint8_t c, draw_mode_t mode) {
    for (uint8_t col = 0; col < OLED_FONT_WIDTH; col++) {
        const uint8_t bits = pgm_read_byte(&font[(c - OLED_FONT_START) * OLED_FONT_WIDTH + col]);
        for (uint8_t row = 0; row < OLED_FONT_HEIGHT; row++) {
            if (bits & (1 << row)) {
                plot(x + col, y + row, mode);
            }
        }
    }
}

static void text(int16_t x, int16_t y, const char *s, draw_mode_t mode) {
    for (; *s; s++, x += OLED_FONT_WIDTH) {
        glyph(x, y, (uint8_t)*s, mode);
    }
}

static int16_t text_width(const char *s) {
    return strlen(s) * OLED_FONT_WIDTH - 1;
}

static void text_c(int16_t y, const char *s, draw_mode_t mode) {
    text((W - text_width(s) + 1) / 2, y, s, mode);
}

// Inverted label across the full width.
static void badge(int16_t y, const char *s) {
    fill(0, y - 1, W, OLED_FONT_HEIGHT + 1, true);
    text_c(y, s, DRAW_OFF);
}

static void hline(int16_t y) {
    fill(2, y, W - 4, 1, true);
}

static void flush(void) {
    for (uint16_t i = 0; i < sizeof(fb); i++) {
        oled_write_raw_byte(fb[i], i);
    }
}

// --- Left: status -----------------------------------------------------------

static const uint8_t *const layer_icons[] = {
    [_BASE] = gfx_icon_base, [_NUM] = gfx_icon_num, [_SYM] = gfx_icon_sym, [_NAV] = gfx_icon_nav, [_FUN] = gfx_icon_fun,
};
static const char *const layer_names[] = {
    [_BASE] = "BASE", [_NUM] = "NUM", [_SYM] = "SYM", [_NAV] = "NAV", [_FUN] = "FUN",
};

// 16x16 cell, glyph centred; active = inverted cell, inactive = dimmed glyph.
static void mod_cell(int16_t x, int16_t y, const uint8_t *bm, bool active) {
    if (active) {
        fill(x, y, 16, 16, true);
    }
    bitmap(bm, x + (16 - bm_w(bm)) / 2, y + (16 - bm_h(bm)) / 2, active ? DRAW_OFF : DRAW_DIM);
}

// GUI cell shows the OS logo from the QMK font (2x2 characters, 12x16 px).
static void gui_cell(int16_t x, int16_t y, bool active) {
    const uint8_t top = os_is_windows() ? 0x97 : 0x99; // Windows : Tux
    if (active) {
        fill(x, y, 16, 16, true);
    }
    const draw_mode_t mode = active ? DRAW_OFF : DRAW_DIM;
    glyph(x + 2, y, top, mode);
    glyph(x + 8, y, top + 1, mode);
    glyph(x + 2, y + 8, top + 0x20, mode);
    glyph(x + 8, y + 8, top + 0x21, mode);
}

static void render_status(void) {
    uint8_t layer = get_highest_layer(layer_state);
    if (layer > _FUN) {
        layer = _FUN;
    }

    // Layer icon and name; a locked layer gets the whole header inverted.
    const uint8_t *icon = layer_icons[layer];
    bitmap(icon, (W - bm_w(icon)) / 2, (32 - bm_h(icon)) / 2, DRAW_ON);
    text_c(34, layer_names[layer], DRAW_ON);
    if (shared_layer_locked(layer)) {
        invert(0, 0, W, 43);
    }
    hline(45);

    // Modifiers: Shift Ctrl / Alt GUI.
    const uint8_t mods = get_mods() | get_oneshot_mods();
    mod_cell(0, 48, gfx_mod_shift, mods & MOD_MASK_SHIFT);
    mod_cell(16, 48, gfx_mod_ctrl, mods & MOD_MASK_CTRL);
    mod_cell(0, 64, gfx_mod_alt, mods & MOD_MASK_ALT);
    gui_cell(16, 64, mods & MOD_MASK_GUI);
    if (user_config.os_mode != OSM_AUTO) {
        fill(18, 81, 12, 1, true); // underline: OS mode is forced, not detected
    }
    hline(83);

    // Lock indicators.
    const led_t led = host_keyboard_led_state();
    if (led.caps_lock) {
        badge(87, "CAPS");
    } else if (shared_caps_word()) {
        badge(87, "WORD");
    }
    if (IS_LAYER_ON(_NUM)) {
        badge(98, led.num_lock ? "NUM" : "num?");
    }

    // Typing speed.
    char buf[6];
    snprintf(buf, sizeof(buf), "%u", get_current_wpm());
    text_c(110, "wpm", DRAW_ON);
    text_c(119, buf, DRAW_ON);
}

// --- Right: fun ---------------------------------------------------------------

static void format_keystrokes(char *buf, size_t n, uint32_t k) {
    if (k < 1000) {
        snprintf(buf, n, "%lu", (unsigned long)k);
    } else if (k < 100000) {
        snprintf(buf, n, "%lu.%luk", (unsigned long)(k / 1000), (unsigned long)((k % 1000) / 100));
    } else if (k < 1000000) {
        snprintf(buf, n, "%luk", (unsigned long)(k / 1000));
    } else {
        snprintf(buf, n, "%lu.%luM", (unsigned long)(k / 1000000), (unsigned long)((k % 1000000) / 100000));
    }
}

static void format_duration(char *buf, size_t n, uint32_t s) {
    if (s < 600) {
        snprintf(buf, n, "%lu:%02lu", (unsigned long)(s / 60), (unsigned long)(s % 60));
    } else if (s < 6000) {
        snprintf(buf, n, "%lum", (unsigned long)(s / 60));
    } else {
        snprintf(buf, n, "%luh", (unsigned long)(s / 3600));
    }
}

static bool claude_panel_visible(void) {
    switch (g_shared.claude_state) {
        case CLAUDE_THINK:
        case CLAUDE_TOOL:
        case CLAUDE_WAIT:
        case CLAUDE_DONE:
        case CLAUDE_ERR:
        case CLAUDE_LIMIT:
            return true;
        default:
            return false;
    }
}

static void render_claude(void) {
    static const uint8_t *const sparkles[] = {gfx_sparkle_0, gfx_sparkle_1, gfx_sparkle_2};
    const uint32_t              now        = timer_read32();
    const uint8_t               state      = g_shared.claude_state;
    char                        label[CLAUDE_TOOL_LEN + 1];

    switch (state) {
        case CLAUDE_DONE:
            bitmap_c(gfx_icon_check, 18, DRAW_ON);
            strcpy(label, "done");
            break;
        case CLAUDE_ERR:
        case CLAUDE_LIMIT:
            bitmap_c(gfx_icon_cross, 18, DRAW_ON);
            strcpy(label, state == CLAUDE_ERR ? "error" : "limit");
            break;
        case CLAUDE_WAIT:
            bitmap_c(gfx_sparkle_0, 14, DRAW_ON);
            strcpy(label, "WAIT!");
            break;
        case CLAUDE_TOOL:
            bitmap_c(sparkles[(now / 180) % 3], 14, DRAW_ON);
            memcpy(label, g_shared.claude_tool, CLAUDE_TOOL_LEN);
            label[CLAUDE_TOOL_LEN] = '\0';
            break;
        default: // THINK
            bitmap_c(sparkles[(now / 300) % 3], 14, DRAW_ON);
            strcpy(label, "think");
            break;
    }
    text_c(49, label, DRAW_ON);

    if (state == CLAUDE_THINK || state == CLAUDE_TOOL || state == CLAUDE_WAIT) {
        char buf[8];
        format_duration(buf, sizeof(buf), g_shared.claude_turn_s);
        text_c(59, buf, DRAW_ON);
    }

    // Context window fill bar.
    if (g_shared.claude_ctx <= 100) {
        char buf[6];
        snprintf(buf, sizeof(buf), "%u%%", g_shared.claude_ctx);
        text_c(72, buf, DRAW_ON);
        fill(1, 82, 30, 1, true);
        fill(1, 88, 30, 1, true);
        fill(1, 82, 1, 7, true);
        fill(30, 82, 1, 7, true);
        fill(3, 84, (26 * g_shared.claude_ctx) / 100, 3, true);
    }

    if (g_shared.claude_others) {
        char buf[6];
        snprintf(buf, sizeof(buf), "+%u", g_shared.claude_others);
        text_c(96, buf, DRAW_ON);
    }

    // Waiting for the user: blink the whole panel.
    if (state == CLAUDE_WAIT && (now / 500) % 2) {
        invert(0, 12, W, 96);
    }
}

// Typing speed as a sauna thermometer: 0 wpm = 40 °C, 120+ wpm = 110 °C.
static void render_sauna(void) {
    const uint8_t  wpm  = get_current_wpm();
    const uint8_t  temp = 40 + (MIN(wpm, 120) * 70) / 120;
    const uint32_t now  = timer_read32();

    if (wpm >= 40) {
        static const uint8_t *const steam[] = {gfx_steam_0, gfx_steam_1, gfx_steam_2};
        bitmap_c(steam[(now / 220) % 3], 13, DRAW_ON);
    }

    // Thermometer at the left; mercury rises inside the tube.
    const int16_t tx = 1, ty = 29;
    bitmap(gfx_thermometer, tx, ty, DRAW_ON);
    const int16_t tube_top = ty + 2, tube_bottom = ty + 52;
    const int16_t level    = ((temp - 40) * (tube_bottom - tube_top)) / 70;
    fill(tx + 4, tube_bottom - level, 5, level, true);
    for (int16_t mark = tube_top + 5; mark < tube_bottom; mark += 10) {
        fill(tx + 11, mark, 2, 1, true); // scale ticks
    }

    // Temperature and speed beside it.
    char buf[6];
    snprintf(buf, sizeof(buf), "%u", temp);
    text(15, 36, buf, DRAW_ON);
    fill(17, 46, 3, 3, true); // degree sign
    px(18, 47, false);
    text(22, 46, "C", DRAW_ON);
    snprintf(buf, sizeof(buf), "%u", wpm);
    text(15, 66, buf, DRAW_ON);
    text(15, 75, "wpm", DRAW_ON);

    if (wpm >= 80 && (now / 400) % 2) {
        badge(98, "LOYLY");
        // Umlaut dots over the O (glyph columns 8..12), cut into the badge.
        px(9, 97, false);
        px(11, 97, false);
    } else {
        text_c(98, "sauna", DRAW_ON);
    }
}

static void render_fun(void) {
    char buf[8];
    if (g_shared.flags & SHF_CLOCK_VALID) {
        snprintf(buf, sizeof(buf), "%02u:%02u", g_shared.hour, g_shared.minute);
    } else {
        // No host app yet: show uptime.
        const uint32_t m = timer_read32() / 60000;
        snprintf(buf, sizeof(buf), "%lu:%02lu", (unsigned long)(m / 60 % 100), (unsigned long)(m % 60));
    }
    text_c(1, buf, DRAW_ON);
    hline(10);

    if (claude_panel_visible()) {
        render_claude();
    } else {
        render_sauna();
    }

    hline(109);
    format_keystrokes(buf, sizeof(buf), g_shared.keystrokes);
    text_c(111, "keys", DRAW_ON);
    text_c(120, buf, DRAW_ON);
}

// --- Driver hooks -------------------------------------------------------------

oled_rotation_t oled_init_user(oled_rotation_t rotation) {
    return OLED_ROTATION_270; // overrides the Mechboards default on both halves
}

bool oled_task_user(void) {
    // Sleep guard: every redraw would otherwise switch the panel back on.
    if (user_config.oled_off || last_input_activity_elapsed() > OLED_TIMEOUT) {
        if (is_oled_on()) {
            oled_clear();
            oled_off();
        }
        return false;
    }
    if (!is_oled_on()) {
        return false; // a key press (keyboard.c) or the master's sync wakes it
    }

    memset(fb, 0, sizeof(fb));
    if (is_keyboard_left()) {
        render_status();
    } else {
        render_fun();
    }
    flush();
    return false;
}

bool process_oled_keys(uint16_t keycode, keyrecord_t *record) {
    if (keycode == OLED_TOG && record->event.pressed) {
        user_config.oled_off = !user_config.oled_off;
        user_config_save();
        return false;
    }
    return true;
}
