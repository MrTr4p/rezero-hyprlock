// Production entry point. Only a successful PAM result releases the lock.
import QtQuick
import Quickshell
import Quickshell.Wayland

ShellRoot {
    Session {
        id: sessionState
        onAuthenticated: {
            lock.locked = false;
            Qt.callLater(Qt.quit);
        }
    }
    WlSessionLock {
        id: lock
        locked: true
        onSecureChanged: if (secure) console.info("ReZero: session secured")
        WlSessionLockSurface {
            color: "#f2efe7"
            LockView { anchors.fill: parent; session: sessionState }
        }
    }
}
