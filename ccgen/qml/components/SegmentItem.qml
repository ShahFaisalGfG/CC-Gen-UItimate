import QtQuick
import QtQuick.Layouts

// One transcript cue: time range, the spoken text, and its translation / transliteration
// underneath once those stages reach it.
Item {
    id: segItem

    required property int index
    required property real segStart
    required property real segEnd
    required property string segText
    required property string segTranslation
    required property string segTransliteration

    implicitHeight: content.implicitHeight + 2 * Theme.spaceSm

    Accessible.role: Accessible.ListItem
    Accessible.name: segItem._time(segItem.segStart) + ". " + segItem.segText
        + (segItem.segTranslation ? ". Translation: " + segItem.segTranslation : "")
        + (segItem.segTransliteration ? ". Transliteration: " + segItem.segTransliteration : "")

    function _time(secs) {
        var t = Math.floor(secs)
        var h = Math.floor(t / 3600)
        var m = Math.floor((t % 3600) / 60)
        var s = t % 60
        return (h > 0 ? h + ":" : "") + String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0")
    }

    Rectangle {
        anchors.fill: parent
        color: segItem.index % 2 === 0 ? Theme.surfaceAlt : "transparent"
        radius: Theme.radius
    }

    RowLayout {
        id: content
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: Theme.spaceMd
        anchors.rightMargin: Theme.spaceMd
        spacing: Theme.spaceMd

        Text {
            Layout.alignment: Qt.AlignTop
            Layout.preferredWidth: 92
            text: segItem._time(segItem.segStart) + " - " + segItem._time(segItem.segEnd)
            font.family: "Cascadia Mono, Consolas"
            font.pixelSize: Theme.fontCaption
            color: Theme.accent
            Accessible.ignored: true
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 3

            Text {
                Layout.fillWidth: true
                text: segItem.segText
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBody
                color: Theme.text
                wrapMode: Text.Wrap
                Accessible.ignored: true
            }
            Text {
                Layout.fillWidth: true
                visible: segItem.segTranslation.length > 0
                text: segItem.segTranslation
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBody
                color: Theme.accent
                wrapMode: Text.Wrap
                Accessible.ignored: true
            }
            Text {
                Layout.fillWidth: true
                visible: segItem.segTransliteration.length > 0
                text: segItem.segTransliteration
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBody
                font.italic: true
                color: Theme.textMuted
                wrapMode: Text.Wrap
                Accessible.ignored: true
            }
        }
    }
}
