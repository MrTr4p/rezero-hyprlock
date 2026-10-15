#!/usr/bin/env python3
"""Real Hyprland/Hyprlock integration in a disposable nested session.

Requires Hyprland, hyprlock, hypridle, bwrap, grim, wtype, dbus, gdbus,
python-gobject, and a Wayland desktop.
The test PAM policy exists ONLY inside bubblewrap. No real account is used.
"""
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "validation"
OUT.mkdir(exist_ok=True)


def wait_for(predicate, description, timeout=12):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if predicate():
                return
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            pass  # compositor IPC is not ready yet
        time.sleep(0.1)
    raise AssertionError("Timeout: " + description)


def main():
    parent_runtime = os.environ["XDG_RUNTIME_DIR"]
    parent_display = os.environ["WAYLAND_DISPLAY"]
    parent_socket = str(Path(parent_runtime) / parent_display)
    processes = []
    handles = []
    results = []
    with tempfile.TemporaryDirectory(prefix="rz-") as runtime:
        env = dict(os.environ, XDG_RUNTIME_DIR=runtime, WAYLAND_DISPLAY="wayland-1", HYPRLAND_NO_SD_VARS="1", LIBSEAT_BACKEND="seatd")
        env.pop("HYPRLAND_INSTANCE_SIGNATURE", None)
        home = Path(runtime) / "friend home"
        config = home / ".config/hypr"
        config.mkdir(parents=True)
        main_conf = config / "hyprland.conf"
        # Do not source the installed idle startup in the compositor: it is
        # started separately under the same isolated PAM namespace below.
        main_conf.write_text("""monitor = , 1280x720@60, auto, 1
misc {
    disable_hyprland_logo = true
    disable_splash_rendering = true
    allow_session_lock_restore = true
}
animations {
    enabled = false
}
xwayland {
    enabled = false
}
debug {
    disable_logs = false
}
""")
        subprocess.run([sys.executable, str(ROOT / "install.py"), "--target-home", str(home)], env=env, check=True)
        pam = Path(runtime) / "pam.d"
        pam.mkdir()
        fixture = Path(runtime) / "pam-fixture.py"
        fixture.write_text('import sys\nsys.exit(0 if sys.stdin.buffer.read().rstrip(b"\\x00") == b"rezero-test-only" else 1)\n')
        (pam / "hyprlock").write_text(f"auth required pam_exec.so expose_authtok quiet /usr/bin/python3 {fixture}\n")

        def launch(command, name, custom_env=None):
            log = OUT / (name + ".log")
            handle = log.open("w")
            handles.append(handle)
            proc = subprocess.Popen(command, env=custom_env or env, stdout=handle, stderr=handle, start_new_session=True)
            processes.append(proc)
            return proc, log

        def ctl(*args):
            return subprocess.check_output(["hyprctl", "-i", "0", *args], env=env, text=True)

        def sandbox(command):
            return ["bwrap", "--ro-bind", "/", "/", "--dev-bind", "/dev", "/dev", "--proc", "/proc", "--bind", runtime, runtime,
                    "--ro-bind", str(pam), "/etc/pam.d", "--unshare-user", "--unshare-pid", "--die-with-parent", *command]

        def type_keys(*args):
            subprocess.run(["wtype", "-s", "150", *args, "-s", "150"], env=env, check=True)

        def screenshot(name, output="REZERO-1"):
            ctl("dismissnotify")
            time.sleep(0.4)
            subprocess.run(["grim", "-o", output, str(OUT / (name + ".png"))], env=env, check=True)

        def check_log(log):
            text = log.read_text()
            assert not re.search(r"config.*error|config option.*does not exist|failed to load|failed to read", text, re.I), text

        lock_command = [str(home / ".local/bin/rezero-lock")]
        try:
            compositor, _ = launch(["Hyprland", "--config", str(main_conf)], "smoke-hyprland", dict(env, WAYLAND_DISPLAY=parent_socket))
            wait_for(lambda: (Path(runtime) / "wayland-1").exists(), "nested compositor startup")
            wait_for(lambda: bool(json.loads(ctl("monitors", "-j"))), "nested monitor")
            old_outputs = [o["name"] for o in json.loads(ctl("monitors", "-j"))]
            ctl("output", "create", "headless", "REZERO-1")
            ctl("keyword", "monitor", "REZERO-1,1920x1080@60,0x0,1")
            for output in old_outputs:
                ctl("keyword", "monitor", output + ",disable")
            ctl("dispatch", "focusmonitor", "REZERO-1")
            assert ctl("configerrors").strip() in ("", "ok"), ctl("configerrors")

            locker, log = launch(sandbox(lock_command), "smoke-lock")
            wait_for(lambda: "onLockLocked called" in log.read_text(), "Wayland session lock acquired")
            time.sleep(1)
            assert locker.poll() is None
            screenshot("preview-1920x1080")
            check_log(log)
            results.append("Real ext-session-lock acquisition and 1920x1080 rendering")

            duplicate = subprocess.run(sandbox(lock_command), env=env, text=True, capture_output=True, timeout=3)
            assert duplicate.returncode == 0 and "Locking session" not in duplicate.stdout
            results.append("Duplicate lock request exits without creating another locker")

            # Escape clears text, and Enter on empty input must not authenticate.
            type_keys("discard-this", "-k", "Escape", "-k", "Return")
            assert "auth: authenticated" not in log.read_text() and "pam_authenticate failed" not in log.read_text()
            type_keys("wrong-test", "-k", "Return")
            wait_for(lambda: "pam_authenticate failed" in log.read_text(), "wrong password rejected by PAM")
            assert locker.poll() is None
            screenshot("password-rejected")
            results.append("Empty input ignored, Escape clears, wrong PAM response remains locked")

            ctl("output", "create", "headless", "REZERO-2")
            ctl("keyword", "monitor", "REZERO-2,1280x720@60,1920x0,1")
            wait_for(lambda: "x: 1280, y: 720" in log.read_text(), "hotplugged display covered")
            screenshot("preview-1280x720", "REZERO-2")
            results.append("Second monitor hotplug while locked is covered at 1280x720")

            for width, height, scale in [(1366, 768, 1), (1080, 1920, 1), (2560, 1440, 1.25)]:
                ctl("keyword", "monitor", f"REZERO-1,{width}x{height}@60,0x0,{scale}")
                time.sleep(0.8)
                screenshot(f"preview-{width}x{height}-scale{scale}")
            results.append("Rendering at 1366x768, portrait 1080x1920, and 2560x1440 at 125%")
            ctl("dispatch", "focusmonitor", "REZERO-1")
            ctl("dispatch", "movecursor", "500", "500")
            time.sleep(2)
            type_keys("-k", "Escape", "rezero-test-only", "-k", "Return")
            assert locker.wait(timeout=10) == 0
            assert "auth: authenticated for hyprlock" in log.read_text()
            results.append("Successful PAM fixture response unlocks and exits normally")

            # Exercise the actual installed hypridle file with only its timeout
            # shortened. No suspend or loginctl commands are sent to the host.
            idle_conf = config / "rezero/hypridle.conf"
            idle_conf.write_text(idle_conf.read_text().replace("timeout = 300", "timeout = 2"))
            # Avoid connecting to the real system/session buses in this test.
            bus_address = "unix:path=" + runtime + "/test-bus"
            bus_proc, _ = launch(["dbus-daemon", "--session", "--nofork", "--address=" + bus_address], "smoke-dbus")
            wait_for(lambda: (Path(runtime) / "test-bus").exists(), "private D-Bus")
            idle_env = dict(env, DBUS_SYSTEM_BUS_ADDRESS=bus_address, DBUS_SESSION_BUS_ADDRESS=bus_address, REZERO_TEST_BUS=bus_address)
            fake, fake_log = launch([sys.executable, str(ROOT / "tests/mock_logind.py")], "smoke-logind", idle_env)
            wait_for(lambda: "mock logind ready" in fake_log.read_text(), "test logind service")
            idle, idle_log = launch(sandbox([str(home / ".local/bin/rezero-idle")]), "smoke-idle", idle_env)
            type_keys("-k", "Shift_L")
            wait_for(lambda: "onLockLocked called" in idle_log.read_text(), "idle timeout launches the installed locker", timeout=12)
            time.sleep(0.5)
            type_keys("rezero-test-only", "-k", "Return")
            wait_for(lambda: "auth: authenticated for hyprlock" in idle_log.read_text(), "idle-triggered locker unlocks")
            check_log(idle_log)
            results.append("Real hypridle timeout starts installed launcher; PAM fixture unlock works")
            # Stop the short-timeout daemon and restore the actual 5-minute
            # config before testing D-Bus lock and sleep paths.
            os.killpg(idle.pid, signal.SIGTERM)
            idle.wait(timeout=3)
            idle_conf.write_text(idle_conf.read_text().replace("timeout = 2", "timeout = 300"))
            idle, event_log = launch(sandbox([str(home / ".local/bin/rezero-idle")]), "smoke-sleep", idle_env)
            wait_for(lambda: "Inhibited sleep with fd" in event_log.read_text(), "sleep delay inhibitor")
            def bus_call(path, method, *args):
                subprocess.run(["gdbus", "call", "--address", bus_address, "--dest", "org.freedesktop.login1", "--object-path", path,
                                "--method", "org.example.RezeroTest." + method, *args], check=True, capture_output=True)
            bus_call("/org/freedesktop/login1", "SimulateSleep", "true")
            wait_for(lambda: "onLockLocked called" in event_log.read_text() and "Releasing the sleep inhibitor" in event_log.read_text(), "lock before sleep and release after compositor confirmation")
            type_keys("rezero-test-only", "-k", "Return")
            wait_for(lambda: "auth: authenticated for hyprlock" in event_log.read_text(), "unlock after simulated sleep")
            bus_call("/org/freedesktop/login1", "SimulateSleep", "false")
            time.sleep(1)
            bus_call("/org/freedesktop/login1/session/test", "SimulateLock")
            wait_for(lambda: event_log.read_text().count("onLockLocked called") == 2, "D-Bus session Lock event")
            type_keys("rezero-test-only", "-k", "Return")
            wait_for(lambda: event_log.read_text().count("auth: authenticated for hyprlock") == 2, "unlock after session Lock")
            results.append("Private login1 sleep and Lock signals trigger locking; sleep inhibitor released after lock confirmation")
            print(json.dumps(results, indent=2), flush=True)
            (OUT / "results.json").write_text(json.dumps(results, indent=2) + "\n")
        finally:
            for proc in reversed(processes):
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGTERM)
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGKILL)
                        proc.wait()
            for handle in handles:
                handle.close()


if __name__ == "__main__":
    main()
