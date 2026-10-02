import QtQuick
import QtQuick.Controls

// A toggle chip for picking output formats. Behaves as a checkbox for keyboard (Space) and
// screen readers, and shows its state with a check mark, not color alone.
AbstractButton {
    id: chip

    property string description: ""

    checkable: true
    focusPolicy: Qt.StrongFocus
    hoverEnabled: true
    implicitHeight: 30
    implicitWidth: label.implicitWidth + (chip.checked ? 34 : 24)

    Accessible.role: Accessible.CheckBox
    Accessible.name: chip.text
    Accessible.description: chip.description
    Accessible.checkable: true
    Accessible.checked: chip.checked

    ToolTip.visible: chip.description.length > 0 && chip.hovered
    ToolTip.text: chip.description
    ToolTip.delay: 600

    contentItem: Row {
        spacing: 4
        leftPadding: 12
        Icon {
            anchors.verticalCenter: parent.verticalCenter
            visible: chip.checked
            name: "check"
            size: 11
            color: Theme.accent
        }
        Text {
            id: label
            anchors.verticalCenter: parent.verticalCenter
            text: chip.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontBody
            font.weight: chip.checked ? Font.DemiBold : Font.Normal
            color: chip.checked ? Theme.accent : Theme.text
            Accessible.ignored: true
        }
    }

    background: Rectangle {
        radius: height / 2
        color: chip.checked ? Theme.accentSoft : (chip.hovered ? Theme.surfaceHover : Theme.surface)
        border.width: chip.visualFocus ? 2 : 1
        border.color: chip.visualFocus ? Theme.focusRing : (chip.checked ? Theme.accent : Theme.border)
    }
}
