# test_rule_engine.py — unit tests for ccgen.engines.transliteration.rule_engine

import pytest

from ccgen.core import Segment, TranslatedSegment
from ccgen.engines.transliteration.rule_engine import RuleEngine, strip_diacritics


def _segment(text: str, seg_id: int = 0) -> Segment:
    return Segment(id=seg_id, start=0.0, end=1.0, text=text, words=[], language="x")


def _translated_segment(translated: str, seg_id: int = 0) -> TranslatedSegment:
    return TranslatedSegment(id=seg_id, start=0.0, end=1.0, original="x", translated=translated, language="x")


class TestUrduToRoman:
    def test_word_map_lookup(self):
        engine = RuleEngine("ur", "roman")
        result = engine.transliterate_segments([_segment("کیا حال ہے")])
        assert result[0]["transliterated"] == "kya haal hai"

    def test_preserves_timing_and_schemes(self):
        engine = RuleEngine("ur", "roman")
        result = engine.transliterate_segments([_segment("شکریہ")])
        seg = result[0]
        assert seg["id"] == 0
        assert seg["start"] == 0.0
        assert seg["end"] == 1.0
        assert seg["original"] == "شکریہ"
        assert seg["source_scheme"] == "ur"
        assert seg["target_scheme"] == "roman"


class TestRomanToUrdu:
    def test_word_map_lookup(self):
        engine = RuleEngine("roman", "ur")
        result = engine.transliterate_segments([_segment("kya haal hai")])
        assert result[0]["transliterated"] == "کیا حال ہے"


class TestSanscriptSchemes:
    def test_hindi_to_urdu_strips_diacritics(self):
        engine = RuleEngine("hi", "ur")
        result = engine.transliterate_segments([_segment("नमस्ते")])
        assert result[0]["transliterated"] == "نمستے"

    def test_bengali_to_roman(self):
        engine = RuleEngine("bn", "roman")
        result = engine.transliterate_segments([_segment("নমস্তে")])
        assert result[0]["transliterated"] == "namaste"


class TestTranslatedSegmentInput:
    def test_uses_translated_field_when_present(self):
        engine = RuleEngine("ur", "roman")
        result = engine.transliterate_segments([_translated_segment("کیا حال ہے")])
        assert result[0]["transliterated"] == "kya haal hai"
        assert result[0]["original"] == "کیا حال ہے"


class TestStripDiacritics:
    def test_removes_diacritics(self):
        assert strip_diacritics("نَمَسَْتَے") == "نمستے"

    def test_leaves_plain_text_unchanged(self):
        assert strip_diacritics("سلام") == "سلام"


class TestUnknownScheme:
    def test_resolve_raises_value_error(self):
        engine = RuleEngine("xx", "roman")
        with pytest.raises(ValueError, match="Unknown transliteration scheme"):
            engine._resolve("xx")

    def test_transliterate_segments_wraps_in_runtime_error(self):
        engine = RuleEngine("xx", "roman")
        with pytest.raises(RuntimeError, match="Unknown transliteration scheme"):
            engine.transliterate_segments([_segment("abc")])


class TestProgressCallbacks:
    def test_progress_num_cb_called_per_segment(self):
        engine = RuleEngine("ur", "roman")
        segments = [_segment("کیا", 0), _segment("شکریہ", 1)]
        calls = []
        engine.transliterate_segments(segments, progress_num_cb=lambda done, total: calls.append((done, total)))
        assert calls == [(1, 2), (2, 2)]

    def test_progress_cb_called_with_message(self):
        engine = RuleEngine("ur", "roman")
        messages = []
        engine.transliterate_segments([_segment("کیا")], progress_cb=messages.append)
        assert messages == ["Transliterated segment 1"]

    def test_no_callbacks_required(self):
        engine = RuleEngine("ur", "roman")
        result = engine.transliterate_segments([_segment("کیا")])
        assert len(result) == 1


class TestSetSchemes:
    def test_updates_source_and_target(self):
        engine = RuleEngine("ur", "roman")
        engine.set_schemes("roman", "ur")
        result = engine.transliterate_segments([_segment("kya")])
        assert result[0]["transliterated"] == "کیا"
        assert result[0]["source_scheme"] == "roman"
        assert result[0]["target_scheme"] == "ur"
