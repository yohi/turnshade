#!/bin/sh
# TurnShade for Google Chrome on Linux.
# Publish only through the verified yohi/turnshade GitHub Pages release site.
set -eu

EXTENSION_ID='__TURNSHADE_EXTENSION_ID__'
UPDATE_URL='https://yohi.github.io/turnshade/updates.xml'
PRIMARY_DIR='/opt/google/chrome/extensions'
ALTERNATE_DIR='/usr/share/google-chrome/extensions'

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

# Both locations are supported by Google Chrome for Linux.
# Prefer an existing registration wherever it is; do not create duplicates.
EXISTING_TARGET=''
for candidate in "$PRIMARY_DIR" "$ALTERNATE_DIR"; do
  target="$candidate/$EXTENSION_ID.json"
  if [ -e "$target" ] || [ -L "$target" ]; then
    [ ! -L "$target" ] || fail "Refusing symlink: $target"
    [ -f "$target" ] || fail "Existing path is not a regular file: $target"
    [ -z "$EXISTING_TARGET" ] ||
      fail "Registration exists in both Chrome directories; inspect them manually"
    EXISTING_TARGET="$target"
  fi
done

if [ -n "$EXISTING_TARGET" ]; then
  python3 -c '
import json, sys
try:
    with open(sys.argv[1], encoding="utf-8") as stream:
        data = json.load(stream)
except (OSError, ValueError):
    sys.exit(1)
sys.exit(0 if data == {"external_update_url": sys.argv[2]} else 1)
' "$EXISTING_TARGET" "$UPDATE_URL" ||
    fail "Existing registration differs; refusing to overwrite $EXISTING_TARGET"
  log "Already registered: $EXTENSION_ID at $EXISTING_TARGET (no changes)"
  exit 0
fi

# Use an already-present, official Chrome directory when possible. For a
# fresh Google Chrome installation, use its documented /opt location.
if [ -d "$PRIMARY_DIR" ]; then
  INSTALL_DIR="$PRIMARY_DIR"
elif [ -d "$ALTERNATE_DIR" ]; then
  INSTALL_DIR="$ALTERNATE_DIR"
else
  INSTALL_DIR="$PRIMARY_DIR"
fi
[ ! -L "$INSTALL_DIR" ] || fail "Refusing symlink directory: $INSTALL_DIR"
TARGET="$INSTALL_DIR/$EXTENSION_ID.json"

# Elevated operations are limited to one of Chrome's two documented directories.
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
