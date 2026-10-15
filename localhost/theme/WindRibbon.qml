import QtQuick

Item {
    id: ribbon
    property bool motionEnabled: true
    property real elapsedMs: 0
    clip: true

    Timer {
        interval: 33; repeat: true
        running: ribbon.motionEnabled && ribbon.visible
        onTriggered: { ribbon.elapsedMs += interval; currents.requestPaint(); }
    }
    Canvas {
        id: currents
        anchors.fill: parent
        onPaint: {
            var c = getContext("2d");
            c.reset();
            var t = ribbon.elapsedMs / 1800;
            for (var i = 0; i < 3; ++i) {
                var y = height / 2 + (i - 1) * 8;
                var wave = Math.sin(t + i * 1.5) * 9;
                c.strokeStyle = i === 1 ? "rgba(173,150,200,0.32)" : "rgba(173,150,200,0.16)";
                c.lineWidth = 1;
                c.beginPath(); c.moveTo(10, y);
                c.bezierCurveTo(width * 0.3, y + wave, width * 0.7, y - wave, width - 10, y);
                c.stroke();
            }
        }
    }
    Repeater {
        model: 5
        Image {
            required property int index
            readonly property real journey: (ribbon.elapsedMs / (9500 + index * 900) + index / 5) % 1
            x: ribbon.width + 45 - journey * (ribbon.width + 90)
            y: ribbon.height / 2 - height / 2 + Math.sin(journey * 8 + index) * 11
            width: 29 + (index % 3) * 10; height: width * 0.4
            rotation: -25 + Math.sin(journey * 9 + index) * 24
            opacity: Math.min(1, Math.sin(journey * Math.PI) * 2) * 0.9
            source: "assets/feather.svg"
        }
    }
}
