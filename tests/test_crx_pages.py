"""Purely local validation tests for pinned-ID CRX self-host update manifests."""
import importlib.util
import json
import struct
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_update_site.py"
SPEC = importlib.util.spec_from_file_location("build_update_site", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class PagesReleaseTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.key = self.root / "signing.pem"
        subprocess.run(["openssl", "genrsa", "-out", str(self.key), "2048"], check=True, capture_output=True)
        self.extension_id, self.der = module.extension_id_from_key(self.key)
        self.crx = self.root / "turnshade-v1.5.0.crx"
        # Header-only fixture; not intended to be a valid signed CRX payload.
        self.crx.write_bytes(b"Cr24" + struct.pack("<II", 3, len(self.der)) + self.der + b"mock content")
        self.manifest = self.root / "manifest.json"
        self.manifest.write_text(json.dumps({
            "version": "1.5.0",
            "update_url": module.UPDATE_URL,
        }))
        self.dest = self.root / "site"

    def publish(self, expected_id=None):
        return module.build_site(self.crx, self.key, self.manifest,
                                 "v1.5.0", expected_id or self.extension_id, self.dest)

    def test_writes_same_origin_crx_and_valid_omaha_manifest(self):
        self.assertEqual(self.publish(), self.extension_id)
        xml = ET.parse(self.dest / "updates.xml").getroot()
        app = xml.find(f"{{{module.NS}}}app")
        self.assertEqual(app.attrib["appid"], self.extension_id)
        check = app.find(f"{{{module.NS}}}updatecheck")
        self.assertEqual(check.attrib["version"], "1.5.0")
        self.assertEqual(check.attrib["codebase"],
                         "https://yohi.github.io/turnshade/turnshade-v1.5.0.crx")
        self.assertEqual((self.dest / self.crx.name).read_bytes(), self.crx.read_bytes())
        self.assertTrue((self.dest / ".nojekyll").exists())
        installer = (self.dest / "install.sh").read_text()
        self.assertIn("EXTENSION_ID='" + self.extension_id + "'", installer)
        self.assertIn("https://yohi.github.io/turnshade/updates.xml", installer)
        self.assertNotIn("__TURNSHADE_EXTENSION_ID__", installer)
        self.assertIn("python3 -c", installer)


    def test_existing_crx_public_key_identity_without_private_key(self):
        # CRX3 protobuf AsymmetricKeyProof with RSA key (field 2, nested field 1).
        def field(number, data):
            def v(n):
                out = bytearray()
                while n >= 128:
                    out.append((n & 127) | 128)
                    n >>= 7
                out.append(n)
                return bytes(out)
            return v((number << 3) | 2) + v(len(data)) + data
        proof = field(1, self.der)
        header = field(2, proof)
        self.crx.write_bytes(b"Cr24" + struct.pack("<II", 3, len(header))
                             + header + b"mock content")
        module.build_site(self.crx, None, self.manifest, "v1.5.0",
                          self.extension_id, self.dest)
        self.assertIn("external_update_url", (self.dest / "install.sh").read_text())

    def test_existing_crx_rejects_wrong_key(self):
        def varint(n):
            out = bytearray()
            while n >= 128:
                out.append((n & 127) | 128)
                n >>= 7
            out.append(n)
            return bytes(out)
        def field(i, value):
            return varint(i << 3 | 2) + varint(len(value)) + value
        header = field(2, field(1, b"not-the-owner-key"))
        self.crx.write_bytes(b"Cr24" + struct.pack("<II", 3, len(header))
                             + header + b"payload")
        with self.assertRaisesRegex(ValueError, "pinned extension ID"):
            module.build_site(self.crx, None, self.manifest, "v1.5.0",
                              self.extension_id, self.dest)

    def test_rejects_wrong_extension_id(self):
        wrong = ("a" if self.extension_id[0] != "a" else "b") + self.extension_id[1:]
        with self.assertRaisesRegex(ValueError, "pinned extension ID"):
            self.publish(wrong)
        self.assertFalse(self.dest.exists())

    def test_rejects_non_crx3_header(self):
        self.crx.write_bytes(b"not a real crx")
        with self.assertRaisesRegex(ValueError, "CRX"):
            self.publish()

    def test_rejects_crx_signed_by_different_key(self):
        self.crx.write_bytes(b"Cr24" + struct.pack("<II", 3, 10) + b"wrong-key!" + b"payload")
        with self.assertRaisesRegex(ValueError, "public key"):
            self.publish()

    def test_rejects_bad_update_url(self):
        m = json.loads(self.manifest.read_text())
        m["update_url"] = "https://invalid.example/updates.xml"
        self.manifest.write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError, "update_url"):
            self.publish()

    def test_rejects_tag_version_mismatch(self):
        m = json.loads(self.manifest.read_text())
        m["version"] = "1.5.1"
        self.manifest.write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError, "version"):
            self.publish()

    def test_refuses_overwrite(self):
        self.dest.mkdir()
        with self.assertRaisesRegex(ValueError, "overwrite"):
            self.publish()


if __name__ == "__main__":
    unittest.main()
