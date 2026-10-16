import QtQuick
import QtQuick.Controls
Button {
    id: control
    property string glyph: ""
    property bool selected: false
    property bool dark: false
    property color accent: "#71639e"
    property string trailing: ""
    hoverEnabled: true
    height: 48
    activeFocusOnTab: true
    opacity: enabled ? 1 : 0.38
    Accessible.name: text
    contentItem: Item {
        ThemeText { x: 17; anchors.verticalCenter: parent.verticalCenter; text: control.glyph; font.family: "DejaVu Sans"; font.pixelSize: 23; color: control.dark || control.selected ? "#f5f1ea" : "#51476e" }
        ThemeText { x: control.glyph ? 58 : 20; anchors.verticalCenter: parent.verticalCenter; text: control.text; font.pixelSize: 16; color: control.dark || control.selected ? "#f5f1ea" : "#30344f"; width: parent.width-x-42; elide: Text.ElideRight }
        ThemeText { anchors.right: parent.right; anchors.rightMargin: 16; anchors.verticalCenter: parent.verticalCenter; text: control.trailing; color: control.dark || control.selected ? "#e6dff4" : control.accent; font.pixelSize: 22 }
    }
    background: Rectangle {
        radius: 3
        color: control.down ? "#52466f" : control.selected ? control.accent : control.dark ? (control.hovered ? "#454461" : "#30344f") : (control.hovered ? "#2271639e" : "transparent")
        border.width: control.activeFocus ? 2 : 0
        border.color: "#a79ac6"
        Behavior on color { ColorAnimation { duration: 150 } }
        Rectangle { visible: !control.dark && !control.selected; anchors.bottom: parent.bottom; width: parent.width; height: 1; color: "#263d3659" }
    }
}
