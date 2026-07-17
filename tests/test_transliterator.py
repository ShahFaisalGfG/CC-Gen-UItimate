# test_transliterator.py — unit tests for ccgen.engines.transliteration

import re
from unittest.mock import MagicMock, patch

import pytest

from ccgen.engines.transliteration import create_engine
from ccgen.engines.transliteration.neural_engine import NeuralEngine
from ccgen.engines.transliteration.rule_engine import RuleEngine, strip_diacritics
from ccgen.engines.transliteration.urdu_roman_map import roman_to_urdu, urdu_to_roman

_ARABIC_RANGE = re.compile(r"[؀-ۿ]")


class TestStripDiacritics:
    def test_removes_harakat(self):
        # Exact garbled sample captured from the live library before this fix.
        assert strip_diacritics("تَُمَ کَےسَے ہَو") == "تم کےسے ہو"

    def test_leaves_plain_text_untouched(self):
        assert strip_diacritics("تم کیسے ہو") == "تم کیسے ہو"


class TestUrduRomanMap:
    def test_urdu_to_roman_dictionary_words(self):
        result = urdu_to_roman("کیا حال ہے پیارے؟")
        assert result == "kya haal hai piyare?"

    def test_urdu_to_roman_has_no_leftover_arabic_script(self):
        # Regression guard: sanscript+IAST used to leave most Arabic glyphs untouched.
        result = urdu_to_roman("کیا حال ہے پیارے؟ تم کیسے ہو")
        assert not _ARABIC_RANGE.search(result)

    def test_roman_to_urdu_dictionary_words(self):
        assert roman_to_urdu("kya hai") == "کیا ہے"


class TestRuleEngine:
    def test_ur_to_roman_matches_user_example(self):
        engine = RuleEngine(source_scheme="ur", target_scheme="roman")
        result = engine.transliterate_segments([
            {"id": 0, "start": 0.0, "end": 1.0, "text": "کیا حال ہے پیارے؟"},
        ])
        assert result[0]["transliterated"] == "kya haal hai piyare?"
        assert result[0]["source_scheme"] == "ur"
        assert result[0]["target_scheme"] == "roman"

    def test_ur_to_roman_never_leaves_arabic_script(self):
        engine = RuleEngine(source_scheme="ur", target_scheme="roman")
        result = engine.transliterate_segments([
            {"id": 0, "start": 0.0, "end": 1.0, "text": "زندگی میں بہت کام ہے"},
        ])
        assert not _ARABIC_RANGE.search(result[0]["transliterated"])

    def test_hi_to_ur_strips_diacritics(self):
        engine = RuleEngine(source_scheme="hi", target_scheme="ur")
        result = engine.transliterate_segments([
            {"id": 0, "start": 0.0, "end": 1.0, "text": "तुम कैसे हो"},
        ])
        assert not re.search(r"[ً-ْ]", result[0]["transliterated"])

    def test_transliterates_translated_segment_text(self):
        engine = RuleEngine(source_scheme="ur", target_scheme="roman")
        result = engine.transliterate_segments([
            {"id": 0, "start": 0.0, "end": 1.0, "original": "hi", "translated": "ہاں"},
        ])
        assert result[0]["transliterated"] == "haan"

    def test_unknown_scheme_raises(self):
        engine = RuleEngine(source_scheme="xx", target_scheme="ur")
        with pytest.raises(RuntimeError):
            engine.transliterate_segments([{"id": 0, "start": 0.0, "end": 1.0, "text": "a"}])


class TestNeuralEngine:
    def test_ur_to_roman_uses_mocked_m2m100(self):
        engine = NeuralEngine(source_scheme="ur", target_scheme="roman")
        mock_tokenizer = MagicMock()
        mock_tokenizer.convert_tokens_to_ids.side_effect = lambda tok: {
            "__ur__": 128095, "__roman-ur__": 128105,
        }[tok]
        mock_tokenizer.return_value = {"input_ids": [10, 11, 12]}
        mock_tokenizer.eos_token_id = 2
        mock_tokenizer.decode.return_value = "kya haal hai"

        mock_model = MagicMock()
        mock_model.generate.return_value = [[0, 1, 2]]

        with patch(
            "ccgen.engines.transliteration.neural_engine.AutoTokenizer.from_pretrained",
            return_value=mock_tokenizer,
        ):
            with patch(
                "ccgen.engines.transliteration.neural_engine.M2M100ForConditionalGeneration.from_pretrained",
                return_value=mock_model,
            ):
                result = engine.transliterate_segments([
                    {"id": 0, "start": 0.0, "end": 1.0, "text": "کیا حال ہے"},
                ])

        assert result[0]["transliterated"] == "kya haal hai"
        mock_model.generate.assert_called_once()
        assert mock_model.generate.call_args.kwargs["forced_bos_token_id"] == 128105

    def test_hi_to_ur_uses_rekhta_backend(self):
        engine = NeuralEngine(source_scheme="hi", target_scheme="ur")
        with patch.object(engine._rekhta, "load") as mock_load:
            with patch.object(engine._rekhta, "convert", return_value="تم کیسے ہو") as mock_convert:
                result = engine.transliterate_segments([
                    {"id": 0, "start": 0.0, "end": 1.0, "text": "तुम कैसे हो"},
                ])
        mock_load.assert_called_once()
        mock_convert.assert_called_once_with("तुम कैसे हो")
        assert result[0]["transliterated"] == "تم کیسے ہو"

    def test_unsupported_pair_raises(self):
        engine = NeuralEngine(source_scheme="bn", target_scheme="roman")
        with pytest.raises(RuntimeError):
            engine.transliterate_segments([{"id": 0, "start": 0.0, "end": 1.0, "text": "a"}])


class TestRegistry:
    def test_create_rule_engine(self):
        engine = create_engine("rule", source_scheme="ur", target_scheme="roman")
        assert isinstance(engine, RuleEngine)

    def test_create_neural_engine(self):
        engine = create_engine("neural", source_scheme="ur", target_scheme="roman")
        assert isinstance(engine, NeuralEngine)

    def test_unknown_engine_raises(self):
        with pytest.raises(ValueError, match="Unknown transliteration engine"):
            create_engine("bogus", source_scheme="ur", target_scheme="roman")
