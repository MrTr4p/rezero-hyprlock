#!/bin/sh
set -eu
cd "$(dirname "$0")"
if [ ! -x preview/qt-preview ] || [ preview/preview.cpp -nt preview/qt-preview ] || [ preview/context.h -nt preview/qt-preview ]; then ./preview/build.sh; fi
if ! systemctl --user is-active --quiet rezero-lock-localhost.service; then
    systemd-run --user --collect --unit=rezero-lock-localhost --description='Re:Zero animated lock-screen localhost preview' \
        --setenv="REZERO_X11VNC=${REZERO_X11VNC:-}" \
        --setenv="REZERO_CAVA=${REZERO_CAVA:-}" \
        --setenv="REZERO_WEBSOCKIFY_PYTHON=${REZERO_WEBSOCKIFY_PYTHON:-}" \
        "$(command -v python3)" "$PWD/preview/serve.py"
fi
python3 - <<'PY'
import json, time, urllib.request
for attempt in range(60):
    try:
        with urllib.request.urlopen('http://localhost:8772/api/status', timeout=1) as response:
            running = json.load(response)['running']
        if all(running.get(name) for name in ('login', 'xvfb', 'vnc', 'websocket')):
            break
    except (OSError, KeyError, ValueError):
        pass
    time.sleep(.2)
else:
    raise SystemExit('Preview did not become ready. Check: journalctl --user -u rezero-lock-localhost.service -n 40')
PY
printf '%s\n' 'http://localhost:8772/'
