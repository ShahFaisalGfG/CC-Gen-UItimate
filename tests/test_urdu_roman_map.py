# test_urdu_roman_map.py — unit tests for ccgen.engines.transliteration.urdu_roman_map

from ccgen.engines.transliteration.urdu_roman_map import roman_to_urdu, urdu_to_roman


class TestUrduToRoman:
    def test_known_words_use_word_map(self):
        assert urdu_to_roman("کیا حال ہے") == "kya haal hai"

    def test_unknown_word_falls_back_to_char_map(self):
        assert urdu_to_roman("زبان") == "zban"

    def test_preserves_whitespace_runs(self):
        assert urdu_to_roman("کیا   حال") == "kya   haal"

    def test_trailing_punctuation_converted(self):
        assert urdu_to_roman("کیا؟") == "kya?"

    def test_empty_string(self):
        assert urdu_to_roman("") == ""


class TestRomanToUrdu:
    def test_known_words_use_word_map(self):
        assert roman_to_urdu("kya haal hai") == "کیا حال ہے"

    def test_unknown_word_falls_back_to_char_map(self):
        assert roman_to_urdu("zar") == "زار"

    def test_digraph_priority_over_single_chars(self):
        assert roman_to_urdu("khan") == "خان"

    def test_aa_digraph(self):
        assert roman_to_urdu("baat") == "بآت"

    def test_case_insensitive_lookup(self):
        assert roman_to_urdu("KYA") == "کیا"

    def test_trailing_punctuation_converted(self):
        assert roman_to_urdu("kya?") == "کیا؟"

    def test_empty_string(self):
        assert roman_to_urdu("") == ""


class TestRoundTrip:
    def test_urdu_roman_urdu_word_map_round_trip(self):
        original = "کیا حال ہے"
        assert roman_to_urdu(urdu_to_roman(original)) == original
