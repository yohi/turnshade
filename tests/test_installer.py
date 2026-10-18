"""Exercise the one-liner installer offline with fake curl and a temporary Chrome path."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTENSION_ID = "jocgdilbieeiopnbfieeiifgifdbkkcg"
UPDATE_URL = "https://yohi.github.io/turnshade/updates.xml"


class InstallerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.directory = self.root / "extensions"
        script = (ROOT / "scripts/install.sh").read_text()
        self.assertEqual(script.count("__TURNSHADE_EXTENSION_ID__"), 1)
        script = script.replace("__TURNSHADE_EXTENSION_ID__", EXTENSION_ID)
        self.assertIn("INSTALL_DIR='/opt/google/chrome/extensions'", script)
        script = script.replace("INSTALL_DIR='/opt/google/chrome/extensions'",
                                f"INSTALL_DIR='{self.directory}'")
        self.script = self.root / "install.sh"
        self.script.write_text(script)

        for command, body in {
            "google-chrome": "#!/bin/sh\nexit 0\n",
            "id": "#!/bin/sh\nif [ \"$1\" = -u ]; then echo 0; else /usr/bin/id \"$@\"; fi\n",
            "curl": "#!/bin/sh\ncat \"$MOCK_XML\"\n",
        }.items():
            path = self.bin / command
            path.write_text(body)
            path.chmod(0o755)

        self.xml = self.root / "updates.xml"
        self.xml.write_text(self.make_xml())
        self.env = dict(os.environ,
                        PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
                        MOCK_XML=str(self.xml))

    def make_xml(self, ext_id=EXTENSION_ID, codebase=None):
        url = codebase or "https://yohi.github.io/turnshade/turnshade-v1.5.0.crx"
        return ('<?xml version="1.0"?>'
                '<gupdate xmlns="http://www.google.com/update2/response" protocol="2.0">'
                f'<app appid="{ext_id}"><updatecheck version="1.5.0"'
                f' codebase="{url}"/></app></gupdate>')

    def run_installer(self):
        return subprocess.run(["sh", str(self.script)], env=self.env,
                              capture_output=True, text=True)

    def target(self):
        return self.directory / f"{EXTENSION_ID}.json"

    def test_register_then_idempotent(self):
        first = self.run_installer()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(self.target().read_text(),
                         '{"external_update_url":"' + UPDATE_URL + '"}\n')
        second = self.run_installer()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("Already registered", second.stdout)

    def test_rejects_other_extension_id_before_writing(self):
        self.xml.write_text(self.make_xml(ext_id="a" * 32))
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.target().exists())

    def test_rejects_external_codebase(self):
        self.xml.write_text(self.make_xml(codebase="https://malicious.example/bad.crx"))
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.target().exists())

    def test_rejects_download_failure(self):
        (self.bin / "curl").write_text("#!/bin/sh\nexit 22\n")
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.target().exists())

    def test_refuses_conflicting_registration(self):
        self.directory.mkdir()
        self.target().write_text('{"external_update_url":"https://elsewhere.invalid"}\n')
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to overwrite", result.stderr)
        self.assertIn("elsewhere.invalid", self.target().read_text())

    def test_refuses_symlink_registration(self):
        self.directory.mkdir()
        other = self.root / "other.json"
        other.write_text("{}\n")
        self.target().symlink_to(other)
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(other.read_text(), "{}\n")

    def test_rejects_oversized_manifest(self):
        self.xml.write_bytes(b"x" * 33000)
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.target().exists())


if __name__ == "__main__":
    unittest.main()
