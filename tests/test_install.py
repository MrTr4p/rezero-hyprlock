"""Installer behavior tests. All writes go to TemporaryDirectory destinations."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rezero-test-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "friend home"
        self.config = self.home / ".config/hypr"
        self.config.mkdir(parents=True)
        self.main = self.config / "hyprland.conf"
        self.original = "# Friend's configuration\n$mainMod = SUPER\n"
        self.main.write_text(self.original)
        # Tests invoke only the installer, which checks command availability.
        # These stubs are not used for locking or authentication.
        stub = Path(self.temp.name) / "bin"
        stub.mkdir()
        for name in ["hyprlock", "hypridle", "hyprctl"]:
            f = stub / name
            f.write_text("#!/bin/sh\nexit 99\n")
            f.chmod(0o755)
        self.env = dict(os.environ, PATH=str(stub) + ":" + os.environ["PATH"])

    def run_install(self, *flags, ok=True):
        result = subprocess.run([sys.executable, str(ROOT / "install.py"), "--target-home", str(self.home), *flags], env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def test_stage_does_not_enable(self):
        self.run_install()
        self.assertEqual(self.main.read_text(), self.original)
        self.assertFalse((self.config / "hyprlock.conf").exists())
        launcher = self.home / ".local/bin/rezero-lock"
        self.assertTrue(os.access(launcher, os.X_OK))
        self.assertIn("--grace 0", launcher.read_text())
        self.assertNotIn("@ASSETS@", (self.config / "rezero/hyprlock.conf").read_text())

    def test_enable_update_and_rollback_preserves_unrelated_edits(self):
        lock = self.config / "hyprlock.conf"
        lock.write_text("# previous theme\n")
        self.run_install("--enable")
        self.run_install("--enable")
        self.assertEqual(self.main.read_text().count("# BEGIN REZERO"), 1)
        self.assertEqual((self.config / "rezero/hyprland.conf").read_text().count("exec-once"), 1)
        with self.main.open("a") as stream:
            stream.write("# later unrelated edit\n")
        self.run_install("--uninstall")
        self.assertEqual(lock.read_text(), "# previous theme\n")
        self.assertIn("# later unrelated edit", self.main.read_text())
        self.assertNotIn("REZERO", self.main.read_text())
        self.assertFalse((self.home / ".local/bin/rezero-lock").exists())

    def test_conflicting_idle_fails_before_writes(self):
        self.main.write_text("exec-once = hypridle\n")
        result = self.run_install("--enable", ok=False)
        self.assertIn("--no-idle", result.stderr)
        self.assertFalse((self.config / "rezero").exists())
        self.run_install("--enable", "--no-idle")
        self.assertNotIn("exec-once", (self.config / "rezero/hyprland.conf").read_text())

    def test_symlink_preflight(self):
        original = self.home / "external.conf"
        original.write_text("do not touch")
        (self.config / "hyprlock.conf").symlink_to(original)
        self.run_install("--enable", ok=False)
        self.assertEqual(original.read_text(), "do not touch")
        self.assertFalse((self.config / "rezero").exists())

    def test_user_edits_are_saved_on_update_and_uninstall(self):
        self.run_install()
        theme = self.config / "rezero/hyprlock.conf"
        theme.write_text("# custom wallpaper\n")
        self.run_install()
        backups = self.home / ".local/state/rezero-hyprlock/preserved"
        self.assertIn("# custom wallpaper\n", [f.read_text() for f in backups.iterdir()])
        theme.write_text("# another custom wallpaper\n")
        self.run_install("--uninstall")
        self.assertIn("# another custom wallpaper\n", [f.read_text() for f in backups.iterdir()])

    def test_invalid_path_fails_before_writes(self):
        self.home = Path(self.temp.name) / "bad#path"
        self.run_install(ok=False)
        self.assertFalse(self.home.exists())


if __name__ == "__main__":
    unittest.main()
