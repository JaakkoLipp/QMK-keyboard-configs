// Copyright 2026 Jaakko Lipponen
// SPDX-License-Identifier: GPL-2.0-or-later
//
// Layers and custom keycodes shared by keymap.c and the feature files.
// The "legend:" comments are read by tools/keymap/gen_layers.py to label the
// layer images and the on-screen overlay. Keep them short (1-6 characters).
#pragma once

#include QMK_KEYBOARD_H

enum layers {
    _BASE = 0,
    _NUM,
    _SYM,
    _NAV,
    _FUN,
};

// Keep below QK_USER_31 so VIA can address every entry.
enum custom_keycodes {
    // Literal versions of Finnish dead keys (dead key + Space).
    GRV_LIT = QK_USER, // legend: `
    CIRC_LIT,          // legend: ^
    TILD_LIT,          // legend: ~
    // Finnish typography, OS-aware (Linux AltGr combos / Windows Alt codes).
    TY_NDSH, // legend: –
    TY_MDSH, // legend: —
    TY_RDQU, // legend: ”
    TY_RSQU, // legend: ’
    TY_DEG,  // legend: °
    // OS-aware shortcuts.
    OS_REDO,  // legend: Redo
    OS_SHOT,  // legend: Shot
    OS_DESKL, // legend: Desk←
    OS_DESKR, // legend: Desk→
    ALT_TAB,  // legend: AltTab
    OS_MODE,  // legend: OS
    // Displays and host link.
    OLED_TOG,   // legend: OLED
    OVL_PIN,    // legend: Ovl
    CLAUDE_ACK, // legend: Nudge
};

// Caps-lock position: tap for Esc, hold for Ctrl.
#define CTL_ESC LCTL_T(KC_ESC)
// € through AltGr+E: AltGr+5 types ‰ on the default Linux Finnish layout.
#define FI_EURE RALT(KC_E)
