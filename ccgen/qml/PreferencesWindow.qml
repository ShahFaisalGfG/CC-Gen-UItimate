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
        color: Material.theme === Material.Dark ? "#1e1e1e" : "#f3f3f3"
        border.color: Material.theme === Material.Dark ? "#3c3c3c" : "#c8c8c8"
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
            Material.accent: "#0078d4"

            TabButton { text: "Appearance";    font.pixelSize: 12; implicitHeight: 44 }
            TabButton { text: "Transcription"; font.pixelSize: 12; implicitHeight: 44 }
            TabButton { text: "Advanced";      font.pixelSize: 12; implicitHeight: 44 }
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
                                Layout.preferredHeight: 34
                                font.pixelSize:         12
                                model: ["System (auto)", "Light", "Dark"]
                                onCurrentIndexChanged: prefsWin._dirty = true
                            }
                            Text {
                                text: "System follows your Windows light/dark setting."
                                font.pixelSize: 11
                                wrapMode: Text.WordWrap
                                color: Material.theme === Material.Dark ? "#888888" : "#777777"
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
                                    Layout.fillWidth: true
                                }
                                StyledComboBox {
                                    id:                     modelCombo
                                    font.pixelSize:         12
                                    Layout.preferredWidth:  120
                                    Layout.preferredHeight: 34
                                    model: prefsController.modelOptions
                                    onCurrentIndexChanged: prefsWin._dirty = true
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: "Output formats"
                                    font.pixelSize: 12
                                    color: Material.foreground
                                    Layout.fillWidth: true
                                }
                                Row {
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
                                }
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
                                    Layout.fillWidth: true
                                }
                                StyledComboBox {
                                    id:                     logLevelCombo
                                    font.pixelSize:         12
                                    Layout.preferredWidth:  130
                                    Layout.preferredHeight: 34
                                    model: ["Critical (silent)", "All (verbose)"]
                                    onCurrentIndexChanged: prefsWin._dirty = true
                                }
                            }

                            Button {
                                text: "Clear Logs"
                                flat: true
                                font.pixelSize: 11
                                Material.foreground: "#e0004f"
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
            color: Material.theme === Material.Dark ? "#3c3c3c" : "#e0e0e0"
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.margins: 16
            spacing: 10

            Button {
                text: "Reset to Defaults"
                flat: true
                font.pixelSize: 12
                Layout.preferredHeight: 40
                Material.foreground: "#e0004f"
                onClicked: {
                    prefsController.resetDefaults()
                    prefsWin.loadValues()
                    prefsWin._dirty = false
                }
            }
            Item { Layout.fillWidth: true }
            Button {
                text: "Cancel"
                font.pixelSize: 12
                Layout.preferredHeight: 40
                onClicked: prefsWin.close()
            }
            Button {
                text: "Save"
                highlighted: true
                font.pixelSize: 12
                Layout.preferredHeight: 40
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
            srtCheck.checked = true
            vttCheck.checked = false
            prefsWin._dirty = false
        } catch(e) {}
    }

    function applyValues() {
        try {
            var themeValues = ["system", "light", "dark"]
            var chosenTheme = themeValues[themeCombo.currentIndex]
            prefsController.setSetting("ui.theme", chosenTheme)
            prefsController.setSetting("model.name", prefsController.modelOptions[modelCombo.currentIndex])
            prefsController.setSetting("logging.enable_logs", enableLogsCheck.checked)
            prefsController.setSetting("logging.log_level", logLevelCombo.currentIndex === 1 ? "all" : "critical")
            appController.applyTheme(chosenTheme)
            prefsWin._dirty = false
        } catch(e) {}
    }
}
