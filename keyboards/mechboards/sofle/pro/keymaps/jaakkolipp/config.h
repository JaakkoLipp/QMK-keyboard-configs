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
