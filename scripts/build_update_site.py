#!/usr/bin/env python3
"""Build an atomic GitHub Pages update site from an already signed CRX3.

The release CRX is also kept as an immutable GitHub Release asset.
The Pages deployment carries the same CRX together with its update manifest,
avoiding asset-redirect/MIME issues and publishing both in one Pages deployment.
"""
import argparse
import hashlib
import json
import re
import shutil
import struct
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

UPDATE_URL = "https://yohi.github.io/turnshade/updates.xml"
BASE_URL = "https://yohi.github.io/turnshade"
ID_PATTERN = re.compile(r"[a-p]{32}\Z")
VERSION_PATTERN = re.compile(r"v([0-9]+(?:\.[0-9]+){1,3})\Z")
NS = "http://www.google.com/update2/response"


def extension_id_from_key(key: Path) -> tuple[str, bytes]:
    public_der = subprocess.run(
        ["openssl", "pkey", "-in", str(key), "-pubout", "-outform", "DER"],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    ).stdout
    if not public_der:
        raise ValueError("Public key DER is empty")
    # Chrome extension ID = first 128 bits of SHA-256(SPKI DER), nibbles mapped a-p.
    raw_id = hashlib.sha256(public_der).digest()[:16]
    return "".join(chr(ord("a") + int(c, 16)) for b in raw_id for c in f"{b:02x}"), public_der


def build_site(crx: Path, key: Path, manifest_path: Path,
               tag: str, expected_id: str, destination: Path) -> str:
    match = VERSION_PATTERN.fullmatch(tag)
    if not match or not ID_PATTERN.fullmatch(expected_id):
        raise ValueError("Invalid release tag or extension ID")
    version = match.group(1)
    if crx.name != f"turnshade-{tag}.crx":
        raise ValueError("CRX file name and release tag differ")
    if destination.exists():
        raise ValueError("Refusing to overwrite a Pages site")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("version") != version:
        raise ValueError("CRX source manifest version differs from release tag")
    if manifest.get("update_url") != UPDATE_URL:
        raise ValueError("Signed CRX must contain the pinned update_url")

    extension_id, public_der = extension_id_from_key(key)
    if extension_id != expected_id:
        raise ValueError("Signing key changed the pinned extension ID")

    blob = crx.read_bytes()
    if len(blob) < 16 or blob[:4] != b"Cr24":
        raise ValueError("Not a CRX container")
    crx_version, header_size = struct.unpack_from("<II", blob, 4)
    if crx_version != 3 or not 0 < header_size <= len(blob) - 13:
        raise ValueError("Invalid CRX3 header")
    if public_der not in blob[12:12 + header_size]:
        raise ValueError("CRX public key differs from pinned signing key")

    ET.register_namespace("", NS)
    gupdate = ET.Element(f"{{{NS}}}gupdate", {"protocol": "2.0"})
    app = ET.SubElement(gupdate, f"{{{NS}}}app", {"appid": extension_id})
    ET.SubElement(app, f"{{{NS}}}updatecheck", {
        "codebase": f"{BASE_URL}/turnshade-{tag}.crx",
        "version": version,
    })
    xml = ET.tostring(gupdate, encoding="utf-8", xml_declaration=True)

    destination.mkdir(parents=True)
    shutil.copyfile(crx, destination / crx.name)
    (destination / "updates.xml").write_bytes(xml + b"\n")
    (destination / ".nojekyll").write_text("", encoding="utf-8")
    (destination / "index.html").write_text(
        '<!doctype html><html lang="ja"><meta charset="utf-8">'
        '<title>TurnShade Updates</title><h1>TurnShade</h1>'
        '<p>Ubuntu / Linux Chrome self-hosted extension updates.</p>'
        '<p>Source: <a href="https://github.com/yohi/turnshade">'
        'yohi/turnshade</a></p></html>\n',
        encoding="utf-8",
    )
    print(f"Pages update site ready for {version}, extension ID {extension_id}")
    return extension_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--crx", type=Path, required=True)
    parser.add_argument("--key", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--expected-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_site(args.crx, args.key, args.manifest, args.tag, args.expected_id, args.output)
