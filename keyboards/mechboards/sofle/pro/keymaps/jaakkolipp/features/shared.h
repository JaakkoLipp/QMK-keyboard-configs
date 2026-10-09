// Copyright 2026 Jaakko Lipponen
// SPDX-License-Identifier: GPL-2.0-or-later
//
// State the master half owns and mirrors to the other half for the OLEDs and
// RGB: things QMK's own split sync does not cover (locked layers, Caps Word,
// host clock, keystroke count, Claude Code status, user config).
#pragma once

#include QMK_KEYBOARD_H

typedef enum {
    CLAUDE_NONE = 0, // no host app / no session
    CLAUDE_IDLE,
    CLAUDE_THINK,
    CLAUDE_TOOL,
    CLAUDE_WAIT, // needs the user: permission prompt
    CLAUDE_DONE,
    CLAUDE_ERR,
    CLAUDE_LIMIT,
    CLAUDE_STATE_COUNT,
} claude_state_t;

#define CLAUDE_TOOL_LEN 5

enum shared_flags {
    SHF_CAPS_WORD   = 1 << 0,
    SHF_HOST        = 1 << 1, // host app talked to us in the last few seconds
    SHF_CLOCK_VALID = 1 << 2,
};

typedef struct __attribute__((packed)) {
    uint8_t  locked_layers; // bit per layer, from Layer Lock
    uint8_t  flags;         // shared_flags
    uint8_t  user_config;   // low byte of user_config_t
    uint8_t  hour;
    uint8_t  minute;
    uint32_t keystrokes; // this session
    uint8_t  claude_state;
    char     claude_tool[CLAUDE_TOOL_LEN];
    uint16_t claude_turn_s; // seconds since the current turn started
    uint8_t  claude_ctx;    // context window used %, 0xFF = unknown
    uint8_t  claude_others; // other sessions currently active
} shared_t;

_Static_assert(sizeof(shared_t) <= 32, "split RPC payload limit");

// Read-only view, valid on both halves.
extern shared_t g_shared;

void shared_init(void);
// Master: rebuild the struct and send it to the slave when it changed.
void shared_housekeeping(void);
// Master: count a key press.
void shared_count_keystroke(void);

bool shared_layer_locked(uint8_t layer);
bool shared_caps_word(void);
