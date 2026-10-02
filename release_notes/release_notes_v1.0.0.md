# CC-Gen-Ultimate 1.0.0

The first Windows release of CC-Gen-Ultimate: a free, fully offline subtitle generator. Drop in video, audio, or subtitle files and get subtitles, translations, and transliterations without uploading anything.

## Highlights

- **Readable subtitles out of the box.** Speech is split into proper subtitle cues using word timings: two balanced lines of up to 42 characters, breaks at sentence ends, commas, and pauses, a comfortable minimum display time, and no overlapping cues. Long sentences are split evenly instead of leaving a one-word cue behind.
- **More accurate transcription.** Long recordings no longer drift into repeated or invented text, silent stretches are skipped safely, and language detection listens to more than the first 30 seconds so music intros don't fool it.
- **New `large-v3-turbo` model.** Close to `large-v3` accuracy at a fraction of the time.
- **Better translations.** Whole sentences are translated and then mapped back onto the subtitle timing, which matters most for languages with a different word order, such as Urdu. Language pairs without a direct package (for example Urdu to French) now work through English, and translating into the language that is already spoken is skipped instead of failing.
- **GPU support.** With an NVIDIA GPU and CUDA installed, transcription runs on the GPU automatically. If the GPU can't be used, the app falls back to the CPU on its own.
- **Real batch processing.** Every file in the queue is processed, one after another, with per-file progress, status, and error messages. Cancel stops the current file and keeps the rest queued; Start picks up where you left off.
- **Large folders load instantly.** Adding a folder scans it and all subfolders in the background. Thousands of files appear within a second while the window stays responsive.

## Redesigned interface

- New layout: the queue on the left, Settings and a live Transcript on the right, and an action bar with overall progress, the current step, and Start / Cancel.
- The live transcript shows each subtitle with its translation underneath as it is produced, and stays visible after the run.
- Choose where subtitles are saved, or keep them next to each source file. "Open output folder" appears when a run finishes.
- Every window resizes from any edge, follows the Windows light or dark theme (including switching while the app is open), and uses consistent icons and colors with readable contrast.
- Tooltips explain every option, and download badges show which models are already on this computer.
- Keyboard shortcuts: **Ctrl+O** add files, **Ctrl+Shift+O** add folder, **Ctrl+Enter** start, **Esc** cancel, **Ctrl+,** preferences, **Ctrl+M** manage models, **Ctrl+1 / Ctrl+2** switch tabs, **Delete** remove selected files, **F1** about.
- Preferences are organized into Appearance, Transcription, Translation, Transliteration, Subtitles, and Advanced, and are saved together in one step.

## Fixes

- Fixed only the first file in the queue being processed when several were added.
- Fixed Cancel having no effect once transcription had started.
- Fixed long speech being cut off in subtitle files (text past two lines was dropped).
- Fixed preferences occasionally being lost when saving, and settings.json being left damaged after a crash during a save.
- Fixed the logging preferences having no effect; logs are now written to `%APPDATA%\CC-Gen-Ultimate\logs` and can be opened or cleared from Preferences.
- Fixed models being reloaded for every file and kept in memory after processing finished.
- Fixed the window freezing while checking which models are downloaded.
- Fixed Start being available with no output format selected.
- Fixed SRT cue numbers skipping values and WebVTT files breaking on `<` or `&` in the text.
- The Hindi/Punjabi to Urdu neural engine no longer cuts off long lines and runs noticeably faster.

## Known limitations

- Cancelling during transcription takes effect at the end of the current 30-second audio window, which can take several seconds on a CPU with larger models.
- GPU acceleration needs an NVIDIA GPU with the CUDA 12 and cuDNN 9 runtime libraries installed; otherwise the CPU is used.
- Translating a subtitle file (SRT, VTT, and so on) needs its spoken language set, since text can't be auto-detected.

## Install

Download one of the installers below. The per-user installer needs no administrator rights. Models download once, the first time each one is used, and work offline afterwards.
