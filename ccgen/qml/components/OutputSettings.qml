// qmllint disable unqualified
import QtQuick
import QtQuick.Dialogs
import QtQuick.Layouts

// Where results are saved, plus the subtitle formats for tabs that write subtitles.
// `options` holds formats and output_dir; edits come back through the two signals.
Card {
    id: card

    property var options: ({})
    property bool showFormats: true
    property string namingExample: "movie.srt"

    signal optionChanged(string key, var value)
    signal formatToggled(string code, bool enabled)

    readonly property var _formats: card.options.formats || []
    readonly property string _folder: card.options.output_dir || ""

    title: "Output"
    description: "Files are named after the source, e.g. " + card.namingExample + "."
    iconName: "page"

    FolderDialog {
        id: folderPicker
        title: "Choose where results are saved"
        onAccepted: card.optionChanged("output_dir", selectedFolder.toString())
    }

    FormRow {
        label: "Formats"
        hint: card._formats.length > 0 ? "" : "Select at least one format."
        visible: card.showFormats
        Flow {
            Layout.fillWidth: true
            spacing: Theme.spaceSm
            Repeater {
                model: [
                    { code: "srt", label: "SRT", info: "SubRip, works almost everywhere" },
                    { code: "vtt", label: "VTT", info: "WebVTT, for web players and HTML5 video" },
                    { code: "ass", label: "ASS", info: "Advanced SubStation Alpha, styled subtitles" },
                    { code: "sbv", label: "SBV", info: "YouTube subtitle format" },
                    { code: "lrc", label: "LRC", info: "Lyrics format, start times only" }
                ]
                delegate: FormatChip {
                    required property var modelData
                    text: modelData.label
                    description: modelData.info
                    checked: card._formats.indexOf(modelData.code) >= 0
                    onToggled: card.formatToggled(modelData.code, checked)
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
                text: card._folder || "Same folder as each source file"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBody
                color: card._folder ? Theme.text : Theme.textMuted
                elide: Text.ElideMiddle
                Accessible.role: Accessible.StaticText
                Accessible.name: "Save to: " + text
            }
        }
        AppButton {
            text: "Browse..."
            toolTipText: "Choose one folder for every result"
            onClicked: folderPicker.open()
        }
        AppButton {
            kind: "ghost"
            iconName: "cancel"
            toolTipText: "Save next to each source file instead"
            visible: card._folder.length > 0
            onClicked: card.optionChanged("output_dir", "")
        }
    }
}
