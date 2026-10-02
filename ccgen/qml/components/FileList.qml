// qmllint disable unqualified
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// The file queue: a virtualized list (fast with thousands of rows), full keyboard support,
// one shared context menu, drag-and-drop of files and folders, and an empty-state prompt.
//
// Keys: Up/Down move, Shift+Up/Down extend, Space toggles, Ctrl+A selects all, Delete removes,
// Menu or Shift+F10 opens the context menu for the current row.
FocusScope {
    id: root

    required property var fileModel
    property bool busy: false
    property bool scanning: false
    property int scanFound: 0

    signal addFilesRequested()
    signal addFolderRequested()
    signal filesDropped(var urls)
    signal revealRequested(string path)

    property int _anchor: -1

    function _click(index, modifiers) {
        if (modifiers & Qt.ShiftModifier) {
            if (root._anchor < 0) root._anchor = index
            root.fileModel.selectRange(root._anchor, index)
        } else if (modifiers & Qt.ControlModifier) {
            root.fileModel.toggleSelection(index)
            root._anchor = index
        } else {
            root.fileModel.setSingle(index)
            root._anchor = index
        }
        listView.currentIndex = index
        listView.forceActiveFocus()
    }

    function _openMenu(index) {
        if (index < 0) return
        var item = listView.itemAtIndex(index) as FileItem
        if (!item || !item.selected)
            root._click(index, Qt.NoModifier)
        contextMenu.row = index
        contextMenu.path = root.fileModel.getPaths()[index] || ""
        contextMenu.popup()
    }

    // Empty state
    ColumnLayout {
        anchors.centerIn: parent
        width: Math.min(parent.width - 2 * Theme.spaceXl, 320)
        spacing: Theme.spaceMd
        visible: root.fileModel.count === 0 && !root.scanning

        Rectangle {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: 64
            Layout.preferredHeight: 64
            radius: 32
            color: Theme.accentSoft
            Icon { anchors.centerIn: parent; name: "captions"; size: 28; color: Theme.accent }
        }
        Text {
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            text: "Add files to get started"
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSubtitle
            font.weight: Font.DemiBold
            color: Theme.text
            Accessible.role: Accessible.Heading
        }
        Text {
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            text: "Drop videos, audio, subtitle files, or whole folders here."
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontBody
            color: Theme.textMuted
            wrapMode: Text.WordWrap
        }
        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: Theme.spaceSm
            AppButton {
                kind: "primary"
                text: "Add files"
                iconName: "add"
                toolTipText: "Ctrl+O"
                onClicked: root.addFilesRequested()
            }
            AppButton {
                text: "Add folder"
                iconName: "folder"
                toolTipText: "Ctrl+Shift+O"
                onClicked: root.addFolderRequested()
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Scan progress for large folders
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 40
            visible: root.scanning
            color: Theme.accentSoft

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.spaceMd
                anchors.rightMargin: Theme.spaceSm
                spacing: Theme.spaceSm

                BusyIndicator {
                    Layout.alignment: Qt.AlignVCenter
                    Layout.preferredWidth: 18
                    Layout.preferredHeight: 18
                    padding: 0  // the style's default padding shrinks the spinner to a sliver at this size
                    running: root.scanning
                    Accessible.ignored: true
                }
                Text {
                    Layout.fillWidth: true
                    text: "Scanning folder... " + root.scanFound.toLocaleString(Qt.locale(), "f", 0) + " files found"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontCaption
                    color: Theme.text
                    elide: Text.ElideRight
                    Accessible.role: Accessible.StaticText
                    Accessible.name: text
                }
                AppButton {
                    kind: "ghost"
                    compact: true
                    text: "Stop"
                    toolTipText: "Stop scanning; files found so far stay in the queue"
                    onClicked: transcriptionController.cancelScan()
                }
            }
        }

        ListView {
            id: listView
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.fileModel.count > 0
            model: root.fileModel
            clip: true
            focus: true
            spacing: 2
            topMargin: Theme.spaceXs
            bottomMargin: Theme.spaceXs
            leftMargin: Theme.spaceXs
            rightMargin: Theme.spaceXs
            reuseItems: true
            cacheBuffer: 600
            keyNavigationEnabled: false
            activeFocusOnTab: true
            highlightFollowsCurrentItem: false
            boundsBehavior: Flickable.StopAtBounds

            Accessible.role: Accessible.List
            Accessible.name: "File queue, " + root.fileModel.count + " files"

            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

            delegate: FileItem {
                width: ListView.view.width - listView.leftMargin - listView.rightMargin
                current: ListView.isCurrentItem
                listHasFocus: listView.activeFocus
                onClicked: (index, modifiers) => root._click(index, modifiers)
                onContextMenuRequested: index => root._openMenu(index)
                onRemoveRequested: index => root.fileModel.removeAt(index)
            }

            Keys.onPressed: function(event) {
                var count = root.fileModel.count
                if (count === 0) return
                var ctrl = event.modifiers & Qt.ControlModifier
                var shift = event.modifiers & Qt.ShiftModifier
                if (event.key === Qt.Key_A && ctrl) {
                    root.fileModel.selectAll()
                } else if (event.key === Qt.Key_Delete) {
                    root.fileModel.removeSelected()
                    listView.currentIndex = Math.min(listView.currentIndex, root.fileModel.count - 1)
                } else if (event.key === Qt.Key_Space && listView.currentIndex >= 0) {
                    root.fileModel.toggleSelection(listView.currentIndex)
                } else if (event.key === Qt.Key_Menu || (event.key === Qt.Key_F10 && shift)) {
                    root._openMenu(Math.max(0, listView.currentIndex))
                } else if (event.key === Qt.Key_Up || event.key === Qt.Key_Down
                           || event.key === Qt.Key_Home || event.key === Qt.Key_End) {
                    var cur = listView.currentIndex
                    if (event.key === Qt.Key_Home) cur = 0
                    else if (event.key === Qt.Key_End) cur = count - 1
                    else if (cur < 0) cur = 0
                    else cur = event.key === Qt.Key_Down ? Math.min(count - 1, cur + 1) : Math.max(0, cur - 1)
                    if (shift) {
                        if (root._anchor < 0) root._anchor = Math.max(0, listView.currentIndex)
                        root.fileModel.selectRange(root._anchor, cur)
                    } else if (!ctrl) {
                        root.fileModel.setSingle(cur)
                        root._anchor = cur
                    }
                    listView.currentIndex = cur
                    listView.positionViewAtIndex(cur, ListView.Contain)
                } else {
                    return
                }
                event.accepted = true
            }
        }
    }

    Menu {
        id: contextMenu
        property int row: -1
        property string path: ""

        MenuItem {
            text: "Show in folder"
            enabled: contextMenu.path.length > 0
            onTriggered: root.revealRequested(contextMenu.path)
        }
        MenuSeparator {}
        MenuItem {
            text: root.fileModel.selectedCount > 1 ? "Remove " + root.fileModel.selectedCount + " selected" : "Remove"
            onTriggered: root.fileModel.removeSelected()
        }
        MenuItem {
            text: "Remove finished"
            enabled: root.fileModel.doneCount > 0
            onTriggered: root.fileModel.removeFinished()
        }
        MenuItem {
            text: "Clear queue"
            onTriggered: transcriptionController.clearQueue()
        }
    }

    DropArea {
        id: dropArea
        anchors.fill: parent
        onDropped: function(drop) {
            if (drop.hasUrls) {
                root.filesDropped(drop.urls)
                drop.acceptProposedAction()
            }
        }

        Rectangle {
            anchors.fill: parent
            anchors.margins: Theme.spaceXs
            radius: Theme.radiusLarge
            color: Theme.dark ? "#332a6fd6" : "#1a0b62c4"
            border.color: Theme.accent
            border.width: 2
            visible: dropArea.containsDrag

            Text {
                anchors.centerIn: parent
                text: "Drop to add to the queue"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSubtitle
                font.weight: Font.DemiBold
                color: Theme.accent
            }
        }
    }
}
