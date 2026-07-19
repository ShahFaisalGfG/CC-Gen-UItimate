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

    function labelFor(data) {
        var value = data ?? ""
        var known = control.downloadStatus[value]
        if (known === undefined) return value
        return value + (known ? "  ✓" : "  ⬇")
    }

    // The popup defaults to at least the control's own (often fillWidth-stretched) width,
    // leaving a wide empty gutter when every entry is much shorter than the closed control -
    // measuring the longest label makes the popup hug its content instead.
    FontMetrics {
        id: _fm
        font: control.font
    }

    function _maxLabelWidth() {
        var max = 0
        for (var i = 0; i < control.count; i++) {
            var w = _fm.boundingRect(control.labelFor(control.textAt(i))).width
            if (w > max) max = w
        }
        return max
    }

    delegate: ItemDelegate {
        required property var modelData
        required property int index

        width:       control.popup.width
        height:      32
        text:        control.labelFor(modelData)
        font.pixelSize: 12
        highlighted: control.highlightedIndex === index
    }

    popup.contentItem: ListView {
        clip:          true
        implicitHeight: Math.min(contentHeight, 260)
        model:         control.delegateModel
        currentIndex:  control.highlightedIndex
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
    }

    popup.width: Math.max(control._maxLabelWidth() + 48, 80)
}
