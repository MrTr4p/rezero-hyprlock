pragma Singleton
import QtQuick

QtObject {
    property bool animations: true
    property string background: "assets/background.png"
    // Use the distribution's existing PAM authentication policy.
    property string pamService: "login"
}
