// qmllint disable unqualified
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

// The Workflow tab's step list: steps run top to bottom on every queued file, and each one
// says which text it uses. Steps can be added, reordered, and removed.
ColumnLayout {
    id: editor

    spacing: Theme.spaceLg

    Text {
        Layout.fillWidth: true
        text: "Steps run in order on every queued file. Each step uses the queued file or the text of an earlier step."
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontCaption
        color: Theme.textMuted
        wrapMode: Text.WordWrap
    }

    Repeater {
        model: workflowController.steps
        delegate: WorkflowStepCard {
            stepCount: workflowController.steps.count
            onOptionChanged: (key, value) => workflowController.setStepOption(index, key, value)
            onMoveRequested: target => workflowController.moveStep(index, target)
            onRemoveRequested: workflowController.removeStep(index)
        }
    }

    Text {
        Layout.fillWidth: true
        visible: workflowController.steps.count === 0
        horizontalAlignment: Text.AlignHCenter
        text: "No steps yet. Add the first one below."
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontBody
        color: Theme.textMuted
    }

    AppButton {
        id: addButton
        kind: "primary"
        text: "Add step"
        iconName: "add"
        toolTipText: "Add a step to the end of the workflow"
        onClicked: addMenu.popup(addButton, 0, addButton.height)

        Menu {
            id: addMenu
            Repeater {
                model: workflowController.stepKinds
                delegate: MenuItem {
                    required property var modelData
                    text: modelData.label
                    onTriggered: workflowController.addStep(modelData.kind)
                }
            }
        }
    }
}
