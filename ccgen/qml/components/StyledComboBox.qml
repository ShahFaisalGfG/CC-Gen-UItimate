// qmllint disable unqualified import
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material

ComboBox {
    id: control

    font.pixelSize: 12

    // Optional map of {itemText: bool} - when an entry exists for a row, a small
    // ready/needs-download glyph is appended to that row's label in the popup list.
    property var downloadStatus: ({})

    delegate: ItemDelegate {
        required property var modelData
        required property int index

        width:       control.popup.width
        height:      32
        text:        labelFor(modelData)
        font.pixelSize: 12
        highlighted: control.highlightedIndex === index

        function labelFor(data) {
            var value = data ?? ""
            var known = control.downloadStatus[value]
            if (known === undefined) return value
            return value + (known ? "  ✓" : "  ⬇")
        }
    }

    popup.contentItem: ListView {
        clip:          true
        implicitHeight: Math.min(contentHeight, 260)
        model:         control.delegateModel
        currentIndex:  control.highlightedIndex
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
    }

    popup.width: Math.max(width, implicitWidth)
}
