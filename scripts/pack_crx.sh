#!/usr/bin/env bash
# Package a vetted release ZIP as a CRX3 using an existing private signing key.
set -euo pipefail
umask 077

if [[ "$#" -ne 4 ]]; then
  echo "Usage: pack_crx.sh RELEASE.zip vX.Y.Z PRIVATE_KEY.pem OUTPUT_DIR" >&2
  exit 2
fi

archive="$(realpath "$1")"
tag="$2"
key="$(realpath "$3")"
output="$(realpath -m "$4")"
chrome="${CHROME_BIN:-google-chrome}"
name="turnshade-${tag}.crx"

[[ -f "$archive" && -s "$archive" ]] || { echo "Missing release ZIP" >&2; exit 1; }
[[ -f "$key" && -s "$key" ]] || { echo "Missing CRX signing key" >&2; exit 1; }
command -v "$chrome" >/dev/null || { echo "Chrome executable not found: $chrome" >&2; exit 1; }
openssl pkey -in "$key" -noout >/dev/null || { echo "Invalid signing key" >&2; exit 1; }

mkdir -p "$output"
[[ ! -e "$output/$name" && ! -e "$output/$name.sha256" ]] || {
  echo "Refusing to overwrite an existing signed package" >&2
  exit 1
}
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

python3 scripts/prepare_crx_input.py "$archive" "$tag" "$work/extension"

# Chrome places extension.crx alongside the extension directory.
"$chrome" --headless --no-sandbox --disable-gpu --disable-dev-shm-usage \
  --no-first-run --no-default-browser-check \
  --user-data-dir="$work/chrome-profile" \
  --pack-extension="$work/extension" \
  --pack-extension-key="$key"

generated="$work/extension.crx"
[[ -s "$generated" ]] || { echo "Chrome did not produce a CRX file" >&2; exit 1; }

python3 - "$generated" <<'PY'
import struct
import sys
from pathlib import Path

blob = Path(sys.argv[1]).read_bytes()
if len(blob) < 16 or blob[:4] != b"Cr24":
    raise SystemExit("Invalid CRX magic")
version, header_len = struct.unpack_from("<II", blob, 4)
if version != 3 or not 0 < header_len < len(blob) - 12:
    raise SystemExit("Not a valid CRX3 container header")
print(f"Validated CRX3 container header (${len(blob)} bytes)")
PY

cp -- "$generated" "$output/$name"
(cd "$output" && sha256sum "$name" > "$name.sha256")
echo "Created: $output/$name (signed with the provided key)"
