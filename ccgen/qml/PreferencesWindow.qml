// qmllint disable unqualified
import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtQuick.Window
import "components"

ApplicationWindow {
    id: prefsWin

    width: 520
    height: 480
    minimumWidth: 460
    minimumHeight: 420
    title: "Preferences"
    flags: Qt.FramelessWindowHint | Qt.Window
    modality: Qt.ApplicationModal

    Material.theme: appController && appController.currentTheme === "dark" ? Material.Dark : Material.Light
    Material.accent: "#0078d4"

    Component.onCompleted: {
        x = Screen.virtualX + Math.round((Screen.desktopAvailableWidth  - width)  / 2)
        y = Screen.virtualY + Math.round((Screen.desktopAvailableHeight - height) / 2)
        prefsWin.loadValues()
    }

    onClosing: prefsWin.destroy()

    property bool _dirty: false

    Connections {
        target: prefsController
        function onSettingsChanged() { prefsWin.loadValues() }
    }

    Rectangle {
        anchors.fill: parent
        color: appController.colorBackground
        border.color: appController.colorDivider
        border.width: 1
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        TitleBar {
            Layout.fillWidth: true
            window: prefsWin
            title: "Preferences"
        }

        TabBar {
            id: tabBar
            Layout.fillWidth:       true
            Layout.preferredHeight: 44

            TabButton { text: "Appearance";      font.pixelSize: 12; implicitHeight: 44 }
            TabButton { text: "Transcription";   font.pixelSize: 12; implicitHeight: 44 }
            TabButton { text: "Translation";     font.pixelSize: 12; implicitHeight: 44 }
            TabButton { text: "Transliteration"; font.pixelSize: 12; implicitHeight: 44 }
            TabButton { text: "Advanced";        font.pixelSize: 12; implicitHeight: 44 }
        }

        StackLayout {
            id: tabContent
            Layout.fillWidth:  true
            Layout.fillHeight: true
            currentIndex: tabBar.currentIndex

            // ── Appearance tab ────────────────────────────────────────────
            Flickable {
                contentHeight: appearanceCol.implicitHeight
                clip: true

                ColumnLayout {
                    id: appearanceCol
                    anchors.left:    parent.left
                    anchors.right:   parent.right
                    anchors.margins: 20
                    spacing: 16

                    Item { implicitHeight: 8 }

                    GroupBox {
                        Layout.fillWidth: true
                        title: "Theme"
                        font.pixelSize: 12

                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 8

                            Text {
                                text: "Application theme"
                                font.pixelSize: 12
                                color: Material.foreground
                            }
                            StyledComboBox {
                                id: themeCombo
                                Layout.fillWidth:       true
                                Layout.preferredHeight: 32
                                font.pixelSize:         12
                                model: ["System (auto)", "Light", "Dark"]
                                onCurrentIndexChanged: prefsWin._dirty = true
                            }
                            Text {
                                text: "System follows your Windows light/dark setting."
                                font.pixelSize: 11
                                wrapMode: Text.WordWrap
                                color: appController.colorTextSecondary
                                Layout.fillWidth: true
                            }
                        }
                    }

                    Item { implicitHeight: 4 }
                }
            }

            // ── Transcription tab ─────────────────────────────────────────
            Flickable {
                contentHeight: transcriptionCol.implicitHeight
                clip: true

                ColumnLayout {
                    id: transcriptionCol
                    anchors.left:    parent.left
                    anchors.right:   parent.right
                    anchors.margins: 20
                    spacing: 16

                    Item { implicitHeight: 8 }

                    GroupBox {
                        Layout.fillWidth: true
                        title: "Defaults"
                        font.pixelSize: 12

                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 10

                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: "Default model"
                                    font.pixelSize: 12
                                    color: Material.foreground
                                    Layout.preferredWidth: 130
                                }
                                StyledComboBox {
                                    id:                     modelCombo
                                    font.pixelSize:         12
                                    Layout.fillWidth:       true
                                    Layout.preferredHeight: 32
                                    model: prefsController.modelOptions
                                    downloadStatus: prefsController.modelStatus
                                    onCurrentIndexChanged: prefsWin._dirty = true
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: "Output formats"
                                    font.pixelSize: 12
                                    color: Material.foreground
                                    Layout.preferredWidth: 130
                                    Layout.alignment: Qt.AlignTop
                                }
                                // Flow wraps onto a second line instead of overflowing/clipping
                                // when the window is narrow and all five checkboxes don't fit.
                                Flow {
                                    Layout.fillWidth: true
                                    spacing: 10
                                    CheckBox {
                                        id: srtCheck
                                        text: "SRT"
                                        font.pixelSize: 12
                                        onCheckedChanged: prefsWin._dirty = true
                                    }
                                    CheckBox {
                                        id: vttCheck
                                        text: "VTT"
                                        font.pixelSize: 12
                                        onCheckedChanged: prefsWin._dirty = true
                                    }
                                    CheckBox {
                                        id: lrcCheck
                                        text: "LRC"
                                        font.pixelSize: 12
                                        onCheckedChanged: prefsWin._dirty = true
                                    }
                                    CheckBox {
                                        id: assCheck
                                        text: "ASS"
                                        font.pixelSize: 12
                                        onCheckedChanged: prefsWin._dirty = true
                                    }
                                    CheckBox {
                                        id: sbvCheck
                                        text: "SBV"
                                        font.pixelSize: 12
                                        onCheckedChanged: prefsWin._dirty = true
                                    }
                                }
                            }
                        }
                    }

                    Item { implicitHeight: 4 }
                }
            }

            // ── Translation tab ────────────────────────────────────────────
            Flickable {
                contentHeight: translationCol.implicitHeight
                clip: true

                ColumnLayout {
                    id: translationCol
                    anchors.left:    parent.left
                    anchors.right:   parent.right
                    anchors.margins: 20
                    spacing: 16

                    Item { implicitHeight: 8 }

                    GroupBox {
                        Layout.fillWidth: true
                        title: "Defaults"
                        font.pixelSize: 12

                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 10

                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: "Translate by default"
                                    font.pixelSize: 12
                                    color: Material.foreground
                                    Layout.fillWidth: true
                                }
                                Switch {
                                    id: translateEnabledSwitch
                                    scale: 0.85  // qmllint disable missing-property
                                    onCheckedChanged: prefsWin._dirty = true
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                enabled: translateEnabledSwitch.checked
                                Text {
                                    text: "Target language"
                                    font.pixelSize: 12
                                    color: Material.foreground
                                    Layout.preferredWidth: 130
                                }
                                StyledComboBox {
                                    id:                     translateTargetCombo
                                    font.pixelSize:         12
                                    Layout.fillWidth:       true
                                    Layout.preferredHeight: 32
                                    model: prefsController.targetOptions.map(o => o.label)
                                    downloadStatus: prefsWin.targetDownloadStatus()
                                    onCurrentIndexChanged: prefsWin._dirty = true
                                }
                            }
                        }
                    }

                    Item { implicitHeight: 4 }
                }
            }

            // ── Transliteration tab ────────────────────────────────────────
            Flickable {
                contentHeight: translitCol.implicitHeight
                clip: true

                ColumnLayout {
                    id: translitCol
                    anchors.left:    parent.left
                    anchors.right:   parent.right
                    anchors.margins: 20
                    spacing: 16

                    Item { implicitHeight: 8 }

                    GroupBox {
                        Layout.fillWidth: true
                        title: "Defaults"
                        font.pixelSize: 12

                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 10

                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: "Transliterate by default"
                                    font.pixelSize: 12
                                    color: Material.foreground
                                    Layout.fillWidth: true
                                }
                                Switch {
                                    id: translitEnabledSwitch
                                    scale: 0.85  // qmllint disable missing-property
                                    onCheckedChanged: prefsWin._dirty = true
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                enabled: translitEnabledSwitch.checked
                                spacing: 6
                                Text {
                                    text: "Scheme"
                                    font.pixelSize: 12
                                    color: Material.foreground
                                    Layout.preferredWidth: 130
                                }
                                StyledComboBox {
                                    id: translitSourceCombo
                                    font.pixelSize:         12
                                    Layout.fillWidth:       true
                                    Layout.preferredHeight: 32
                                    model: prefsController.translitSchemeOptions.map(o => o.label)
                                    onCurrentIndexChanged: prefsWin._dirty = true
                                }
                                Text {
                                    text: "→"
                                    font.pixelSize: 12
                                    color: Material.foreground
                                }
                                StyledComboBox {
                                    id: translitTargetCombo
                                    font.pixelSize:         12
                                    Layout.fillWidth:       true
                                    Layout.preferredHeight: 32
                                    model: prefsController.translitSchemeOptions.map(o => o.label)
                                    onCurrentIndexChanged: prefsWin._dirty = true
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                enabled: translitEnabledSwitch.checked
                                Text {
                                    text: "Transliterate from"
                                    font.pixelSize: 12
                                    color: Material.foreground
                                    Layout.preferredWidth: 130
                                }
                                StyledComboBox {
                                    id:                     translitInputCombo
                                    font.pixelSize:         12
                                    Layout.fillWidth:       true
                                    Layout.preferredHeight: 32
                                    model: ["Transcription", "Translation"]
                                    onCurrentIndexChanged: prefsWin._dirty = true
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                enabled: translitEnabledSwitch.checked
                                Text {
                                    text: "Engine"
                                    font.pixelSize: 12
                                    color: Material.foreground
                                    Layout.preferredWidth: 130
                                }
                                StyledComboBox {
                                    id:                     translitEngineCombo
                                    font.pixelSize:         12
                                    Layout.fillWidth:       true
                                    Layout.preferredHeight: 32
                                    model: prefsController.translitEngineOptions.map(o => o.label)
                                    downloadStatus: prefsWin.engineDownloadStatus()
                                    onCurrentIndexChanged: prefsWin._dirty = true
                                }
                            }

                            Text {
                                text: "Neural gives more natural results but downloads a larger model on first use."
                                font.pixelSize: 11
                                wrapMode: Text.WordWrap
                                color: appController.colorTextSecondary
                                Layout.fillWidth: true
                            }
                        }
                    }

                    Item { implicitHeight: 4 }
                }
            }

            // ── Advanced tab ──────────────────────────────────────────────
            Flickable {
                contentHeight: advCol.implicitHeight
                clip: true

                ColumnLayout {
                    id: advCol
                    anchors.left:    parent.left
                    anchors.right:   parent.right
                    anchors.margins: 20
                    spacing: 16

                    Item { implicitHeight: 8 }

                    GroupBox {
                        Layout.fillWidth: true
                        title: "Logging"
                        font.pixelSize: 12

                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 10

                            CheckBox {
                                id: enableLogsCheck
                                text: "Enable logging"
                                font.pixelSize: 12
                                onCheckedChanged: prefsWin._dirty = true
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                enabled: enableLogsCheck.checked

                                Text {
                                    text: "Log level"
                                    font.pixelSize: 12
                                    color: Material.foreground
                                    Layout.preferredWidth: 130
                                }
                                StyledComboBox {
                                    id:                     logLevelCombo
                                    font.pixelSize:         12
                                    Layout.fillWidth:       true
                                    Layout.preferredHeight: 32
                                    model: ["Critical (silent)", "All (verbose)"]
                                    onCurrentIndexChanged: prefsWin._dirty = true
                                }
                            }

                            Button {
                                text: "Clear Logs"
                                flat: true
                                font.pixelSize: 11
                                Material.foreground: appController.colorDanger
                                onClicked: appController.clearLogs()
                            }
                        }
                    }

                    Item { implicitHeight: 4 }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 1
            color: appController.colorDivider
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.margins: 16
            spacing: 10

            Button {
                text: "Reset to Defaults"
                flat: true
                font.pixelSize: 12
                Layout.preferredHeight: 36
                Material.foreground: appController.colorDanger
                onClicked: prefsController.resetDefaults()
            }
            Item { Layout.fillWidth: true }
            Button {
                text: "Cancel"
                font.pixelSize: 12
                Layout.preferredHeight: 36
                onClicked: prefsWin.close()
            }
            Button {
                text: "Save"
                highlighted: true
                font.pixelSize: 12
                Layout.preferredHeight: 36
                onClicked: { prefsWin.applyValues(); prefsWin.close() }
            }
        }
    }

    function loadValues() {
        try {
            var themeMap = { "system": 0, "light": 1, "dark": 2 }
            themeCombo.currentIndex = themeMap[prefsController.theme] ?? 0
            var models = prefsController.modelOptions
            var defaultIdx = models.indexOf(prefsController.defaultModel)
            modelCombo.currentIndex = defaultIdx >= 0 ? defaultIdx : 0
            enableLogsCheck.checked = prefsController.enableLogs
            logLevelCombo.currentIndex = prefsController.logLevel === "all" ? 1 : 0
            srtCheck.checked = prefsController.defaultEmitSrt
            vttCheck.checked = prefsController.defaultEmitVtt
            lrcCheck.checked = prefsController.defaultEmitLrc
            assCheck.checked = prefsController.defaultEmitAss
            sbvCheck.checked = prefsController.defaultEmitSbv

            translateEnabledSwitch.checked = prefsController.defaultTranslateEnabled
            translateTargetCombo.currentIndex = indexByCode(
                prefsController.targetOptions, prefsController.defaultTranslateTarget, 0)

            translitEnabledSwitch.checked = prefsController.defaultTransliterateEnabled
            translitSourceCombo.currentIndex = indexByCode(
                prefsController.translitSchemeOptions, prefsController.defaultTranslitSource, 0)
            translitTargetCombo.currentIndex = indexByCode(
                prefsController.translitSchemeOptions, prefsController.defaultTranslitTarget, 1)
            translitInputCombo.currentIndex = prefsController.defaultTranslitInput === "translation" ? 1 : 0
            translitEngineCombo.currentIndex = indexByCode(
                prefsController.translitEngineOptions, prefsController.defaultTranslitEngine, 0)

            prefsWin._dirty = false
        } catch(e) {}
    }

    function indexByCode(options, code, fallback) {
        for (var i = 0; i < options.length; i++)
            if (options[i].code === code) return i
        return fallback
    }

    // Downloaded/needs-download indicator maps, keyed by the label shown in each combo box.
    // Source language is unknown here (no default source-language setting), so translation
    // readiness is checked without a fixed source, same as the main window's Auto-detect case.
    function targetDownloadStatus() {
        var status = {}
        var opts = prefsController.targetOptions
        for (var i = 0; i < opts.length; i++)
            status[opts[i].label] = prefsController.isTranslationReady("", opts[i].code)
        return status
    }

    function engineDownloadStatus() {
        var status = {}
        var opts = prefsController.translitEngineOptions
        var schemes = prefsController.translitSchemeOptions
        var source = schemes[translitSourceCombo.currentIndex] ? schemes[translitSourceCombo.currentIndex].code : ""
        var target = schemes[translitTargetCombo.currentIndex] ? schemes[translitTargetCombo.currentIndex].code : ""
        for (var i = 0; i < opts.length; i++) {
            status[opts[i].label] = opts[i].code === "neural"
                ? prefsController.isNeuralReady(source, target)
                : true
        }
        return status
    }

    function applyValues() {
        try {
            var themeValues = ["system", "light", "dark"]
            var chosenTheme = themeValues[themeCombo.currentIndex]
            prefsController.setSetting("ui.theme", chosenTheme)
            prefsController.setSetting("model.name", prefsController.modelOptions[modelCombo.currentIndex])
            prefsController.setSetting("logging.enable_logs", enableLogsCheck.checked)
            prefsController.setSetting("logging.log_level", logLevelCombo.currentIndex === 1 ? "all" : "critical")
            prefsController.setSetting("output.srt", srtCheck.checked)
            prefsController.setSetting("output.vtt", vttCheck.checked)
            prefsController.setSetting("output.lrc", lrcCheck.checked)
            prefsController.setSetting("output.ass", assCheck.checked)
            prefsController.setSetting("output.sbv", sbvCheck.checked)

            prefsController.setSetting("translation.enabled", translateEnabledSwitch.checked)
            prefsController.setSetting(
                "translation.target_lang",
                prefsController.targetOptions[translateTargetCombo.currentIndex].code)

            prefsController.setSetting("transliteration.enabled", translitEnabledSwitch.checked)
            prefsController.setSetting(
                "transliteration.source",
                prefsController.translitSchemeOptions[translitSourceCombo.currentIndex].code)
            prefsController.setSetting(
                "transliteration.target",
                prefsController.translitSchemeOptions[translitTargetCombo.currentIndex].code)
            prefsController.setSetting(
                "transliteration.input_source",
                translitInputCombo.currentIndex === 1 ? "translation" : "transcription")
            prefsController.setSetting(
                "transliteration.engine",
                prefsController.translitEngineOptions[translitEngineCombo.currentIndex].code)

            appController.applyTheme(chosenTheme)
            prefsWin._dirty = false
        } catch(e) {}
    }
}
