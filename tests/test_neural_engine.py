# test_neural_engine.py — unit tests for ccgen.engines.transliteration.neural_engine

from unittest.mock import MagicMock, call, patch

import pytest
from indic_transliteration import sanscript

from ccgen.core import Segment
from ccgen.engines.transliteration.neural_engine import NeuralEngine


def _tracking_download_progress(call_order):
    """Build a fake `download_progress(cb)` that records context enter/exit into `call_order`."""

    def _fake(_callback):
        context = MagicMock()

        def _enter():
            call_order.append("enter")

        def _exit(*_args):
            call_order.append("exit")
            return False

        context.__enter__.side_effect = _enter
        context.__exit__.side_effect = _exit
        return context

    return _fake


class TestEnsureLoaded:
    def test_ur_to_roman_routes_to_load_m2m100(self):
        engine = NeuralEngine("ur", "roman")
        with patch.object(engine, "_load_m2m100") as mock_load:
            engine.ensure_loaded(None, None)
        mock_load.assert_called_once_with(("ur", "roman"), None, None)

    def test_m2m100_loads_only_once(self):
        engine = NeuralEngine("ur", "roman")
        engine._m2m_model = MagicMock()
        with patch.object(engine, "_load_m2m100") as mock_load:
            engine.ensure_loaded(None, None)
        mock_load.assert_not_called()

    def test_hi_to_ur_routes_to_rekhta_load(self):
        engine = NeuralEngine("hi", "ur")
        with patch.object(engine._rekhta, "load") as mock_load:
            engine.ensure_loaded(None, None)
            engine.ensure_loaded(None, None)
        mock_load.assert_called_once_with(None, None)
        assert engine._rekhta_loaded is True

    def test_pa_to_ur_routes_to_rekhta_load(self):
        engine = NeuralEngine("pa", "ur")
        with patch.object(engine._rekhta, "load") as mock_load:
            engine.ensure_loaded(None, None)
        mock_load.assert_called_once_with(None, None)

    def test_unsupported_pair_raises_value_error(self):
        engine = NeuralEngine("bn", "roman")
        with pytest.raises(ValueError, match="No neural engine available"):
            engine.ensure_loaded(None, None)


class TestLoadM2m100:
    def test_cached_model_loads_via_local_files_only_without_progress_context(self):
        mock_tokenizer = MagicMock()
        mock_model = MagicMock()

        engine = NeuralEngine("ur", "roman")
        with patch(
            "ccgen.engines.transliteration.neural_engine.download_progress",
        ) as mock_download_progress:
            with patch(
                "ccgen.engines.transliteration.neural_engine.AutoTokenizer.from_pretrained",
                return_value=mock_tokenizer,
            ) as mock_tok_load:
                with patch(
                    "ccgen.engines.transliteration.neural_engine.M2M100ForConditionalGeneration.from_pretrained",
                    return_value=mock_model,
                ) as mock_model_load:
                    engine._load_m2m100(("ur", "roman"), None, None)

        mock_tok_load.assert_called_once_with("Mavkif/m2m100_rup_tokenizer_both", local_files_only=True)
        mock_model_load.assert_called_once_with("Mavkif/m2m100_rup_ur_to_rur", local_files_only=True)
        mock_download_progress.assert_not_called()
        assert engine._m2m_model is mock_model
        mock_model.eval.assert_called_once()

    def test_uncached_model_falls_back_to_download_with_progress_context(self):
        call_order = []
        mock_tokenizer = MagicMock()
        mock_model = MagicMock()

        def fake_tokenizer_load(*_args, **kwargs):
            if kwargs.get("local_files_only"):
                raise OSError("not cached")
            call_order.append("tokenizer")
            return mock_tokenizer

        def fake_model_load(*_args, **kwargs):
            if kwargs.get("local_files_only"):
                raise OSError("not cached")
            call_order.append("model")
            return mock_model

        engine = NeuralEngine("ur", "roman")
        with patch(
            "ccgen.engines.transliteration.neural_engine.download_progress",
            side_effect=_tracking_download_progress(call_order),
        ):
            with patch(
                "ccgen.engines.transliteration.neural_engine.AutoTokenizer.from_pretrained",
                side_effect=fake_tokenizer_load,
            ):
                with patch(
                    "ccgen.engines.transliteration.neural_engine.M2M100ForConditionalGeneration.from_pretrained",
                    side_effect=fake_model_load,
                ):
                    engine._load_m2m100(("ur", "roman"), None, None)

        assert call_order == ["enter", "tokenizer", "model", "exit"]
        assert engine._m2m_model is mock_model
        mock_model.eval.assert_called_once()

    def test_transient_download_failure_is_retried(self):
        mock_tokenizer = MagicMock()
        mock_model = MagicMock()
        tokenizer_attempts = {"count": 0}

        def flaky_tokenizer_load(*_args, **kwargs):
            if kwargs.get("local_files_only"):
                raise OSError("not cached")
            tokenizer_attempts["count"] += 1
            if tokenizer_attempts["count"] == 1:
                raise OSError("cold download race, try again")
            return mock_tokenizer

        def fake_model_load(*_args, **kwargs):
            if kwargs.get("local_files_only"):
                raise OSError("not cached")
            return mock_model

        engine = NeuralEngine("ur", "roman")
        with patch("ccgen.utils.download_progress.time.sleep"):
            with patch("ccgen.engines.transliteration.neural_engine.download_progress"):
                with patch(
                    "ccgen.engines.transliteration.neural_engine.AutoTokenizer.from_pretrained",
                    side_effect=flaky_tokenizer_load,
                ):
                    with patch(
                        "ccgen.engines.transliteration.neural_engine.M2M100ForConditionalGeneration.from_pretrained",
                        side_effect=fake_model_load,
                    ):
                        engine._load_m2m100(("ur", "roman"), None, None)

        assert tokenizer_attempts["count"] == 2
        assert engine._m2m_tokenizer is mock_tokenizer


class TestTransliterateSegments:
    def test_progress_num_cb_called_once_per_segment_one_indexed(self):
        mock_tokenizer = MagicMock()
        mock_tokenizer.convert_tokens_to_ids.side_effect = lambda token: {
            "__ur__": 1, "__roman-ur__": 2,
        }[token]
        mock_tokenizer.return_value = {"input_ids": [10]}
        mock_tokenizer.eos_token_id = 0
        mock_tokenizer.decode.return_value = "converted"
        mock_model = MagicMock()
        mock_model.generate.return_value = [[0, 1]]

        engine = NeuralEngine("ur", "roman")
        segments: list[Segment] = [
            {"id": 0, "start": 0.0, "end": 1.0, "text": "a", "words": [], "language": "ur"},
            {"id": 1, "start": 1.0, "end": 2.0, "text": "b", "words": [], "language": "ur"},
            {"id": 2, "start": 2.0, "end": 3.0, "text": "c", "words": [], "language": "ur"},
        ]
        progress_num_cb = MagicMock()

        with patch(
            "ccgen.engines.transliteration.neural_engine.AutoTokenizer.from_pretrained",
            return_value=mock_tokenizer,
        ):
            with patch(
                "ccgen.engines.transliteration.neural_engine.M2M100ForConditionalGeneration.from_pretrained",
                return_value=mock_model,
            ):
                engine.transliterate_segments(segments, progress_num_cb=progress_num_cb)

        assert progress_num_cb.call_args_list == [call(1, 3), call(2, 3), call(3, 3)]

    def test_segment_cb_receives_each_transliterated_segment(self):
        mock_tokenizer = MagicMock()
        mock_tokenizer.convert_tokens_to_ids.side_effect = lambda token: {
            "__ur__": 1, "__roman-ur__": 2,
        }[token]
        mock_tokenizer.return_value = {"input_ids": [10]}
        mock_tokenizer.eos_token_id = 0
        mock_tokenizer.decode.return_value = "converted"
        mock_model = MagicMock()
        mock_model.generate.return_value = [[0, 1]]

        engine = NeuralEngine("ur", "roman")
        segments: list[Segment] = [
            {"id": 0, "start": 0.0, "end": 1.0, "text": "a", "words": [], "language": "ur"},
        ]
        received = []

        with patch(
            "ccgen.engines.transliteration.neural_engine.AutoTokenizer.from_pretrained",
            return_value=mock_tokenizer,
        ):
            with patch(
                "ccgen.engines.transliteration.neural_engine.M2M100ForConditionalGeneration.from_pretrained",
                return_value=mock_model,
            ):
                engine.transliterate_segments(segments, segment_cb=received.append)

        assert len(received) == 1
        assert received[0]["id"] == 0
        assert received[0]["transliterated"] == "converted"


class TestConvertText:
    def test_pa_routes_through_sanscript_before_rekhta(self):
        engine = NeuralEngine("pa", "ur")
        with patch(
            "ccgen.engines.transliteration.neural_engine.sanscript.transliterate",
            return_value="devanagari-text",
        ) as mock_translit:
            with patch.object(engine._rekhta, "convert", return_value="urdu-text") as mock_convert:
                result = engine._convert_text("gurmukhi-text")
        mock_translit.assert_called_once_with(
            "gurmukhi-text", sanscript.GURMUKHI, sanscript.DEVANAGARI,
        )
        mock_convert.assert_called_once_with("devanagari-text")
        assert result == "urdu-text"

    def test_hi_routes_straight_to_rekhta(self):
        engine = NeuralEngine("hi", "ur")
        with patch(
            "ccgen.engines.transliteration.neural_engine.sanscript.transliterate",
        ) as mock_translit:
            with patch.object(engine._rekhta, "convert", return_value="urdu-text") as mock_convert:
                result = engine._convert_text("hindi-text")
        mock_translit.assert_not_called()
        mock_convert.assert_called_once_with("hindi-text")
        assert result == "urdu-text"
