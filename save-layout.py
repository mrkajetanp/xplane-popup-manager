#!/usr/bin/env python3
"""Save the current geometry of open X-Plane popup windows for the KWin script.

Reads the popups through XWayland (xdotool/xprop/xwininfo), merges them into
the "Layout" key of [Script-xplane-popup-manager] in kwinrc, and reloads the
KWin script so the new layout takes effect immediately.

Usage:
    save-layout.py              save all open popups
    save-layout.py --print      show what would be saved, change nothing
    save-layout.py --remove T   stop managing the popup titled T
"""

import argparse
import json
import re
import subprocess
import sys

SCRIPT_ID = "xplane-popup-manager"
CONFIG_GROUP = f"Script-{SCRIPT_ID}"
WINDOW_CLASS = "X-Plane"
# The main simulator window ("X-Plane Personal Edition", etc.) is not a popup.
MAIN_WINDOW_RE = re.compile(r"^X-Plane\b")


def run(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout


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


def read_layout():
    raw = run("kreadconfig6", "--file", "kwinrc", "--group", CONFIG_GROUP, "--key", "Layout").strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print("warning: existing Layout in kwinrc is not valid JSON, replacing it", file=sys.stderr)
        return {}


def write_layout(layout):
    subprocess.run(["kwriteconfig6", "--file", "kwinrc", "--group", CONFIG_GROUP,
                    "--key", "Layout", json.dumps(layout, separators=(",", ":"))], check=True)


def reload_script():
    def kwin(method, *args):
        return run("qdbus6", "org.kde.KWin", "/Scripting", f"org.kde.kwin.Scripting.{method}", *args).strip()

    if kwin("isScriptLoaded", SCRIPT_ID) != "true":
        print(f"note: KWin script '{SCRIPT_ID}' is not loaded; layout saved but not applied")
        return
    kwin("unloadScript", SCRIPT_ID)
    kwin("start")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--print", action="store_true", help="only print the open popups")
    parser.add_argument("--remove", metavar="TITLE", action="append", default=[],
                        help="stop managing the popup with this title")
    args = parser.parse_args()

    if args.print:
        print(json.dumps(open_popups(), indent=2))
        return

    layout = read_layout()
    if args.remove:
        for title in args.remove:
            # null overrides an entry in the script's built-in defaults
            layout[title] = None
            print(f"removed: {title}")
    else:
        popups = open_popups()
        if not popups:
            sys.exit("no open X-Plane popup windows found")
        for title, geometry in popups.items():
            layout[title] = geometry
            print(f"saved: {title:<20} {geometry['x']},{geometry['y']} {geometry['width']}x{geometry['height']}")

    write_layout(layout)
    reload_script()


if __name__ == "__main__":
    main()
