import QtQuick
import QtQuick.Controls
import Quickshell.Services.Mpris

Panel {
    id: panel
    property var player: {
        var players = Mpris.players.values;
        for (var i = 0; i < players.length; ++i) {
            var p = players[i];
            if (/^org\.mpris\.MediaPlayer2\.spotify(?:\.|$)/i.test(p.dbusName)
                    && p.canControl && (p.canTogglePlaying || p.canGoNext || p.canGoPrevious)) return p;
        }
        return null;
    }
    visible: player !== null
    height: 194
    title: "Spotify"
    mark: "♫"

    Image {
        id: art; x: 18; y: 54; width: 68; height: 68
        source: panel.player ? panel.player.trackArtUrl : ""
        fillMode: Image.PreserveAspectCrop; asynchronous: true
    }
    Rectangle {
        x: 18; y: 54; width: 68; height: 68; color: "#e4deec"
        visible: art.status !== Image.Ready
        ThemeText { anchors.centerIn: parent; text: "♫"; font.pixelSize: 30; color: "#71639e" }
    }
    ThemeText {
        x: 101; y: 58; width: 307; elide: Text.ElideRight
        text: panel.player ? panel.player.trackTitle || "Spotify" : ""
        font.pixelSize: 14; font.letterSpacing: 0.2
    }
    ThemeText {
        x: 101; y: 84; width: 307; elide: Text.ElideRight
        text: panel.player ? panel.player.trackArtist || panel.player.trackAlbum : ""
        font.pixelSize: 11; font.letterSpacing: 0.2; color: "#756a85"
    }
    Rectangle { x: 18; y: 138; width: 390; height: 1; color: "#56857995" }
    Row {
        x: 220; y: 146; spacing: 8
        Repeater {
            model: ["previous", "toggle", "next"]
            Button {
                id: control
                required property string modelData
                objectName: "spotify-" + modelData
                width: 56; height: 36; hoverEnabled: true; activeFocusOnTab: true
                enabled: panel.player !== null && (modelData === "previous" ? panel.player.canGoPrevious : modelData === "next" ? panel.player.canGoNext : panel.player.canTogglePlaying)
                opacity: enabled ? 1 : 0.35
                Accessible.name: modelData === "toggle" ? (panel.player && panel.player.isPlaying ? "Pause Spotify" : "Play Spotify") : (modelData === "next" ? "Next Spotify track" : "Previous Spotify track")
                ToolTip.visible: hovered; ToolTip.text: Accessible.name
                background: Rectangle { color: control.hovered || control.activeFocus ? "#2871639e" : "transparent"; radius: 3; border.width: control.activeFocus ? 1 : 0; border.color: "#71639e" }
                contentItem: ThemeText {
                    text: control.modelData === "previous" ? "|◀" : control.modelData === "next" ? "▶|" : panel.player && panel.player.isPlaying ? "Ⅱ" : "▶"
                    font.family: "DejaVu Sans"; font.pixelSize: 19; font.letterSpacing: 0
                    horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                }
                onClicked: {
                    if (!enabled || !panel.player) return;
                    if (modelData === "previous") panel.player.previous();
                    else if (modelData === "next") panel.player.next();
                    else panel.player.togglePlaying();
                }
            }
        }
    }
    ThemeText { x: 18; y: 159; text: panel.player && panel.player.isPlaying ? "NOW PLAYING" : "PAUSED"; font.pixelSize: 9; color: "#756a85"; font.letterSpacing: 1.1 }
}
