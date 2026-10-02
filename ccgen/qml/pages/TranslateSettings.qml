// qmllint disable unqualified
import QtQuick
import QtQuick.Layouts
import "../components"

// Translation options for the Translate tab and translate workflow steps.
ColumnLayout {
    id: root

    property var options: ({})
    // In a workflow, "Detect" means the language the input step produced.
    property string detectHint: "Detect reads the language from names like movie_en.srt, or from the tab the file came from."
    signal optionChanged(string key, var value)

    spacing: Theme.spaceLg

    // A target is ready when every package its route needs (both legs through English) is downloaded.
    function translationReadiness(readiness, source) {
        var result = {}
        var targets = prefsController.targetOptions
        for (var i = 0; i < targets.length; i++) {
            var ids = modelsController.translationAssetIds(source, targets[i].code)
            if (ids.length === 0) continue
            result[targets[i].code] = ids.every(id => readiness[id] === true)
        }
        return result
    }

    Card {
        Layout.fillWidth: true
        title: "Translation"
        description: "Translates whole sentences offline. English bridges other language pairs."
        iconName: "globe"

        FormRow {
            label: "Translate from"
            hint: root.options.source_lang === "auto" ? root.detectHint : ""
            StyledComboBox {
                Layout.fillWidth: true
                accessibleName: "Translate from"
                toolTipText: "Language the subtitles are written in."
                model: prefsController.sourceOptions
                value: root.options.source_lang
                onActivated: root.optionChanged("source_lang", currentValue)
            }
        }

        FormRow {
            label: "Translate to"
            hint: root.options.source_lang !== "auto" && root.options.source_lang === root.options.target_lang
                ? "Choose a language different from the source." : ""
            StyledComboBox {
                Layout.fillWidth: true
                accessibleName: "Translate to"
                toolTipText: "Language the subtitles are translated into, e.g. movie_ur.srt."
                model: prefsController.targetOptions
                value: root.options.target_lang
                readiness: root.translationReadiness(modelsController.readiness, root.options.source_lang)
                onActivated: root.optionChanged("target_lang", currentValue)
            }
        }
    }
}
