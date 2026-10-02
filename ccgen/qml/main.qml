// qmllint disable unqualified
import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Dialogs
import QtQuick.Layouts
import "components"

AppWindow {
    id: mainWin

    width: 1120
    height: 740
    minimumWidth: 860
    minimumHeight: 560
    visible: true
    title: appController.appName + " " + appController.appVersion

    readonly property var queue: transcriptionController.fileModel
    readonly property bool busy: transcriptionController.busy
    property string transcriptFile: ""
    property var _rowOfSegment: ({})
    property var _prefsWindow: null
    property var _modelsWindow: null

    // Why Start is unavailable right now ("" when it can run).
    readonly property string startBlocker: {
        if (transcriptionController.scanning) return "Wait for the folder scan to finish (or stop it)."
        if (mainWin.queue.count === 0) return "Add files to the queue first."
        if (!transcriptionController.hasOutputFormat) return "Select at least one output format."
        if (transcriptionController.transliterateEnabled) {
            if (transcriptionController.translitSource === transcriptionController.translitTarget)
                return "Choose two different transliteration scripts."
            if (transcriptionController.translitEngine === "neural" && !mainWin.neuralSupported)
                return "The neural engine doesn't support this script pair. Choose the rule-based engine."
        }
        return ""
    }
    readonly property bool neuralSupported: modelsController.neuralAssetId(
        transcriptionController.translitSource, transcriptionController.translitTarget).length > 0

    // quitOnLastWindowClosed is disabled app-wide (see app.py) since it can misfire while a
    // QML window is still open, so closing the main window quits explicitly.
    onClosing: Qt.quit()

    titleActions: [
        AppButton {
            kind: "ghost"
            compact: true
            text: "Models"
            iconName: "library"
            toolTipText: "Manage downloaded models (Ctrl+M)"
            focusPolicy: Qt.TabFocus
            onClicked: mainWin.openModels()
        },
        AppButton {
            kind: "ghost"
            compact: true
            text: "Preferences"
            iconName: "settings"
            toolTipText: "Default settings, appearance, and logs (Ctrl+,)"
            focusPolicy: Qt.TabFocus
            onClicked: mainWin.openPreferences()
        },
        AppButton {
            kind: "ghost"
            compact: true
            iconName: "info"
            toolTipText: "About " + appController.appName + " (F1)"
            focusPolicy: Qt.TabFocus
            onClicked: aboutDialog.open()
        }
    ]

    // ── Windows and dialogs ────────────────────────────────────────────────

    function openPreferences() {
        if (!mainWin._prefsWindow) {
            var comp = Qt.createComponent("PreferencesWindow.qml")
            if (comp.status !== Component.Ready) { console.error(comp.errorString()); return }
            mainWin._prefsWindow = comp.createObject(mainWin)
            mainWin._prefsWindow.closing.connect(function() { mainWin._prefsWindow = null })
        }
        mainWin._prefsWindow.show()
        mainWin._prefsWindow.raise()
        mainWin._prefsWindow.requestActivate()
    }

    function openModels() {
        if (!mainWin._modelsWindow) {
            var comp = Qt.createComponent("ManageModelsWindow.qml")
            if (comp.status !== Component.Ready) { console.error(comp.errorString()); return }
            mainWin._modelsWindow = comp.createObject(mainWin)
            mainWin._modelsWindow.closing.connect(function() { mainWin._modelsWindow = null })
        }
        mainWin._modelsWindow.show()
        mainWin._modelsWindow.raise()
        mainWin._modelsWindow.requestActivate()
    }

    function start() {
        if (mainWin.busy) return
        if (mainWin.startBlocker.length > 0) { toast.show(mainWin.startBlocker); return }
        transcriptionController.startQueue()
    }

    FileDialog {
        id: filePicker
        title: "Add media or subtitle files"
        fileMode: FileDialog.OpenFiles
        nameFilters: [
            "Supported files (*.mp4 *.mkv *.avi *.mov *.webm *.flv *.wmv *.ts *.m2ts *.mp3 *.wav *.m4a *.flac *.aac *.ogg *.wma *.srt *.vtt *.lrc *.ass *.ssa *.sbv)",
            "Video files (*.mp4 *.mkv *.avi *.mov *.webm *.flv *.wmv *.ts *.m2ts)",
            "Audio files (*.mp3 *.wav *.m4a *.flac *.aac *.ogg *.wma)",
            "Subtitle files (*.srt *.vtt *.lrc *.ass *.ssa *.sbv)"
        ]
        onAccepted: transcriptionController.addFiles(selectedFiles)
    }

    FolderDialog {
        id: folderPicker
        title: "Add every supported file in a folder (including subfolders)"
        onAccepted: transcriptionController.addFolder(selectedFolder.toString())
    }

    FolderDialog {
        id: outputFolderPicker
        title: "Choose where subtitle files are saved"
        onAccepted: transcriptionController.setOutputDir(selectedFolder.toString())
    }

    // ── Keyboard shortcuts ─────────────────────────────────────────────────

    Shortcut { sequences: [StandardKey.Open]; onActivated: filePicker.open() }
    Shortcut { sequence: "Ctrl+Shift+O"; onActivated: folderPicker.open() }
    Shortcut { sequences: ["Ctrl+Return", "Ctrl+Enter", "F5"]; onActivated: mainWin.start() }
    Shortcut { sequence: "Escape"; enabled: mainWin.busy; onActivated: transcriptionController.cancelQueue() }
    Shortcut { sequence: "Ctrl+,"; onActivated: mainWin.openPreferences() }
    Shortcut { sequence: "Ctrl+M"; onActivated: mainWin.openModels() }
    Shortcut { sequence: "F1"; onActivated: aboutDialog.open() }
    Shortcut { sequence: "Ctrl+1"; onActivated: tabs.currentIndex = 0 }
    Shortcut { sequence: "Ctrl+2"; onActivated: tabs.currentIndex = 1 }

    // ── Controller events ──────────────────────────────────────────────────

    Connections {
        target: transcriptionController

        function onFileStarted(path, name) {
            transcriptModel.clear()
            mainWin._rowOfSegment = {}
            mainWin.transcriptFile = name
            if (transcriptionController.runPosition === 1) tabs.currentIndex = 1
        }

        function onSegmentAdded(id, start, end, text, kind) {
            var row = mainWin._rowOfSegment[id]
            if (row === undefined) {
                row = transcriptModel.count
                mainWin._rowOfSegment[id] = row
                transcriptModel.append({
                    segStart: start, segEnd: end,
                    segText: kind === "transcript" ? text : "",
                    segTranslation: kind === "translation" ? text : "",
                    segTransliteration: kind === "transliteration" ? text : ""
                })
                return
            }
            var role = kind === "translation" ? "segTranslation"
                : kind === "transliteration" ? "segTransliteration" : "segText"
            transcriptModel.setProperty(row, role, text)
        }

        function onNotice(message) {
            toast.show(message)
        }
    }

    Connections {
        target: prefsController
        function onSaveFinished(success, error) {
            if (success) transcriptionController.reloadDefaults()
        }
    }

    ListModel { id: transcriptModel }

    // ── Layout ─────────────────────────────────────────────────────────────

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal

            handle: Rectangle {
                implicitWidth: 5
                color: SplitHandle.pressed || SplitHandle.hovered ? Theme.accentSoft : Theme.background
                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 1
                    height: parent.height
                    color: Theme.border
                }
            }

            // ── Queue panel ─────────────────────────────────────────────────
            Rectangle {
                SplitView.preferredWidth: 400
                SplitView.minimumWidth: 300
                SplitView.maximumWidth: 600
                color: Theme.surface

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.margins: Theme.spaceLg
                        Layout.bottomMargin: Theme.spaceSm
                        spacing: Theme.spaceSm

                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: "Queue"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontTitle
                                font.weight: Font.DemiBold
                                color: Theme.text
                                Accessible.role: Accessible.Heading
                                Accessible.name: "Queue"
                            }
                            Item { Layout.fillWidth: true }
                            Text {
                                text: mainWin.queue.count === 0 ? "" :
                                    mainWin.queue.count + (mainWin.queue.count === 1 ? " file" : " files")
                                    + "  ·  " + mainWin.queue.totalSize
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontCaption
                                color: Theme.textMuted
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spaceSm

                            AppButton {
                                kind: "primary"
                                text: "Add files"
                                iconName: "add"
                                toolTipText: "Add media or subtitle files (Ctrl+O)"
                                onClicked: filePicker.open()
                            }
                            AppButton {
                                text: "Add folder"
                                iconName: "folder"
                                toolTipText: "Add every supported file in a folder and its subfolders (Ctrl+Shift+O)"
                                onClicked: folderPicker.open()
                            }
                            Item { Layout.fillWidth: true }
                            AppButton {
                                id: queueMenuButton
                                kind: "ghost"
                                iconName: "more"
                                toolTipText: "More queue actions"
                                enabled: mainWin.queue.count > 0
                                onClicked: queueMenu.popup(queueMenuButton, 0, queueMenuButton.height)

                                Menu {
                                    id: queueMenu
                                    MenuItem {
                                        text: "Select all"
                                        onTriggered: mainWin.queue.selectAll()
                                    }
                                    MenuItem {
                                        text: "Remove selected"
                                        enabled: mainWin.queue.selectedCount > 0
                                        onTriggered: mainWin.queue.removeSelected()
                                    }
                                    MenuItem {
                                        text: "Remove finished"
                                        enabled: mainWin.queue.doneCount > 0
                                        onTriggered: mainWin.queue.removeFinished()
                                    }
                                    MenuSeparator {}
                                    MenuItem {
                                        text: "Clear queue"
                                        onTriggered: transcriptionController.clearQueue()
                                    }
                                }
                            }
                        }
                    }

                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.border }

                    FileList {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        fileModel: mainWin.queue
                        busy: mainWin.busy
                        scanning: transcriptionController.scanning
                        scanFound: transcriptionController.scanFound
                        onAddFilesRequested: filePicker.open()
                        onAddFolderRequested: folderPicker.open()
                        onFilesDropped: urls => transcriptionController.addFiles(urls)
                        onRevealRequested: path => appController.revealFile(path)
                    }
                }
            }

            // ── Settings / transcript panel ────────────────────────────────
            ColumnLayout {
                SplitView.fillWidth: true
                spacing: 0

                TabBar {
                    id: tabs
                    objectName: "mainTabs"
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.spaceLg
                    Layout.topMargin: Theme.spaceSm
                    background: Item {}

                    TabButton {
                        text: mainWin.busy ? "Settings (locked)" : "Settings"
                        width: implicitWidth + 24
                        font.pixelSize: Theme.fontBody
                        ToolTip.visible: hovered
                        ToolTip.text: "Options for the next run (Ctrl+1)"
                        ToolTip.delay: 600
                    }
                    TabButton {
                        text: transcriptModel.count > 0 ? "Transcript (" + transcriptModel.count + ")" : "Transcript"
                        width: implicitWidth + 24
                        font.pixelSize: Theme.fontBody
                        ToolTip.visible: hovered
                        ToolTip.text: "Live subtitles of the file being processed (Ctrl+2)"
                        ToolTip.delay: 600
                    }
                }

                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.border }

                StackLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    currentIndex: tabs.currentIndex

                    ScrollView {
                    id: settingsPage
                    contentWidth: availableWidth
                    clip: true

                    ColumnLayout {
                        width: settingsPage.availableWidth
                        spacing: Theme.spaceLg
                        enabled: !mainWin.busy

                        Item { Layout.preferredHeight: Theme.spaceXs }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.leftMargin: Theme.spaceXl
                            Layout.rightMargin: Theme.spaceXl
                            Layout.preferredHeight: lockedText.implicitHeight + 2 * Theme.spaceMd
                            radius: Theme.radius
                            color: Theme.accentSoft
                            visible: mainWin.busy

                            Text {
                                id: lockedText
                                anchors.fill: parent
                                anchors.margins: Theme.spaceMd
                                text: "Settings are locked while files are processing. Changes apply to the next run."
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontCaption
                                color: Theme.text
                                wrapMode: Text.WordWrap
                            }
                        }

                        Card {
                            Layout.fillWidth: true
                            Layout.leftMargin: Theme.spaceXl
                            Layout.rightMargin: Theme.spaceXl
                            title: "Transcription"
                            description: "Speech recognition runs offline with Whisper."
                            iconName: "mic"

                            FormRow {
                                label: "Model"
                                hint: "Larger models are more accurate but slower."
                                StyledComboBox {
                                    id: modelCombo
                                    Layout.fillWidth: true
                                    accessibleName: "Transcription model"
                                    toolTipText: "Whisper model used to recognize speech. Bigger models are more accurate but slower; models download once on first use."
                                    model: prefsController.modelOptions
                                    readiness: mainWin.whisperReadiness(modelsController.readiness)
                                    onActivated: transcriptionController.setModelName(currentValue)
                                    Component.onCompleted: selectCode(transcriptionController.modelName)
                                    Connections {
                                        target: transcriptionController
                                        function onOptionsChanged() { modelCombo.selectCode(transcriptionController.modelName) }
                                    }
                                }
                            }

                            FormRow {
                                label: "Spoken language"
                                hint: "Auto-detect works for most files; pick the language if detection guesses wrong."
                                StyledComboBox {
                                    id: languageCombo
                                    Layout.fillWidth: true
                                    accessibleName: "Spoken language"
                                    toolTipText: "Language spoken in the files. Auto-detect listens to the opening minutes; choose a language to skip detection."
                                    model: prefsController.languageOptions
                                    onActivated: transcriptionController.setLanguage(currentValue)
                                    Component.onCompleted: selectCode(transcriptionController.language)
                                    Connections {
                                        target: transcriptionController
                                        function onOptionsChanged() { languageCombo.selectCode(transcriptionController.language) }
                                    }
                                }
                            }
                        }

                        Card {
                            Layout.fillWidth: true
                            Layout.leftMargin: Theme.spaceXl
                            Layout.rightMargin: Theme.spaceXl
                            title: "Translation"
                            description: "Translates whole sentences offline. English bridges other language pairs."
                            iconName: "globe"
                            trailing: AppSwitch {
                                checked: transcriptionController.translateEnabled
                                onToggled: transcriptionController.setTranslate(checked)
                                accessibleName: "Translate subtitles"
                                toolTipText: "Also write subtitles translated into another language, e.g. movie_ur.srt."
                            }

                            FormRow {
                                label: "Translate to"
                                visible: transcriptionController.translateEnabled
                                StyledComboBox {
                                    id: targetCombo
                                    Layout.fillWidth: true
                                    accessibleName: "Translation target language"
                                    toolTipText: "Language the subtitles are translated into."
                                    model: prefsController.targetOptions
                                    readiness: mainWin.translationReadiness(modelsController.readiness)
                                    onActivated: transcriptionController.setTargetLang(currentValue)
                                    Component.onCompleted: selectCode(transcriptionController.targetLang)
                                    Connections {
                                        target: transcriptionController
                                        function onOptionsChanged() { targetCombo.selectCode(transcriptionController.targetLang) }
                                    }
                                }
                            }
                        }

                        Card {
                            Layout.fillWidth: true
                            Layout.leftMargin: Theme.spaceXl
                            Layout.rightMargin: Theme.spaceXl
                            title: "Transliteration"
                            description: "Rewrites the text in another script, e.g. Urdu as natural Roman Urdu."
                            iconName: "characters"
                            trailing: AppSwitch {
                                checked: transcriptionController.transliterateEnabled
                                onToggled: transcriptionController.setTransliterate(checked)
                                accessibleName: "Transliterate subtitles"
                                toolTipText: "Also write subtitles rewritten in another script, e.g. movie_tr_ur_roman.srt."
                            }

                            FormRow {
                                label: "Scripts"
                                visible: transcriptionController.transliterateEnabled
                                StyledComboBox {
                                    id: translitSourceCombo
                                    Layout.fillWidth: true
                                    accessibleName: "Transliterate from script"
                                    toolTipText: "Script the source text is written in."
                                    model: prefsController.translitSchemeOptions
                                    onActivated: transcriptionController.setTranslitSource(currentValue)
                                    Component.onCompleted: selectCode(transcriptionController.translitSource)
                                    Connections {
                                        target: transcriptionController
                                        function onOptionsChanged() { translitSourceCombo.selectCode(transcriptionController.translitSource) }
                                    }
                                }
                                Icon { name: "chevronDown"; rotation: -90; size: 10; color: Theme.textMuted }
                                StyledComboBox {
                                    id: translitTargetCombo
                                    Layout.fillWidth: true
                                    accessibleName: "Transliterate to script"
                                    toolTipText: "Script to rewrite the text in."
                                    model: prefsController.translitSchemeOptions
                                    onActivated: transcriptionController.setTranslitTarget(currentValue)
                                    Component.onCompleted: selectCode(transcriptionController.translitTarget)
                                    Connections {
                                        target: transcriptionController
                                        function onOptionsChanged() { translitTargetCombo.selectCode(transcriptionController.translitTarget) }
                                    }
                                }
                            }

                            FormRow {
                                label: "Convert from"
                                visible: transcriptionController.transliterateEnabled
                                StyledComboBox {
                                    id: translitInputCombo
                                    Layout.fillWidth: true
                                    accessibleName: "Text to transliterate"
                                    toolTipText: "Transliterate the original transcript or its translation."
                                    model: prefsController.translitInputOptions
                                    onActivated: transcriptionController.setTranslitInput(currentValue)
                                    Component.onCompleted: selectCode(transcriptionController.translitInput)
                                    Connections {
                                        target: transcriptionController
                                        function onOptionsChanged() { translitInputCombo.selectCode(transcriptionController.translitInput) }
                                    }
                                }
                            }

                            FormRow {
                                label: "Engine"
                                hint: transcriptionController.translitEngine === "neural" && !mainWin.neuralSupported
                                    ? "Neural supports Urdu and Roman Urdu both ways, and Hindi or Punjabi to Urdu."
                                    : "Neural is more natural but downloads a model on first use."
                                visible: transcriptionController.transliterateEnabled
                                StyledComboBox {
                                    id: translitEngineCombo
                                    Layout.fillWidth: true
                                    accessibleName: "Transliteration engine"
                                    toolTipText: "Rule-based is instant and needs no download. Neural sounds more natural but downloads a model."
                                    model: prefsController.translitEngineOptions
                                    readiness: mainWin.engineReadiness(modelsController.readiness)
                                    onActivated: transcriptionController.setTranslitEngine(currentValue)
                                    Component.onCompleted: selectCode(transcriptionController.translitEngine)
                                    Connections {
                                        target: transcriptionController
                                        function onOptionsChanged() { translitEngineCombo.selectCode(transcriptionController.translitEngine) }
                                    }
                                }
                            }
                        }

                        Card {
                            Layout.fillWidth: true
                            Layout.leftMargin: Theme.spaceXl
                            Layout.rightMargin: Theme.spaceXl
                            title: "Output"
                            description: "Files are named after the source, e.g. movie.srt, movie_ur.srt."
                            iconName: "page"

                            FormRow {
                                label: "Formats"
                                hint: transcriptionController.hasOutputFormat ? "" : "Select at least one format."
                                Flow {
                                    Layout.fillWidth: true
                                    spacing: Theme.spaceSm
                                    Repeater {
                                        model: [
                                            { code: "srt", label: "SRT", info: "SubRip, works almost everywhere", on: transcriptionController.emitSrt },
                                            { code: "vtt", label: "VTT", info: "WebVTT, for web players and HTML5 video", on: transcriptionController.emitVtt },
                                            { code: "ass", label: "ASS", info: "Advanced SubStation Alpha, styled subtitles", on: transcriptionController.emitAss },
                                            { code: "sbv", label: "SBV", info: "YouTube subtitle format", on: transcriptionController.emitSbv },
                                            { code: "lrc", label: "LRC", info: "Lyrics format, start times only", on: transcriptionController.emitLrc }
                                        ]
                                        delegate: FormatChip {
                                            required property var modelData
                                            text: modelData.label
                                            description: modelData.info
                                            checked: modelData.on
                                            onToggled: transcriptionController.setFormat(modelData.code, checked)
                                        }
                                    }
                                }
                            }

                            FormRow {
                                label: "Save to"
                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: Theme.controlHeight
                                    radius: Theme.radius
                                    color: Theme.surfaceAlt
                                    border.width: 1
                                    border.color: Theme.border

                                    Text {
                                        anchors.fill: parent
                                        anchors.leftMargin: 10
                                        anchors.rightMargin: 10
                                        verticalAlignment: Text.AlignVCenter
                                        text: transcriptionController.outputDir || "Same folder as each source file"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontBody
                                        color: transcriptionController.outputDir ? Theme.text : Theme.textMuted
                                        elide: Text.ElideMiddle
                                        Accessible.role: Accessible.StaticText
                                        Accessible.name: "Save to: " + text
                                    }
                                }
                                AppButton {
                                    text: "Browse..."
                                    toolTipText: "Choose a folder for all subtitle files"
                                    onClicked: outputFolderPicker.open()
                                }
                                AppButton {
                                    kind: "ghost"
                                    iconName: "cancel"
                                    toolTipText: "Save next to each source file instead"
                                    visible: transcriptionController.outputDir.length > 0
                                    onClicked: transcriptionController.setOutputDir("")
                                }
                            }
                        }

                        Item { Layout.preferredHeight: Theme.spaceLg }
                    }
                }

                    ColumnLayout {
                    spacing: 0

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.margins: Theme.spaceLg
                        Layout.leftMargin: Theme.spaceXl
                        Layout.rightMargin: Theme.spaceXl
                        visible: mainWin.transcriptFile.length > 0

                        Icon { name: "captions"; color: Theme.accent }
                        Text {
                            Layout.fillWidth: true
                            text: mainWin.transcriptFile
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSubtitle
                            font.weight: Font.DemiBold
                            color: Theme.text
                            elide: Text.ElideMiddle
                            Accessible.role: Accessible.Heading
                            Accessible.name: "Transcript of " + text
                        }
                        Text {
                            text: transcriptModel.count + " cues"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontCaption
                            color: Theme.textMuted
                        }
                    }

                    ListView {
                        id: transcriptView
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.leftMargin: Theme.spaceLg
                        Layout.rightMargin: Theme.spaceLg
                        model: transcriptModel
                        clip: true
                        spacing: 2
                        activeFocusOnTab: true
                        boundsBehavior: Flickable.StopAtBounds
                        Accessible.role: Accessible.List
                        Accessible.name: "Transcript"

                        // Keep following new cues only while the user is already at the bottom.
                        property bool follow: true
                        onMovementEnded: follow = atYEnd
                        onCountChanged: if (follow) Qt.callLater(positionViewAtEnd)

                        delegate: SegmentItem {
                            width: ListView.view.width
                        }

                        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                        Keys.onUpPressed: flick(0, 800)
                        Keys.onDownPressed: flick(0, -800)
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        visible: transcriptModel.count === 0
                        spacing: Theme.spaceSm

                        Item { Layout.fillHeight: true }
                        Icon {
                            Layout.alignment: Qt.AlignHCenter
                            name: "captions"
                            size: 32
                            color: Theme.textMuted
                        }
                        Text {
                            Layout.fillWidth: true
                            horizontalAlignment: Text.AlignHCenter
                            text: mainWin.busy ? "Waiting for the first lines..." : "Subtitles appear here as each file is processed."
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBody
                            color: Theme.textMuted
                            wrapMode: Text.WordWrap
                        }
                        Item { Layout.fillHeight: true }
                    }
                }
                }
            }
        }

        Rectangle {
        Layout.fillWidth: true
        implicitHeight: 72
        color: Theme.surface

        Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: Theme.border }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: Theme.spaceXl
            anchors.rightMargin: Theme.spaceXl
            spacing: Theme.spaceLg

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceXs

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceSm

                    Text {
                        id: statusText
                        Layout.fillWidth: true
                        text: {
                            if (mainWin.busy) {
                                var stage = transcriptionController.stage || "Working..."
                                return "File " + transcriptionController.runPosition + " of " + transcriptionController.runTotal + "  ·  " + stage
                            }
                            if (transcriptionController.scanning) return "Scanning folder... " + transcriptionController.scanFound + " files found so far."
                            if (transcriptionController.summary) return transcriptionController.summary
                            if (mainWin.queue.count === 0) return "Ready. Add files to begin."
                            return mainWin.startBlocker || ("Ready to process " + mainWin.queue.runnableCount + (mainWin.queue.runnableCount === 1 ? " file." : " files."))
                        }
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBody
                        font.weight: Font.DemiBold
                        color: !mainWin.busy && !transcriptionController.scanning && mainWin.startBlocker && mainWin.queue.count > 0
                            ? Theme.warning : Theme.text
                        elide: Text.ElideRight
                        Accessible.role: Accessible.StaticText
                        Accessible.name: text
                    }
                    Text {
                        visible: mainWin.busy
                        text: Math.round(transcriptionController.overallProgress * 100) + "%"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontCaption
                        color: Theme.textMuted
                    }
                }

                ProgressBar {
                    Layout.fillWidth: true
                    visible: mainWin.busy
                    from: 0
                    to: 1
                    value: transcriptionController.overallProgress
                    Accessible.role: Accessible.ProgressBar
                    Accessible.name: "Overall progress"
                }

                Text {
                    Layout.fillWidth: true
                    visible: mainWin.busy && transcriptionController.currentFile.length > 0
                    text: transcriptionController.currentFile
                        + (transcriptionController.stageProgress >= 0
                           ? "  ·  " + Math.round(transcriptionController.stageProgress * 100) + "% of this step" : "")
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontCaption
                    color: Theme.textMuted
                    elide: Text.ElideMiddle
                }
            }

            AppButton {
                visible: !mainWin.busy && transcriptionController.lastOutputFolder.length > 0
                text: "Open output folder"
                iconName: "folderOpen"
                toolTipText: transcriptionController.lastOutputFolder
                onClicked: appController.openFolder(transcriptionController.lastOutputFolder)
            }

            AppButton {
                visible: mainWin.busy
                kind: "danger"
                text: "Cancel"
                iconName: "stop"
                toolTipText: "Stop after the current step; remaining files stay queued (Esc)"
                onClicked: transcriptionController.cancelQueue()
            }

            AppButton {
                visible: !mainWin.busy
                kind: "primary"
                text: mainWin.queue.runnableCount > 0 ? "Start (" + mainWin.queue.runnableCount + ")" : "Start"
                iconName: "play"
                enabled: mainWin.startBlocker.length === 0
                toolTipText: enabled ? "Process the queue (Ctrl+Enter)" : mainWin.startBlocker
                onClicked: mainWin.start()
            }
        }
    }
    }

    Toast {
        id: toast
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 88
        z: 50
    }




    // ── Download badges for the combo boxes ────────────────────────────────

    function whisperReadiness(readiness) {
        var result = {}
        var options = prefsController.modelOptions
        for (var i = 0; i < options.length; i++) {
            var ready = readiness[modelsController.whisperAssetId(options[i].code)]
            if (ready !== undefined) result[options[i].code] = ready
        }
        return result
    }

    function translationReadiness(readiness) {
        var result = {}
        var options = prefsController.targetOptions
        for (var i = 0; i < options.length; i++) {
            var ready = readiness[modelsController.translationAssetId(options[i].code)]
            if (ready !== undefined) result[options[i].code] = ready
        }
        return result
    }

    function engineReadiness(readiness) {
        var id = modelsController.neuralAssetId(transcriptionController.translitSource, transcriptionController.translitTarget)
        var result = {}
        if (id && readiness[id] !== undefined) result["neural"] = readiness[id]
        return result
    }

    // ── About ──────────────────────────────────────────────────────────────

    Dialog {
        id: aboutDialog
        title: "About " + appController.appName
        modal: true
        standardButtons: Dialog.Close
        anchors.centerIn: parent
        width: Math.min(460, mainWin.width - 48)

        ColumnLayout {
            anchors.fill: parent
            spacing: Theme.spaceMd

            RowLayout {
                spacing: Theme.spaceLg
                Image {
                    source: "../assets/icons/Square44x44Logo.targetsize-48.png"
                    Layout.preferredWidth: 48
                    Layout.preferredHeight: 48
                    fillMode: Image.PreserveAspectFit
                    Accessible.ignored: true
                }
                ColumnLayout {
                    spacing: 2
                    Text {
                        text: appController.appName + " " + appController.appVersion
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSubtitle
                        font.weight: Font.DemiBold
                        color: Theme.text
                    }
                    Text {
                        text: "By " + appController.appAuthor
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontCaption
                        color: Theme.textMuted
                    }
                }
            }
            Text {
                Layout.fillWidth: true
                text: appController.appDescription + ". Everything runs on this computer; nothing is uploaded."
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBody
                color: Theme.text
                wrapMode: Text.WordWrap
            }
            Text {
                Layout.fillWidth: true
                text: "Shortcuts: Ctrl+O add files, Ctrl+Shift+O add folder, Ctrl+Enter start, Esc cancel, "
                    + "Ctrl+, preferences, Ctrl+M models, Ctrl+1 / Ctrl+2 switch tabs."
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontCaption
                color: Theme.textMuted
                wrapMode: Text.WordWrap
            }
        }
    }
}
