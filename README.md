# X-Plane Popup Manager

A KWin script that puts X-Plane instrument popups (matched by window title) at
saved positions and sizes, with a separate layout per aircraft. Runs entirely
outside X-Plane; nothing in the sim is modified.

## Requirements

This is **Linux and KDE Plasma specific**: it needs KWin as the window manager
(tested with Plasma 6.8 on Wayland, X-Plane running through XWayland) and won't
work on other desktops, Windows or macOS. The helper scripts use Python 3,
`xdotool`, `xprop`, `xwininfo`, `qdbus6`, `kreadconfig6`/`kwriteconfig6` and
`kpackagetool6`. Per-aircraft layouts need X-Plane 12's web API (on by default
at `127.0.0.1:8086`).

## Parts

- `package/` — the KWin script. Places popups using the layout for the
  current aircraft.
- `watcher.py` — tells the KWin script which aircraft is loaded. It subscribes
  to `sim/aircraft/view/acf_relative_path` over X-Plane's web API WebSocket
  (`127.0.0.1:8086`). X-Plane only sends a message when the aircraft changes,
  so there is no polling: one dataref lookup and one connection per X-Plane
  session. While X-Plane isn't running it tries to connect every 30 s.
- `save-layout.py` — saves the current popup positions.
- `apply-layout.py` — one-off: detects the loaded aircraft and re-places all
  open popups by its layout, including ones you moved by hand.

## Install / update

    ./install.sh

This installs and loads the KWin script. The watcher is not started
automatically; run it yourself while flying:

    ./watcher.py

Without the watcher, the KWin script keeps using the layout of the last
aircraft it was told about. Run `./apply-layout.py` after switching aircraft
(or any time) to pick up the current one and place its popups; every
`save-layout.py` run updates it too.

## Saving a layout

Arrange the popups by hand, then:

    ./save-layout.py                  # save for the current aircraft
    ./save-layout.py --shared         # save for all aircraft
    ./save-layout.py --print          # show current aircraft, popups, saved layout
    ./save-layout.py --remove "LOWER MDU"            # current aircraft
    ./save-layout.py --shared --remove "LOWER MDU"   # shared layout

Aircraft are identified by `.acf` path, so liveries share a layout. The active
layout is the shared one overlaid with the current aircraft's. It is stored as
JSON in `~/.config/kwinrc`, group `[Script-xplane-popup-manager]`, key
`Layout`; the current aircraft is in key `Aircraft`.

Tip: bind `save-layout.py` to a key in System Settings → Keyboard → Shortcuts
→ Add New → Command.

## Behaviour

- A popup is placed when it opens (or gets renamed to a known title), and is
  held there if the aircraft tries to move it.
- Once you drag or resize it by hand, it is left alone until it is reopened.
- **Meta+Ctrl+P** re-applies the layout to all open popups (rebindable under
  Shortcuts → KWin).
- Changing aircraft reloads the KWin script, which applies the new layout.
- Geometry is the client area (excluding the title bar), in global XWayland
  pixel coordinates.

## License

BSD 2-Clause, see [LICENSE](LICENSE).
