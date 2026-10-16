import QtQuick
Rectangle {
    id: panel
    property string title: ""
    property string mark: "✦"
    color: "#b8f4f1e9"
    border.width: 1
    border.color: "#68617d"
    radius: 3
    Rectangle { width: parent.width; height: 38; color: "#30344f"; radius: 3 }
    Rectangle { y: 34; width: parent.width; height: 4; color: "#30344f" }
    ThemeText { x: 20; y: 9; text: panel.title; color: "#f4f0e8"; font.pixelSize: 17; font.letterSpacing: 1.5 }
    ThemeText { anchors.right: parent.right; anchors.rightMargin: 18; y: 6; text: panel.mark; color: "#d6cdeb"; font.pixelSize: 22 }
}
