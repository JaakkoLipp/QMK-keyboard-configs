# qmk keyboard configs for custom keyboards. 

## sofle pro (v2+) Finnish QMK Layout
This repository contains a complete QMK configuration for a Sofle V2 split keyboard using the Windows Finnish layout. The firmware defines three layers: Base, Symbol, and Extra, each optimized for writing, coding, and extended controls such as mouse keys and numpad input for the finnish keyboard layout.

### base layer
```
 LEFT HALF                                   RIGHT HALF
┌────┬────┬────┬────┬────┬────┐         ┌────┬────┬────┬────┬────┬────┐
│  § │  1 │  2 │  3 │  4 │  5 │         │  6 │  7 │  8 │  9 │  0 │  + │
├────┼────┼────┼────┼────┼────┤         ├────┼────┼────┼────┼────┼────┤
│Esc │  Q │  W │  E │  R │  T │         │  Y │  U │  I │  O │  P │Bksp│
├────┼────┼────┼────┼────┼────┤         ├────┼────┼────┼────┼────┼────┤
│Tab │  A │  S │  D │  F │  G │         │  H │  J │  K │  L │  Ö │  Ä │
├────┼────┼────┼────┼────┼────┤         ├────┼────┼────┼────┼────┼────┤
│Shift│ Z │  X │  C │  V │  B │Mute│Play│  N │  M │  , │  . │  - │Shift│
└────┴────┴────┴────┴────┴────┘         └────┴────┴────┴────┴────┴────┘
          ┌────┬────┬────┬─────┐        ┌────┬────┬─────┬────┐
          │GUI │Alt │Ctl │Space│        │Enter│Ctl │AltGr│GUI│
          └────┴────┴────┴─────┘        └────┴────┴─────┴────┘
```

### Symbol layer
```

 LEFT HALF                                   RIGHT HALF
┌────┬────┬────┬────┬────┬────┐         ┌────┬────┬────┬────┬────┬────┐
│ F1 │ F2 │ F2 │ F4 │ F5 │ F6 │         │ F7 │ F8 │ F9 │F10 │F11 │F12 │
├────┼────┼────┼────┼────┼────┤         ├────┼────┼────┼────┼────┼────┤
│    │  # │  [ │  ] │  = │  ' │         │PgUp│Home│ End│Prt │ Ins│ Del│
├────┼────┼────┼────┼────┼────┤         ├────┼────┼────┼────┼────┼────┤
│Caps│  { │  ( │  ) │  } │  _ │         │Menu│ ←  │ ↑  │ ↓  │ →  │  å │
├────┼────┼────┼────┼────┼────┤         ├────┼────┼────┼────┼────┼────┤
│    │  | │  < │  > │  / │  \ │    │    │PgDn│Prev│Play│Next│  ` │    │
└────┴────┴────┴────┴────┴────┘         └────┴────┴────┴────┴────┴────┘
          ┌────┬────┬────┬────┐         ┌────────┬────┬────┬────┐
          │    │    │    │    │         │LayerLck│    │    │    │
          └────┴────┴────┴────┘         └────────┴────┴────┴────┘
```

### Extra layer
```

 LEFT HALF                                   RIGHT HALF
┌────┬────┬────┬────┬────┬────┐         ┌────┬────┬────┬────┬────┬────┐
│F13 │F14 │F15 │F16 │F17 │F18 │         │F19 │F20 │F21 │F22 │F23 │F24 │
├────┼────┼────┼────┼────┼────┤         ├────┼────┼────┼────┼────┼────┤
│PB1 │PB2 │ML  │M↑  │MR  │WH↑ │         │Num │  7 │  8 │  9 │  - │    │
├────┼────┼────┼────┼────┼────┤         ├────┼────┼────┼────┼────┼────┤
│PB3 │PB4 │M←  │M↓  │M→  │WH↓ │         │  / │  4 │  5 │  6 │  + │    │
├────┼────┼────┼────┼────┼────┤         ├────┼────┼────┼────┼────┼────┤
│PB5 │PB6 │WH← │MM  │WH→ │MB5 │    │    │  * │  1 │  2 │  3 │  , │    │
└────┴────┴────┴────┴────┴────┘         └────┴────┴────┴────┴────┴────┘
          ┌────┬────┬────┬────┐         ┌──────┬────┬────┬────┐
          │    │    │    │    │         │Lck   │  0 │  . │Enter│
          └────┴────┴────┴────┘         └──────┴────┴────┴────┘
```

The keymap is built using keymap_finnish.h, enabling correct Scandinavian symbol output. Three layers provide full typing, symbol access, nav cluster, mouse control, media controls, and a complete numpad. The repository includes encoder mappings and optional layer lock support.


## PocketType small pocket sized custom keyboard
config file located in kedyboards/pockettype. minimal compromise apporoach despite small physical size and keycount.
