<div align="center">

![CC-Gen-Ultimate Logo](ccgen/assets/icons/Square150x150Logo.scale-100.png)

# CC-Gen-Ultimate

**Free, open-source, fully offline subtitle generator - transcribe, translate, and transliterate any video or audio file, entirely on your machine.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D4.svg?logo=windows&logoColor=white)](#download--install)
[![Status](https://img.shields.io/badge/Status-Pre--release-orange.svg)](#roadmap)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB.svg?logo=python&logoColor=white)](pyproject.toml)

</div>

---

CC-Gen-Ultimate is a **free, open-source** desktop app that turns any video or audio file into accurate subtitles - automatically, and **entirely offline**. It transcribes speech with OpenAI's Whisper, optionally translates it into another language, and optionally transliterates the result into a different script (including natural, colloquial Roman Urdu - not academic transliteration). Drop in a file, pick your options, click Start. No account, no cloud upload, no subscription, no telemetry. Ever.

> *Your media. Your machine. Your subtitles.*

> 🚧 **Status:** in active development. The Windows release (installers + GitHub Releases) is targeted for **August 2026**, with a [winget](#download--install) package to follow shortly after. See the [Roadmap](#roadmap) for what's next, including Linux, macOS, and Android.

---

## Table of Contents

- [CC-Gen-Ultimate](#cc-gen-ultimate)
  - [Table of Contents](#table-of-contents)
  - [Who Is This For?](#who-is-this-for)
  - [Why CC-Gen-Ultimate?](#why-cc-gen-ultimate)
  - [Features](#features)
  - [Download \& Install](#download--install)
    - [Option 1 - Windows Package Manager (Coming Soon)](#option-1---windows-package-manager-coming-soon)
    - [Option 2 - Installers](#option-2---installers)
  - [Quick Start](#quick-start)
  - [Screenshots](#screenshots)
  - [How It Works](#how-it-works)
    - [Whisper Model Sizes](#whisper-model-sizes)
    - [Supported Languages \& Scripts](#supported-languages--scripts)
    - [Transliteration Engines](#transliteration-engines)
  - [Privacy \& Offline Guarantees](#privacy--offline-guarantees)
  - [Settings \& Preferences](#settings--preferences)
  - [Building from Source](#building-from-source)
    - [Prerequisites](#prerequisites)
    - [Development Setup](#development-setup)
    - [Running Tests \& Checks](#running-tests--checks)
  - [Troubleshooting](#troubleshooting)
  - [Contributing](#contributing)
  - [Roadmap](#roadmap)
  - [License \& Credits](#license--credits)
  - [Support the Project](#support-the-project)

---

## Who Is This For?

CC-Gen-Ultimate is for anyone who needs subtitles without handing their media over to a cloud service:

- **Content creators & YouTubers** who need accurate captions without a subscription to a captioning SaaS
- **Journalists & researchers** transcribing interviews that can't leave their machine for confidentiality reasons
- **Language learners** who want to see foreign-language audio transcribed, translated, and romanized side by side
- **Urdu, Hindi, and Punjabi speakers** who want subtitles in their own script - or in natural Roman Urdu, not a robotic phonetic dump
- **Students & educators** captioning lecture recordings for accessibility
- **Anyone in a low-connectivity environment** who needs captioning tools that work with zero internet after setup

If you've ever thought *"I just need subtitles for this file, without uploading it anywhere"* - this is for you.

---

## Why CC-Gen-Ultimate?

Most auto-captioning tools are cloud services in disguise: upload your file, wait in a queue, pay per minute, and hope nothing sensitive was in the audio. CC-Gen-Ultimate runs the entire pipeline - transcription, translation, and transliteration - on your own hardware.

- 🔒 **100% offline** - no accounts, no cloud sync, no telemetry, models download once and never again
- 🎙️ **Whisper-accurate transcription** - powered by `faster-whisper`, from a 75 MB `tiny` model up to `large-v3`
- 🌍 **Built-in translation** - 10 target languages via fully offline neural machine translation
- ✍️ **Real Roman Urdu, not academic transliteration** - a dedicated converter tuned for colloquial spelling ("kya haal hai", not diacritic-laden Sanskrit-style romanization)
- 🔀 **Two transliteration engines** - a fast rule-based converter and an optional neural engine for higher-quality output, your choice
- 🎨 **Modern, clean UI** - PySide6 + QML with System, Light, and Dark themes
- 📦 **Two install modes** - system-wide and per-user (no admin required)
- 📺 **Live progress** - watch each subtitle segment appear as it's transcribed, no black-box waiting

---

## Features

- **Transcription** - drag in video/audio files, get word-timestamped subtitles via `faster-whisper` (CPU, `int8` by default; CUDA supported)
- **Translation** - optionally translate the transcript into any of 10 supported languages, fully offline via `argostranslate`, models auto-downloaded once
- **Transliteration** - optionally convert the transcript (or its translation) between 14 scripts, including a purpose-built Urdu ⇄ Roman Urdu converter
- **Dual transliteration engines** - switch between a lightweight rule-based engine and a higher-quality neural engine per job or as a global default
- **Multi-file queue** - add files or entire folders, process them sequentially, drag-and-drop supported
- **Batch-friendly formats** - accepts MP4, MKV, AVI, MOV, WebM, FLV, WMV, TS, M2TS, MP3, WAV, M4A, FLAC, AAC, OGG, WMA, and existing SRT/VTT files (for re-translating or re-transliterating subtitles you already have)
- **Standard subtitle output** - SRT and/or WebVTT, line-wrapped to readable lengths
- **Live segment streaming** - transcribed lines appear in the UI in real time as they're produced
- **Global Settings** - persisted defaults for model, language, translation, and transliteration (including engine choice), so new jobs start exactly how you like them
- **Detailed logging** - critical-only or full activity logs saved locally
- **Live theme switching** - System / Light / Dark with instant preview

---

## Download & Install

### Option 1 - Windows Package Manager (Coming Soon)

```powershell
winget install gfgRoyal.CCGenUltimate
```

*(Package submission follows the initial GitHub release - see [Roadmap](#roadmap).)*

### Option 2 - Installers

Once published, installers will be available on the [Releases](https://github.com/ShahFaisalGfG/CC-Gen-UItimate/releases) page:

| Package | Admin Required | Best For |
| --- | :---: | --- |
| `CCGenUltimate_<version>_system_installer.exe` | ✅ | Shared / corporate machines |
| `CCGenUltimate_<version>_user_installer.exe` | ❌ | Personal machines - recommended |

The first Windows models (`faster-whisper`, `argostranslate`, and transliteration models) download automatically on first use and are cached locally - no repeated downloads, no internet required afterward.

---

## Quick Start

1. **Add files** - drag & drop onto the window, or use **+ Files** / **+ Folder**
2. **Choose a model** - `base` is the default and a good balance of speed and accuracy; see [Whisper Model Sizes](#whisper-model-sizes)
3. **Pick a language** - or leave it on auto-detect
4. **Optionally translate** - turn on **Translate** and pick a target language
5. **Optionally transliterate** - turn on **Transliterate**, pick source/target scripts, and choose whether to convert the transcript or the translation
6. **Start** - click **▶ Start** and watch segments stream in live

Output files are written next to the input, named by what they contain: `video.srt` (original), `video_ur.srt` (translated to Urdu), `video_tr_ur_roman.srt` (transliterated Urdu → Roman).

---

## Screenshots

> 📸 Screenshots will be added here closer to the Windows release.

---

## How It Works

```
Input file (video/audio)
  │
  ▼ Extract audio (ffmpeg, 16 kHz mono WAV)
  │
  ▼ Transcribe (faster-whisper) ──── live segments stream into the UI
  │
  ├─ [optional] Translate (argostranslate) ─────────► video_<lang>.srt
  │
  └─ [optional] Transliterate (rule or neural engine) ─► video_tr_<source>_<target>.srt
```

### Whisper Model Sizes

| Model | Size | Speed (CPU) | Quality |
|-------|------|-------------|---------|
| tiny | 75 MB | Fastest | Basic |
| **base** | **145 MB** | **Fast** | **Default - good balance** |
| small | 466 MB | Moderate | Good |
| medium | 1.5 GB | Slow | High |
| large-v3 | 3.0 GB | Very slow | Best |

### Supported Languages & Scripts

| Stage | Options |
|---|---|
| **Transcription** | Auto-detect, Arabic, Chinese, English, French, German, Hindi, Japanese, Korean, Portuguese, Russian, Spanish, Turkish, Urdu |
| **Translation targets** | Arabic, English, French, German, Hindi, Portuguese, Russian, Spanish, Turkish, Urdu |
| **Transliteration scripts** | Roman/Latin, Urdu (Nastaliq), Hindi (Devanagari), Bengali, Gujarati, Punjabi (Gurmukhi), Tamil, Telugu, Kannada, Malayalam, Odia, Sinhala, Thai, Burmese |

### Transliteration Engines

Urdu's Arabic-derived script doesn't romanize the way a purely academic transliteration scheme assumes - "کیا حال ہے پیارے؟" should read as **"kya haal hai piyare?"**, not a string of diacritics. CC-Gen-Ultimate ships two engines so you can pick the right trade-off:

| Engine | Speed | Download | Best For |
|---|:---:|---|---|
| **Rule-based** *(default)* | Fast | None - built in | Offline-first use, older PCs, instant results |
| **Neural** | Slower | ~50 MB - 2 GB on first use, per direction | Higher-quality, more natural output |

> **Note:** the neural engine's Hindi→Urdu model is distributed under an unclear license (its upstream repository ships an empty `LICENSE` file). It's included because it's currently the only option for that direction, but if you have licensing concerns, stick to the rule-based engine - it's fully open-source (0BSD) and available offline by default.

---

## Privacy & Offline Guarantees

- ❌ No telemetry or usage reporting
- ❌ No cloud sync, no file uploads
- ❌ No accounts or registration required
- ❌ No third-party analytics or tracking
- ✅ All processing - transcription, translation, transliteration - runs on your own CPU (or GPU, if configured)
- ✅ Models are downloaded once, from their original open-source hosts, and cached locally forever after

CC-Gen-Ultimate's UI talks to a small local backend embedded in the same app process, bound only to `127.0.0.1` - nothing ever leaves your machine.

---

## Settings & Preferences

| Tab | Contents |
|---|---|
| **Appearance** | Theme: System / Light / Dark |
| **Transcription** | Default Whisper model, default output formats (SRT/VTT) |
| **Translation** | Default enabled state, default target language |
| **Transliteration** | Default enabled state, default source/target script, default input source, default engine (rule/neural) |
| **Advanced** | Logging on/off, log level (critical/all), clear logs |

All settings persist to `%APPDATA%\CC-Gen-Ultimate\settings.json` and apply to every new job automatically.

---

## Building from Source

### Prerequisites

- Python 3.12+
- [ffmpeg](https://www.ffmpeg.org/download.html) on your `PATH` (bundled by the installer once released)
- [Inno Setup 6](https://jrsoftware.org/isinfo.php) - only needed to build installers

### Development Setup

```powershell
# 1. Clone the repository
git clone https://github.com/ShahFaisalGfG/CC-Gen-UItimate.git
cd CC-Gen-UItimate

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the GUI
python app.py

# ...or drive the core pipeline without a UI
python main.py path\to\video.mp4 --model tiny --translate --target-lang ur
```

### Running Tests & Checks

```powershell
pytest tests/ -v
pyright ccgen/ app.py main.py server.py
qmllint ccgen/qml/main.qml ccgen/qml/PreferencesWindow.qml ccgen/qml/components/*.qml
```

---

## Troubleshooting

| Issue | Solution |
|---|---|
| First run is slow | The selected Whisper/translation/transliteration model is downloading - this only happens once per model |
| Translation/transliteration fails with a language-pair error | Not every language pair has a pre-trained offline model; try translating to/from English as an intermediate step |
| GUI window doesn't appear | Check the log output for "Embedded API server failed to start" - another process may be holding the local port |
| Slow transcription on CPU | Use a smaller model (`tiny`/`base`), or enable CUDA if you have a supported Nvidia GPU |

Still stuck? [Open an issue](https://github.com/ShahFaisalGfG/CC-Gen-UItimate/issues) with your log output and CC-Gen-Ultimate version - I'll get back to you.

---

## Contributing

Contributions of all kinds are genuinely welcome - bug reports, fixes, new features, translations, or just improving a sentence in the docs.

1. **Fork** the repository and clone your fork
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes and ensure:
   - `pytest` passes
   - `pyright` passes on all edited Python files
   - `qmllint` passes on all edited `.qml` files
4. Commit with a clear message and open a **Pull Request** targeting the `development` branch

For significant changes, please [open an issue](https://github.com/ShahFaisalGfG/CC-Gen-UItimate/issues) first to discuss the approach.

---

## Roadmap

| Target | Plan |
|---|---|
| **August 2026** | Initial Windows release - system & user Inno Setup installers on GitHub Releases |
| **Shortly after** | `winget` package submission |
| **Later** | Linux packages (Flatpak / AppImage) |
| **Later** | macOS package (`.dmg` / Homebrew) |
| **Later** | Android release |

Have a feature idea or a use case not covered above? [Start a discussion](https://github.com/ShahFaisalGfG/CC-Gen-UItimate/discussions).

---

## License & Credits

Released under the [MIT License](LICENSE) - free to use, modify, and distribute.

Built with faster-whisper, argostranslate, indic-transliteration, and the transformers/PyTorch ecosystem for neural transliteration.

Built with ❤️ by **Shah Faisal** · [Portfolio](https://shahfaisalgfg.github.io/shahfaisal/) · [shahfaisalgfg@outlook.com](mailto:shahfaisalgfg@outlook.com)

---

## Support the Project

CC-Gen-Ultimate is free and will always stay free. If it's saved you time or helped you caption something that mattered, here are a few ways to give back:

- ⭐ **Star the repo** - it takes two seconds and helps others find the project
- 🐛 **Report a bug** - honest feedback makes the tool better for everyone
- 💡 **Suggest a feature** - if you need it, chances are someone else does too
- 🔁 **Share it** - tell a friend, post it in a forum, or mention it in a blog post
- 🛠️ **Contribute code** - PRs are always welcome; see [Contributing](#contributing)

**[★ Star CC-Gen-Ultimate on GitHub](https://github.com/ShahFaisalGfG/CC-Gen-UItimate)**

---

*Your media. Your machine. Your subtitles.* 🎬
