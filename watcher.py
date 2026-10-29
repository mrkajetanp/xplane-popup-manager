#!/usr/bin/env python3
"""Tell the KWin script which aircraft is loaded in X-Plane.

Subscribes to the loaded aircraft's path over X-Plane's web API WebSocket;
X-Plane only sends a message when the value changes, so there is no polling.
On a change, the aircraft is written to kwinrc and the KWin script reloaded so
that aircraft's popup layout is used. Keeps running (and reconnecting) until
interrupted, so it can be started before or after X-Plane.
"""

import time

from common import (AIRCRAFT_NAME_DATAREF, AIRCRAFT_PATH_DATAREF, WebSocket, XPlaneAPI,
                    decode_string, read_config, use_aircraft)

# How often to try connecting while X-Plane isn't running.
RECONNECT_SECONDS = 30


def log(message):
    print(message, flush=True)


class Watcher:
    def __init__(self):
        self.current = read_config("Aircraft")

    def aircraft_changed(self, api, path):
        self.current = path
        reloaded = use_aircraft(path)
        name = api.read_string(AIRCRAFT_NAME_DATAREF)
        log(f"aircraft: {name} ({path}){'' if reloaded else ' [KWin script not loaded]'}")

    def follow(self):
        """Follow aircraft changes for one X-Plane session; returns when the
        connection ends. Raises OSError if X-Plane can't be reached at all."""
        api = XPlaneAPI()
        path_id = api.dataref_ids()[AIRCRAFT_PATH_DATAREF]
        ws = WebSocket()
        log("connected to X-Plane")
        try:
            ws.send_json({"req_id": 1, "type": "dataref_subscribe_values",
                          "params": {"datarefs": [{"id": path_id}]}})
            while True:
                message = ws.recv_json()
                if message.get("type") == "result" and not message.get("success"):
                    raise ConnectionError(f"subscription failed: {message}")
                if message.get("type") != "dataref_update_values":
                    continue
                value = message.get("data", {}).get(str(path_id))
                path = decode_string(value) if value else ""
                if path and path != self.current:
                    self.aircraft_changed(api, path)
        except (OSError, ValueError) as e:
            log(f"disconnected from X-Plane: {e}")
        finally:
            ws.close()

    def run(self):
        log(f"watcher started, last aircraft: {self.current or '(none)'}")
        while True:
            try:
                self.follow()
            except (OSError, KeyError, ValueError):
                pass  # X-Plane not running (or API not up yet)
            time.sleep(RECONNECT_SECONDS)


def main():
    Watcher().run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
