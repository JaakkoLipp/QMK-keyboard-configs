// Copyright 2026 Jaakko Lipponen
// SPDX-License-Identifier: GPL-2.0-or-later

#include "host_link.h"
#include <string.h>
#include "raw_hid.h"
#include "os_detection.h"
#include "fi_keys.h"
#include "keycodes.h"

// The app polls every ~30 ms; after this long without a request it is gone and
// host-provided state (Claude status) is dropped instead of going stale.
#define HOST_TIMEOUT 5000

static bool     host_ever = false;
static uint32_t host_seen = 0;

static bool     clock_valid = false;
static uint32_t clock_secs  = 0; // seconds since midnight when received
static uint32_t clock_at    = 0;

static uint8_t  claude_state = CLAUDE_NONE;
static char     claude_tool[CLAUDE_TOOL_LEN];
static uint16_t claude_turn_s = 0;
static uint8_t  claude_ctx    = 0xFF;
static uint8_t  claude_others = 0;
static uint32_t claude_at     = 0;

static uint8_t pin_count = 0;

static bool host_alive(void) {
    return host_ever && timer_elapsed32(host_seen) < HOST_TIMEOUT;
}

void host_link_fill(shared_t *s) {
    if (host_alive()) {
        s->flags |= SHF_HOST;
    }
    if (clock_valid) {
        // Keep ticking locally between host updates (and after it goes away).
        const uint32_t now = (clock_secs + timer_elapsed32(clock_at) / 1000) % 86400UL;
        s->hour   = now / 3600;
        s->minute = (now / 60) % 60;
        s->flags |= SHF_CLOCK_VALID;
    }
    if (host_alive()) {
        s->claude_state = claude_state;
        memcpy(s->claude_tool, claude_tool, CLAUDE_TOOL_LEN);
        uint32_t turn = claude_turn_s;
        if (claude_state == CLAUDE_THINK || claude_state == CLAUDE_TOOL || claude_state == CLAUDE_WAIT) {
            turn += timer_elapsed32(claude_at) / 1000;
        }
        s->claude_turn_s = turn > UINT16_MAX ? UINT16_MAX : turn;
        s->claude_ctx    = claude_ctx;
        s->claude_others = claude_others;
    } else {
        s->claude_state = CLAUDE_NONE;
        s->claude_ctx   = 0xFF;
    }
}

static void put_u32(uint8_t *p, uint32_t v) {
    p[0] = v;
    p[1] = v >> 8;
    p[2] = v >> 16;
    p[3] = v >> 24;
}

static void fill_state(uint8_t *data) {
    const led_t led = host_keyboard_led_state();
    data[2]         = HL_VERSION;
    put_u32(&data[3], layer_state);
    data[7]  = get_highest_layer(default_layer_state);
    data[8]  = g_shared.locked_layers;
    data[9]  = get_mods() | get_oneshot_mods();
    data[10] = (led.caps_lock ? 1 : 0) | (led.num_lock ? 2 : 0) | (is_caps_word_on() ? 4 : 0) | (led.scroll_lock ? 8 : 0);
    data[11] = detected_host_os();
    data[12] = user_config.os_mode;
    data[13] = os_is_windows();
    data[14] = pin_count;
    data[15] = get_current_wpm();
    data[16] = user_config.nudge_off;
}

bool via_command_kb(uint8_t *data, uint8_t length) {
    if (length < 17 || data[0] != HL_CMD) {
        return false; // not ours: let VIA handle it
    }
    host_ever = true;
    host_seen = timer_read32();

    switch (data[1]) {
        case HL_GET_STATE:
            fill_state(data);
            break;
        case HL_SET_TIME:
            if (data[2] < 24 && data[3] < 60 && data[4] < 60) {
                clock_secs  = data[2] * 3600UL + data[3] * 60UL + data[4];
                clock_at    = timer_read32();
                clock_valid = true;
            }
            break;
        case HL_SET_CLAUDE:
            claude_state = data[2] < CLAUDE_STATE_COUNT ? data[2] : CLAUDE_NONE;
            memcpy(claude_tool, &data[3], CLAUDE_TOOL_LEN);
            claude_turn_s = data[8] | (data[9] << 8);
            claude_ctx    = data[10];
            claude_others = data[11];
            claude_at     = timer_read32();
            break;
        case HL_PING:
            data[2] = HL_VERSION;
            break;
        default:
            data[1] = 0xFF;
            break;
    }
    raw_hid_send(data, length);
    return true;
}

#ifndef VIA_ENABLE
void raw_hid_receive(uint8_t *data, uint8_t length) {
    if (!via_command_kb(data, length)) {
        data[0] = 0xFF;
        raw_hid_send(data, length);
    }
}
#endif

bool process_host_keys(uint16_t keycode, keyrecord_t *record) {
    if (!record->event.pressed) {
        return true;
    }
    switch (keycode) {
        case OVL_PIN:
            pin_count++;
            return false;
        case CLAUDE_ACK:
            user_config.nudge_off = !user_config.nudge_off;
            user_config_save();
            return false;
    }
    return true;
}
