# test_argos_engine.py — unit tests for ccgen.engines.translation.argos_engine

from unittest.mock import MagicMock, patch

import pytest

from ccgen.core import Segment
from ccgen.engines.translation.argos_engine import ArgosEngine


def _segment(text: str, seg_id: int = 0) -> Segment:
    return Segment(id=seg_id, start=0.0, end=1.0, text=text, words=[], language="en")


class _FakePackage:
    def __init__(self, from_code: str, to_code: str, archive_path: str = "archive.argosmodel") -> None:
        self.from_code = from_code
        self.to_code = to_code
        self.download = MagicMock(return_value=archive_path)


class TestEnsureModelAlreadyInstalled:
    @patch("ccgen.engines.translation.argos_engine.argostranslate.translate")
    @patch("ccgen.engines.translation.argos_engine.argostranslate.package")
    def test_skips_download(self, mock_package, mock_translate):
        mock_package.get_installed_packages.return_value = [_FakePackage("en", "es")]
        mock_translate.get_translation_from_codes.return_value = MagicMock()
        engine = ArgosEngine("en", "es")
        engine.ensure_model()
        mock_package.update_package_index.assert_not_called()
        mock_package.install_from_path.assert_not_called()

    @patch("ccgen.engines.translation.argos_engine.argostranslate.translate")
    @patch("ccgen.engines.translation.argos_engine.argostranslate.package")
    def test_does_not_call_progress_cb(self, mock_package, mock_translate):
        mock_package.get_installed_packages.return_value = [_FakePackage("en", "es")]
        mock_translate.get_translation_from_codes.return_value = MagicMock()
        engine = ArgosEngine("en", "es")
        progress_cb = MagicMock()
        engine.ensure_model(progress_cb=progress_cb)
        progress_cb.assert_not_called()


class TestEnsureModelDownload:
    @patch("ccgen.engines.translation.argos_engine.download_progress")
    @patch("ccgen.engines.translation.argos_engine.argostranslate.translate")
    @patch("ccgen.engines.translation.argos_engine.argostranslate.package")
    def test_downloads_and_installs(self, mock_package, mock_translate, mock_download_progress):
        mock_package.get_installed_packages.return_value = []
        fake_pkg = _FakePackage("en", "es", archive_path="path/to/en_es.argosmodel")
        mock_package.get_available_packages.return_value = [fake_pkg]
        mock_translate.get_translation_from_codes.return_value = MagicMock()

        engine = ArgosEngine("en", "es")
        engine.ensure_model()

        mock_package.update_package_index.assert_called_once()
        fake_pkg.download.assert_called_once()
        mock_package.install_from_path.assert_called_once_with("path/to/en_es.argosmodel")

    @patch("ccgen.engines.translation.argos_engine.download_progress")
    @patch("ccgen.engines.translation.argos_engine.argostranslate.translate")
    @patch("ccgen.engines.translation.argos_engine.argostranslate.package")
    def test_wraps_download_in_progress_context(self, mock_package, mock_translate, mock_download_progress):
        mock_package.get_installed_packages.return_value = []
        fake_pkg = _FakePackage("en", "es")
        mock_package.get_available_packages.return_value = [fake_pkg]
        mock_translate.get_translation_from_codes.return_value = MagicMock()

        engine = ArgosEngine("en", "es")
        cb = MagicMock()
        engine.ensure_model(progress_num_cb=cb)

        mock_download_progress.assert_called_once_with(cb)

    @patch("ccgen.engines.translation.argos_engine.download_progress")
    @patch("ccgen.engines.translation.argos_engine.argostranslate.translate")
    @patch("ccgen.engines.translation.argos_engine.argostranslate.package")
    def test_progress_cb_messages(self, mock_package, mock_translate, mock_download_progress):
        mock_package.get_installed_packages.return_value = []
        fake_pkg = _FakePackage("en", "es")
        mock_package.get_available_packages.return_value = [fake_pkg]
        mock_translate.get_translation_from_codes.return_value = MagicMock()

        engine = ArgosEngine("en", "es")
        messages = []
        engine.ensure_model(progress_cb=messages.append)

        assert messages == [
            "Downloading translation model en→es...",
            "Translation model ready.",
        ]


class TestEnsureModelUnsupportedPair:
    @patch("ccgen.engines.translation.argos_engine.argostranslate.translate")
    @patch("ccgen.engines.translation.argos_engine.argostranslate.package")
    def test_raises_runtime_error(self, mock_package, mock_translate):
        mock_package.get_installed_packages.return_value = []
        mock_package.get_available_packages.return_value = [_FakePackage("fr", "de")]
        engine = ArgosEngine("en", "es")
        with pytest.raises(RuntimeError, match="No translation package for en→es"):
            engine.ensure_model()


class TestTranslateSegmentsBeforeEnsureModel:
    def test_raises_runtime_error(self):
        engine = ArgosEngine("en", "es")
        with pytest.raises(RuntimeError, match="Call ensure_model"):
            engine.translate_segments([_segment("Hello")])


class TestTranslateSegments:
    @patch("ccgen.engines.translation.argos_engine.argostranslate.translate")
    @patch("ccgen.engines.translation.argos_engine.argostranslate.package")
    def test_translates_and_preserves_timing(self, mock_package, mock_translate):
        mock_package.get_installed_packages.return_value = [_FakePackage("en", "es")]
        fake_engine = MagicMock()
        fake_engine.translate.return_value = "Hola"
        mock_translate.get_translation_from_codes.return_value = fake_engine

        engine = ArgosEngine("en", "es")
        engine.ensure_model()
        result = engine.translate_segments([_segment("Hello", seg_id=3)])

        assert result[0]["id"] == 3
        assert result[0]["translated"] == "Hola"
        assert result[0]["language"] == "es"

    @patch("ccgen.engines.translation.argos_engine.argostranslate.translate")
    @patch("ccgen.engines.translation.argos_engine.argostranslate.package")
    def test_progress_num_cb_per_segment(self, mock_package, mock_translate):
        mock_package.get_installed_packages.return_value = [_FakePackage("en", "es")]
        fake_engine = MagicMock()
        fake_engine.translate.return_value = "x"
        mock_translate.get_translation_from_codes.return_value = fake_engine

        engine = ArgosEngine("en", "es")
        engine.ensure_model()
        calls = []
        engine.translate_segments(
            [_segment("a", 0), _segment("b", 1)],
            progress_num_cb=lambda done, total: calls.append((done, total)),
        )
        assert calls == [(1, 2), (2, 2)]


class TestSetPair:
    @patch("ccgen.engines.translation.argos_engine.argostranslate.translate")
    @patch("ccgen.engines.translation.argos_engine.argostranslate.package")
    def test_resets_engine(self, mock_package, mock_translate):
        mock_package.get_installed_packages.return_value = [_FakePackage("en", "es")]
        mock_translate.get_translation_from_codes.return_value = MagicMock()
        engine = ArgosEngine("en", "es")
        engine.ensure_model()
        engine.set_pair("en", "fr")
        with pytest.raises(RuntimeError, match="Call ensure_model"):
            engine.translate_segments([_segment("Hello")])


class TestListInstalled:
    @patch("ccgen.engines.translation.argos_engine.argostranslate.package")
    def test_formats_pairs(self, mock_package):
        mock_package.get_installed_packages.return_value = [_FakePackage("en", "es"), _FakePackage("en", "fr")]
        engine = ArgosEngine()
        assert engine.list_installed() == ["en→es", "en→fr"]
