"""Shared helpers: X-Plane web API (read-only) and KWin script config."""

import base64
import json
import os
import socket
import struct
import subprocess
import sys
import urllib.parse
import urllib.request

SCRIPT_ID = "xplane-popup-manager"
CONFIG_GROUP = f"Script-{SCRIPT_ID}"
API_HOST, API_PORT = "127.0.0.1", 8086
API = f"http://{API_HOST}:{API_PORT}/api/v2"

AIRCRAFT_PATH_DATAREF = "sim/aircraft/view/acf_relative_path"
AIRCRAFT_NAME_DATAREF = "sim/aircraft/view/acf_ui_name"


def run(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout


# --- X-Plane web API ---------------------------------------------------------

def _get(path, params=None):
    url = API + path
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    with urllib.request.urlopen(url, timeout=2) as response:
        return json.load(response)


def decode_string(value):
    """Byte-array datarefs arrive base64-encoded and NUL-padded."""
    return base64.b64decode(value).split(b"\0")[0].decode(errors="replace")


class XPlaneAPI:
    """Reads the loaded aircraft. Dataref ids are only valid for one X-Plane
    session, so they are looked up again whenever a request fails."""

    def __init__(self):
        self._ids = None

    def dataref_ids(self):
        if self._ids is None:
            names = [AIRCRAFT_PATH_DATAREF, AIRCRAFT_NAME_DATAREF]
            data = _get("/datarefs", {"filter[name]": names})["data"]
            self._ids = {d["name"]: d["id"] for d in data}
        return self._ids

    def read_string(self, name):
        return decode_string(_get(f"/datarefs/{self.dataref_ids()[name]}/value")["data"])

    def current_aircraft(self):
        """Return (relative_path, ui_name), or None if X-Plane is unreachable."""
        for _ in range(2):
            try:
                return self.read_string(AIRCRAFT_PATH_DATAREF), self.read_string(AIRCRAFT_NAME_DATAREF)
            except (OSError, KeyError, ValueError):
                self._ids = None
        return None


class WebSocket:
    """Minimal WebSocket client (RFC 6455) for X-Plane's /api/v2 endpoint:
    text messages only, no extensions."""

    def __init__(self, path="/api/v2"):
        self.sock = socket.create_connection((API_HOST, API_PORT), timeout=5)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((
            f"GET {path} HTTP/1.1\r\nHost: {API_HOST}:{API_PORT}\r\n"
            "Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        ).encode())
        response = b""
        while b"\r\n\r\n" not in response:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("connection closed during handshake")
            response += chunk
        header, self._buffer = response.split(b"\r\n\r\n", 1)
        if b" 101 " not in header.split(b"\r\n", 1)[0]:
            raise ConnectionError("WebSocket upgrade refused: " + header.split(b"\r\n", 1)[0].decode())
        # Updates only arrive when something changes, so wait indefinitely;
        # a crashed or closed X-Plane still ends the connection.
        self.sock.settimeout(None)

    def close(self):
        self.sock.close()

    def _recv_exact(self, n):
        while len(self._buffer) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("connection closed")
            self._buffer += chunk
        data, self._buffer = self._buffer[:n], self._buffer[n:]
        return data

    def _send_frame(self, opcode, payload):
        mask = os.urandom(4)
        n = len(payload)
        if n < 126:
            header = struct.pack("!BB", 0x80 | opcode, 0x80 | n)
        elif n < 1 << 16:
            header = struct.pack("!BBH", 0x80 | opcode, 0x80 | 126, n)
        else:
            header = struct.pack("!BBQ", 0x80 | opcode, 0x80 | 127, n)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(header + mask + masked)

    def send_json(self, message):
        self._send_frame(0x1, json.dumps(message).encode())

    def recv_json(self):
        """Block until the next complete text message and return it parsed."""
        message = b""
        while True:
            b1, b2 = self._recv_exact(2)
            fin, opcode, n = b1 & 0x80, b1 & 0x0F, b2 & 0x7F
            if n == 126:
                n, = struct.unpack("!H", self._recv_exact(2))
            elif n == 127:
                n, = struct.unpack("!Q", self._recv_exact(8))
            mask = self._recv_exact(4) if b2 & 0x80 else None
            payload = self._recv_exact(n)
            if mask:
                payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
            if opcode == 0x8:
                raise ConnectionError("closed by X-Plane")
            if opcode == 0x9:
                self._send_frame(0xA, payload)
                continue
            if opcode in (0x0, 0x1):
                message += payload
                if fin:
                    return json.loads(message)


# --- KWin script config (kwinrc) ---------------------------------------------

def read_config(key):
    return run("kreadconfig6", "--file", "kwinrc", "--group", CONFIG_GROUP, "--key", key).strip()


def write_config(key, value):
    subprocess.run(["kwriteconfig6", "--file", "kwinrc", "--group", CONFIG_GROUP,
                    "--key", key, value], check=True)


def read_layout():
    """Layout is {"shared": {title: geom}, "aircraft": {acf_path: {title: geom}}}."""
    raw = read_config("Layout")
    layout = {}
    if raw:
        try:
            layout = json.loads(raw)
        except json.JSONDecodeError:
            print("warning: Layout in kwinrc is not valid JSON, starting fresh", file=sys.stderr)
    layout.setdefault("shared", {})
    layout.setdefault("aircraft", {})
    return layout


def write_layout(layout):
    write_config("Layout", json.dumps(layout, separators=(",", ":")))


def use_aircraft(path):
    """Point the KWin script at an aircraft's layout and reload it, which also
    re-places all open popups. Returns False if the script isn't enabled."""
    write_config("Aircraft", path)
    return reload_script()


def reload_script():
    """Reload the KWin script so it re-reads its config. Returns False if it
    isn't enabled."""
    def kwin(method, *args):
        return run("qdbus6", "org.kde.KWin", "/Scripting", f"org.kde.kwin.Scripting.{method}", *args).strip()

    if kwin("isScriptLoaded", SCRIPT_ID) != "true":
        return False
    kwin("unloadScript", SCRIPT_ID)
    kwin("start")
    return True
