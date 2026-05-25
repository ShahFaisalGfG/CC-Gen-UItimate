pragma ComponentBehavior: Bound
// qmllint disable unqualified import
import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

Item {
    id: fileListRoot

    property int _anchor: -1
    property int _cursor: -1

    signal emptyPanelClicked()

    function handleClick(idx, mods) {
        try {
            if (mods & Qt.ShiftModifier) {
                if (_anchor < 0) _anchor = idx
                transcriptionController.fileModel.selectRange(_anchor, idx)
                _cursor = idx
            } else if (mods & Qt.ControlModifier) {
                transcriptionController.fileModel.toggleSelection(idx)
                _anchor = idx
                _cursor = idx
            } else {
                transcriptionController.fileModel.setSingle(idx)
                _anchor = idx
                _cursor = idx
            }
            listView.forceActiveFocus()
        } catch(e) {}
    }

    // Empty-state placeholder
    Rectangle {
        anchors.centerIn: parent
        width:  Math.min(parent.width * 0.82, 320)
        height: 130
        radius: 12
        visible: transcriptionController.fileModel.count === 0
        color:        Material.theme === Material.Dark ? "#1c1c1c" : "#f8f8f8"
        border.color: Material.theme === Material.Dark ? "#3a3a3a" : "#cccccc"
        border.width: 1

        ColumnLayout {
            anchors.centerIn: parent
            spacing: 6

            Text {
                Layout.alignment: Qt.AlignHCenter
                text: "🎬"
                font.pixelSize: 32
            }
            Text {
                Layout.alignment: Qt.AlignHCenter
                text: "Drop video, audio, or subtitle files"
                color: Material.theme === Material.Dark ? "#777777" : "#888888"
                font.pixelSize: 12
            }
            Text {
                Layout.alignment: Qt.AlignHCenter
                text: "or click  + Files  /  + Folder"
                color: Material.theme === Material.Dark ? "#444444" : "#aaaaaa"
                font.pixelSize: 11
            }
        }

        MouseArea {
            anchors.fill: parent
            onClicked: fileListRoot.emptyPanelClicked()
        }
    }

    // Scrollable file list
    ScrollView {
        anchors.fill: parent
        clip: true
        visible: transcriptionController.fileModel.count > 0
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
        ScrollBar.vertical.policy:   ScrollBar.AsNeeded

        ListView {
            id: listView
            model: transcriptionController.fileModel
            spacing: 4
            topMargin: 4
            bottomMargin: 4
            leftMargin: 4
            rightMargin: 4
            clip: true
            focus: true

            delegate: FileItem {
                width: ListView.view.width - 8
                onItemClicked: function(idx, mods) { fileListRoot.handleClick(idx, mods) }
            }

            displaced: Transition {
                NumberAnimation { properties: "x,y"; easing.type: Easing.OutQuad; duration: 120 }
            }

            Keys.onPressed: function(event) {
                var count = transcriptionController.fileModel.count
                if (count === 0) { event.accepted = false; return }

                if (event.key === Qt.Key_A && (event.modifiers & Qt.ControlModifier)) {
                    transcriptionController.fileModel.selectAll()
                    fileListRoot._anchor = 0
                    fileListRoot._cursor = count - 1
                    event.accepted = true
                } else if (event.key === Qt.Key_Delete) {
                    transcriptionController.fileModel.removeSelected()
                    fileListRoot._anchor = -1
                    fileListRoot._cursor = -1
                    event.accepted = true
                } else if (event.key === Qt.Key_Up || event.key === Qt.Key_Down) {
                    var isDown  = event.key === Qt.Key_Down
                    var isShift = !!(event.modifiers & Qt.ShiftModifier)
                    var cur     = fileListRoot._cursor

                    if (cur < 0) {
                        cur = isDown ? 0 : count - 1
                    } else {
                        cur = isDown ? Math.min(count - 1, cur + 1) : Math.max(0, cur - 1)
                    }

                    if (isShift) {
                        if (fileListRoot._anchor < 0)
                            fileListRoot._anchor = fileListRoot._cursor < 0 ? cur : fileListRoot._cursor
                        fileListRoot._cursor = cur
                        transcriptionController.fileModel.selectRange(fileListRoot._anchor, cur)
                    } else {
                        fileListRoot._anchor = cur
                        fileListRoot._cursor = cur
                        transcriptionController.fileModel.setSingle(cur)
                    }
                    listView.positionViewAtIndex(cur, ListView.Contain)
                    event.accepted = true
                }
            }
        }
    }

    // Drag-and-drop overlay
    DropArea {
        anchors.fill: parent
        onDropped: function(drop) {
            if (drop.hasUrls) {
                var urls = []
                for (var i = 0; i < drop.urls.length; i++)
                    urls.push(drop.urls[i])
                transcriptionController.addFiles(urls)
            }
        }

        Rectangle {
            anchors.fill: parent
            radius: 8
            color: Qt.rgba(0, 0.47, 0.83, 0.08)
            border.color: "#0078d4"
            border.width: 2
            visible: parent.containsDrag
        }
    }
}
