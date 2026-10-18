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
        self.alternate = self.root / "alternate"
        self.beta = self.root / "beta"
        self.dev = self.root / "dev"
        script = (ROOT / "scripts/install.sh").read_text()
        self.assertEqual(script.count("__TURNSHADE_EXTENSION_ID__"), 1)
        script = script.replace("__TURNSHADE_EXTENSION_ID__", EXTENSION_ID)
        self.binaries = {
            "stable": self.root / "chrome-stable",
            "beta": self.root / "chrome-beta",
            "dev": self.root / "chrome-dev",
        }
        for browser in self.binaries.values():
            browser.write_text("#!/bin/sh\\nexit 0\\n")
            browser.chmod(0o755)
        for original, local in (
            ("CHANNEL_DIR='/opt/google/chrome/extensions'", f"CHANNEL_DIR='{self.directory}'"),
            ("CHANNEL_DIR='/opt/google/chrome-beta/extensions'", f"CHANNEL_DIR='{self.beta}'"),
            ("CHANNEL_DIR='/opt/google/chrome-unstable/extensions'", f"CHANNEL_DIR='{self.dev}'"),
            ("BROWSER_BINARY='/opt/google/chrome/chrome'", f"BROWSER_BINARY='{self.binaries['stable']}'"),
            ("BROWSER_BINARY='/opt/google/chrome-beta/chrome'", f"BROWSER_BINARY='{self.binaries['beta']}'"),
            ("BROWSER_BINARY='/opt/google/chrome-unstable/chrome'", f"BROWSER_BINARY='{self.binaries['dev']}'"),
            ("SHARED_DIR='/usr/share/google-chrome/extensions'", f"SHARED_DIR='{self.alternate}'"),
        ):
            self.assertIn(original, script)
            script = script.replace(original, local)
        self.assertIn("main() {", script)
        self.assertTrue(script.endswith('main "$@"\\n'))
        self.script = self.root / "install.sh"
        self.script.write_text(script)

        for command, body in {
            "google-chrome": "#!/bin/sh\nexit 0\n",
            "google-chrome-beta": "#!/bin/sh\nexit 0\n",
            "google-chrome-unstable": "#!/bin/sh\nexit 0\n",
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

    def run_installer(self, *args):
        return subprocess.run(["sh", str(self.script), *args], env=self.env,
                              capture_output=True, text=True)

    def target(self, channel="stable"):
        folders = {"stable": self.directory, "beta": self.beta, "dev": self.dev}
        return folders[channel] / f"{EXTENSION_ID}.json"

    def test_register_then_idempotent(self):
        first = self.run_installer()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(self.target().read_text(),
                         '{"external_update_url":"' + UPDATE_URL + '"}\n')
        second = self.run_installer()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("Already registered", second.stdout)

    def test_reuses_valid_registration_at_alternate_official_path(self):
        self.alternate.mkdir()
        existing = self.alternate / f"{EXTENSION_ID}.json"
        existing.write_text('{"external_update_url":"' + UPDATE_URL + '"}\n')
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Already registered", result.stdout)
        self.assertFalse(self.target().exists())
        self.assertEqual(existing.read_text(),
                         '{"external_update_url":"' + UPDATE_URL + '"}\n')

    def test_new_registration_never_creates_a_shared_entry(self):
        self.alternate.mkdir()
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.target().is_file())
        self.assertFalse((self.alternate / f"{EXTENSION_ID}.json").exists())

    def test_refuses_duplicate_registration_in_both_locations(self):
        self.directory.mkdir()
        self.alternate.mkdir()
        content = '{"external_update_url":"' + UPDATE_URL + '"}\n'
        self.target().write_text(content)
        alternate_file = self.alternate / f"{EXTENSION_ID}.json"
        alternate_file.write_text(content)
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("both channel and shared Chrome directories", result.stderr)
        self.assertEqual(self.target().read_text(), content)
        self.assertEqual(alternate_file.read_text(), content)

    def test_refuses_conflicting_alternate_registration(self):
        self.alternate.mkdir()
        alternate_file = self.alternate / f"{EXTENSION_ID}.json"
        alternate_file.write_text('{"external_update_url":"https://different.example"}\n')
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.target().exists())

    def test_beta_channel_has_distinct_registration(self):
        result = self.run_installer("--channel", "beta")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.target("beta").is_file())
        self.assertFalse(self.target("stable").exists())
        self.assertFalse(self.target("dev").exists())
        self.assertFalse((self.alternate / f"{EXTENSION_ID}.json").exists())
        self.assertIn("Chrome beta (all profiles)", result.stdout)

    def test_dev_channel_via_equals_syntax(self):
        result = self.run_installer("--channel=dev")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.target("dev").is_file())
        self.assertFalse(self.target("stable").exists())
        self.assertFalse(self.target("beta").exists())

    def test_channel_registrations_can_coexist(self):
        for channel in ("stable", "beta", "dev"):
            result = self.run_installer("--channel", channel)
            self.assertEqual(result.returncode, 0, result.stderr)
        for channel in ("stable", "beta", "dev"):
            self.assertTrue(self.target(channel).is_file())

    def test_shared_registration_is_respected_for_beta(self):
        self.alternate.mkdir()
        existing = self.alternate / f"{EXTENSION_ID}.json"
        content = '{"external_update_url":"' + UPDATE_URL + '"}\n'
        existing.write_text(content)
        result = self.run_installer("--channel=beta")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("shared registration may affect", result.stdout)
        self.assertFalse(self.target("beta").exists())

    def test_profile_specific_option_is_rejected_before_writing(self):
        result = self.run_installer("--profile=Profile 2")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Profile-specific install unsupported", result.stderr)
        self.assertFalse(self.target().exists())

    def test_unknown_channel_is_rejected_before_writing(self):
        result = self.run_installer("--channel=canary")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unsupported Chrome channel", result.stderr)
        self.assertFalse(self.target().exists())

    def test_missing_channel_binary_rejects_path_wrappers(self):
        # PATH contains a fake google-chrome-beta, but no actual selected binary.
        self.binaries["beta"].unlink()
        result = self.run_installer("--channel=beta")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Google Chrome beta is not installed", result.stderr)
        self.assertFalse(self.target("beta").exists())

    def test_non_executable_channel_binary_rejected(self):
        self.binaries["stable"].chmod(0o644)
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.target().exists())

    def test_truncated_piped_script_does_not_create_registration(self):
        script = self.script.read_text()
        # Full main body is not parsed in these prefixes; no installer actions run.
        cut_points = [
            script.index("# Never run a network script"),
            script.index('  sudo install -d -m 755 "$INSTALL_DIR"'),
            script.index('\n}\n\nmain "$@"'),
        ]
        for cut in cut_points:
            with self.subTest(cut=cut):
                result = subprocess.run(["sh"], input=script[:cut], env=self.env,
                                        capture_output=True, text=True)
                self.assertFalse(self.target().exists())
                self.assertFalse(self.target("beta").exists())
                self.assertFalse(self.target("dev").exists())

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
