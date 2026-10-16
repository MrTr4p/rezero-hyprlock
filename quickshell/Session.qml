import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Services.Pam

Scope {
    id: session
    property var telemetry: ({})
    readonly property string userName: telemetry.user || Quickshell.env("USER")
    readonly property string displayName: telemetry.displayName || userName
    readonly property string sessionName: telemetry.session || "Hyprland"
    property bool busy: false
    property bool failed: false
    property string message: ""
    property string pendingResponse: ""
    readonly property bool canPowerOff: telemetry.canPowerOff === true
    readonly property bool canReboot: telemetry.canReboot === true
    readonly property bool canSuspend: telemetry.canSuspend === true
    signal authenticated()
    signal clearInputs()

    function submit(response) {
        if (busy || !response.length) return;
        busy = true; failed = false; message = "Unlocking your session…";
        if (pam.active && pam.responseRequired) {
            pam.respond(response);
        } else {
            pendingResponse = response;
            if (!pam.start()) {
                pendingResponse = ""; busy = false; failed = true;
                message = "Authentication could not start. Try again.";
            }
        }
        clearInputs();
    }

    PamContext {
        id: pam
        config: Settings.pamService
        // Leave user unset: Quickshell authenticates the actual current user.
        onPamMessage: {
            if (responseRequired) {
                if (session.pendingResponse.length) {
                    respond(session.pendingResponse);
                    session.pendingResponse = "";
                } else {
                    session.busy = false;
                    session.message = message || "Enter your authentication response.";
                }
            } else if (message.length) {
                session.message = message;
            }
        }
        onCompleted: result => {
            session.pendingResponse = "";
            session.busy = false;
            session.clearInputs();
            if (result === PamResult.Success) {
                session.authenticated();
            } else {
                session.failed = true;
                session.message = result === PamResult.Error ? "Authentication is unavailable. Check the PAM policy." : "Incorrect password. Try again.";
            }
        }
    }

    Process {
        id: stats
        command: ["python3", decodeURIComponent(Qt.resolvedUrl("telemetry.py").toString().replace(/^file:\/\//, ""))]
        running: true
        stdout: SplitParser {
            onRead: data => {
                try { session.telemetry = JSON.parse(data); } catch (e) { /* keep last valid sample */ }
            }
        }
    }

    function performPower(action) {
        if (power.running) return;
        var command = action === "power off" && canPowerOff ? "poweroff" : action === "restart" && canReboot ? "reboot" : action === "sleep" && canSuspend ? "suspend" : "";
        if (!command) return;
        power.command = ["systemctl", "--no-ask-password", command];
        power.running = true;
    }
    Process {
        id: power
        onExited: (code, status) => {
            if (code !== 0) {
                session.failed = true;
                session.message = "The power action was declined by the system.";
            }
        }
    }
}
