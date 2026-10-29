#!/usr/bin/env python3
"""Place all open X-Plane popups according to the saved layout, once.

Asks X-Plane's web API which aircraft is loaded, points the KWin script at
that aircraft's layout and reloads it, which re-places every open popup
(including ones you moved by hand). If X-Plane can't be reached, the last
known aircraft is used.
"""

import sys

from common import XPlaneAPI, read_config, read_layout, reload_script, use_aircraft


def main():
    aircraft = XPlaneAPI().current_aircraft()
    if aircraft:
        path, name = aircraft
        loaded = use_aircraft(path)
    else:
        path = name = read_config("Aircraft")
        print(f"can't reach X-Plane's web API, using last known aircraft: {path or '(none)'}", file=sys.stderr)
        loaded = reload_script()
    if not loaded:
        sys.exit("KWin script is not loaded; run ./install.sh")

    layout = read_layout()
    titles = sorted(set(layout["shared"]) | set(layout["aircraft"].get(path, {})))
    print(f"applied layout for {name or '(no aircraft)'}: {', '.join(titles) or '(nothing saved)'}")


if __name__ == "__main__":
    main()
