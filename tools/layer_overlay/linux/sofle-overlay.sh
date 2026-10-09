#!/bin/sh
# Launcher for Linux desktops. On Wayland the overlay runs through XWayland so
# it can stay on top and be positioned (GNOME and KDE both allow this for X11
# windows). layer_overlay does the same automatically when started directly.
if [ -n "$WAYLAND_DISPLAY" ] && [ -z "$QT_QPA_PLATFORM" ]; then
    export QT_QPA_PLATFORM=xcb
fi
exec python3 -m layer_overlay "$@"
