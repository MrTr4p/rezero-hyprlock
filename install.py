#!/usr/bin/env python3
"""Install a per-user Hyprlock theme; never start a locker or reload Hyprland."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import sys
import time

SOURCE = Path(__file__).resolve().parent
BEGIN = "# BEGIN REZERO HYPRLOCK (managed by install.py)"
END = "# END REZERO HYPRLOCK"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def paths(target):
    home = Path(target).expanduser().resolve() if target else Path.home()
    def xdg(key, suffix):
        return home / suffix if target else Path(os.environ.get(key, home / suffix))
    return {
        "config": xdg("XDG_CONFIG_HOME", ".config") / "hypr",
        "data": xdg("XDG_DATA_HOME", ".local/share") / "rezero-hyprlock",
        "state": xdg("XDG_STATE_HOME", ".local/state") / "rezero-hyprlock",
        "bin": home / ".local/bin",
    }


class Installation:
    def __init__(self, locations):
        self.p = locations
        self.manifest = self.p["state"] / "manifest.json"
        self.entries = json.loads(self.manifest.read_text()) if self.manifest.exists() else {}

    def save(self):
        self.manifest.parent.mkdir(parents=True, exist_ok=True)
        self.manifest.write_text(json.dumps(self.entries, indent=2) + "\n")

    def write(self, path, data, mode=0o644):
        if isinstance(data, str):
            data = data.encode()
        if path.is_symlink():
            raise ValueError(f"Refusing to replace symlink: {path}")
        key = str(path)
        if key not in self.entries:
            backup = None
            if path.exists():
                backup = self.p["state"] / "originals" / digest(key.encode())
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, backup)
            self.entries[key] = {"backup": str(backup) if backup else None}
        elif path.exists() and digest(path.read_bytes()) != self.entries[key].get("sha256"):
            self.preserve(path)
        self.save()  # recovery information exists before any replacement
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(path.name + ".rezero-new")
        temp.write_bytes(data)
        temp.chmod(mode)
        temp.replace(path)
        self.entries[key]["sha256"] = digest(data)
        self.save()

    def preserve(self, path):
        saved = self.p["state"] / "preserved" / (str(time.time_ns()) + "-" + path.name)
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, saved)
        print(f"Saved your edited file: {saved}")

    def uninstall(self):
        main = self.p["config"] / "hyprland.conf"
        if main.is_symlink():
            raise ValueError("Remove the Re:Zero source block from your symlinked Hyprland config manually before rollback.")
        if main.exists():
            text = main.read_text()
            clean = re.sub(r"\n?" + re.escape(BEGIN) + r"\n.*?\n" + re.escape(END) + r"\n?", "\n", text, flags=re.S)
            if clean != text:
                # Preserve unrelated edits made since installation.
                main.write_text(clean)
        for key, entry in reversed(list(self.entries.items())):
            path = Path(key)
            if path.is_symlink():
                raise ValueError(f"Refusing to replace symlink during rollback: {path}")
            if path.exists() and digest(path.read_bytes()) != entry.get("sha256"):
                self.preserve(path)
            if entry["backup"]:
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(entry["backup"], path)
            else:
                path.unlink(missing_ok=True)
        self.manifest.unlink(missing_ok=True)
        print("Uninstalled. Original files restored; backups retained at " + str(self.p["state"]))
        print("Log out and back in to stop using the old idle daemon.")


def launcher(command, kind):
    pam_check = '''if [ ! -r /etc/pam.d/hyprlock ]; then
    echo "Missing /etc/pam.d/hyprlock; install your distribution's hyprlock package." >&2
    exit 1
fi
''' if kind == "lock" else ""
    return f'''#!/bin/sh
set -eu
if [ "$#" -ne 0 ]; then
    echo "This launcher takes no arguments." >&2
    exit 2
fi
: "${{XDG_RUNTIME_DIR:?Run this inside your Hyprland session}}"
: "${{WAYLAND_DISPLAY:?Run this inside your Hyprland session}}"
{pam_check}\
display=${{WAYLAND_DISPLAY##*/}}
# flock holds the lock until the child exits; simultaneous requests are harmless.
exec flock --nonblock --conflict-exit-code 0 "$XDG_RUNTIME_DIR/rezero-{kind}-$display.lock" {command}
'''


def install(args):
    p = paths(args.target_home)
    for path in p.values():
        if not path.is_absolute() or any(c in str(path) for c in "\n\r#$\\"):
            raise ValueError("Installation paths must be absolute and cannot contain newline, #, $, or backslash.")
    instance = Installation(p)
    if args.uninstall:
        instance.uninstall()
        return

    required = ["hyprlock", "flock"] + ([] if args.no_idle else ["hypridle", "hyprctl"])
    missing = [name for name in required if not shutil.which(name)]
    if missing:
        raise ValueError("Install dependencies first. Missing: " + ", ".join(missing))
    main = p["config"] / "hyprland.conf"
    if args.enable:
        if not main.is_file() or main.is_symlink():
            raise ValueError("--enable needs a regular hyprland.conf. For a symlink or other layout, install without --enable and source the generated snippet manually.")
        if not args.no_idle:
            conflicts = []
            for file in p["config"].rglob("*.conf"):
                if "rezero" in file.relative_to(p["config"]).parts:
                    continue
                lines = "\n".join(line.split("#", 1)[0] for line in file.read_text(errors="replace").splitlines())
                if re.search(r"\b(?:hypridle|swayidle)\b", lines):
                    conflicts.append(str(file))
            if conflicts:
                raise ValueError("Existing idle setup found in " + ", ".join(conflicts) + ". Use --no-idle and integrate the lock command into your current daemon; see README.")
            check = shutil.which("systemctl")
            if check and not args.target_home:
                import subprocess
                for state in ["is-enabled", "is-active"]:
                    result = subprocess.run([check, "--user", state, "--quiet", "hypridle.service"], capture_output=True)
                    if result.returncode == 0:
                        raise ValueError("hypridle.service is already enabled/running. Use --no-idle; see README.")

    config = p["config"] / "rezero"
    lock = p["bin"] / "rezero-lock"
    idle = p["bin"] / "rezero-idle"
    planned = [config / "hyprlock.conf", config / "hypridle.conf", config / "hyprland.conf", lock, idle]
    if args.enable:
        planned.append(p["config"] / "hyprlock.conf")
    planned.extend(p["data"] / "assets" / asset.name for asset in (SOURCE / "theme/assets").iterdir())
    for path in planned:
        if path.is_symlink():
            raise ValueError(f"Refusing to replace symlink: {path}")

    for asset in (SOURCE / "theme/assets").iterdir():
        instance.write(p["data"] / "assets" / asset.name, asset.read_bytes())
    template = (SOURCE / "theme/hyprlock.conf.in").read_text()
    instance.write(config / "hyprlock.conf", template.replace("@ASSETS@", str(p["data"] / "assets")))
    template = (SOURCE / "theme/hypridle.conf.in").read_text()
    instance.write(config / "hypridle.conf", template.replace("@LOCK_COMMAND@", shlex.quote(str(lock))))
    instance.write(lock, launcher("hyprlock --config " + shlex.quote(str(config / "hyprlock.conf")) + " --grace 0 --no-fade-in", "lock"), 0o755)
    instance.write(idle, launcher("hypridle --config " + shlex.quote(str(config / "hypridle.conf")), "idle"), 0o755)
    snippet = "# Re:Zero — sourced by Hyprland on every login.\n"
    snippet += "unbind = SUPER, L\nbind = SUPER, L, exec, " + shlex.quote(str(lock)) + "\n"
    if not args.no_idle:
        snippet += "exec-once = " + shlex.quote(str(idle)) + "\n"
    instance.write(config / "hyprland.conf", snippet)

    if args.enable:
        instance.write(p["config"] / "hyprlock.conf", "source = " + str(config / "hyprlock.conf") + "\n")
        text = main.read_text()
        block = BEGIN + "\nsource = " + str(config / "hyprland.conf") + "\n" + END
        if BEGIN in text:
            text = re.sub(re.escape(BEGIN) + r"\n.*?\n" + re.escape(END), lambda _: block, text, flags=re.S)
        else:
            backup = p["state"] / "hyprland.conf.before-enable"
            if not backup.exists():
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(main, backup)
            text = text.rstrip("\n") + "\n\n" + block + "\n"
        main.write_text(text)
        print("Enabled for future Hyprland logins. Log out and back in when ready.")
    else:
        print("Installed files only. To enable at every login, add to hyprland.conf:")
        print("source = " + str(config / "hyprland.conf"))
    print("Manual lock: " + str(lock))
    print("Configuration: " + str(config))
    print("No session was locked, reloaded, or restarted.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enable", action="store_true", help="back up the default lock config and add persistent Hyprland integration")
    parser.add_argument("--no-idle", action="store_true", help="leave automatic locking to your existing idle daemon")
    parser.add_argument("--uninstall", action="store_true", help="restore backed-up files and remove the managed Hyprland block")
    parser.add_argument("--target-home", type=Path, help="use a separate directory for installation tests")
    try:
        install(parser.parse_args())
    except (ValueError, OSError, json.JSONDecodeError) as error:
        sys.exit(str(error))
