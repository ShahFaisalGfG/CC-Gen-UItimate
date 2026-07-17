// qmllint disable unqualified import
import QtQuick
import QtQuick.Controls.Material

Rectangle {
    id: root

    signal clicked()

    property string label: ""
    property color activeColor: Material.foreground
    property color hoverTint: Qt.rgba(0.5, 0.5, 0.5, 0.12)

    height: 24
    implicitWidth: labelText.implicitWidth + 16
    radius: height / 2
    color: mouseArea.containsMouse && root.enabled ? root.hoverTint : "transparent"

    Behavior on color { ColorAnimation { duration: 80 } }

    Text {
        id: labelText
        anchors.centerIn: parent
        text: root.label
        font.pixelSize: 10
        color: root.enabled
            ? root.activeColor
            : (Material.theme === Material.Dark ? "#555555" : "#bbbbbb")
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: if (root.enabled) root.clicked()
    }
}
