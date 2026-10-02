"""Collect coqui-tts (TTS) with its Python source files on disk, not only in the archive.

TTS compiles some functions with TorchScript, which reads their source code when the module is
imported, and it imports its vocoder configs by listing that folder's .py files. Both need the
real files next to the bundled bytecode.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

module_collection_mode = "pyz+py"
# Imported by name at runtime from the folder listing, so the analysis can't see them.
hiddenimports = collect_submodules("TTS.vocoder.configs")
datas = collect_data_files("TTS")
