#!/usr/bin/env python3
"""Real QuickShell/PAM session locking in a disposable nested Hyprland.

Requires Hyprland, quickshell, hypridle, bwrap, grim, wtype, python-gobject.
Test authentication exists only inside bubblewrap, never in the host PAM tree.
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
OUT = ROOT / "validation/quickshell"


def wait_for(predicate, label, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if predicate():
                return
        except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
            pass
        time.sleep(.1)
    raise AssertionError("Timeout: " + label)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    processes, handles, results = [], [], []
    socket = str(Path(os.environ["XDG_RUNTIME_DIR"]) / os.environ["WAYLAND_DISPLAY"])
    with tempfile.TemporaryDirectory(prefix="rz-qs-") as runtime:
        env = dict(os.environ, XDG_RUNTIME_DIR=runtime, WAYLAND_DISPLAY="wayland-1", HYPRLAND_NO_SD_VARS="1",
                   LIBSEAT_BACKEND="seatd", QT_QUICK_CONTROLS_STYLE="Basic", QT_QPA_PLATFORM="wayland", QSG_RHI_BACKEND="opengl")
        env.pop("HYPRLAND_INSTANCE_SIGNATURE", None)
        home = Path(runtime) / "friend home"
        config = home / ".config/hypr"
        config.mkdir(parents=True)
        conf = config / "hyprland.conf"
        conf.write_text("""monitor = , 1280x720@60, auto, 1
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
        subprocess.run([sys.executable, str(ROOT / "install.py"), "--enable", "--no-idle", "--target-home", str(home)], env=env, check=True)
        subprocess.run(["Hyprland", "--verify-config", "--config", str(conf)], env=env, check=True, capture_output=True)
        shell = home / ".config/quickshell/rezero"
        pam = Path(runtime) / "pam.d"
        pam.mkdir()
        fixture = Path(runtime) / "pam-fixture.py"
        fixture.write_text('import sys\nsys.exit(0 if sys.stdin.buffer.read().rstrip(b"\\x00") == b"rezero-test-only" else 1)\n')
        (pam / "login").write_text(f"auth required pam_exec.so expose_authtok quiet /usr/bin/python3 {fixture}\n")
        # A test-only inspection endpoint observes real surfaces and triggers
        # media button clicks. It cannot authenticate or unlock the screen.
        main_qml = shell / "shell.qml"
        text = main_qml.read_text().replace("import Quickshell.Wayland", "import Quickshell.Wayland\nimport Quickshell.Io")
        text = text.replace("    WlSessionLock {", '''    property var views: []
    IpcHandler {
        target: "test"
        function state(): string {
            var data = {secure: lock.secure, busy: sessionState.busy, failed: sessionState.failed, surfaces: views.length, message: sessionState.message};
            if (views.length) {
                var panel = find(views[0], "spotifyPanel");
                data.spotify = panel ? panel.visible : false;
                data.title = panel && panel.player ? panel.player.trackTitle : "";
                data.nextEnabled = find(views[0], "spotify-next").enabled;
            }
            return JSON.stringify(data);
        }
        function click(name: string): void {
            var button = views.length ? find(views[0], name) : null;
            if (button && button.enabled) button.clicked();
        }
    }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (var i=0; i<item.children.length; ++i) {
            var child = find(item.children[i], name);
            if (child) return child;
        }
        return null;
    }
    WlSessionLock {''')
        text = text.replace("session: sessionState }", "session: sessionState; Component.onCompleted: views.push(this); Component.onDestruction: views.splice(views.indexOf(this), 1) }")
        main_qml.write_text(text)

        def launch(command, name, custom_env=None):
            log = OUT / (name + ".log")
            handle = log.open("w")
            handles.append(handle)
            process = subprocess.Popen(command, env=custom_env or env, stdout=handle, stderr=handle, start_new_session=True)
            processes.append(process)
            return process, log

        def ctl(*args):
            return subprocess.check_output(["hyprctl", "-i", "0", *args], env=env, text=True)

        def sandbox(command):
            return ["bwrap", "--ro-bind", "/", "/", "--dev-bind", "/dev", "/dev", "--proc", "/proc", "--bind", runtime, runtime,
                    "--ro-bind", str(pam), "/etc/pam.d", "--unshare-user", "--unshare-pid", "--die-with-parent", *command]

        def keys(*args):
            subprocess.run(["wtype", "-s", "100", *args, "-s", "100"], env=env, check=True)

        def ipc(method, *args):
            return subprocess.check_output(["quickshell", "--path", str(main_qml), "ipc", "call", "test", method, *args], env=env, text=True, stderr=subprocess.DEVNULL)

        def state():
            return json.loads(ipc("state"))

        def launcher_released(kind="lock"):
            return subprocess.run(["flock", "--nonblock", str(Path(runtime) / f"rezero-{kind}-wayland-1.lock"), "true"], env=env).returncode == 0

        def screenshot(name, output="REZERO-1"):
            ctl("dismissnotify")
            time.sleep(.4)
            subprocess.run(["grim", "-o", output, str(OUT / (name + ".png"))], env=env, check=True)

        lock_command = [str(home / ".local/bin/rezero-lock")]
        try:
            launch(["Hyprland", "--config", str(conf)], "hyprland", dict(env, WAYLAND_DISPLAY=socket))
            wait_for(lambda: (Path(runtime) / "wayland-1").exists(), "nested compositor")
            wait_for(lambda: bool(json.loads(ctl("monitors", "-j"))), "monitor")
            env["HYPRLAND_INSTANCE_SIGNATURE"] = json.loads(subprocess.check_output(["hyprctl", "instances", "-j"], env=env, text=True))[0]["instance"]
            outputs = [o["name"] for o in json.loads(ctl("monitors", "-j"))]
            ctl("output", "create", "headless", "REZERO-1")
            ctl("keyword", "monitor", "REZERO-1,1920x1080@60,0x0,1")
            for output in outputs:
                ctl("keyword", "monitor", output + ",disable")
            ctl("dispatch", "focusmonitor", "REZERO-1")

            # No connection to real Spotify or login1 in integration tests.
            address = "unix:path=" + runtime + "/bus"
            launch(["dbus-daemon", "--session", "--nofork", "--address=" + address], "dbus")
            wait_for(lambda: (Path(runtime) / "bus").exists(), "private D-Bus")
            env.update(DBUS_SESSION_BUS_ADDRESS=address, DBUS_SYSTEM_BUS_ADDRESS=address, REZERO_TEST_BUS=address)
            launch([sys.executable, str(ROOT / "tests/mock_logind.py")], "logind")
            locker, log = launch(sandbox(lock_command), "lock")
            wait_for(lambda: "ReZero: session secured" in log.read_text(), "session lock acquired")
            wait_for(lambda: state()["secure"], "secure inspection")
            assert not state()["spotify"]
            unrelated, _ = launch([sys.executable, str(ROOT / "tests/mock_spotify.py")], "other-player", dict(env, REZERO_MPRIS_NAME="org.mpris.MediaPlayer2.vlc"))
            time.sleep(.6)
            assert not state()["spotify"]
            unrelated.terminate()
            unrelated.wait(timeout=3)
            time.sleep(1.5)
            screenshot("installed-1920x1080")
            results.append("Installed QuickShell acquires ext-session-lock; no Spotify panel without Spotify")
            duplicate = subprocess.run(sandbox(lock_command), env=env, capture_output=True, timeout=3)
            assert duplicate.returncode == 0
            results.append("Repeated lock request succeeds without a second locker")

            # Spotify is an actual D-Bus MPRIS service fixture, not a QML mock.
            spotify, spotify_log = launch([sys.executable, str(ROOT / "tests/mock_spotify.py")], "spotify")
            wait_for(lambda: state()["spotify"] and state()["title"] == "Another Beginning", "Spotify discovery")
            for action in ["toggle", "next", "previous"]:
                ipc("click", "spotify-" + action)
            wait_for(lambda: all(x in spotify_log.read_text() for x in ["Pause", "Next", "Previous"]), "media methods reached Spotify over D-Bus")
            screenshot("spotify-1920x1080")
            subprocess.run(["gdbus", "call", "--address", address, "--dest", "org.mpris.MediaPlayer2.spotify", "--object-path", "/org/mpris/MediaPlayer2", "--method", "org.example.RezeroTest.SetCapabilities", "false"], check=True, capture_output=True)
            wait_for(lambda: not state()["nextEnabled"], "unsupported Spotify controls disabled")
            before = spotify_log.read_text().count("Next")
            ipc("click", "spotify-next")
            time.sleep(.2)
            assert spotify_log.read_text().count("Next") == before
            spotify.terminate()
            spotify.wait(timeout=3)
            wait_for(lambda: not state()["spotify"], "Spotify disconnection")
            results.append("Spotify metadata, play/pause, next, previous, appearance and disappearance via real MPRIS")

            keys("discard-this", "-k", "Escape", "-k", "Return")
            assert not state()["busy"] and not state()["failed"]
            keys("wrong-test", "-k", "Return")
            wait_for(lambda: state()["failed"], "PAM rejection")
            assert locker.poll() is None and state()["secure"]
            screenshot("password-rejected")
            results.append("Empty input ignored; Escape clears; real PAM rejection stays securely locked")

            ctl("output", "create", "headless", "REZERO-2")
            ctl("keyword", "monitor", "REZERO-2,1280x720@60,1920x0,1")
            wait_for(lambda: state()["surfaces"] == 2, "hotplug lock surface")
            screenshot("hotplug-1280x720", "REZERO-2")
            for width, height, scale in [(1366, 768, 1), (1080, 1920, 1), (2560, 1440, 1.25)]:
                ctl("keyword", "monitor", f"REZERO-1,{width}x{height}@60,0x0,{scale}")
                time.sleep(.7)
                screenshot(f"{width}x{height}-scale{scale}")
            results.append("Hotplug covered; 720p, 1366x768, portrait and 1440p at 125% render")
            ctl("dispatch", "focusmonitor", "REZERO-1")
            ctl("dispatch", "movecursor", "500", "500")
            keys("-k", "Escape", "rezero-test-only", "-k", "Return")
            assert locker.wait(timeout=10) == 0
            results.append("Correct real PAM fixture response unlocks every monitor and exits")
            assert not re.search(r"ReferenceError|TypeError|Binding loop|failed to load|is not a type|Cannot assign", log.read_text(), re.I), log.read_text()

            idle_config = config / "rezero/hypridle.conf"
            idle_config.write_text(idle_config.read_text().replace("timeout = 300", "timeout = 2"))
            idle, idle_log = launch(sandbox([str(home / ".local/bin/rezero-idle")]), "idle")
            keys("-k", "Shift_L")
            wait_for(lambda: "ReZero: session secured" in idle_log.read_text(), "idle locks")
            time.sleep(.4)
            keys("rezero-test-only", "-k", "Return")
            wait_for(lambda: "Wayland session got unlocked" in idle_log.read_text(), "idle unlock")
            results.append("Installed Hypridle starts the QuickShell locker after inactivity")
            os.killpg(idle.pid, signal.SIGTERM)
            idle.wait(timeout=3)
            wait_for(lambda: launcher_released("idle"), "old idle launcher released")
            wait_for(launcher_released, "idle-triggered locker exits")
            idle_config.write_text(idle_config.read_text().replace("timeout = 2", "timeout = 300"))
            idle, event_log = launch(sandbox([str(home / ".local/bin/rezero-idle")]), "sleep")
            wait_for(lambda: "Inhibited sleep with fd" in event_log.read_text(), "sleep inhibitor")

            def bus_call(path, method, *args):
                subprocess.run(["gdbus", "call", "--address", address, "--dest", "org.freedesktop.login1", "--object-path", path,
                                "--method", "org.example.RezeroTest." + method, *args], check=True, capture_output=True)

            bus_call("/org/freedesktop/login1", "SimulateSleep", "true")
            wait_for(lambda: "ReZero: session secured" in event_log.read_text() and "Releasing the sleep inhibitor" in event_log.read_text(), "secured before simulated suspend")
            time.sleep(.4)
            keys("rezero-test-only", "-k", "Return")
            wait_for(lambda: "Wayland session got unlocked" in event_log.read_text(), "unlock after simulated sleep")
            wait_for(launcher_released, "locker exits after authentication")
            bus_call("/org/freedesktop/login1", "SimulateSleep", "false")
            bus_call("/org/freedesktop/login1/session/test", "SimulateLock")
            wait_for(lambda: event_log.read_text().count("ReZero: session secured") == 2, "login1 Lock event")
            time.sleep(.4)
            keys("rezero-test-only", "-k", "Return")
            wait_for(lambda: event_log.read_text().count("Wayland session got unlocked") == 2, "unlock after Lock event")
            results.append("Private login1 sleep/Lock signals launch QuickShell; sleep delay releases after compositor lock confirmation")
            (OUT / "results.json").write_text(json.dumps(results, indent=2) + "\n")
            print(json.dumps(results, indent=2))
        finally:
            for process in reversed(processes):
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
            for handle in handles:
                handle.close()


if __name__ == "__main__":
    main()
