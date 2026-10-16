> Archived browser demo. For the real installed QuickShell locker, use the [main installation guide](../README.md). This older demo is kept only for reference.

# Full Re:Zero lock-screen design — localhost preview

This preview restores the original Re:Zero composition and interactions. It is a design preview with mock authentication and power actions, not an installed system locker.

## Run

From the repository root:

```sh
./localhost/start.sh
```

Open **http://localhost:8772/**. Type **`test`** in the password field and press Enter or click Unlock. A different nonempty password shows the failure state. Successful demo unlock automatically resets after a short pause. The username represents the existing session and cannot be edited.

The complete layout includes:

- Re:Zero title, Japanese subtitle, quote, framed artwork, and bottom ribbon.
- Drifting feathers, animated wind header, breathing compass, and hover effects. Character artwork is still.
- Current Hyprland session panel and account/password form, including reveal, Caps Lock, and Escape-to-clear feedback.
- Clock, date, hostname greeting, live CPU/RAM/swap values, battery, and CAVA spectrum when available.
- Synthesized ambience with play/pause, volume, and mute. Audio starts paused.
- Power-off, restart, and sleep dialogs whose actions are simulated only.
- Browser controls for all three wallpapers, resetting the demo, and full screen.

For reduced motion, set `Animations=false` in `localhost/theme/theme.conf`, then use Reset in the browser.

## Dependencies on a fresh Arch computer

The commands below assume you have cloned the repository and are in its root.

```sh
sudo pacman -S --needed base-devel git python qt6-base qt6-declarative \
  qt6-multimedia qt6-svg mesa xorg-server-xvfb x11vnc \
  cava ttf-jetbrains-mono noto-fonts-cjk
python3 -m venv "$HOME/.local/share/rezero-lock-preview/venv"
"$HOME/.local/share/rezero-lock-preview/venv/bin/pip" install -r localhost/preview/requirements.txt
./localhost/start.sh
```

The launcher compiles the small Qt preview program locally and starts a transient systemd **user** service named `rezero-lock-localhost.service`. No login manager or lock daemon is installed. Assets and code stay inside the checkout; Python packages stay in the separate environment above. The existing local tool overrides `REZERO_X11VNC`, `REZERO_CAVA`, and `REZERO_WEBSOCKIFY_PYTHON` are supported.

The browser service binds to `127.0.0.1:8772`, WebSocket to `127.0.0.1:6072`, and VNC to loopback port `5972`. Xvfb uses the private display `:172`. The original SDDM preview on port 8770 is independent.

## Stop and inspect

```sh
./localhost/stop.sh
journalctl --user -u rezero-lock-localhost.service -n 40
```

Logs are written under `localhost/runtime/`, excluded from Git. Stopping the service also stops its virtual display and streaming processes. It is not enabled at boot.

## Verify

```sh
./localhost/preview/test.sh
```

The QML interaction suite verifies the read-only current account, password validation, duplicate submission handling, reveal/clear, simulated unlock, power confirmation/cancel, and audio controls. It does not authenticate a real user or execute system power commands.

The supported [QuickShell installation](../README.md) connects the full design to real session locking, PAM, and Spotify controls. This archived browser demo continues to use simulated authentication and ambience audio.

Artwork comes from [the original Re:Zero theme](https://github.com/MrTr4p/rezero-sddm). Vendored noVNC retains its [upstream license](preview/vendor/novnc/LICENSE.txt).
