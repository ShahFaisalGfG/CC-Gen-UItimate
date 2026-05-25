// qmllint disable unqualified import
import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

Rectangle {
    id: fileItem

    signal itemClicked(int idx, int modifiers)

    required property int    index
    required property string name
    required property string path
    required property string size
    required property string ext
    required property bool   selected
    required property string status

    property string fileName:   name
    property string filePath:   path
    property string fileSize:   size
    property string fileExt:    ext.length > 0 ? ext : "FILE"
    property bool   isSelected: selected
    property string fileStatus: status

    readonly property bool _isVideo: {
        var v = ["MP4","MKV","AVI","MOV","WEBM","FLV","WMV","TS","M2TS"]
        return v.indexOf(fileItem.fileExt) >= 0
    }
    readonly property bool _isSubtitle: {
        var s = ["SRT","VTT","ASS","SSA"]
        return s.indexOf(fileItem.fileExt) >= 0
    }

    height: 68
    radius: 6
    color: isSelected
        ? (Material.theme === Material.Dark ? "#1a3a5c" : "#cce4f7")
        : (Material.theme === Material.Dark ? "#2a2a2a" : "#ffffff")

    border.color: isSelected ? "#0078d4"
        : (Material.theme === Material.Dark ? "#3a3a3a" : "#e0e0e0")
    border.width: isSelected ? 2 : 1

    Behavior on color { ColorAnimation { duration: 80 } }

    ToolTip.text: fileItem.filePath
    ToolTip.visible: itemHover.hovered
    ToolTip.delay: 800

    // Non-consuming hover tracker — HoverHandler does not steal events from child MouseAreas
    HoverHandler { id: itemHover }

    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        color: itemHover.hovered && !fileItem.isSelected
            ? (Material.theme === Material.Dark ? Qt.rgba(1, 1, 1, 0.04) : Qt.rgba(0, 0, 0, 0.03))
            : "transparent"
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin:  10
        anchors.rightMargin: 10
        anchors.topMargin:   8
        anchors.bottomMargin: 8
        spacing: 12

        // Extension badge
        Rectangle {
            Layout.preferredWidth:  46
            Layout.preferredHeight: 46
            radius: 7
            color: fileItem._isSubtitle
                ? (Material.theme === Material.Dark ? Qt.rgba(0.42, 0.18, 0.62, 0.18) : Qt.rgba(0.42, 0.18, 0.62, 0.10))
                : fileItem._isVideo
                    ? (Material.theme === Material.Dark ? Qt.rgba(0.082, 0.396, 0.753, 0.18) : Qt.rgba(0.082, 0.396, 0.753, 0.10))
                    : (Material.theme === Material.Dark ? Qt.rgba(0.18, 0.49, 0.2, 0.2) : Qt.rgba(0.18, 0.49, 0.2, 0.1))
            border.color: fileItem._isSubtitle ? "#7b1fa2" : fileItem._isVideo ? "#1565c0" : "#2e7d32"
            border.width: 1

            Text {
                anchors.centerIn: parent
                text: fileItem.fileExt.length > 5 ? fileItem.fileExt.substring(0, 4) + "…" : fileItem.fileExt
                color: fileItem._isSubtitle ? "#7b1fa2" : fileItem._isVideo ? "#1565c0" : "#2e7d32"
                font.pixelSize: fileItem.fileExt.length > 4 ? 9 : 11
                font.weight: Font.Bold
            }
        }

        // Name + size column
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 3

            Text {
                Layout.fillWidth: true
                text: fileItem.fileName
                color: Material.foreground
                font.pixelSize: 13
                font.weight: Font.Medium
                elide: Text.ElideMiddle
            }

            Text {
                Layout.fillWidth: true
                text: fileItem.fileSize
                color: Material.theme === Material.Dark ? "#888888" : "#767676"
                font.pixelSize: 11
            }
        }

        // Status indicator
        Row {
            spacing: 5
            visible: !itemHover.hovered

            Rectangle {
                width: 8; height: 8
                radius: 4
                anchors.verticalCenter: parent.verticalCenter
                color: {
                    switch (fileItem.fileStatus) {
                        case "processing": return "#0078d4"
                        case "done":       return "#2e7d32"
                        case "error":      return "#e81123"
                        default:           return "#888888"
                    }
                }

                SequentialAnimation on opacity {
                    running: fileItem.fileStatus === "processing"
                    loops: Animation.Infinite
                    NumberAnimation { to: 0.3; duration: 600 }
                    NumberAnimation { to: 1.0; duration: 600 }
                }
            }

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: {
                    switch (fileItem.fileStatus) {
                        case "done":       return "✓ Done"
                        case "error":      return "✗ Error"
                        case "processing": return ""
                        default:           return ""
                    }
                }
                font.pixelSize: 10
                color: {
                    switch (fileItem.fileStatus) {
                        case "done":  return "#2e7d32"
                        case "error": return "#e81123"
                        default:      return "#888888"
                    }
                }
            }
        }
    }

    MouseArea {
        id: itemMouse
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: function(mouse) {
            if (mouse.button === Qt.RightButton) {
                if (!fileItem.isSelected)
                    fileItem.itemClicked(fileItem.index, Qt.NoModifier)
                contextMenu.popup()
            } else {
                fileItem.itemClicked(fileItem.index, mouse.modifiers)
            }
        }
    }

    Menu {
        id: contextMenu
        MenuItem {
            text:           "Remove"
            height:         32
            font.pixelSize: 12
            onTriggered: transcriptionController.fileModel.removeAt(fileItem.index)
        }
        MenuItem {
            text:           "Remove selected"
            height:         32
            font.pixelSize: 12
            onTriggered: transcriptionController.fileModel.removeSelected()
        }
        MenuItem {
            text:           "Remove all"
            height:         32
            font.pixelSize: 12
            onTriggered: transcriptionController.fileModel.clearAll()
        }
    }

    Rectangle {
        id: removeBtn
        width: 26; height: 26
        radius: 4
        anchors.right:          parent.right
        anchors.rightMargin:    10
        anchors.verticalCenter: parent.verticalCenter
        visible: itemHover.hovered
        color: removeMouse.containsMouse ? "#e81123" : "transparent"
        Behavior on color { ColorAnimation { duration: 80 } }

        Text {
            anchors.centerIn: parent
            text:  "✕"
            font.pixelSize: 10
            color: removeMouse.containsMouse ? "#ffffff"
                : (Material.theme === Material.Dark ? "#888888" : "#777777")
            Behavior on color { ColorAnimation { duration: 80 } }
        }

        MouseArea {
            id: removeMouse
            anchors.fill: parent
            hoverEnabled: true
            onClicked: transcriptionController.fileModel.removeAt(fileItem.index)
        }
    }

    Accessible.name:      "File: " + fileName + ", " + fileSize
    Accessible.role:      Accessible.ListItem
    Accessible.checkable: true
    Accessible.checked:   isSelected
    Accessible.onPressAction: transcriptionController.fileModel.toggleSelection(fileItem.index)
}
