#!/bin/sh
# TurnShade for Google Chrome on Linux.
# Publish only through the verified yohi/turnshade GitHub Pages release site.
set -eu

EXTENSION_ID='__TURNSHADE_EXTENSION_ID__'
UPDATE_URL='https://yohi.github.io/turnshade/updates.xml'
INSTALL_DIR='/opt/google/chrome/extensions'
TARGET="$INSTALL_DIR/$EXTENSION_ID.json"

fail() { printf 'TurnShade: %s\n' "$*" >&2; exit 1; }
log() { printf 'TurnShade: %s\n' "$*"; }

[ "$(uname -s)" = "Linux" ] || fail 'Linux is required.'
if ! command -v google-chrome >/dev/null 2>&1 &&
   ! command -v google-chrome-stable >/dev/null 2>&1 &&
   [ ! -x /opt/google/chrome/chrome ]; then
  fail 'Google Chrome for Linux is not installed; Chromium/Snap paths are not supported.'
fi

for command in curl python3 install chmod tee; do
  command -v "$command" >/dev/null 2>&1 || fail "Missing dependency: $command"
done

# Never run a network script as root: only the final registration write needs sudo.
# Confirm the official update manifest still advertises the pinned extension ID
# and a same-origin, versioned CRX URL before any privileged operation.
MANIFEST_XML=$(curl -fsSL --connect-timeout 10 --max-time 30 "$UPDATE_URL") ||
  fail 'Failed to download updates.xml; no changes made.'
printf '%s' "$MANIFEST_XML" |
python3 -c '
import re, sys, xml.etree.ElementTree as ET
expected_id, expected_url = sys.argv[1:3]
if not re.fullmatch("[a-p]{32}", expected_id):
    sys.exit("TurnShade: invalid pinned extension ID")
data = sys.stdin.buffer.read(32769)
if len(data) > 32768:
    sys.exit("TurnShade: update manifest is too large")
try:
    root = ET.fromstring(data)
except ET.ParseError:
    sys.exit("TurnShade: invalid update manifest XML")
ns = "{http://www.google.com/update2/response}"
apps = root.findall(ns + "app")
if root.tag != ns + "gupdate" or len(apps) != 1 or apps[0].get("appid") != expected_id:
    sys.exit("TurnShade: extension ID mismatch in updates.xml")
checks = apps[0].findall(ns + "updatecheck")
if len(checks) != 1 or not re.fullmatch(r"[0-9]+(?:\.[0-9]+){1,3}", checks[0].get("version", "")):
    sys.exit("TurnShade: invalid update version")
codebase = checks[0].get("codebase", "")
if codebase != "https://yohi.github.io/turnshade/turnshade-v" + checks[0].get("version") + ".crx":
    sys.exit("TurnShade: unexpected CRX URL in updates.xml")
print("TurnShade: update manifest verified for " + expected_id)
' "$EXTENSION_ID" "$UPDATE_URL" ||
  fail 'Update manifest verification failed; no changes made.'

if [ -e "$TARGET" ] || [ -L "$TARGET" ]; then
  [ ! -L "$TARGET" ] || fail "Refusing symlink: $TARGET"
  [ -f "$TARGET" ] || fail "Existing path is not a regular file: $TARGET"
  python3 -c '
import json, sys
try:
    data = json.load(open(sys.argv[1], encoding="utf-8"))
except (OSError, ValueError):
    sys.exit(1)
sys.exit(0 if data == {"external_update_url": sys.argv[2]} else 1)
' "$TARGET" "$UPDATE_URL" ||
    fail "Existing registration differs; refusing to overwrite $TARGET"
  log "Already registered: $EXTENSION_ID (no changes)"
  exit 0
fi

# Limit elevated operations to the single fixed Chrome registration directory.
if [ "$(id -u)" -eq 0 ]; then
  install -d -m 755 "$INSTALL_DIR"
  printf '{"external_update_url":"%s"}\n' "$UPDATE_URL" > "$TARGET"
  chmod 644 "$TARGET"
else
  command -v sudo >/dev/null 2>&1 || fail 'sudo is required to register Chrome extension.'
  sudo install -d -m 755 "$INSTALL_DIR"
  printf '{"external_update_url":"%s"}\n' "$UPDATE_URL" |
    sudo tee "$TARGET" >/dev/null
  sudo chmod 644 "$TARGET"
fi
log "Registered extension: $EXTENSION_ID"
log 'Restart Google Chrome completely, then check chrome://extensions.'
log 'Chrome stores its installed extension internally; no unpacked source folder is required.'
