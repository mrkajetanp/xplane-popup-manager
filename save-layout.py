#!/usr/bin/env python3
"""Save the current geometry of open X-Plane popup windows for the KWin script.

Popups are saved under the aircraft currently loaded in X-Plane (read from its
web API), or under the shared layout used for every aircraft with --shared.
Aircraft-specific entries take precedence over shared ones.

Usage:
    save-layout.py                 save open popups for the current aircraft
    save-layout.py --shared        save open popups for all aircraft
    save-layout.py --print         show open popups and the saved layout
    save-layout.py --remove TITLE  forget a popup (current aircraft, or --shared)
"""

import argparse
import json
import re
import sys

from common import XPlaneAPI, read_layout, reload_script, run, use_aircraft, write_layout

WINDOW_CLASS = "X-Plane"
# The main simulator window ("X-Plane Personal Edition", etc.) is not a popup.
MAIN_WINDOW_RE = re.compile(r"^X-Plane\b")


def xprop_value(window_id, prop):
    out = run("xprop", "-id", window_id, prop)
    return re.findall(r'"((?:[^"\\]|\\.)*)"', out)


def window_geometry(window_id):
    info = run("xwininfo", "-id", window_id)
    fields = {
        "x": r"Absolute upper-left X:\s+(-?\d+)",
        "y": r"Absolute upper-left Y:\s+(-?\d+)",
        "width": r"Width:\s+(\d+)",
        "height": r"Height:\s+(\d+)",
    }
    if "IsViewable" not in info:
        return None
    return {k: int(re.search(p, info).group(1)) for k, p in fields.items()}


def open_popups():
    ids = run("xdotool", "search", "--class", f"^{re.escape(WINDOW_CLASS)}$").split()
    popups = {}
    for window_id in ids:
        wm_class = xprop_value(window_id, "WM_CLASS")
        if len(wm_class) < 2 or wm_class[1] != WINDOW_CLASS:
            continue
        title = (xprop_value(window_id, "_NET_WM_NAME") or [""])[0]
        if not title or MAIN_WINDOW_RE.match(title):
            continue
        geometry = window_geometry(window_id)
        if geometry:
            popups[title] = geometry
    return popups


def fmt(geometry):
    return f"{geometry['x']},{geometry['y']} {geometry['width']}x{geometry['height']}"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--shared", action="store_true", help="use the layout shared by all aircraft")
    parser.add_argument("--print", action="store_true", help="only print, change nothing")
    parser.add_argument("--remove", metavar="TITLE", action="append", default=[],
                        help="forget the popup with this title")
    args = parser.parse_args()

    layout = read_layout()
    aircraft = None if args.shared and not args.print else XPlaneAPI().current_aircraft()

    if args.print:
        if aircraft:
            print(f"current aircraft: {aircraft[1]} ({aircraft[0]})")
        print("open popups:", json.dumps(open_popups(), indent=2))
        print("saved layout:", json.dumps(layout, indent=2))
        return

    if args.shared:
        section, label = layout["shared"], "shared"
    else:
        if aircraft is None:
            sys.exit("can't reach X-Plane's web API to identify the aircraft (use --shared to save for all aircraft)")
        path, name = aircraft
        section, label = layout["aircraft"].setdefault(path, {}), name

    if args.remove:
        for title in args.remove:
            if section.pop(title, None) is None:
                print(f"not in {label} layout: {title}")
            else:
                print(f"removed from {label}: {title}")
    else:
        popups = open_popups()
        if not popups:
            sys.exit("no open X-Plane popup windows found")
        for title, geometry in popups.items():
            section[title] = geometry
            print(f"saved for {label}: {title:<20} {fmt(geometry)}")

    layout["aircraft"] = {k: v for k, v in layout["aircraft"].items() if v}
    write_layout(layout)
    # Also keeps the KWin script on the right aircraft if the watcher isn't running.
    if not (use_aircraft(aircraft[0]) if aircraft else reload_script()):
        print("note: KWin script is not loaded; layout saved but not applied")


if __name__ == "__main__":
    main()
