// qmllint disable unqualified
import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtQuick.Window
import QtQuick.Dialogs
import "components"

ApplicationWindow {
    id: mainWin

    width:       820
    height:      560
    minimumWidth:  680
    minimumHeight: 460
    visible:     true
    title: appController.appName
    flags: Qt.FramelessWindowHint | Qt.Window

    Material.theme: appController && appController.currentTheme === "dark" ? Material.Dark : Material.Light
    Material.accent: "#0078d4"

    Component.onCompleted: {
        x = Screen.virtualX + Math.round((Screen.desktopAvailableWidth  - width)  / 2)
        y = Screen.virtualY + Math.round((Screen.desktopAvailableHeight - height) / 2)
    }

    // Live segment model — QML-side ListModel populated by worker signals
    ListModel { id: segmentModel }

    Connections {
        target: transcriptionController

        function onSegmentAdded(id, start, end, text) {
            segmentModel.append({ segId: id, segStart: start, segEnd: end, segText: text })
        }

        function onOperationFinished(success, errorMsg, outputFiles) {
            if (!success) {
                statusLabel.text = "✗ " + (errorMsg || "Unknown error")
            } else {
                var dirs = []
                for (var i = 0; i < outputFiles.length; i++) {
                    var d = outputFiles[i].toString().replace(/[^\\/]+$/, "")
                    if (dirs.indexOf(d) < 0) dirs.push(d)
                }
                statusLabel.text = "✓ " + outputFiles.length + " file(s) written"
                completionDialog.fileCount  = outputFiles.length
                completionDialog.outputDirs = dirs
                completionDialog.open()
            }
        }

        function onStatusChanged(msg) {
            statusLabel.text = msg
        }

        function onBusyChanged() {
            if (!transcriptionController.busy) {
                progressBar.value = 0
                segCountLabel.text = ""
            }
        }

        function onProgressChanged(done, total) {
            segCountLabel.text = "Seg " + done + (total > done ? "/" + total : "")
            progressBar.value = total > 0 ? done / total : 0
        }
    }

    // File-picker dialog
    FileDialog {
        id: filePicker
        title: "Add Media Files"
        nameFilters: [
            "Supported files (*.mp4 *.mkv *.avi *.mov *.webm *.flv *.wmv *.ts *.mp3 *.wav *.m4a *.flac *.aac *.ogg *.wma *.srt *.vtt)",
            "Video files (*.mp4 *.mkv *.avi *.mov *.webm *.flv *.wmv *.ts)",
            "Audio files (*.mp3 *.wav *.m4a *.flac *.aac *.ogg *.wma)",
            "Subtitle files (*.srt *.vtt)",
            "All files (*)"
        ]
        fileMode: FileDialog.OpenFiles
        onAccepted: transcriptionController.addFiles(selectedFiles)
    }

    // Folder-picker dialog
    FolderDialog {
        id: folderPicker
        title: "Add All Media Files from Folder"
        onAccepted: transcriptionController.addFolder(selectedFolder.toString())
    }

    // ── Background ─────────────────────────────────────────────────────────
    Rectangle {
        anchors.fill: parent
        color: Material.theme === Material.Dark ? "#1e1e1e" : "#f0f0f0"
        border.color: Material.theme === Material.Dark ? "#3a3a3a" : "#c0c0c0"
        border.width: 1
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ── Title bar ───────────────────────────────────────────────────
        TitleBar {
            Layout.fillWidth: true
            window: mainWin
            title: appController.appName + " " + appController.appVersion
            showMaximize: true
        }

        // ── Two-panel body ──────────────────────────────────────────────
        Row {
            Layout.fillWidth:  true
            Layout.fillHeight: true

            // ── Left panel — file list ──────────────────────────────────
            Rectangle {
                width:  260
                height: parent.height
                color: Material.theme === Material.Dark ? "#242424" : "#f8f8f8"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 0
                    spacing: 0

                    // Panel header toolbar
                    Rectangle {
                        Layout.fillWidth:       true
                        Layout.preferredHeight: 36
                        color: Material.theme === Material.Dark ? "#1e1e1e" : "#ebebeb"

                        RowLayout {
                            anchors.fill:        parent
                            anchors.leftMargin:  10
                            anchors.rightMargin:  4
                            spacing: 2

                            Text {
                                text: "Files (" + transcriptionController.fileModel.count + ")"
                                font.pixelSize: 10
                                font.weight:    Font.Bold
                                color: Material.theme === Material.Dark ? "#888888" : "#777777"
                            }

                            Item { Layout.fillWidth: true }

                            // + Files
                            Rectangle {
                                Layout.preferredHeight: 24
                                implicitWidth: _t0.implicitWidth + 16
                                radius: height / 2
                                color: _m0.containsMouse ? Qt.rgba(0.5,0.5,0.5,0.12) : "transparent"
                                Behavior on color { ColorAnimation { duration: 80 } }
                                Text { id: _t0; anchors.centerIn: parent; text: "+ Files";    font.pixelSize: 10; color: "#0078d4" }
                                MouseArea { id: _m0; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: filePicker.open() }
                            }
                            // + Folder
                            Rectangle {
                                Layout.preferredHeight: 24
                                implicitWidth: _t1.implicitWidth + 16
                                radius: height / 2
                                color: _m1.containsMouse ? Qt.rgba(0.5,0.5,0.5,0.12) : "transparent"
                                Behavior on color { ColorAnimation { duration: 80 } }
                                Text { id: _t1; anchors.centerIn: parent; text: "+ Folder";   font.pixelSize: 10; color: "#0078d4" }
                                MouseArea { id: _m1; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: folderPicker.open() }
                            }
                            // Select All
                            Rectangle {
                                Layout.preferredHeight: 24
                                implicitWidth: _t2.implicitWidth + 16
                                radius: height / 2
                                color: _m2.containsMouse && transcriptionController.fileModel.count > 0
                                    ? Qt.rgba(0.5,0.5,0.5,0.12) : "transparent"
                                Behavior on color { ColorAnimation { duration: 80 } }
                                Text {
                                    id: _t2; anchors.centerIn: parent; text: "Select All"; font.pixelSize: 10
                                    color: transcriptionController.fileModel.count > 0
                                        ? (Material.theme === Material.Dark ? "#cccccc" : "#444444")
                                        : (Material.theme === Material.Dark ? "#555555" : "#bbbbbb")
                                }
                                MouseArea {
                                    id: _m2; anchors.fill: parent; hoverEnabled: true
                                    cursorShape: transcriptionController.fileModel.count > 0 ? Qt.PointingHandCursor : Qt.ArrowCursor
                                    onClicked: if (transcriptionController.fileModel.count > 0) transcriptionController.fileModel.selectAll()
                                }
                            }
                            // Remove
                            Rectangle {
                                Layout.preferredHeight: 24
                                implicitWidth: _t3.implicitWidth + 16
                                radius: height / 2
                                color: _m3.containsMouse && transcriptionController.fileModel.selectedCount > 0
                                    ? Qt.rgba(0.91,0.07,0.14,0.08) : "transparent"
                                Behavior on color { ColorAnimation { duration: 80 } }
                                Text {
                                    id: _t3; anchors.centerIn: parent; text: "Remove"; font.pixelSize: 10
                                    color: transcriptionController.fileModel.selectedCount > 0
                                        ? "#e81123"
                                        : (Material.theme === Material.Dark ? "#555555" : "#bbbbbb")
                                }
                                MouseArea {
                                    id: _m3; anchors.fill: parent; hoverEnabled: true
                                    cursorShape: transcriptionController.fileModel.selectedCount > 0 ? Qt.PointingHandCursor : Qt.ArrowCursor
                                    onClicked: if (transcriptionController.fileModel.selectedCount > 0) transcriptionController.fileModel.removeSelected()
                                }
                            }
                        }
                    }

                    // File list component
                    FileList {
                        Layout.fillWidth:  true
                        Layout.fillHeight: true
                        onEmptyPanelClicked: filePicker.open()
                    }
                }
            }

            // ── Vertical divider ────────────────────────────────────────
            Rectangle {
                width:  1
                height: parent.height
                color: Material.theme === Material.Dark ? "#333333" : "#d0d0d0"
            }

            // ── Right panel — settings / output ─────────────────────────
            Item {
                width:  parent.width - 261
                height: parent.height

                StackLayout {
                    anchors.fill: parent
                    currentIndex: transcriptionController.busy ? 1 : 0

                    // ── Page 0: Settings (idle) ────────────────────────
                    Flickable {
                        contentHeight: settingsCol.implicitHeight + 24
                        clip: true

                        ColumnLayout {
                            id: settingsCol
                            anchors.left:    parent.left
                            anchors.right:   parent.right
                            anchors.margins: 20
                            spacing: 12

                            Item { implicitHeight: 4 }

                            // Model selector
                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: "Model"
                                    font.pixelSize: 12
                                    color: Material.foreground
                                    Layout.preferredWidth: 110
                                }
                                StyledComboBox {
                                    id: modelCombo
                                    Layout.fillWidth:       true
                                    Layout.preferredHeight: 34
                                    font.pixelSize:         12
                                    model: prefsController.modelOptions
                                    Component.onCompleted: {
                                        var idx = model.indexOf("base")
                                        currentIndex = idx >= 0 ? idx : 0
                                    }
                                    onCurrentIndexChanged:
                                        transcriptionController.setModelName(currentText)
                                }
                            }

                            // Language selector
                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: "Language"
                                    font.pixelSize: 12
                                    color: Material.foreground
                                    Layout.preferredWidth: 110
                                }
                                StyledComboBox {
                                    id: langCombo
                                    Layout.fillWidth:       true
                                    Layout.preferredHeight: 34
                                    font.pixelSize:         12
                                    model: prefsController.languageOptions.map(o => o.label)
                                    currentIndex: 0
                                    onCurrentIndexChanged: {
                                        var opts = prefsController.languageOptions
                                        if (currentIndex < opts.length)
                                            transcriptionController.setLanguage(opts[currentIndex].code)
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth:       true
                                Layout.preferredHeight: 1
                                color: Material.theme === Material.Dark ? "#333333" : "#e0e0e0"
                            }

                            // Translate toggle + target lang
                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: "Translate"
                                    font.pixelSize: 12
                                    color: Material.foreground
                                    Layout.preferredWidth: 110
                                }
                                Switch {
                                    id: translateSwitch
                                    checked: false
                                    onCheckedChanged: transcriptionController.setTranslate(checked)
                                }
                                StyledComboBox {
                                    id: targetLangCombo
                                    Layout.fillWidth:       true
                                    Layout.preferredHeight: 34
                                    font.pixelSize:         12
                                    visible: translateSwitch.checked
                                    model: prefsController.targetOptions.map(o => o.label)
                                    currentIndex: {
                                        var opts = prefsController.targetOptions
                                        for (var i = 0; i < opts.length; i++)
                                            if (opts[i].code === "ur") return i
                                        return 0
                                    }
                                    onCurrentIndexChanged: {
                                        var opts = prefsController.targetOptions
                                        if (currentIndex < opts.length)
                                            transcriptionController.setTargetLang(opts[currentIndex].code)
                                    }
                                }
                            }

                            // Transliterate toggle + scheme selectors
                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: "Transliterate"
                                    font.pixelSize: 12
                                    color: Material.foreground
                                    Layout.preferredWidth: 110
                                }
                                Switch {
                                    id: translitSwitch
                                    checked: false
                                    onCheckedChanged: transcriptionController.setTransliterate(checked)
                                }
                                Row {
                                    spacing: 6
                                    visible: translitSwitch.checked

                                    StyledComboBox {
                                        id: translitSrcCombo
                                        width: 100; height: 34
                                        font.pixelSize: 11
                                        model: prefsController.translitSchemeOptions.map(o => o.label)
                                        currentIndex: 0
                                        onCurrentIndexChanged: {
                                            var opts = prefsController.translitSchemeOptions
                                            if (currentIndex < opts.length)
                                                transcriptionController.setTranslitSource(opts[currentIndex].code)
                                        }
                                    }
                                    Text {
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: "→"
                                        font.pixelSize: 12
                                        color: Material.foreground
                                    }
                                    StyledComboBox {
                                        id: translitTgtCombo
                                        width: 100; height: 34
                                        font.pixelSize: 11
                                        model: prefsController.translitSchemeOptions.map(o => o.label)
                                        currentIndex: {
                                            var opts = prefsController.translitSchemeOptions
                                            for (var i = 0; i < opts.length; i++)
                                                if (opts[i].code === "ur") return i
                                            return 1
                                        }
                                        onCurrentIndexChanged: {
                                            var opts = prefsController.translitSchemeOptions
                                            if (currentIndex < opts.length)
                                                transcriptionController.setTranslitTarget(opts[currentIndex].code)
                                        }
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth:       true
                                Layout.preferredHeight: 1
                                color: Material.theme === Material.Dark ? "#333333" : "#e0e0e0"
                            }

                            // Output format checkboxes
                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: "Output"
                                    font.pixelSize: 12
                                    color: Material.foreground
                                    Layout.preferredWidth: 110
                                }
                                CheckBox {
                                    id: srtCheck
                                    text: "SRT"
                                    font.pixelSize: 12
                                    checked: true
                                    onCheckedChanged: transcriptionController.setEmitSrt(checked)
                                }
                                CheckBox {
                                    id: vttCheck
                                    text: "VTT"
                                    font.pixelSize: 12
                                    checked: false
                                    onCheckedChanged: transcriptionController.setEmitVtt(checked)
                                }
                            }

                            Item { Layout.fillHeight: true; implicitHeight: 8 }

                            // Status bar
                            Text {
                                id: statusLabel
                                Layout.fillWidth: true
                                text: ""
                                font.pixelSize: 11
                                color: Material.theme === Material.Dark ? "#888888" : "#777777"
                                wrapMode: Text.WordWrap
                                visible: text.length > 0
                            }

                            // Action buttons
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8

                                Button {
                                    text: "▶  Start"
                                    highlighted: true
                                    font.pixelSize: 12
                                    Layout.preferredHeight: 38
                                    enabled: transcriptionController.fileModel.count > 0
                                    onClicked: {
                                        var paths = transcriptionController.fileModel.getPaths()
                                        if (paths.length > 0) {
                                            segmentModel.clear()
                                            statusLabel.text = ""
                                            transcriptionController.startProcessing(paths[0])
                                        }
                                    }
                                }

                                Button {
                                    text: "⚙  Preferences"
                                    flat: true
                                    font.pixelSize: 12
                                    Layout.preferredHeight: 38
                                    onClicked: {
                                        var comp = Qt.createComponent("PreferencesWindow.qml")
                                        if (comp.status === Component.Ready) {
                                            var win = comp.createObject(mainWin)
                                            if (win) win.show()  // qmllint disable missing-property
                                        }
                                    }
                                }

                                Button {
                                    text: "ℹ  About"
                                    flat: true
                                    font.pixelSize: 12
                                    Layout.preferredHeight: 38
                                    onClicked: aboutDialog.open()
                                }
                            }

                            Item { implicitHeight: 8 }
                        }
                    }

                    // ── Page 1: Processing ──────────────────────────────
                    ColumnLayout {
                        spacing: 0

                        // Processing header
                        ColumnLayout {
                            Layout.fillWidth:  true
                            Layout.margins: 16
                            spacing: 8

                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: transcriptionController.fileModel.count > 0
                                        ? transcriptionController.fileModel.getPaths()[0].split("/").pop().split("\\").pop()
                                        : ""
                                    font.pixelSize: 12
                                    font.weight:    Font.Medium
                                    color: Material.foreground
                                    elide: Text.ElideMiddle
                                    Layout.fillWidth: true
                                }
                                Text {
                                    id: segCountLabel
                                    text: ""
                                    font.pixelSize: 11
                                    color: Material.theme === Material.Dark ? "#888888" : "#777777"
                                }
                            }

                            ProgressBar {
                                id: progressBar
                                Layout.fillWidth: true
                                value: 0
                                indeterminate: transcriptionController.busy && value === 0
                            }

                            Text {
                                id: procStatusLabel
                                text: statusLabel.text
                                font.pixelSize: 11
                                color: Material.theme === Material.Dark ? "#888888" : "#777777"
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                        }

                        Rectangle {
                            Layout.fillWidth:       true
                            Layout.preferredHeight: 1
                            color: Material.theme === Material.Dark ? "#333333" : "#e0e0e0"
                        }

                        // Live segment list
                        ListView {
                            id: segList
                            Layout.fillWidth:  true
                            Layout.fillHeight: true
                            model: segmentModel
                            clip: true
                            spacing: 0

                            delegate: SegmentItem {
                                width: segList.width
                            }

                            onCountChanged: segList.positionViewAtEnd()

                            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                        }

                        Rectangle {
                            Layout.fillWidth:       true
                            Layout.preferredHeight: 1
                            color: Material.theme === Material.Dark ? "#333333" : "#e0e0e0"
                        }

                        // Cancel button
                        Button {
                            Layout.fillWidth:       true
                            Layout.margins:         12
                            Layout.preferredHeight: 38
                            text: "Cancel"
                            font.pixelSize: 12
                            Material.foreground: "#e81123"
                            onClicked: transcriptionController.cancelProcessing()
                        }
                    }
                }
            }
        }
    }

    // Full-window drop area (z below content)
    DropArea {
        anchors.fill: parent
        z: -1
        onDropped: function(drop) {
            if (drop.hasUrls)
                transcriptionController.addFiles(drop.urls)
        }
    }

    // Resize grip
    Rectangle {
        id: resizeGrip
        width: 14; height: 14
        anchors.right:  parent.right
        anchors.bottom: parent.bottom
        color: "transparent"

        Text {
            anchors.centerIn: parent
            text: "⌟"
            font.pixelSize: 14
            color: Material.theme === Material.Dark ? "#555555" : "#aaaaaa"
        }

        DragHandler {
            target: null
            onActiveChanged: if (active) mainWin.startSystemResize(Qt.RightEdge | Qt.BottomEdge)
        }
    }

    // Completion dialog
    Dialog {
        id: completionDialog
        title: "Processing Complete"
        modal: true
        standardButtons: Dialog.Ok
        anchors.centerIn: parent

        property int fileCount:  0
        property var outputDirs: []

        ColumnLayout {
            spacing: 8

            Text {
                text: "✓ " + completionDialog.fileCount + " subtitle file(s) written."
                font.pixelSize: 13
                font.weight:    Font.Medium
                color: "#2e7d32"
                Layout.preferredWidth: 360
                wrapMode: Text.WordWrap
            }

            Text {
                text: completionDialog.outputDirs.length > 1 ? "Output folders:" : "Output folder:"
                font.pixelSize: 11
                color: Material.foreground
            }

            Repeater {
                model: completionDialog.outputDirs

                delegate: Rectangle {
                    Layout.fillWidth:       true
                    Layout.preferredHeight: 36
                    Layout.preferredWidth:  360
                    radius: 4
                    color: dirMouse.containsMouse
                        ? (Material.theme === Material.Dark ? "#1a3a5c" : "#e3f2fd")
                        : (Material.theme === Material.Dark ? "#2a2a2a" : "#f5f5f5")
                    border.color: dirMouse.containsMouse ? "#0078d4"
                        : (Material.theme === Material.Dark ? "#444444" : "#dddddd")
                    border.width: 1

                    Behavior on color { ColorAnimation { duration: 80 } }

                    RowLayout {
                        anchors.fill:    parent
                        anchors.margins: 8
                        spacing: 6

                        Text {
                            text: "📂"
                            font.pixelSize: 13
                        }
                        Text {
                            Layout.fillWidth: true
                            text: modelData
                            font.pixelSize: 11
                            font.family:    "Consolas"
                            color: dirMouse.containsMouse ? "#0078d4" : Material.foreground
                            elide: Text.ElideMiddle
                            verticalAlignment: Text.AlignVCenter
                            Behavior on color { ColorAnimation { duration: 80 } }
                        }
                        Text {
                            text: "↗"
                            font.pixelSize: 10
                            color: "#0078d4"
                            visible: dirMouse.containsMouse
                        }
                    }

                    MouseArea {
                        id: dirMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape:  Qt.PointingHandCursor
                        onClicked:    Qt.openUrlExternally("file:///" + modelData.replace(/\\/g, "/"))
                    }
                }
            }
        }
    }

    // About dialog
    Dialog {
        id: aboutDialog
        title: "About " + appController.appName
        modal: true
        standardButtons: Dialog.Ok
        anchors.centerIn: parent

        RowLayout {
            spacing: 16

            Image {
                source: "../assets/icons/Square44x44Logo.targetsize-48.png"
                Layout.preferredWidth:  48
                Layout.preferredHeight: 48
                Layout.alignment: Qt.AlignTop
                fillMode: Image.PreserveAspectFit
                smooth: true
            }

            ColumnLayout {
                spacing: 6
                Text {
                    text: appController.appName + " " + appController.appVersion
                    font.pixelSize: 14
                    font.weight: Font.Bold
                    color: Material.foreground
                }
                Text {
                    text: appController.appDescription
                    font.pixelSize: 12
                    color: Material.foreground
                    wrapMode: Text.WordWrap
                    Layout.preferredWidth: 280
                }
                Text {
                    text: "By " + appController.appAuthor
                    font.pixelSize: 11
                    color: Material.theme === Material.Dark ? "#888888" : "#777777"
                }
            }
        }
    }
}
