#!/usr/bin/env python3
"""Read-only local telemetry; JSON lines on stdout, no HTTP server."""
import json
import os
from pathlib import Path
import platform
import pwd
import shutil
import signal
import subprocess
import tempfile
import threading
import time


def read_text(path):
    return Path(path).read_text().strip()


def power_capabilities():
    result = {}
    for key, method in [("canPowerOff", "CanPowerOff"), ("canReboot", "CanReboot"), ("canSuspend", "CanSuspend")]:
        try:
            reply = subprocess.check_output([
                "gdbus", "call", "--system", "--dest", "org.freedesktop.login1",
                "--object-path", "/org/freedesktop/login1",
                "--method", "org.freedesktop.login1.Manager." + method,
            ], stderr=subprocess.DEVNULL, text=True, timeout=2)
            result[key] = "'yes'" in reply
        except (OSError, subprocess.SubprocessError):
            result[key] = False
    return result


def keyboard():
    try:
        data = json.loads(subprocess.check_output(["hyprctl", "devices", "-j"], text=True, stderr=subprocess.DEVNULL, timeout=1))
        devices = data.get("keyboards", [])
        device = next((d for d in devices if d.get("main")), devices[0] if devices else {})
        layouts = device.get("layout", "").split(",")
        index = device.get("active_layout_index", 0)
        label = layouts[index] if 0 <= index < len(layouts) and layouts[index] else device.get("active_keymap", "—")
        return {"layout": label, "capsLock": device.get("capsLock", False)}
    except (OSError, ValueError, subprocess.SubprocessError):
        return {"layout": "—", "capsLock": False}


def battery():
    for supply in Path("/sys/class/power_supply").glob("*"):
        try:
            if read_text(supply / "type") == "Battery":
                return int(read_text(supply / "capacity"))
        except (OSError, ValueError):
            pass
    return None


def main():
    stop = threading.Event()
    cava_child = None
    spectrum = {"bars": [0] * 64, "cava": False}
    account = pwd.getpwuid(os.getuid())
    name = account.pw_gecos.split(",")[0].strip() or account.pw_name
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "Hyprland").split(":")[0]
    try:
        os_name = platform.freedesktop_os_release().get("PRETTY_NAME", "Linux")
    except OSError:
        os_name = "Linux"

    def shutdown(*_):
        stop.set()
        if cava_child is not None and cava_child.poll() is None:
            cava_child.terminate()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    def monitor_audio():
        nonlocal cava_child
        if not shutil.which("cava"):
            return
        # Temporary config is private and disappears when the helper exits.
        with tempfile.TemporaryDirectory(prefix="rezero-cava-", dir=os.environ.get("XDG_RUNTIME_DIR")) as tmp:
            config = Path(tmp) / "cava.conf"
            config.write_text("""[general]
framerate = 30
bars = 64
[input]
method = pulse
source = auto
[output]
method = raw
raw_target = /dev/stdout
data_format = ascii
ascii_max_range = 1000
bar_delimiter = 59
frame_delimiter = 10
channels = mono
""")
            while not stop.is_set():
                try:
                    cava_child = subprocess.Popen(["cava", "-p", str(config)], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
                    for line in cava_child.stdout:
                        values = [min(1, max(0, int(v) / 1000)) for v in line.strip().split(";") if v]
                        if len(values) == 64:
                            spectrum.update(bars=values, cava=True)
                        if stop.is_set():
                            break
                except (OSError, ValueError):
                    pass
                finally:
                    if cava_child is not None:
                        if cava_child.poll() is None:
                            cava_child.terminate()
                        try:
                            cava_child.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            cava_child.kill()
                            cava_child.wait()
                        if cava_child.stdout:
                            cava_child.stdout.close()
                    spectrum.update(bars=[0] * 64, cava=False)
                stop.wait(5)

    audio = threading.Thread(target=monitor_audio, daemon=True)
    audio.start()
    previous = None
    data = {"user": account.pw_name, "displayName": name, "session": desktop, "os": os_name + " · " + platform.release()}
    next_stats = next_capabilities = 0
    try:
        while not stop.is_set():
            now = time.monotonic()
            if now >= next_capabilities:
                data.update(power_capabilities())
                next_capabilities = now + 30
            if now >= next_stats:
                try:
                    cpu = list(map(int, read_text("/proc/stat").splitlines()[0].split()[1:9]))
                    total, idle = sum(cpu), cpu[3] + cpu[4]
                    usage = 0 if previous is None else 100 * (1 - (idle - previous[1]) / max(1, total - previous[0]))
                    previous = total, idle
                    mem = {line.split(":")[0]: int(line.split()[1]) for line in read_text("/proc/meminfo").splitlines()}
                    gib = lambda kb: f"{kb / 1048576:.1f}"
                    data.update(cpu=f"{max(0, min(100, usage)):.1f}%",
                                memory=f'{gib(mem["MemTotal"] - mem["MemAvailable"])} / {gib(mem["MemTotal"])} GiB',
                                swap=f'{gib(mem["SwapTotal"] - mem["SwapFree"])} / {gib(mem["SwapTotal"])} GiB',
                                battery=battery())
                except (OSError, ValueError, KeyError):
                    pass
                data.update(keyboard())
                next_stats = now + 1
            print(json.dumps(dict(data, **spectrum)), flush=True)
            stop.wait(1 / 30 if spectrum["cava"] else .5)
    except (BrokenPipeError, KeyboardInterrupt):
        pass
    finally:
        shutdown()
        audio.join(timeout=3)


if __name__ == "__main__":
    main()
