"""Installer behavior tests. All writes go to TemporaryDirectory destinations."""
import os
from pathlib import Path
import shlex
import shutil
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
        for name in ["hyprlock", "quickshell", "hypridle", "hyprctl"]:
            f = stub / name
            f.write_text("#!/bin/sh\nexit 99\n")
            f.chmod(0o755)
        self.env = dict(os.environ, PATH=str(stub) + ":" + os.environ["PATH"])

    def run_install(self, *flags, ok=True):
        result = subprocess.run([sys.executable, str(ROOT / "install.py"), "--backend", "hyprlock", "--target-home", str(self.home), *flags], env=self.env, text=True, capture_output=True)
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

    def use_lua_config(self):
        self.main = self.config / "hyprland.lua"
        self.original_lua = '-- Friend\'s Lua configuration\nlocal mainMod = "SUPER"\n'
        self.main.write_text(self.original_lua)

    def test_lua_auto_enable_update_and_rollback(self):
        # A leftover .conf must not take precedence over the Lua configuration.
        conf = self.main
        self.use_lua_config()
        self.run_install("--enable")
        self.run_install("--enable")
        self.assertEqual(conf.read_text(), self.original)
        self.assertEqual(self.main.read_text().count("-- BEGIN REZERO"), 1)
        self.assertIn("dofile(", self.main.read_text())
        self.assertNotIn("source =", self.main.read_text())
        backup = self.home / ".local/state/rezero-hyprlock/hyprland.lua.before-enable"
        self.assertEqual(backup.read_text(), self.original_lua)
        with self.main.open("a") as stream:
            stream.write("-- later unrelated edit\n")
        self.run_install("--uninstall")
        self.assertIn(self.original_lua, self.main.read_text())
        self.assertIn("-- later unrelated edit", self.main.read_text())
        self.assertNotIn("REZERO", self.main.read_text())
        self.assertEqual(conf.read_text(), self.original)
        self.assertFalse((self.config / "rezero/hyprland.lua").exists())

    def test_lua_conflicting_idle_fails_before_writes(self):
        self.use_lua_config()
        startup = self.config / "startup.lua"
        startup.write_text('hl.exec_cmd("env --quiet hypridle") -- existing daemon\n')
        result = self.run_install("--enable", ok=False)
        self.assertIn(str(startup), result.stderr)
        self.assertIn("--no-idle", result.stderr)
        self.assertEqual(self.main.read_text(), self.original_lua)
        self.assertFalse((self.config / "rezero").exists())
        self.run_install("--enable", "--no-idle")
        self.assertNotIn("hyprland.start", (self.config / "rezero/hyprland.lua").read_text())

    def test_lua_commented_idle_is_ignored(self):
        self.use_lua_config()
        with self.main.open("a") as stream:
            stream.write('-- hl.exec_cmd("hypridle")\n')
            stream.write('--[[\nhl.exec_cmd("swayidle")\n]]\n')
            stream.write('--[=[\nhl.exec_cmd("hypridle")\n]=]\n')
        self.run_install("--enable")

    def test_explicit_format_and_uninstall_both_formats(self):
        conf = self.main
        self.use_lua_config()
        self.run_install("--enable")
        lua_enabled = self.main.read_text()
        self.run_install("--enable", "--hyprland-format", "conf")
        self.assertIn("# BEGIN REZERO", conf.read_text())
        self.assertEqual(self.main.read_text(), lua_enabled)
        self.run_install("--uninstall")
        self.assertNotIn("REZERO", conf.read_text())
        self.assertNotIn("REZERO", self.main.read_text())

    def test_lua_staging_and_missing_main(self):
        self.main.unlink()
        result = self.run_install("--enable", "--hyprland-format", "lua", ok=False)
        self.assertIn("regular hyprland.lua", result.stderr)
        self.assertFalse((self.config / "rezero").exists())
        result = self.run_install("--hyprland-format", "lua")
        self.assertIn("add to hyprland.lua:", result.stdout)
        self.assertIn("dofile(", result.stdout)
        self.assertFalse((self.config / "hyprland.lua").exists())

    def test_lua_symlink_preflight(self):
        external = self.home / "external.lua"
        external.write_text('-- managed by another tool\n')
        (self.config / "hyprland.lua").symlink_to(external)
        self.run_install("--enable", ok=False)
        self.assertEqual(external.read_text(), '-- managed by another tool\n')
        self.assertFalse((self.config / "rezero").exists())
        result = self.run_install()
        self.assertIn("add to hyprland.lua:", result.stdout)
        # An unrelated symlink should not prevent removing staged runtime files.
        self.run_install("--uninstall")
        self.assertTrue((self.config / "hyprland.lua").is_symlink())

    @unittest.skipUnless(shutil.which("lua"), "Lua interpreter is optional")
    def test_lua_loads_with_quoted_paths_and_defers_idle_until_start(self):
        new_home = self.home.with_name('friend\'s "Lua" home 日本')
        self.home.rename(new_home)
        self.home = new_home
        self.config = self.home / ".config/hypr"
        self.use_lua_config()
        harness = '''
local unbound, command, startup
local executions = 0
hl = {
    unbind = function(key) assert(key == "SUPER + L"); unbound = true end,
    dsp = { exec_cmd = function(cmd) return cmd end },
    bind = function(key, cmd)
        assert(unbound and key == "SUPER + L")
        command = cmd
    end,
    on = function(event, callback)
        assert(event == "hyprland.start" and startup == nil)
        startup = callback
    end,
    exec_cmd = function(cmd) executions = executions + 1; print(cmd) end,
}
dofile(arg[1])
assert(command and executions == 0)
print(command)
if arg[2] == "idle" then
    assert(type(startup) == "function")
    startup()
    assert(executions == 1)
else
    assert(startup == nil)
end
'''
        for no_idle in [False, True]:
            with self.subTest(no_idle=no_idle):
                self.run_install("--enable", *(["--no-idle"] if no_idle else []))
                result = subprocess.run(["lua", "-", str(self.main), "no-idle" if no_idle else "idle"], input=harness, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                expected = [[str(self.home / ".local/bin/rezero-lock")]]
                if not no_idle:
                    expected.append([str(self.home / ".local/bin/rezero-idle")])
                self.assertEqual([shlex.split(line) for line in result.stdout.splitlines()], expected)


class QuickshellInstallTests(InstallTests):
    """Exercise the new default backend and shared rollback behavior."""
    def run_install(self, *flags, ok=True):
        result = subprocess.run([sys.executable, str(ROOT / "install.py"), "--target-home", str(self.home), *flags], env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def test_stage_does_not_enable(self):
        self.run_install()
        self.assertEqual(self.main.read_text(), self.original)
        self.assertFalse((self.config / "hyprlock.conf").exists())
        launcher = self.home / ".local/bin/rezero-lock"
        self.assertIn("quickshell --no-duplicate --path", launcher.read_text())
        shell = self.home / ".config/quickshell/rezero"
        self.assertTrue((shell / "shell.qml").is_file())
        self.assertTrue((shell / "telemetry.py").is_file())
        self.assertTrue((shell / "assets/background.png").is_file())
        self.assertFalse(list(shell.rglob("*.qsb")))

    def test_user_edits_are_saved_on_update_and_uninstall(self):
        self.run_install()
        settings = self.home / ".config/quickshell/rezero/Settings.qml"
        settings.write_text("// custom wallpaper\n")
        self.run_install()
        backups = self.home / ".local/state/rezero-hyprlock/preserved"
        self.assertIn("// custom wallpaper\n", [f.read_text() for f in backups.iterdir()])
        settings.write_text("// custom animation setting\n")
        self.run_install("--uninstall")
        self.assertIn("// custom animation setting\n", [f.read_text() for f in backups.iterdir()])

    def test_symlink_preflight(self):
        external = self.home / "external"
        external.mkdir()
        (self.home / ".config/quickshell").symlink_to(external, target_is_directory=True)
        self.run_install("--enable", ok=False)
        self.assertFalse(list(external.iterdir()))
        self.assertFalse((self.home / ".local/bin/rezero-lock").exists())

    def test_launcher_guard_does_not_leak_to_descendants(self):
        self.run_install()
        stub = Path(self.env["PATH"].split(":")[0]) / "hypridle"
        stub.write_text("#!/bin/sh\nsleep 2 >/dev/null 2>&1 &\nexit 0\n")
        env = dict(self.env, XDG_RUNTIME_DIR=self.temp.name, WAYLAND_DISPLAY="test-display")
        subprocess.run([str(self.home / ".local/bin/rezero-idle")], env=env, check=True, timeout=2)
        guard = Path(self.temp.name) / "rezero-idle-test-display.lock"
        result = subprocess.run(["flock", "--nonblock", str(guard), "true"], env=env)
        self.assertEqual(result.returncode, 0, "A background descendant retained the launcher guard")


if __name__ == "__main__":
    unittest.main()
