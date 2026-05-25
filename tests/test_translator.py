# test_translator.py — unit tests for ccgen.core.translator

from unittest.mock import MagicMock, patch

import pytest

from ccgen.core.translator import Translator


class TestTranslator:
    def _make_translator(self, installed: bool = False) -> Translator:
        t = Translator(source_lang="en", target_lang="es")
        if installed:
            pkg = MagicMock()
            pkg.from_code = "en"
            pkg.to_code = "es"
            with patch(
                "ccgen.core.translator.argostranslate.package.get_installed_packages",
                return_value=[pkg],
            ):
                engine = MagicMock()
                engine.translate.return_value = "Hola mundo"
                with patch(
                    "ccgen.core.translator.argostranslate.translate.get_translation_from_codes",
                    return_value=engine,
                ):
                    t.ensure_model()
        return t

    def test_ensure_model_skips_download_when_installed(self):
        t = Translator(source_lang="en", target_lang="es")
        pkg = MagicMock()
        pkg.from_code = "en"
        pkg.to_code = "es"
        engine = MagicMock()

        with patch(
            "ccgen.core.translator.argostranslate.package.get_installed_packages",
            return_value=[pkg],
        ):
            with patch(
                "ccgen.core.translator.argostranslate.translate.get_translation_from_codes",
                return_value=engine,
            ):
                with patch(
                    "ccgen.core.translator.argostranslate.package.update_package_index"
                ) as mock_update:
                    t.ensure_model()
                    mock_update.assert_not_called()

    def test_translate_without_ensure_raises(self, sample_segments):
        t = Translator()
        with pytest.raises(RuntimeError, match="ensure_model"):
            t.translate_segments(sample_segments)

    def test_translate_returns_translated_segments(self, sample_segments):
        t = Translator(source_lang="en", target_lang="es")
        pkg = MagicMock()
        pkg.from_code = "en"
        pkg.to_code = "es"
        engine = MagicMock()
        engine.translate.return_value = "Hola mundo, esto es una prueba."

        with patch(
            "ccgen.core.translator.argostranslate.package.get_installed_packages",
            return_value=[pkg],
        ):
            with patch(
                "ccgen.core.translator.argostranslate.translate.get_translation_from_codes",
                return_value=engine,
            ):
                t.ensure_model()
                result = t.translate_segments(sample_segments)

        assert len(result) == len(sample_segments)
        assert result[0]["language"] == "es"
        assert "translated" in result[0]
        assert result[0]["start"] == sample_segments[0]["start"]
        assert result[0]["end"] == sample_segments[0]["end"]

    def test_list_installed_returns_strings(self):
        t = Translator()
        pkg = MagicMock()
        pkg.from_code = "en"
        pkg.to_code = "es"
        with patch(
            "ccgen.core.translator.argostranslate.package.get_installed_packages",
            return_value=[pkg],
        ):
            result = t.list_installed()
        assert result == ["en→es"]

    def test_unavailable_pair_raises(self):
        t = Translator(source_lang="xx", target_lang="yy")
        with patch(
            "ccgen.core.translator.argostranslate.package.get_installed_packages",
            return_value=[],
        ):
            with patch(
                "ccgen.core.translator.argostranslate.package.update_package_index"
            ):
                with patch(
                    "ccgen.core.translator.argostranslate.package.get_available_packages",
                    return_value=[],
                ):
                    with pytest.raises(RuntimeError, match="No translation package"):
                        t.ensure_model()
