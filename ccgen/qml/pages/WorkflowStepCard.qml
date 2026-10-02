// qmllint disable unqualified
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import "../components"

// One workflow step: what it reads, whether its files are kept, and its own options.
Card {
    id: card

    required property int index
    required property string kind
    required property string stepTitle
    required property var options
    required property var inputs
    property int stepCount: 0

    signal optionChanged(string key, var value)
    signal moveRequested(int target)
    signal removeRequested()

    readonly property var _icons: ({ generate: "mic", translate: "globe", transliterate: "characters", dub: "speaker" })

    Layout.fillWidth: true
    title: "Step " + (card.index + 1) + ": " + card.stepTitle
    iconName: card._icons[card.kind] || "page"
    Accessible.name: card.stepTitle

    trailing: [
        AppButton {
            kind: "ghost"
            compact: true
            iconName: "arrowUp"
            enabled: card.index > 0
            toolTipText: "Move this step up"
            Accessible.name: "Move step " + (card.index + 1) + " up"
            onClicked: card.moveRequested(card.index - 1)
        },
        AppButton {
            kind: "ghost"
            compact: true
            iconName: "arrowDown"
            enabled: card.index < card.stepCount - 1
            toolTipText: "Move this step down"
            Accessible.name: "Move step " + (card.index + 1) + " down"
            onClicked: card.moveRequested(card.index + 1)
        },
        AppButton {
            kind: "ghost"
            compact: true
            iconName: "delete"
            toolTipText: "Remove this step"
            Accessible.name: "Remove step " + (card.index + 1)
            onClicked: card.removeRequested()
        }
    ]

    FormRow {
        label: "Uses"
        visible: card.kind !== "generate"
        hint: "The queued file must be a subtitle file to be used directly."
        StyledComboBox {
            Layout.fillWidth: true
            accessibleName: "Step input"
            toolTipText: "Which text this step works on: the queued file or an earlier step."
            model: card.inputs
            value: card.options.input
            onActivated: card.optionChanged("input", currentValue)
        }
    }

    FormRow {
        label: "Save its subtitles"
        visible: card.kind !== "dub"
        hint: "Turn off to only pass the text on to later steps."
        AppSwitch {
            checked: !!card.options.write_output
            onToggled: card.optionChanged("write_output", checked)
            accessibleName: "Save this step's subtitles"
            toolTipText: "Write this step's subtitle files, or only hand its text to later steps."
        }
        Item { Layout.fillWidth: true }
    }

    Loader {
        Layout.fillWidth: true
        sourceComponent: card.kind === "generate" ? generateOptions
            : card.kind === "translate" ? translateOptions
            : card.kind === "transliterate" ? transliterateOptions : dubOptions
    }

    Component {
        id: generateOptions
        GenerateSettings {
            options: card.options
            onOptionChanged: (key, value) => card.optionChanged(key, value)
        }
    }
    Component {
        id: translateOptions
        TranslateSettings {
            options: card.options
            detectHint: "Detect uses the language of the step it reads, such as the language a transcript was spoken in."
            onOptionChanged: (key, value) => card.optionChanged(key, value)
        }
    }
    Component {
        id: transliterateOptions
        TransliterateSettings {
            options: card.options
            onOptionChanged: (key, value) => card.optionChanged(key, value)
        }
    }
    Component {
        id: dubOptions
        DubSettings {
            options: card.options
            onOptionChanged: (key, value) => card.optionChanged(key, value)
        }
    }
}
