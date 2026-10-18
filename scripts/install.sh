#!/bin/sh
# TurnShade for Google Chrome on Linux.
# Publish only through the verified yohi/turnshade GitHub Pages release site.
set -eu

EXTENSION_ID='__TURNSHADE_EXTENSION_ID__'
UPDATE_URL='https://yohi.github.io/turnshade/updates.xml'
SHARED_DIR='/usr/share/google-chrome/extensions'
CHANNEL='stable'

fail() { printf 'TurnShade: %s\n' "$*" >&2; exit 1; }
log() { printf 'TurnShade: %s\n' "$*"; }

usage() {
  printf '%s\n' 'Usage: sh install.sh [--channel stable|beta|dev]'
  printf '%s\n' 'This registers TurnShade for all profiles in the selected Chrome channel.'
  printf '%s\n' 'Profile-specific installation is not supported.'
}

case "$#" in
  0) ;;
  1)
    case "$1" in
      --channel=*) CHANNEL=$(printf '%s' "$1" | sed 's/^--channel=//') ;;
      --help|-h) usage; exit 0 ;;
      --profile|--profile=*) fail 'Profile-specific install unsupported; manage enablement within each profile at chrome://extensions.' ;;
      *) fail 'Unknown option. Run with --help.' ;;
    esac
    ;;
  2)
    [ "$1" = '--channel' ] || fail 'Unknown option. Run with --help.'
    CHANNEL="$2"
    ;;
  *) fail 'Too many arguments. Run with --help.' ;;
esac

case "$CHANNEL" in
  stable)
    CHANNEL_DIR='/opt/google/chrome/extensions'
    BROWSER_COMMAND='google-chrome-stable'
    FALLBACK_COMMAND='google-chrome'
    BROWSER_BINARY='/opt/google/chrome/chrome'
    ;;
  beta)
    CHANNEL_DIR='/opt/google/chrome-beta/extensions'
    BROWSER_COMMAND='google-chrome-beta'
    FALLBACK_COMMAND='google-chrome-beta'
    BROWSER_BINARY='/opt/google/chrome-beta/chrome'
    ;;
  dev)
    CHANNEL_DIR='/opt/google/chrome-unstable/extensions'
    BROWSER_COMMAND='google-chrome-unstable'
    FALLBACK_COMMAND='google-chrome-unstable'
    BROWSER_BINARY='/opt/google/chrome-unstable/chrome'
    ;;
  *) fail "Unsupported Chrome channel: $CHANNEL (choose stable, beta, dev)" ;;
esac

[ "$(uname -s)" = "Linux" ] || fail 'Linux is required.'
if ! command -v "$BROWSER_COMMAND" >/dev/null 2>&1 &&
   ! command -v "$FALLBACK_COMMAND" >/dev/null 2>&1 &&
   [ ! -x "$BROWSER_BINARY" ]; then
  fail "Google Chrome $CHANNEL is not installed (Chromium and Snap are unsupported)."
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

# Chromium checks the per-channel executable directory and the shared
# /usr/share location. Avoid fresh shared registration because it affects
# other channels; respect an existing one without creating duplicates.
[ ! -L "$CHANNEL_DIR" ] || fail "Refusing symlink directory: $CHANNEL_DIR"
[ ! -L "$SHARED_DIR" ] || fail "Refusing symlink directory: $SHARED_DIR"
EXISTING_TARGET=''
for candidate in "$CHANNEL_DIR" "$SHARED_DIR"; do
  target="$candidate/$EXTENSION_ID.json"
  if [ -e "$target" ] || [ -L "$target" ]; then
    [ ! -L "$target" ] || fail "Refusing symlink: $target"
    [ -f "$target" ] || fail "Existing path is not a regular file: $target"
    [ -z "$EXISTING_TARGET" ] ||
      fail 'Registration exists in both channel and shared Chrome directories; inspect them manually.'
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
  if [ "$EXISTING_TARGET" = "$SHARED_DIR/$EXTENSION_ID.json" ]; then
    log 'This shared registration may affect Stable, Beta and Dev profiles.'
  fi
  exit 0
fi

# Use only a dedicated registration path for the selected channel.
INSTALL_DIR="$CHANNEL_DIR"
TARGET="$INSTALL_DIR/$EXTENSION_ID.json"

# Elevated operations are limited to the selected channel's Chrome directory.
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
log "Registered $EXTENSION_ID for Google Chrome $CHANNEL (all profiles)."
log 'Restart the selected Google Chrome channel and check chrome://extensions.'
log 'Chrome stores its installed extension internally; no unpacked source folder is required.'
