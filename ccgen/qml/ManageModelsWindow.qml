// qmllint disable unqualified
import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtQuick.Window
import "components"

ApplicationWindow {
    id: manageWin

    width: 820
    height: 740
    minimumWidth: 720
    minimumHeight: 580
    title: "Manage Models"
    flags: Qt.FramelessWindowHint | Qt.Window
    modality: Qt.ApplicationModal

    Material.theme: appController && appController.currentTheme === "dark" ? Material.Dark : Material.Light
    Material.accent: "#0078d4"
    Overlay.modal: Rectangle { color: "#99000000" }

    // Per-asset-id live download state (queued/downloading + progress), kept outside the
    // flat catalog snapshot so a refresh triggered by ONE finished download doesn't wipe the
    // "Queued…" indicator off every OTHER item still waiting in the backend's FIFO queue.
    property var pendingState: ({})
    // Flat, merged (catalog + pendingState) snapshot rebuilt on every relevant event; every
    // tab/engine-group view below is just a filtered read of this one list.
    property var catalog: []
    property real totalBytes: 0

    Component.onCompleted: {
        x = Screen.virtualX + Math.round((Screen.desktopAvailableWidth  - width)  / 2)
        y = Screen.virtualY + Math.round((Screen.desktopAvailableHeight - height) / 2)
        rebuild()
    }

    onClosing: manageWin.destroy()

    Connections {
        target: modelsController
        function onAssetsChanged() { manageWin.rebuild() }
        function onAssetQueued(id) {
            manageWin.pendingState[id] = {
                downloadState: "queued", progressDone: 0, progressTotal: 0, statusMessage: "",
            }
            manageWin.rebuild()
        }
        function onAssetStatus(id, message) {
            // A status message is proof the worker has actually started on this asset, even
            // when no byte-progress ticks ever arrive (some download paths report late or
            // not at all) - so it also clears "queued" the same way a real progress tick would.
            var pending = manageWin.pendingState[id]
            if (pending) {
                pending.statusMessage = message
                pending.downloadState = "downloading"
            }
            manageWin.rebuild()
        }
        function onAssetProgress(id, done, total) {
            manageWin.pendingState[id] = {
                downloadState: "downloading", progressDone: done, progressTotal: total, statusMessage: "",
            }
            manageWin.rebuild()
        }
        function onAssetFinished(id, success, error) {
            delete manageWin.pendingState[id]
            if (!success && error !== "Cancelled") {
                errorBanner.text = "Download failed: " + error
                errorBanner.visible = true
            }
            // The controller's own refreshAssets() call (made after every finished event)
            // triggers onAssetsChanged shortly after, rebuilding with the real
            // downloaded/size state; rebuild() here avoids a stale progress row in the meantime.
            manageWin.rebuild()
        }
    }

    function rebuild() {
        var list = modelsController.assets
        var rows = []
        var total = 0
        for (var i = 0; i < list.length; i++) {
            var a = list[i]
            var pending = manageWin.pendingState[a.id]
            rows.push({
                id: a.id, category: a.category, engine: a.engine, label: a.label,
                downloaded: a.downloaded, sizeBytes: a.size_bytes || 0,
                approxSizeMb: a.approx_size_mb || 0,
                downloadState: pending ? pending.downloadState : "idle",
                progressDone: pending ? pending.progressDone : 0,
                progressTotal: pending ? pending.progressTotal : 0,
                statusMessage: pending ? pending.statusMessage : "",
            })
            if (a.downloaded) total += a.size_bytes || 0
        }
        manageWin.catalog = rows
        manageWin.totalBytes = total
    }

    function rowsFor(category, engine) {
        return manageWin.catalog.filter(r => r.category === category && r.engine === engine)
    }

    function enginesIn(category) {
        var seen = []
        for (var i = 0; i < manageWin.catalog.length; i++) {
            var r = manageWin.catalog[i]
            if (r.category === category && seen.indexOf(r.engine) < 0) seen.push(r.engine)
        }
        return seen
    }

    function statsFor(category, engine) {
        var rows = manageWin.rowsFor(category, engine)
        return { downloaded: rows.filter(r => r.downloaded).length, total: rows.length }
    }

    function downloadAllInGroup(category, engine) {
        var rows = manageWin.rowsFor(category, engine)
        for (var i = 0; i < rows.length; i++) {
            if (!rows[i].downloaded && rows[i].downloadState === "idle")
                modelsController.downloadAsset(rows[i].id)
        }
    }

    function removeAllInGroup(category, engine) {
        var rows = manageWin.rowsFor(category, engine)
        for (var i = 0; i < rows.length; i++) {
            if (rows[i].downloaded) modelsController.removeAsset(rows[i].id)
        }
    }

    function removeAllDownloaded() {
        for (var i = 0; i < manageWin.catalog.length; i++) {
            if (manageWin.catalog[i].downloaded) modelsController.removeAsset(manageWin.catalog[i].id)
        }
    }

    function cancelDownload(id) {
        modelsController.cancelAsset(id)
        delete manageWin.pendingState[id]
        manageWin.rebuild()
    }

    function formatBytes(bytes) {
        if (!bytes || bytes <= 0) return "—"
        var units = ["B", "KB", "MB", "GB"]
        var value = bytes
        var unitIndex = 0
        while (value >= 1024 && unitIndex < units.length - 1) {
            value /= 1024
            unitIndex++
        }
        return value.toFixed(value >= 10 || unitIndex === 0 ? 0 : 1) + " " + units[unitIndex]
    }

    // One asset row's action area is exactly one of these four states at a time; declaring
    // them as Loader-swapped Components (instead of four always-present sibling items toggled
    // by `visible`) keeps the invisible ones from still reserving layout space, which is what
    // made the progress row render inset from the flush-right edge every other state uses.
    Component {
        id: idleActionComp
        Button {
            property string rowId: ""
            text: "⬇  Download"
            flat: true
            font.pixelSize: 12
            onClicked: modelsController.downloadAsset(rowId)
        }
    }

    Component {
        id: downloadedActionComp
        RowLayout {
            property string rowId: ""
            spacing: 8
            Text {
                text: "✓ Downloaded"
                font.pixelSize: 12
                color: appController.colorSuccess
            }
            Button {
                text: "Remove"
                flat: true
                font.pixelSize: 12
                Material.foreground: appController.colorDanger
                onClicked: modelsController.removeAsset(parent.rowId)
            }
        }
    }

    Component {
        id: queuedActionComp
        RowLayout {
            property string rowId: ""
            spacing: 8
            Text {
                text: "Queued…"
                font.pixelSize: 12
                color: appController.colorTextSecondary
            }
            Button {
                text: "✕"
                flat: true
                font.pixelSize: 12
                implicitWidth: 28
                Material.foreground: appController.colorDanger
                onClicked: manageWin.cancelDownload(parent.rowId)
            }
        }
    }

    Component {
        id: downloadingActionComp
        RowLayout {
            property string rowId: ""
            property int progressDone: 0
            property int progressTotal: 0
            property string statusMessage: ""
            property int approxSizeMb: 0
            spacing: 8
            Layout.preferredWidth: 250

            // The static known size is a stable denominator - the live backend total can
            // reset upward mid-download (a multi-file repo's aggregate total grows as each
            // new file joins), which made the percentage look like it was jumping around.
            readonly property real approxTotalBytes: approxSizeMb > 0 ? approxSizeMb * 1024 * 1024 : 0
            readonly property real effectiveTotal: approxTotalBytes > 0 ? approxTotalBytes : progressTotal

            ProgressBar {
                Layout.preferredWidth: 100
                from: 0
                to: parent.effectiveTotal > 0 ? parent.effectiveTotal : 1
                value: parent.effectiveTotal > 0 ? Math.min(parent.progressDone, parent.effectiveTotal) : 0
                indeterminate: parent.effectiveTotal === 0 || parent.statusMessage.length > 0
            }
            Text {
                text: parent.statusMessage.length > 0
                    ? parent.statusMessage
                    : (parent.effectiveTotal > 0
                        ? Math.min(100, Math.round(100 * parent.progressDone / parent.effectiveTotal)) + "%"
                        : "")
                font.pixelSize: 12
                elide: Text.ElideRight
                Layout.fillWidth: true
                color: appController.colorTextSecondary
            }
            Button {
                text: "✕"
                flat: true
                font.pixelSize: 12
                implicitWidth: 28
                Material.foreground: appController.colorDanger
                onClicked: manageWin.cancelDownload(parent.rowId)
            }
        }
    }

    // One catalog row: label, size, and the state-driven action area above.
    Component {
        id: assetRowComp

        Item {
            id: rowRoot
            required property string id
            required property string label
            required property bool downloaded
            required property real sizeBytes
            required property int approxSizeMb
            required property string downloadState
            required property int progressDone
            required property int progressTotal
            required property string statusMessage

            Layout.fillWidth: true
            implicitHeight: 52

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin:  12
                anchors.rightMargin: 12
                spacing: 10

                Text {
                    text: rowRoot.label
                    font.pixelSize: 13
                    color: Material.foreground
                    Layout.preferredWidth: 220
                    elide: Text.ElideRight
                }

                Text {
                    text: rowRoot.downloaded
                        ? manageWin.formatBytes(rowRoot.sizeBytes)
                        : (rowRoot.approxSizeMb > 0
                            ? "~" + manageWin.formatBytes(rowRoot.approxSizeMb * 1024 * 1024)
                            : "—")
                    font.pixelSize: 12
                    color: appController.colorTextSecondary
                    Layout.preferredWidth: 70
                }

                Item { Layout.fillWidth: true }

                Loader {
                    Layout.alignment: Qt.AlignRight
                    sourceComponent: {
                        if (rowRoot.downloadState === "downloading") return downloadingActionComp
                        if (rowRoot.downloadState === "queued") return queuedActionComp
                        if (rowRoot.downloaded) return downloadedActionComp
                        return idleActionComp
                    }
                    onLoaded: {
                        if (item.hasOwnProperty("rowId")) item.rowId = rowRoot.id
                        if (item.hasOwnProperty("progressDone")) {
                            item.progressDone    = rowRoot.progressDone
                            item.progressTotal   = rowRoot.progressTotal
                            item.statusMessage   = rowRoot.statusMessage
                            item.approxSizeMb    = rowRoot.approxSizeMb
                        }
                    }
                }
            }

            Rectangle {
                anchors.bottom: parent.bottom
                anchors.left:   parent.left
                anchors.right:  parent.right
                height: 1
                color: appController.colorDivider
            }
        }
    }

    // One engine group within a category tab: a titled GroupBox with bulk actions plus a
    // Repeater of asset rows for that (category, engine) pair.
    Component {
        id: engineGroupComp

        GroupBox {
            id: groupRoot
            required property string category
            required property string engineName

            Layout.fillWidth: true
            title: engineName
            font.pixelSize: 12

            ColumnLayout {
                anchors.fill: parent
                spacing: 4

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: {
                            var s = manageWin.statsFor(groupRoot.category, groupRoot.engineName)
                            return s.downloaded + " of " + s.total + " downloaded"
                        }
                        font.pixelSize: 12
                        color: appController.colorTextSecondary
                        Layout.fillWidth: true
                    }
                    Button {
                        text: "Download All"
                        flat: true
                        font.pixelSize: 12
                        onClicked: manageWin.downloadAllInGroup(groupRoot.category, groupRoot.engineName)
                    }
                    Button {
                        text: "Remove All"
                        flat: true
                        font.pixelSize: 12
                        Material.foreground: appController.colorDanger
                        onClicked: manageWin.removeAllInGroup(groupRoot.category, groupRoot.engineName)
                    }
                }

                Repeater {
                    model: manageWin.rowsFor(groupRoot.category, groupRoot.engineName)
                    delegate: assetRowComp
                }
            }
        }
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
            window: manageWin
            title: "Manage Models"
        }

        Text {
            id: errorBanner
            Layout.fillWidth: true
            Layout.margins: 12
            visible: false
            wrapMode: Text.WordWrap
            font.pixelSize: 12
            color: appController.colorDanger
        }

        TabBar {
            id: modelsTabBar
            Layout.fillWidth:       true
            Layout.preferredHeight: 44

            TabButton { text: "Transcription";   font.pixelSize: 12; implicitHeight: 44 }
            TabButton { text: "Translation";     font.pixelSize: 12; implicitHeight: 44 }
            TabButton { text: "Transliteration"; font.pixelSize: 12; implicitHeight: 44 }
        }

        StackLayout {
            Layout.fillWidth:  true
            Layout.fillHeight: true
            currentIndex: modelsTabBar.currentIndex

            Repeater {
                model: ["whisper", "translation", "transliteration"]

                delegate: Flickable {
                    id: tabRoot
                    required property string modelData
                    contentWidth:  width
                    contentHeight: col.implicitHeight
                    clip: true

                    ColumnLayout {
                        id: col
                        anchors.left:    parent.left
                        anchors.right:   parent.right
                        anchors.margins: 20
                        spacing: 16

                        Item { implicitHeight: 4 }

                        Repeater {
                            // Each row carries its own category alongside the engine name, so
                            // engineGroupComp's required properties bind directly at creation
                            // (a plain array-of-strings model only auto-binds `modelData`).
                            model: manageWin.enginesIn(tabRoot.modelData).map(
                                e => ({ category: tabRoot.modelData, engineName: e }))
                            delegate: engineGroupComp
                        }

                        Item { implicitHeight: 4 }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth:       true
            Layout.preferredHeight: 1
            color: appController.colorDivider
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.margins: 12
            spacing: 10

            Text {
                text: "Total disk usage: " + manageWin.formatBytes(manageWin.totalBytes)
                font.pixelSize: freeUpBtn.font.pixelSize
                color: Material.foreground
                Layout.fillWidth: true
            }
            Button {
                id: freeUpBtn
                text: "Free up space"
                flat: true
                font.pixelSize: 12
                enabled: manageWin.totalBytes > 0
                Material.foreground: appController.colorDanger
                onClicked: manageWin.removeAllDownloaded()
            }
            Button {
                text: "Close"
                font.pixelSize: 12
                Layout.preferredHeight: 36
                onClicked: manageWin.close()
            }
        }
    }
}
