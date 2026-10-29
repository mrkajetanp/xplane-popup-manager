#!/bin/sh
# Install (or update) the KWin script, enable it, and (re)load it.
set -e
cd "$(dirname "$0")"

id=xplane-popup-manager
if kpackagetool6 --type=KWin/Script --show "$id" >/dev/null 2>&1; then
    kpackagetool6 --type=KWin/Script --upgrade package
else
    kpackagetool6 --type=KWin/Script --install package
fi
kwriteconfig6 --file kwinrc --group Plugins --key "${id}Enabled" true

# Force a fresh load so code changes take effect.
qdbus6 org.kde.KWin /Scripting org.kde.kwin.Scripting.unloadScript "$id" >/dev/null
qdbus6 org.kde.KWin /KWin reconfigure
qdbus6 org.kde.KWin /Scripting org.kde.kwin.Scripting.start

printf 'KWin script loaded: %s\n' "$(qdbus6 org.kde.KWin /Scripting org.kde.kwin.Scripting.isScriptLoaded "$id")"
