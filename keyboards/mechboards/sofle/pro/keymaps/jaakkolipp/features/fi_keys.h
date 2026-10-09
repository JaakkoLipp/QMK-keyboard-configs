// Copyright 2026 Jaakko Lipponen
// SPDX-License-Identifier: GPL-2.0-or-later
//
// Finnish-layout helpers: literal dead keys, typography, OS-aware shortcuts,
// NumLock handling for the NUM layer and a Finnish-aware Caps Word.
#pragma once

#include QMK_KEYBOARD_H

typedef enum {
    OSM_AUTO = 0, // follow OS detection
    OSM_WINDOWS,
    OSM_LINUX,
} os_mode_t;

// Persisted in the 32-bit user EEPROM word (VIA leaves it alone).
typedef union {
    uint32_t raw;
    struct {
        uint8_t os_mode : 2;   // os_mode_t
        bool    nudge_off : 1; // Claude WAIT underglow nudge disabled
        bool    oled_off : 1;  // OLEDs switched off with OLED_TOG
    };
} user_config_t;

extern user_config_t user_config;

void user_config_load(void);
void user_config_save(void);

// True when shortcuts should use the Windows variant.
bool os_is_windows(void);

bool          process_fi_keys(uint16_t keycode, keyrecord_t *record);
layer_state_t fi_keys_layer_state(layer_state_t state);
void          fi_keys_housekeeping(void);
