/*
 * X-Plane Popup Manager - KWin script
 *
 * Places X-Plane popup windows (matched by window title) at saved positions.
 * Geometry is stored as the *client* area (what X-Plane draws, excluding the
 * KWin title bar), so it stays correct whether or not the window has a frame.
 *
 * A window is held at its saved geometry until you move/resize it by hand;
 * after that it is left alone until it is reopened or the re-apply shortcut
 * is pressed.
 *
 * The layout is read from kwinrc, group [Script-xplane-popup-manager],
 * key "Layout" (JSON), written by save-layout.py, merged over DEFAULT_LAYOUT.
 */

const DEFAULT_LAYOUT = {
    "LEFT PDU":  { x: 230,  y: 2188, width: 1566, height: 1045 },
    "UPPER MDU": { x: 1920, y: 2188, width: 1549, height: 1046 },
    "LOWER MDU": { x: 3840, y: 1163, width: 1427, height: 907 },
};

// Upper bound on corrections per window appearance, in case the aircraft keeps
// fighting back (or KWin's aspect-ratio constraint makes the target unreachable).
const MAX_CORRECTIONS = 20;

const windowClass = readConfig("WindowClass", "X-Plane").toString().toLowerCase();
const layout = loadLayout();
const state = {}; // internalId -> { userMoved, corrections }

function log(msg) {
    print("xplane-popup-manager: " + msg);
}

// Saved entries override the defaults; a null entry removes one.
function loadLayout() {
    const merged = Object.assign({}, DEFAULT_LAYOUT);
    const raw = readConfig("Layout", "").toString();
    if (raw !== "") {
        try {
            Object.assign(merged, JSON.parse(raw));
        } catch (e) {
            log("invalid Layout in kwinrc, using defaults: " + e);
        }
    }
    for (const title of Object.keys(merged)) {
        if (!merged[title])
            delete merged[title];
    }
    return merged;
}

function isXPlaneWindow(window) {
    return String(window.resourceClass).toLowerCase() === windowClass;
}

function stateOf(window) {
    const id = window.internalId.toString();
    if (!state[id])
        state[id] = { userMoved: false, corrections: 0 };
    return state[id];
}

function resetState(window) {
    const s = stateOf(window);
    s.userMoved = false;
    s.corrections = 0;
}

// Convert a saved client rect into a frame rect using the window's current
// decoration margins.
function frameRectFor(window, client) {
    const f = window.frameGeometry;
    const c = window.clientGeometry;
    const left = c.x - f.x;
    const top = c.y - f.y;
    const right = (f.x + f.width) - (c.x + c.width);
    const bottom = (f.y + f.height) - (c.y + c.height);
    return {
        x: client.x - left,
        y: client.y - top,
        width: client.width + left + right,
        height: client.height + top + bottom,
    };
}

function sameRect(a, b) {
    return Math.abs(a.x - b.x) <= 1 && Math.abs(a.y - b.y) <= 1 &&
        Math.abs(a.width - b.width) <= 1 && Math.abs(a.height - b.height) <= 1;
}

function apply(window) {
    if (!isXPlaneWindow(window))
        return;
    const saved = layout[window.caption];
    if (!saved)
        return;
    const s = stateOf(window);
    if (s.userMoved)
        return;

    const target = frameRectFor(window, saved);
    if (sameRect(window.frameGeometry, target))
        return;
    if (s.corrections >= MAX_CORRECTIONS) {
        if (s.corrections === MAX_CORRECTIONS) {
            log("giving up on '" + window.caption + "' after " + MAX_CORRECTIONS + " corrections");
            s.corrections++;
        }
        return;
    }
    s.corrections++;
    window.frameGeometry = target;
}

function setup(window) {
    if (!isXPlaneWindow(window))
        return;
    window.captionChanged.connect(() => {
        resetState(window);
        apply(window);
    });
    window.frameGeometryChanged.connect(() => apply(window));
    window.interactiveMoveResizeStarted.connect(() => {
        stateOf(window).userMoved = true;
    });
    apply(window);
}

workspace.windowAdded.connect(setup);
workspace.windowRemoved.connect((window) => {
    delete state[window.internalId.toString()];
});
workspace.windowList().forEach(setup);

registerShortcut("XPlanePopupManagerReapply", "X-Plane Popup Manager: Re-apply Layout", "Meta+Ctrl+P", () => {
    workspace.windowList().forEach((window) => {
        if (!isXPlaneWindow(window))
            return;
        resetState(window);
        apply(window);
    });
});

log("loaded, managing: " + Object.keys(layout).join(", "));
