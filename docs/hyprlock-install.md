# Optional Hyprlock installation

This installs the **simpler static Hyprlock design**, not the full animated localhost preview. For the full preview, use the [main setup guide](../README.md#install-and-run-the-full-preview-on-arch-linux).

An ivory and lavender **lock screen for Hyprland**, adapted from [the Re:Zero SDDM design](https://github.com/MrTr4p/rezero-sddm). Unlock your existing session with your normal Linux password.

![Re:Zero Hyprlock, captured in a separate Hyprland session](preview.png)

Includes the Emilia/Subaru artwork, two alternate wallpapers, clock, date, compass, keyboard layout, Caps Lock color, and password failure feedback. Hyprlock handles authentication and the Wayland session lock. The wallpaper is still; the original QML hair, feathers, audio player, and desktop-session chooser are not part of this version. Password dots and unlock fading use Hyprlock's animations.

## Install permanently on your friend's computer

Tested with **Hyprland 0.56.2, Hyprlock 0.9.6, and Hypridle 0.1.8 on Arch Linux**. This installer targets Hyprland's `hyprland.conf` format. Use a current distro package for Hyprlock and its supplied PAM policy; do not create a test PAM policy on your computer.

### 1. Install dependencies

On an up-to-date Arch Linux system:

```sh
sudo pacman -S --needed git python hyprlock hypridle util-linux \
  ttf-jetbrains-mono noto-fonts-cjk
```

Hyprland should already be installed and working. Other distributions need equivalent packages, including `/etc/pam.d/hyprlock`. Automatic suspend protection uses Hypridle's `inhibit_sleep = 3` and Hyprland's lock notification protocol. No SDDM, Sway, Quickshell, browser server, build tools, or Python packages are needed to use the installed theme.

### 2. Download and install

Run as your normal desktop user, **without sudo**:

```sh
git clone https://github.com/MrTr4p/rezero-hyprlock.git
cd rezero-hyprlock
python3 install.py --enable
```

The installer copies the artwork to `~/.local/share/rezero-hyprlock/`, creates configuration under `~/.config/hypr/rezero/`, and installs two launchers in `~/.local/bin/`. It backs up an existing default `hyprlock.conf`, makes bare `hyprlock` use this theme, and adds one managed `source` block to `hyprland.conf`. It does not launch the locker, reload Hyprland, or change the login manager.

**Already have Hypridle, Swayidle, or managed dotfiles?** Read [Existing idle setups](#existing-idle-setups) below. The installer refuses automatic idle integration when it detects another idle configuration or an enabled/running `hypridle.service`. Dotfile suites may start a daemon outside these files; check their startup settings too. Run only one idle daemon.

### 3. Log out and log back in

Save your work, then log out of Hyprland and log back in. The sourced snippet starts the idle daemon on every login, including after reboot. A config reload alone does not rerun `exec-once`.

After login:

- **Super + L** locks immediately.
- **Five minutes of inactivity** locks automatically, respecting normal idle inhibitors.
- **Suspend** triggers locking before sleep; Hypridle delays sleep until Hyprland confirms the lock, subject to logind's system delay limit.
- `loginctl lock-session` is handled by the idle daemon.
- Type your Linux password and press **Enter** to unlock. **Escape** clears the input. An amber input border indicates Caps Lock.

Lid close is covered when your existing power policy suspends the machine. This theme does not change lid behavior or force suspend. It does not lock immediately on login or replace the boot login screen.

### 4. Check it on that computer

First test a manual lock from a terminal:

```sh
~/.local/bin/rezero-lock
```

Unlock with that user's actual Linux password. Then verify Super + L, `loginctl lock-session`, and a suspend/resume cycle with work saved. Leave the session idle for five minutes once to check automatic locking. Confirm the idle daemon is running after a fresh login:

```sh
pgrep -a hypridle
hyprctl configerrors
```

The launcher requires an active Wayland session and the distro's Hyprlock PAM file. It has **zero grace time**, and repeated lock requests share one `flock` guard. Passwords are handled by Hyprlock/PAM; the theme has no password database or demo password.

## Existing idle setups

Keep your existing idle daemon and install only the theme/key binding:

```sh
python3 install.py --enable --no-idle
```

For an existing **Hypridle** configuration, edit its current `general` block to use these values, preserving unrelated settings:

```ini
general {
    lock_cmd = ~/.local/bin/rezero-lock
    before_sleep_cmd = ~/.local/bin/rezero-lock
    after_sleep_cmd = hyprctl dispatch dpms on
    inhibit_sleep = 3
}
```

Replace the lock command in its existing idle listener as well:

```ini
listener {
    timeout = 300
    on-timeout = ~/.local/bin/rezero-lock
}
```

Edit the existing blocks rather than creating competing listeners. Keep your existing Hypridle startup method. If you migrate from Swayidle, remove its startup entry and stop using it at the next login before enabling Re:Zero's Hypridle snippet. For lock menu buttons or other shortcuts, point their command to `~/.local/bin/rezero-lock`.

For symlinked configs or a dotfile manager, run `python3 install.py` without `--enable`, then add the printed `source = .../rezero/hyprland.conf` line to the configuration managed by your dotfile tool. Add `--no-idle` if your setup already starts an idle daemon. The files-only install leaves the default `hyprlock.conf` unchanged; use the Re:Zero launcher. The source snippet replaces **Super + L** using `unbind` before `bind`.

Hyprland versions using a different configuration language need equivalent binding/startup entries in that format; the installer does not rewrite Lua configurations.

## Customize

Edit `~/.config/hypr/rezero/hyprlock.conf`. In the `background` block, change only the filename at the end of `path`:

| File | Artwork |
| --- | --- |
| `background.png` | Emilia and Subaru overlooking the city |
| `royal-capital.png` | Lugunica at dawn |
| `moonlit-forest.png` | Silver trees and pale mist |

Keep the full installed asset path. Change `animations { enabled = false }` for reduced motion. The fixed panel fits tested outputs with at least 720 logical pixels in height and 600 in width. Extremely long usernames may need a smaller greeting font.

Edit the `timeout` in `~/.config/hypr/rezero/hypridle.conf` to change the five-minute delay. For an existing idle setup, edit that daemon's config instead. Log out/in after idle-policy changes. Theme edits appear the next time you lock.

The installer respects `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, and `XDG_STATE_HOME`. The paths above show defaults. Assets are copied, so the installed theme continues working if you move or delete the Git checkout.

## Update and uninstall

To update, run `git pull --ff-only`, then rerun the same installation command and flags. Changed managed files are saved under `~/.local/state/rezero-hyprlock/preserved/` before replacement; reapply desired customizations afterward. The original files remain in `originals/`, and the pre-enable Hyprland config is saved as `hyprland.conf.before-enable`.

To uninstall, while the desktop is unlocked:

```sh
python3 install.py --uninstall
```

This removes the managed source block, restores the previous default Hyprlock configuration and any replaced files, and preserves unrelated changes to `hyprland.conf`. Then log out and log back in. If you integrated manually, remove your source entry and restore the lock commands in your existing idle setup yourself. Backups are retained; dependencies are not removed.

If the lock UI cannot authenticate, use **Ctrl + Alt + F3**, log in to your own account, and inspect your distro's Hyprlock/PAM setup. Fix the theme or end the affected graphical session after saving what you can. Removing theme files is not an unlock mechanism. Do not configure a passwordless PAM policy as a workaround.

## Validation

The installer and theme were developed without applying them to the author's desktop. [Validation notes](validation.md) distinguish real integration checks from machine-specific checks still needed by the recipient.

```sh
# No desktop required; all writes use temporary destinations.
python3 -m unittest discover -s tests -v

# Optional developer integration test from a Wayland desktop.
# Briefly creates a separate nested Hyprland window, then headless outputs.
# Needs bwrap, grim, wtype, dbus, gdbus and python-gobject in addition.
python3 tests/smoke.py
```

The integration test uses private runtime/config directories, a private D-Bus with simulated login1 events, and a PAM fixture mounted **only inside a disposable namespace**. The installer never copies test files. No real password, host suspend, or real session lock request is used. Logs and screenshots are kept in the ignored `validation/` directory.

## Credits

Unofficial Re:Zero fan theme. Artwork and the compass are reused from [MrTr4p/rezero-sddm](https://github.com/MrTr4p/rezero-sddm), source commit `cea4cc1`. The PNG compass is a raster export of the original SVG. [Artwork provenance](artwork.md) includes the original generation prompts.

References: [Hyprlock configuration](https://wiki.hypr.land/Hypr-Ecosystem/hyprlock/), [Hypridle configuration](https://wiki.hypr.land/Hypr-Ecosystem/hypridle/), and [Hyprlock source](https://github.com/hyprwm/hyprlock).
