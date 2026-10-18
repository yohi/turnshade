#!/usr/bin/env python3
"""Validate the tested release ZIP and extract only allowlisted extension assets."""
import json
import re
import stat
import sys
from pathlib import Path
from zipfile import ZipFile

FILES = frozenset((
    "manifest.json", "service-worker.js", "content.js",
    "popup.html", "popup.js",
    "icons/icon16.png", "icons/icon48.png", "icons/icon128.png",
))


def prepare(archive: Path, tag: str, destination: Path) -> None:
    if not re.fullmatch(r"v[0-9]+(?:\.[0-9]+){1,3}", tag):
        raise ValueError("Release tag must be vX.Y[.Z[.W]]")
    if destination.exists():
        raise ValueError("Destination must not exist")
    with ZipFile(archive) as package:
        entries = package.infolist()
        names = [entry.filename for entry in entries]
        if len(names) != len(set(names)) or set(names) != FILES:
            raise ValueError("ZIP entries must match the extension allowlist exactly")
        for entry in entries:
            file_type = stat.S_IFMT(entry.external_attr >> 16)
            if entry.is_dir() or file_type == stat.S_IFLNK or entry.file_size > 5 * 1024 * 1024:
                raise ValueError("Unsafe ZIP entry: " + entry.filename)
        if package.testzip() is not None:
            raise ValueError("ZIP CRC check failed")
        data = {name: package.read(name) for name in FILES}

    manifest = json.loads(data["manifest.json"].decode("utf-8"))
    if manifest.get("manifest_version") != 3 or "v" + manifest.get("version", "") != tag:
        raise ValueError("Release tag and manifest version do not match")
    if manifest.get("update_url") != "https://yohi.github.io/turnshade/updates.xml":
        raise ValueError("This release predates the self-hosted update_url")
    if manifest.get("background", {}).get("service_worker") != "service-worker.js":
        raise ValueError("Unexpected service worker")
    if manifest.get("action", {}).get("default_popup") != "popup.html":
        raise ValueError("Unexpected popup")
    if manifest.get("content_scripts", [{}])[0].get("js") != ["content.js"]:
        raise ValueError("Unexpected content script")
    for n in (16, 48, 128):
        path = f"icons/icon{n}.png"
        if not data[path].startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("Invalid PNG icon: " + path)
        if manifest.get("icons", {}).get(str(n)) != path:
            raise ValueError("Icon path mismatch: " + path)

    destination.mkdir(parents=True)
    for name, body in data.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    print(f"Validated {tag}: {len(FILES)} allowlisted extension assets")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("Usage: prepare_crx_input.py RELEASE.zip vX.Y.Z OUTPUT_DIRECTORY")
    try:
        prepare(Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise SystemExit(f"CRX packaging input rejected: {exc}") from exc
