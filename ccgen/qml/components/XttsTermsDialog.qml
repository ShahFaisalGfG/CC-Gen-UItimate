// qmllint disable unqualified
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// One-time notice for the XTTS-v2 voice cloning model's licence (Coqui Public Model License).
// Accepting is saved in preferences; `accepted()` lets the caller continue what it started.
Dialog {
    id: dialog

    signal accepted()

    title: "XTTS-v2 licence"
    modal: true
    anchors.centerIn: parent
    width: Math.min(520, parent ? parent.width - 48 : 520)
    standardButtons: Dialog.Cancel

    onOpened: acceptButton.forceActiveFocus()

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spaceMd

        Text {
            Layout.fillWidth: true
            text: "Voice cloning uses the XTTS-v2 model by Coqui, released under the Coqui Public Model "
                + "License. It allows personal, research, and other non-commercial use of the model and "
                + "of the audio it creates. Commercial use needs a separate licence."
            wrapMode: Text.WordWrap
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontBody
            color: Theme.text
        }
        Text {
            Layout.fillWidth: true
            text: "Only clone voices you have permission to use. Kokoro and Piper voices have no such limits."
            wrapMode: Text.WordWrap
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontCaption
            color: Theme.textMuted
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm
            AppButton {
                kind: "ghost"
                text: "Read the licence"
                iconName: "openExternal"
                toolTipText: "Open coqui.ai/cpml in your browser"
                onClicked: Qt.openUrlExternally("https://coqui.ai/cpml")
            }
            Item { Layout.fillWidth: true }
            AppButton {
                id: acceptButton
                kind: "primary"
                text: "I agree"
                toolTipText: "Accept the licence and continue"
                onClicked: {
                    prefsController.saveSettings({ "dubbing.xtts_terms_accepted": true })
                    dialog.close()
                    dialog.accepted()
                }
            }
        }
    }
}
