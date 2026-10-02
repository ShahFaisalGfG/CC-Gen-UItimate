pragma Singleton
import QtQuick

// Design tokens shared by every window. Colors are chosen so body and muted text keep at least
// a 4.5:1 contrast ratio against their surfaces in both themes (WCAG 2.1 AA).
QtObject {
    id: theme

    // Set once by main.qml from appController.currentTheme.
    property bool dark: false

    // ── Surfaces ─────────────────────────────────────────────────────────────
    readonly property color background:   dark ? "#15171c" : "#f3f4f6"
    readonly property color surface:      dark ? "#1d2027" : "#ffffff"
    readonly property color surfaceAlt:   dark ? "#242832" : "#f7f8fa"
    readonly property color surfaceHover: dark ? "#2b303b" : "#eceff3"
    readonly property color titleBar:     dark ? "#111317" : "#e9ebef"
    readonly property color border:       dark ? "#343a46" : "#d6dae1"
    readonly property color borderStrong: dark ? "#4a5263" : "#b7bec9"

    // ── Text ─────────────────────────────────────────────────────────────────
    readonly property color text:      dark ? "#e8eaee" : "#1a1d23"
    readonly property color textMuted: dark ? "#a6adba" : "#565f6c"
    readonly property color textOnAccent: "#ffffff"

    // ── Accent and status ────────────────────────────────────────────────────
    readonly property color accent:      dark ? "#5aa9ff" : "#0b62c4"
    readonly property color accentFill:  dark ? "#2a6fd6" : "#0b62c4"
    readonly property color accentHover: dark ? "#3a7fe6" : "#0a56ad"
    readonly property color accentSoft:  dark ? "#1b2c45" : "#e5effb"
    readonly property color success:     dark ? "#4ac26b" : "#1a7f37"
    readonly property color successSoft: dark ? "#16301f" : "#e3f4e8"
    readonly property color danger:      dark ? "#ff6b63" : "#c62828"
    readonly property color dangerSoft:  dark ? "#3a1d1d" : "#fdecec"
    readonly property color warning:     dark ? "#e0b341" : "#8a5a00"
    readonly property color focusRing:   dark ? "#8cc4ff" : "#0b62c4"

    // ── Typography (pixel sizes) ─────────────────────────────────────────────
    readonly property string fontFamily: "Segoe UI Variable Text"
    readonly property int fontCaption: 12
    readonly property int fontBody: 13
    readonly property int fontSubtitle: 15
    readonly property int fontTitle: 18

    // ── Spacing and shape ────────────────────────────────────────────────────
    readonly property int spaceXs: 4
    readonly property int spaceSm: 8
    readonly property int spaceMd: 12
    readonly property int spaceLg: 16
    readonly property int spaceXl: 24
    readonly property int radius: 6
    readonly property int radiusLarge: 10
    readonly property int controlHeight: 34

    // ── Icons (Segoe Fluent Icons on Windows 11, MDL2 Assets on Windows 10) ──
    readonly property string iconFont: Qt.fontFamilies().indexOf("Segoe Fluent Icons") >= 0
        ? "Segoe Fluent Icons" : "Segoe MDL2 Assets"
    readonly property var icons: ({
        add: "",
        folder: "",
        folderOpen: "",
        remove: "",
        delete: "",
        close: "",
        cancel: "",
        minimize: "",
        maximize: "",
        restore: "",
        settings: "",
        info: "",
        download: "",
        play: "",
        stop: "",
        check: "",
        completed: "",
        error: "",
        warning: "",
        video: "",
        audio: "",
        captions: "",
        globe: "",
        characters: "",
        page: "",
        library: "",
        more: "",
        clear: "",
        mic: "",
        openExternal: "",
        sync: "",
        chevronDown: ""
    })
}
