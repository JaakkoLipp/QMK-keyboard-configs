// Copyright 2026 Jaakko Lipponen
// SPDX-License-Identifier: GPL-2.0-or-later
//
// Raw HID link to the desktop overlay app (tools/layer_overlay).
//
// Shares VIA's raw HID interface: VIA hands every report to via_command_kb()
// first, and reports starting with HL_CMD are answered here. The link is
// strictly request/response so the VIA app never sees unsolicited reports.
//
// Request:  [0]=0xA0 [1]=sub-command [2..]=payload    (32 bytes)
// Response: same buffer with the answer filled in; [1]=0xFF if unknown.
//
// GET_STATE (0x01) response:
//   [2] protocol version   [3..6] layer_state (LE)   [7] default layer
//   [8] locked layers      [9] mods (held | one-shot)
//   [10] flags: bit0 Caps Lock, bit1 Num Lock, bit2 Caps Word, bit3 Scroll Lock
//   [11] detected OS (os_variant_t)  [12] OS mode  [13] 1 = Windows shortcuts
//   [14] overlay-pin press counter   [15] WPM      [16] Claude nudge off
// SET_TIME (0x02):   [2] hour [3] minute [4] second
// SET_CLAUDE (0x03): [2] claude_state_t [3..7] tool name (5 chars, no NUL)
//                    [8..9] turn seconds (LE) [10] context % (0xFF unknown)
//                    [11] other active sessions
// PING (0x04) response: [2] protocol version
#pragma once

#include QMK_KEYBOARD_H
#include "shared.h"

#define HL_CMD 0xA0
#define HL_VERSION 1

enum host_link_command {
    HL_GET_STATE  = 0x01,
    HL_SET_TIME   = 0x02,
    HL_SET_CLAUDE = 0x03,
    HL_PING       = 0x04,
};

// Master: add host-provided data (clock, Claude status) to the shared struct.
void host_link_fill(shared_t *s);
bool process_host_keys(uint16_t keycode, keyrecord_t *record);
