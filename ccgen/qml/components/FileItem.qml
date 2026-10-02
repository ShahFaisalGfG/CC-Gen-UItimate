import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// One row of the file queue: type badge, name, size or status message, and a status badge.
// Status is always spelled out in text and with an icon, never by color alone.
Rectangle {
    id: fileItem

    signal clicked(int index, int modifiers)
    signal contextMenuRequested(int index)
    signal removeRequested(int index)

    required property int index
    required property string name
    required property string path
    required property string folder
    required property string size
    required property string ext
    required property string kind
    required property bool selected
    required property string status
    required property real progress
    required property string message
    property bool current: false
    property bool listHasFocus: false

    readonly property bool _busy: fileItem.status === "processing"
    readonly property string _statusText: {
        switch (fileItem.status) {
        case "processing": return fileItem.progress > 0 ? Math.round(fileItem.progress * 100) + "%" : "Working"
        case "done":       return "Done"
        case "error":      return "Failed"
        case "cancelled":  return "Cancelled"
        default:           return "Waiting"
        }
    }
    readonly property color _statusColor: {
        switch (fileItem.status) {
        case "processing": return Theme.accent
        case "done":       return Theme.success
        case "error":      return Theme.danger
        default:           return Theme.textMuted
        }
    }

    implicitHeight: 60
    radius: Theme.radius
    color: fileItem.selected ? Theme.accentSoft : (hover.hovered ? Theme.surfaceHover : "transparent")
    border.width: fileItem.current && fileItem.listHasFocus ? 2 : 0
    border.color: Theme.focusRing

    Accessible.role: Accessible.ListItem
    Accessible.name: fileItem.name + ", " + fileItem._statusText
        + (fileItem.message ? ", " + fileItem.message : "")
    Accessible.description: fileItem.size + ", " + fileItem.folder
    Accessible.selectable: true
    Accessible.selected: fileItem.selected

    HoverHandler { id: hover }

    ToolTip.visible: hover.hovered && !removeButton.hovered
    ToolTip.text: fileItem.message ? fileItem.path + "\n" + fileItem.message : fileItem.path
    ToolTip.delay: 900

    Rectangle {
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        width: 3
        height: parent.height - 16
        radius: 2
        color: Theme.accent
        visible: fileItem.selected
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.spaceMd
        anchors.rightMargin: Theme.spaceSm
        spacing: Theme.spaceMd

        Rectangle {
            Layout.preferredWidth: 36
            Layout.preferredHeight: 36
            radius: Theme.radius
            color: Theme.surfaceAlt
            border.width: 1
            border.color: Theme.border

            Icon {
                anchors.centerIn: parent
                anchors.verticalCenterOffset: -4
                name: fileItem.kind === "video" ? "video" : fileItem.kind === "subtitle" ? "captions" : "audio"
                size: 14
                color: Theme.accent
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 2
                text: fileItem.ext.length > 4 ? fileItem.ext.substring(0, 4) : fileItem.ext
                font.family: Theme.fontFamily
                font.pixelSize: 9
                font.weight: Font.DemiBold
                color: Theme.textMuted
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2

            Text {
                Layout.fillWidth: true
                text: fileItem.name
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBody
                font.weight: Font.DemiBold
                color: Theme.text
                elide: Text.ElideMiddle
            }
            Text {
                Layout.fillWidth: true
                text: fileItem.status === "error" && fileItem.message ? fileItem.message
                    : fileItem.status === "done" && fileItem.message ? fileItem.size + "  ·  " + fileItem.message
                    : fileItem.size + "  ·  " + fileItem.folder
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontCaption
                color: fileItem.status === "error" ? Theme.danger : Theme.textMuted
                elide: Text.ElideMiddle
            }
        }

        RowLayout {
            spacing: 4
            visible: !removeButton.visible

            Icon {
                name: fileItem.status === "done" ? "completed"
                    : fileItem.status === "error" ? "error"
                    : fileItem.status === "cancelled" ? "cancel"
                    : fileItem._busy ? "sync" : ""
                visible: name.length > 0
                size: 13
                color: fileItem._statusColor
            }
            Text {
                text: fileItem._statusText
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontCaption
                font.weight: fileItem._busy ? Font.DemiBold : Font.Normal
                color: fileItem._statusColor
            }
        }

        AppButton {
            id: removeButton
            kind: "ghost"
            compact: true
            iconName: "cancel"
            toolTipText: "Remove " + fileItem.name + " from the queue"
            visible: hover.hovered && !fileItem._busy
            focusPolicy: Qt.NoFocus
            onClicked: fileItem.removeRequested(fileItem.index)
        }
    }

    ProgressBar {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.leftMargin: Theme.spaceMd
        anchors.rightMargin: Theme.spaceMd
        height: 3
        visible: fileItem._busy
        from: 0
        to: 1
        value: Math.max(0, fileItem.progress)
        indeterminate: fileItem.progress <= 0
        Accessible.ignored: true
    }

    MouseArea {
        anchors.fill: parent
        z: -1
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: function(mouse) {
            if (mouse.button === Qt.RightButton) {
                fileItem.contextMenuRequested(fileItem.index)
            } else {
                fileItem.clicked(fileItem.index, mouse.modifiers)
            }
        }
    }
}
