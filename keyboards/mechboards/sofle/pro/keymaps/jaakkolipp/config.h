// Copyright 2026 Jaakko Lipponen
// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

// VIA only loads this many layers from the compiled keymap.
#define DYNAMIC_KEYMAP_LAYER_COUNT 5

// Tap-hold: only the Caps-position Ctrl/Esc key is a mod-tap.
#define TAPPING_TERM 200
#define HOLD_ON_OTHER_KEY_PRESS_PER_KEY

// Caps Word: tap both Shifts. Finnish handling lives in features/fi_keys.c.
#define BOTH_SHIFTS_TURNS_ON_CAPS_WORD
#define CAPS_WORD_IDLE_TIMEOUT 3000

// A locked layer turns itself off after a minute without typing.
#define LAYER_LOCK_IDLE_TIMEOUT 60000

// Linux desktop switching: Ctrl+GUI+arrow (KDE, same as Windows) by default.
// Uncomment for GNOME, which uses Ctrl+Alt+arrow.
// #define DESKTOP_GNOME

// Split sync for the OLEDs and RGB on the non-USB half.
#define SPLIT_LAYER_STATE_ENABLE
#define SPLIT_LED_STATE_ENABLE
#define SPLIT_MODS_ENABLE
#define SPLIT_WPM_ENABLE
#define SPLIT_OLED_ENABLE
#define SPLIT_ACTIVITY_ENABLE
#define SPLIT_DETECTED_OS_ENABLE
// Our own state (features/shared.h): locked layers, clock, Claude status...
#define SPLIT_TRANSACTION_IDS_USER RPC_ID_USER_SHARED

// Displays sleep after a minute; RGB after five (features/rgb_layers.c),
// except while Claude Code is waiting for you.
#define OLED_TIMEOUT 60000
#define RGB_MATRIX_SLEEP
