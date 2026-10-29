# X-Plane Popup Manager

A KWin script that puts X-Plane instrument popups (matched by window title) at
saved positions and sizes. Runs entirely in KWin; nothing in X-Plane is touched.

## Requirements

This is **Linux and KDE Plasma specific**: it needs KWin as the window manager
(tested with Plasma 6.8 on Wayland, X-Plane running through XWayland) and won't
work on other desktops, Windows or macOS. The helper scripts use Python 3,
`xdotool`, `xprop`, `xwininfo`, `qdbus6`, `kreadconfig6`/`kwriteconfig6` and
`kpackagetool6`.

## Install / update

    ./install.sh

## Saving a layout

Arrange the popups by hand, then:

    ./save-layout.py            # save all open popups and reload the script
    ./save-layout.py --print    # preview only
    ./save-layout.py --remove "LOWER MDU"

Entries are merged, so popups from different aircraft accumulate in one
layout. It is stored as JSON in `~/.config/kwinrc`, group
`[Script-xplane-popup-manager]`, key `Layout`, on top of the defaults in
`package/contents/code/main.js`.

Tip: bind `save-layout.py` to a key in System Settings → Keyboard → Shortcuts
→ Add New → Command.

## Behaviour

- A popup is placed when it opens (or gets renamed to a known title), and is
  held there if the aircraft tries to move it.
- Once you drag or resize it by hand, it is left alone until it is reopened.
- **Meta+Ctrl+P** re-applies the layout to all open popups (rebindable under
  Shortcuts → KWin).
- Geometry is the client area (excluding the title bar), in global XWayland
  pixel coordinates.

## License

BSD 2-Clause, see [LICENSE](LICENSE).
