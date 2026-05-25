// qmllint disable unqualified import
import QtQuick
import QtQuick.Controls.Material

Rectangle {
    id: segItem

    required property int    segId
    required property real   segStart
    required property string segText

    height: contentRow.implicitHeight + 12
    radius: 4
    color: (segId % 2 === 0)
        ? (Material.theme === Material.Dark ? "#1a1a1a" : "#f5f5f5")
        : "transparent"

    Row {
        id: contentRow
        anchors.left:    parent.left
        anchors.right:   parent.right
        anchors.top:     parent.top
        anchors.margins: 8
        spacing: 10

        Text {
            id: tsLabel
            text: _formatTime(segItem.segStart)
            color: "#0078d4"
            font.family: "Consolas"
            font.pixelSize: 11
            width: 64
            topPadding: 1
        }

        Text {
            text: segItem.segText.trim()
            wrapMode: Text.WordWrap
            font.pixelSize: 12
            color: Material.foreground
            width: segItem.width - tsLabel.width - contentRow.spacing - 16
        }
    }

    function _formatTime(secs) {
        var t = Math.floor(secs)
        var h = Math.floor(t / 3600)
        var m = Math.floor((t % 3600) / 60)
        var s = t % 60
        return (h > 0 ? String(h).padStart(2, "0") + ":" : "")
            + String(m).padStart(2, "0") + ":"
            + String(s).padStart(2, "0")
    }
}
