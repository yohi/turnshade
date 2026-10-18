"""Offline rejection/acceptance tests for release ZIP -> CRX input preparation."""
import importlib.util
import json
import stat
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile, ZipInfo

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "prepare_crx_input.py"
SPEC = importlib.util.spec_from_file_location("prepare_crx_input", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def assets(version="1.4.0"):
    manifest = {
        "manifest_version": 3,
        "version": version,
        "background": {"service_worker": "service-worker.js"},
        "action": {"default_popup": "popup.html"},
        "content_scripts": [{"js": ["content.js"]}],
        "icons": {str(n): f"icons/icon{n}.png" for n in (16, 48, 128)},
    }
    result = {name: b"const version = 1;\n" for name in module.FILES}
    result["manifest.json"] = json.dumps(manifest).encode()
    for n in (16, 48, 128):
        result[f"icons/icon{n}.png"] = b"\x89PNG\r\n\x1a\n" + b"test"
    return result


class ReleaseZipTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / "release.zip"
        self.out = self.root / "extension"

    def make_zip(self, entries=None, symlink=None):
        with ZipFile(self.archive, "w") as z:
            for name, data in (entries if entries is not None else assets()).items():
                info = ZipInfo(name)
                if name == symlink:
                    info.external_attr = (stat.S_IFLNK | 0o777) << 16
                z.writestr(info, data)

    def test_accepts_exact_release_assets(self):
        self.make_zip()
        module.prepare(self.archive, "v1.4.0", self.out)
        self.assertEqual(json.loads((self.out / "manifest.json").read_text())["version"], "1.4.0")
        self.assertEqual(len(list(self.out.rglob("*"))), 9)  # 8 files + icons directory

    def test_rejects_mismatched_version(self):
        self.make_zip()
        with self.assertRaisesRegex(ValueError, "version"):
            module.prepare(self.archive, "v1.5.0", self.out)

    def test_rejects_unexpected_file(self):
        unsafe = assets()
        unsafe["private-key.pem"] = b"never ship a key"
        self.make_zip(unsafe)
        with self.assertRaisesRegex(ValueError, "allowlist"):
            module.prepare(self.archive, "v1.4.0", self.out)
        self.assertFalse(self.out.exists())

    def test_rejects_zip_slip(self):
        unsafe = assets()
        unsafe["../escape.txt"] = b"escape"
        self.make_zip(unsafe)
        with self.assertRaisesRegex(ValueError, "allowlist"):
            module.prepare(self.archive, "v1.4.0", self.out)

    def test_rejects_symlink(self):
        self.make_zip(symlink="popup.js")
        with self.assertRaisesRegex(ValueError, "Unsafe ZIP"):
            module.prepare(self.archive, "v1.4.0", self.out)

    def test_rejects_bad_icon(self):
        bad = assets()
        bad["icons/icon16.png"] = b"not a PNG"
        self.make_zip(bad)
        with self.assertRaisesRegex(ValueError, "PNG"):
            module.prepare(self.archive, "v1.4.0", self.out)

    def test_rejects_existing_destination(self):
        self.make_zip()
        self.out.mkdir()
        with self.assertRaisesRegex(ValueError, "Destination"):
            module.prepare(self.archive, "v1.4.0", self.out)


if __name__ == "__main__":
    unittest.main()
