// Copyright 2026 Jaakko Lipponen
// SPDX-License-Identifier: GPL-2.0-or-later

#include "shared.h"
#include <string.h>
#include "transactions.h"
#include "fi_keys.h"
#include "host_link.h"

#define SHARED_MIN_INTERVAL 100   // ms between sends when something changed
#define SHARED_KEEPALIVE    1000  // resend at least this often (slave reboot)

shared_t        g_shared;
static uint32_t keystrokes = 0;

static void shared_slave_handler(uint8_t in_len, const void *in_data, uint8_t out_len, void *out_data) {
    if (in_len != sizeof(shared_t)) {
        return;
    }
    memcpy(&g_shared, in_data, sizeof(shared_t));
    // Mirror the master's settings (OS mode, OLED off, nudge off) in RAM only.
    user_config.raw = (user_config.raw & ~0xFFUL) | g_shared.user_config;
}

void shared_init(void) {
    memset(&g_shared, 0, sizeof(g_shared));
    g_shared.claude_ctx = 0xFF;
    transaction_register_rpc(RPC_ID_USER_SHARED, shared_slave_handler);
}

void shared_count_keystroke(void) {
    keystrokes++;
}

void shared_housekeeping(void) {
    if (!is_keyboard_master()) {
        return;
    }

    shared_t s;
    memset(&s, 0, sizeof(s));
    for (uint8_t layer = 0; layer < 8; layer++) {
        if (is_layer_locked(layer)) {
            s.locked_layers |= 1 << layer;
        }
    }
    if (is_caps_word_on()) {
        s.flags |= SHF_CAPS_WORD;
    }
    s.user_config = user_config.raw & 0xFF;
    s.keystrokes  = keystrokes;
    host_link_fill(&s);

    static bool     pending   = true;
    static uint32_t last_send = 0;
    if (memcmp(&s, &g_shared, sizeof(s)) != 0) {
        g_shared = s;
        pending  = true;
    }
    const uint32_t since = timer_elapsed32(last_send);
    if ((pending && since >= SHARED_MIN_INTERVAL) || since >= SHARED_KEEPALIVE) {
        if (transaction_rpc_send(RPC_ID_USER_SHARED, sizeof(g_shared), &g_shared)) {
            pending = false;
        }
        last_send = timer_read32();
    }
}

bool shared_layer_locked(uint8_t layer) {
    return layer < 8 && (g_shared.locked_layers & (1 << layer));
}

bool shared_caps_word(void) {
    return g_shared.flags & SHF_CAPS_WORD;
}
