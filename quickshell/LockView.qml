import QtQuick
import QtQuick.Controls
import Quickshell

Rectangle {
    id: root
    width: 1920; height: 1080; color: "#f2efe7"
    readonly property color ink: "#30344f"
    readonly property color accent: "#71639e"
    required property var session
    readonly property string host: session.userName
    readonly property real sceneScale: Math.min(width / 1920, height / 1080)
    readonly property bool animations: Settings.animations
    readonly property string backgroundPath: Settings.background
    readonly property var telemetry: session.telemetry
    readonly property bool busy: session.busy
    readonly property bool failed: session.failed
    readonly property string message: session.message
    readonly property string sessionName: session.sessionName
    property var clock: new Date()
    property bool revealPassword: false
    property string powerAction: ""
    property bool entrance: false

    function submit() {
        if (!password.text.length || root.busy) return;
        root.revealPassword = false;
        session.submit(password.text);
    }
    Timer { interval: 1000; running: true; repeat: true; onTriggered: root.clock = new Date() }
    Connections {
        target: root.session
        function onClearInputs() { password.clear(); root.revealPassword = false; password.forceActiveFocus(); }
    }
    Component.onCompleted: { entrance = true; password.forceActiveFocus(); }

    Item {
        id: scene; width: 1920; height: 1080; anchors.centerIn: parent; scale: root.sceneScale
        AnimatedBackground {
            objectName: "animatedBackground"
            x: 0; y: 56; width: 1920; height: 968
            source: root.backgroundPath
            motionEnabled: root.animations
        }
        // Fine architectural rules frame the artwork without boxing in the composition.
        Rectangle { x: 12; y: 68; width: 1896; height: 944; color: "transparent"; border.color: "#5a877b9b"; border.width: 1 }
        Repeater {
            model: 24
            ThemeText { required property int index; x: 23 + index * 81; y: 68; text: "+"; color: "#6c8d819e"; font.pixelSize: 13 }
        }
        Repeater {
            model: 24
            ThemeText { required property int index; x: 23 + index * 81; y: 987; text: "+"; color: "#6c8d819e"; font.pixelSize: 13 }
        }
        // Wind and feathers replace the duplicate title in the top ribbon.
        Rectangle {
            x: 0; y: 0; width: 1920; height: 56; color: root.ink
            Image { x: 22; y: 9; width: 38; height: 38; source: "assets/compass.svg" }
            ThemeText { x: 76; y: 9; text: "“You’re weak, you’re hopeless, and you can’t do anything, but you still fight.”"; color: "#e5dfef"; font.pixelSize: 15; font.italic: true; font.letterSpacing: 0.7 }
            ThemeText { x: 78; y: 32; text: "— Subaru Natsuki"; color: "#b8afcc"; font.pixelSize: 11; font.letterSpacing: 1.4 }
            WindRibbon { objectName: "windRibbon"; x: 1438; y: 0; width: 445; height: 56; motionEnabled: root.animations }
        }
        Item {
            id: left; x: 78; y: 102; width: 410; height: 860
            opacity: root.entrance ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: root.animations ? 1100 : 0 } }
            ThemeText { x: -6; y: -10; text: "Re:ゼロ"; font.family: "Noto Serif CJK JP"; font.pixelSize: 83; font.letterSpacing: -5; font.weight: Font.Medium }
            ThemeText { x: 79; y: 99; text: "から始める異世界生活"; font.family: "Noto Sans CJK JP"; font.pixelSize: 26; font.weight: Font.DemiBold; font.letterSpacing: 0 }
            ThemeText { x: 0; y: 151; text: "✦  Starting Life in Another World"; font.pixelSize: 12; font.letterSpacing: 1.1 }
            Rectangle { x: 0; y: 186; width: 400; height: 1; color: "#777c728e" }
            ThemeText { y: 206; text: "LOCKED SESSION"; color: "#756b88"; font.pixelSize: 12; font.letterSpacing: 3 }
            ThemeButton {
                y: 243; width: 410; height: 50; text: root.sessionName; glyph: "●"; trailing: "›"; selected: true
                Accessible.name: "Current session: " + root.sessionName
                onClicked: password.forceActiveFocus()
            }
            ThemeText { y: 313; text: "WAYLAND  /  SESSION LOCKED"; color: "#83798f"; font.pixelSize: 10; font.letterSpacing: 1.7 }
            SessionNote {
                id: currentSessionInfo
                y: 650; width: 405; height: 185
                sessionName: root.sessionName
                displayName: root.session.displayName
            }
        }
        Item {
            id: center; x: 660; y: 292; width: 600; height: 610
            opacity: root.entrance ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: root.animations ? 1500 : 0 } }
            ThemeText { y: 0; width: 600; text: Qt.formatDateTime(root.clock, "HH:mm"); font.pixelSize: 83; font.letterSpacing: 5; horizontalAlignment: Text.AlignHCenter }
            ThemeText { y: 105; width: 600; text: Qt.formatDateTime(root.clock, "ddd, MMM d yyyy").toUpperCase(); font.pixelSize: 17; font.letterSpacing: 3; horizontalAlignment: Text.AlignHCenter }
            ThemeText { y: 157; width: 600; text: "[ Nice to see you, " + root.host + " ]"; font.pixelSize: 24; font.letterSpacing: 2; horizontalAlignment: Text.AlignHCenter; fontSizeMode: Text.HorizontalFit; minimumPixelSize: 14 }
            ThemeText { y: 200; width: 600; text: "また、会えたね"; font.family: "Noto Sans CJK JP"; font.pixelSize: 19; font.letterSpacing: 5; color: root.accent; horizontalAlignment: Text.AlignHCenter }
            Rectangle { x: 112; y: 240; width: 145; height: 1; color: "#87729a" }
            ThemeText { x: 287; y: 225; text: "✦"; font.pixelSize: 25; color: root.accent }
            Rectangle { x: 340; y: 240; width: 148; height: 1; color: "#87729a" }
            Rectangle {
                id: loginFrame; x: 100; y: 300; width: 400; height: 254; radius: 3
                color: "#b5f3f0e9"; border.width: 1; border.color: "#7d718e"
                Repeater {
                    model: 4
                    ThemeText { required property int index; x: index % 2 === 0 ? 8 : 373; y: index < 2 ? 0 : 227; text: "+"; font.pixelSize: 23; color: "#92839f" }
                }
                Rectangle { anchors.horizontalCenter: parent.horizontalCenter; y: -23; width: 112; height: 65; color: "#f2efe7"; radius: 35 }
                Image {
                    id: compass; x: 151; y: -45; width: 98; height: 98; source: "assets/compass.svg"
                    SequentialAnimation on scale { running: root.animations; loops: Animation.Infinite; NumberAnimation { to: 1.04; duration: 2400; easing.type: Easing.InOutSine } NumberAnimation { to: 1; duration: 2400; easing.type: Easing.InOutSine } }
                    RotationAnimation on rotation { running: root.busy && root.animations; from: 0; to: 360; duration: 3000; loops: Animation.Infinite }
                }
                Column {
                    x: 52; y: 67; width: 296; spacing: 15
                    enabled: !root.busy
                    TextField {
                        id: username; objectName: "username"; width: 296; height: 46
                        readOnly: true
                        text: root.session.userName; placeholderText: "Username"; leftPadding: 54; rightPadding: 12
                        font.family: "JetBrains Mono"; font.pixelSize: 15; color: root.ink; placeholderTextColor: "#9c91a5"
                        selectByMouse: true; maximumLength: 256
                        Accessible.name: "Username"; inputMethodHints: Qt.ImhNoPredictiveText | Qt.ImhNoAutoUppercase
                        background: Rectangle { color: username.activeFocus ? "#daf8f5ee" : "#55f8f5ee"; radius: 3; border.width: username.activeFocus ? 2 : 1; border.color: username.activeFocus ? root.accent : "#7f718e"; Behavior on color { ColorAnimation { duration: 150 } } }
                        Canvas { x: 17; y: 11; width: 21; height: 25; onPaint: { var c=getContext("2d"); c.fillStyle="#30344f"; c.beginPath(); c.arc(10,6,4,0,6.28); c.fill(); c.beginPath(); c.moveTo(1,23); c.lineTo(1,18); c.bezierCurveTo(1,10,19,10,19,18); c.lineTo(19,23); c.closePath(); c.fill(); } }
                        onAccepted: password.forceActiveFocus()
                        KeyNavigation.tab: password
                    }
                    TextField {
                        id: password; objectName: "password"; width: 296; height: 46
                        placeholderText: "Password"; echoMode: root.revealPassword ? TextInput.Normal : TextInput.Password; passwordCharacter: "●"; passwordMaskDelay: 0
                        leftPadding: 54; rightPadding: 46; font.family: "JetBrains Mono"; font.pixelSize: 15
                        color: root.ink; placeholderTextColor: "#9c91a5"; selectByMouse: true; maximumLength: 4096
                        Accessible.name: "Password"; inputMethodHints: Qt.ImhSensitiveData | Qt.ImhNoPredictiveText | Qt.ImhNoAutoUppercase
                        background: Rectangle { color: password.activeFocus ? "#daf8f5ee" : "#55f8f5ee"; radius: 3; border.width: password.activeFocus ? 2 : 1; border.color: password.activeFocus ? root.accent : "#7f718e"; Behavior on color { ColorAnimation { duration: 150 } } }
                        // The lock and eye use simple vector strokes so they remain crisp at every scale.
                        Canvas { x: 17; y: 12; width: 20; height: 24; onPaint: { var c=getContext('2d'); c.strokeStyle='#30344f'; c.lineWidth=2; c.beginPath(); c.arc(10,8,5,Math.PI,0); c.stroke(); c.fillStyle='#30344f'; c.fillRect(2,9,16,13); c.fillStyle='#f2efe7'; c.fillRect(9,13,2,5); } }
                        Button {
                            id: reveal; objectName: "reveal"; x: 250; y: 0; width: 44; height: 46; hoverEnabled: true
                            Accessible.name: root.revealPassword ? "Hide password" : "Show password"; checkable: true; checked: root.revealPassword
                            KeyNavigation.tab: enter
                            onClicked: root.revealPassword = !root.revealPassword
                            background: Rectangle { color: reveal.hovered || reveal.activeFocus ? "#2271639e" : "transparent"; radius: 3 }
                            contentItem: Canvas { onPaint: { var c=getContext('2d'); c.strokeStyle='#71639e'; c.lineWidth=1.7; c.beginPath(); c.moveTo(5,16); c.quadraticCurveTo(16,3,27,16); c.quadraticCurveTo(16,29,5,16); c.stroke(); c.beginPath(); c.arc(16,16,3,0,6.28); c.fillStyle='#71639e'; c.fill(); } }
                        }
                        onAccepted: root.submit()
                        Keys.onEscapePressed: { clear(); root.revealPassword = false; }
                        KeyNavigation.tab: reveal
                        KeyNavigation.backtab: username
                    }
                }
                Button {
                    id: enter; objectName: "enter"; x: 52; y: 189; width: 296; height: 42; enabled: !root.busy; hoverEnabled: true
                    Accessible.name: "Unlock session"
                    background: Rectangle { radius: 3; color: enter.down ? "#51446e" : enter.hovered || enter.activeFocus ? "#8170ae" : "#71639e"; border.color: enter.activeFocus ? "#cdbce9" : "#57496f"; border.width: enter.activeFocus ? 2 : 1; Behavior on color { ColorAnimation { duration: 160 } } }
                    contentItem: ThemeText { text: root.busy ? "UNLOCKING…" : "UNLOCK"; color: "#f7f3ed"; font.pixelSize: 14; font.letterSpacing: 2.3; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    onClicked: root.submit()
                    KeyNavigation.backtab: reveal
                }
            }
            ThemeText {
                objectName: "statusText"; y: 572; x: 40; width: 520
                text: root.telemetry.capsLock ? "Caps Lock is on" : root.message
                color: root.failed ? "#944d65" : root.accent; font.pixelSize: 13; font.letterSpacing: 0.4
                horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap
                Accessible.name: text
            }
        }
        Item {
            id: right; x: 1444; y: 126; width: 426; height: 820
            opacity: root.entrance ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: root.animations ? 1800 : 0 } }
            Panel {
                id: systemPanel; width: 426; height: 295; title: "System"; mark: "⌁"
                Rectangle { x: 18; y: 54; width: 75; height: 102; color: "#393453"; radius: 3
                    ThemeText { y: 13; width: 75; text: Qt.formatDateTime(root.clock,"dd"); color: "#f5f1ea"; font.pixelSize: 30; horizontalAlignment: Text.AlignHCenter; font.letterSpacing: 0 }
                    ThemeText { y: 52; width: 75; text: Qt.formatDateTime(root.clock,"MMM").toUpperCase(); color: "#e5dcec"; font.pixelSize: 15; horizontalAlignment: Text.AlignHCenter; font.letterSpacing: 2 }
                    ThemeText { y: 80; width: 75; text: Qt.formatDateTime(root.clock,"ddd").toUpperCase(); color: "#b7aacd"; font.pixelSize: 9; horizontalAlignment: Text.AlignHCenter; font.letterSpacing: 2 }
                }
                Repeater {
                    model: [ ["CPU", root.telemetry.cpu || "—"], ["RAM", root.telemetry.memory || "—"], ["SWAP", root.telemetry.swap || "—"] ]
                    Item {
                        required property var modelData; required property int index
                        x: 113; y: 54 + index * 34; width: 294; height: 32
                        ThemeText { text: modelData[0]; font.pixelSize: 13; font.letterSpacing: 1.4 }
                        ThemeText { width: parent.width; text: modelData[1]; horizontalAlignment: Text.AlignRight; font.pixelSize: 13; font.letterSpacing: 0.6 }
                        Rectangle { y: 26; width: parent.width; height: 1; color: "#23877a99" }
                    }
                }
                Rectangle { x: 18; y: 169; width: 390; height: 1; color: "#7c857995" }
                Item {
                    id: spectrum; x: 19; y: 180; width: 388; height: 42
                    Repeater {
                        model: 64
                        Rectangle {
                            required property int index
                            x: index * spectrum.width/64; y: spectrum.height-height
                            width: 2.6; height: Math.max(2, (root.telemetry.bars && root.telemetry.bars[index] || 0) * 40)
                            radius: 0.6; color: index % 5 === 0 ? "#595077" : "#8d7aae"
                            Behavior on height { NumberAnimation { duration: 85; easing.type: Easing.OutCubic } }
                        }
                    }
                }
                ThemeText { x: 19; y: 227; text: root.telemetry.cava === true ? "AUDIO SPECTRUM · CAVA" : "AUDIO SPECTRUM · OFFLINE"; color: "#85798e"; font.pixelSize: 9; font.letterSpacing: 1.2 }
                ThemeText { x: 19; y: 249; text: "✦  " + (root.telemetry.os || "Linux"); font.pixelSize: 12; font.letterSpacing: 0.5; width: 389; elide: Text.ElideRight }
                ThemeText { x: 19; y: 270; text: "▣  " + root.sessionName; font.pixelSize: 12; color: "#756a85"; font.letterSpacing: 0.5 }
            }
            SpotifyPanel {
                id: spotifyPanel; objectName: "spotifyPanel"; y: 337; width: 426
            }
            Column {
                y: left.y + currentSessionInfo.y - right.y
                width: 426; spacing: 12
                ThemeButton { objectName: "powerOff"; width: 426; height: 43; dark: true; text: "Power off"; glyph: "⏻"; trailing: "+"; enabled: root.session.canPowerOff; onClicked: { root.powerAction = "power off"; powerDialog.open(); } }
                ThemeButton { objectName: "restart"; width: 426; height: 43; dark: true; text: "Restart"; glyph: "⟳"; trailing: "+"; enabled: root.session.canReboot; onClicked: { root.powerAction = "restart"; powerDialog.open(); } }
                ThemeButton { objectName: "sleep"; width: 426; height: 43; dark: true; text: "Sleep"; glyph: "☾"; trailing: "+"; enabled: root.session.canSuspend; onClicked: { root.powerAction = "sleep"; powerDialog.open(); } }
            }
        }
        Rectangle {
            y: 1024; width: 1920; height: 56; color: root.ink
            ThemeText { x: 25; y: 15; text: "⚔"; color: "#d9cfea"; font.family: "DejaVu Sans"; font.pixelSize: 24 }
            ThemeText { x: 70; y: 20; text: "Starting life in another world…"; color: "#e4dced"; font.pixelSize: 14; font.letterSpacing: 1.1 }
            // The footer deliberately contains no date or time.
            ThemeText { x: 1640; y: 20; width: 88; elide: Text.ElideRight; text: "⌨  " + (root.telemetry.layout || "—").toUpperCase(); color: "#cec4de"; font.pixelSize: 13; font.letterSpacing: 0.7 }
            Rectangle { x: 1737; y: 20; width: 1; height: 18; color: "#776c88" }
            Rectangle {
                x: 1770; y: 22; width: 30; height: 15; radius: 2; color: "transparent"; border.color: "#dcd3e8"
                Rectangle { x: 3; y: 3; width: Math.max(1, 24 * (root.telemetry.battery === undefined ? 0 : root.telemetry.battery) / 100); height: 9; color: "#dcd3e8"; radius: 1 }
                Rectangle { x: 31; y: 5; width: 3; height: 6; color: "#dcd3e8" }
            }
            ThemeText { x: 1817; y: 20; text: root.telemetry.battery === undefined || root.telemetry.battery === null ? "AC" : root.telemetry.battery + "%"; color: "#e4dced"; font.pixelSize: 13 }
        }
    }
    Popup {
        id: powerDialog; objectName: "powerDialog"; anchors.centerIn: parent; width: Math.min(500, root.width - 40); height: 230
        modal: true; focus: true; padding: 28; closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        Overlay.modal: Rectangle { color: "#9930344f" }
        background: Rectangle { color: "#f2efe7"; border.color: "#71639e"; border.width: 1; radius: 4 }
        contentItem: Column {
            spacing: 22
            ThemeText { text: root.powerAction === "power off" ? "End this chapter?" : root.powerAction === "restart" ? "Begin again?" : "A moment of rest?"; font.pixelSize: 24; font.letterSpacing: 0.5 }
            ThemeText { width: parent.width; text: "This computer will " + root.powerAction + "."; wrapMode: Text.WordWrap; font.pixelSize: 13; font.letterSpacing: 0.2; color: "#786b85" }
            Row {
                spacing: 14
                ThemeButton { objectName: "cancelPower"; width: 180; text: "Cancel"; onClicked: powerDialog.close() }
                ThemeButton { objectName: "confirmPower"; width: 230; dark: true; text: "Confirm"; onClicked: {
                    powerDialog.close();
                    root.session.performPower(root.powerAction);
                } }
            }
        }
    }
}
