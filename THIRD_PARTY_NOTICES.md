# Third-Party Notices

CC-Gen-Ultimate's own source code is released under the [MIT License](LICENSE). The installers and
the portable app bundle the open-source libraries below, and download models on first use.

## Licence of the distributed app

The dubbing feature bundles **piper-tts**, **phonemizer**, and the **eSpeak NG** library, which are
licensed under the GNU General Public License v3.0 or later. Because they are distributed inside the
same app, the installers and portable app as a whole are conveyed under the terms of the
**GPL-3.0-or-later**. CC-Gen-Ultimate's source stays available under MIT, which is compatible with
the GPL, and the complete source for every bundled component is available from the projects listed
below.

## Bundled libraries

| Component | Licence | Used for |
|---|---|---|
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | MIT | Speech recognition |
| [CTranslate2](https://github.com/OpenNMT/CTranslate2) | MIT | Whisper inference |
| [Argos Translate](https://github.com/argosopentech/argos-translate) | MIT | Translation |
| [Transformers](https://github.com/huggingface/transformers) | Apache-2.0 | Neural transliteration |
| [Hugging Face Hub](https://github.com/huggingface/huggingface_hub) | Apache-2.0 | Model downloads |
| [PyTorch](https://github.com/pytorch/pytorch) | BSD-3-Clause | Neural transliteration, voice cloning |
| [torchaudio](https://github.com/pytorch/audio) | BSD-2-Clause | Voice cloning audio processing |
| [ONNX Runtime](https://github.com/microsoft/onnxruntime) (CPU and DirectML builds) | MIT | Piper and Kokoro voices, voice activity detection |
| [coqui-tts](https://github.com/idiap/coqui-ai-TTS) | MPL-2.0 | XTTS-v2 voice cloning |
| [piper-tts](https://github.com/OHF-Voice/piper1-gpl) | GPL-3.0-or-later | Piper voices |
| [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) | MIT | Kokoro voices |
| [phonemizer](https://github.com/bootphon/phonemizer) | GPL-3.0-or-later | Kokoro pronunciation |
| [eSpeak NG](https://github.com/espeak-ng/espeak-ng) (via piper-tts and espeakng-loader) | GPL-3.0-or-later | Pronunciation for Piper and Kokoro |
| [cutlet](https://github.com/polm/cutlet), [fugashi](https://github.com/polm/fugashi), [unidic-lite](https://github.com/polm/unidic-lite) | MIT; fugashi MIT and BSD-3-Clause | Japanese text for voice cloning |
| [pypinyin](https://github.com/mozillazg/python-pinyin), [spacy-pkuseg](https://github.com/explosion/spacy-pkuseg) | MIT | Chinese text for voice cloning |
| [ko-speech-tools](https://github.com/eginhard/ko-speech-tools), [mecab-ko](https://github.com/NoUnique/pymecab-ko) | Apache-2.0; BSD | Korean text for voice cloning |
| [num2words](https://github.com/savoirfairelinux/num2words) | LGPL | Spelling out numbers for voice cloning |
| [PyAV](https://github.com/PyAV-Org/PyAV) and its FFmpeg libraries | BSD-3-Clause (FFmpeg: LGPL-2.1-or-later) | Audio decoding, adding the dub track |
| [indic-transliteration](https://github.com/indic-transliteration/indic_transliteration_py) | MIT | Rule-based transliteration |
| [PySide6 / Qt](https://www.qt.io/qt-for-python) | LGPL-3.0 | User interface |
| [FastAPI](https://github.com/fastapi/fastapi), [Uvicorn](https://github.com/encode/uvicorn) | MIT; BSD-3-Clause | Embedded local API |
| [spaCy](https://github.com/explosion/spaCy) | MIT | Required by Argos Translate |
| [NumPy](https://github.com/numpy/numpy) | BSD-3-Clause and others | Audio and math |

## Models downloaded on first use

Models are not bundled. Each downloads from its original host when first needed (or from
**Manage Models**) and keeps its own licence:

| Model | Licence |
|---|---|
| Whisper (Systran faster-whisper conversions) | MIT |
| Argos Translate language packages | Listed in each package's metadata |
| M2M100 Urdu ↔ Roman Urdu fine-tunes (Mavkif) | Apache-2.0 |
| Rekhta Hindi → Urdu transliteration | Unclear: its repository ships an empty licence file |
| [XTTS-v2](https://huggingface.co/coqui/XTTS-v2) | [Coqui Public Model License](https://coqui.ai/cpml): non-commercial use of the model and the audio it creates. The app asks you to accept it before the first download. |
| [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) | Apache-2.0 |
| [Piper voices](https://huggingface.co/rhasspy/piper-voices) | Each voice's own licence, stated in its `MODEL_CARD` |
