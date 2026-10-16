import QtQuick

Item {
    id: background
    property url source
    property bool motionEnabled: true
    property real elapsedMs: 0
    clip: true

    // One 30 fps clock drives every feather.
    Timer {
        property real startedAt: Date.now()
        interval: 33; repeat: true
        running: background.motionEnabled && background.visible
        onRunningChanged: if (running) startedAt = Date.now() - background.elapsedMs
        onTriggered: background.elapsedMs = Date.now() - startedAt
    }

    // Keep the character artwork still; only the separate feathers move.
    Image {
        anchors.fill: parent
        source: background.source
        fillMode: Image.PreserveAspectCrop
        opacity: 0.86
    }
    Rectangle { anchors.fill: parent; color: "#15f6f3eb" }

    // Each feather starts at a different point, so the scene is alive immediately.
    Repeater {
        model: background.motionEnabled ? 22 : 0
        Image {
            id: feather
            required property int index
            readonly property real travel: background.elapsedMs / (11000 + (index % 6) * 1250)
            readonly property real journey: (travel + index / 22) % 1
            readonly property real depth: 0.8 + (index % 3) * 0.2
            x: 45 + index * (background.width - 90) / 22 + Math.sin(journey * 6.28 + index) * 110
            y: background.height + 35 - journey * (background.height + 100)
            width: (48 + (index % 4) * 14) * depth
            height: width * 0.4
            rotation: -30 + Math.sin(journey * 9 + index) * 48
            opacity: Math.sin(journey * Math.PI) * (0.42 + depth * 0.28)
            source: "assets/feather.svg"
        }
    }

}
