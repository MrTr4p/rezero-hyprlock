import QtQuick

Item {
    property string sessionName: "Hyprland"
    property string displayName: ""
    // Match the reference: text on the artwork, no card or session pill.
    ThemeText {
        width: parent.width; elide: Text.ElideRight
        text: "CURRENT SESSION: " + sessionName.toUpperCase()
        font.pixelSize: 13; font.weight: Font.DemiBold; font.letterSpacing: 1
    }
    Rectangle { y: 26; width: parent.width; height: 1; color: "#267c728e" }
    ThemeText { y: 40; text: "Welcome back, " + displayName + "."; width: parent.width; elide: Text.ElideRight; font.pixelSize: 13; font.weight: Font.DemiBold; font.letterSpacing: 0.2 }
    ThemeText { y: 68; text: "A new day, a new chance to change your fate."; font.pixelSize: 11; font.letterSpacing: 0.1 }
    Rectangle { y: 109; width: 70; height: 1; color: "#857596" }
    ThemeText { x: 81; y: 95; text: "✦"; color: "#71639e"; font.pixelSize: 23 }
    Rectangle { x: 113; y: 109; width: parent.width - x; height: 1; color: "#857596" }
    ThemeText { y: 132; text: "FATE IS NOT WRITTEN."; font.pixelSize: 16; font.letterSpacing: 1.8 }
    ThemeText { y: 162; text: "それでも、僕は、君を選ぶ。"; font.family: "Noto Sans CJK JP"; font.pixelSize: 16; color: "#71639e"; font.letterSpacing: 2 }
}
