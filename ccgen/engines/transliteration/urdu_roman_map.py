# urdu_roman_map.py — dedicated Urdu (Nastaliq) <-> Roman Urdu character/word converter
#
# indic-transliteration's "urdu" scheme is built for its Sanskrit-derived phonemic framework
# and does not produce colloquial Roman Urdu (verified: it barely converts real Urdu text at
# all when paired with IAST). This module replaces that pair with a purpose-built converter:
# common words are looked up whole (spelling doesn't follow letter-by-letter phonetics), and
# anything else falls back to a per-character map.

import re

_WORD_MAP: dict[str, str] = {
    "کیا": "kya", "حال": "haal", "ہے": "hai", "پیارے": "piyare", "ہو": "ho",
    "تم": "tum", "میں": "mein", "نہیں": "nahi", "ہاں": "haan", "کیسے": "kaise",
    "کیوں": "kyun", "کہاں": "kahan", "کب": "kab", "کون": "kaun", "یہ": "yeh",
    "وہ": "woh", "اور": "aur", "کی": "ki", "کا": "ka", "کے": "ke",
    "سے": "se", "پر": "par", "کو": "ko", "ایک": "ek", "بہت": "bohat",
    "اچھا": "acha", "شکریہ": "shukriya", "خدا": "khuda", "حافظ": "hafiz",
    "سلام": "salam", "وقت": "waqt", "دن": "din", "رات": "raat", "پانی": "pani",
    "کھانا": "khana", "جانا": "jana", "آنا": "aana", "کرنا": "karna", "ہونا": "hona",
    "میرا": "mera", "تیرا": "tera", "اپنا": "apna", "دوست": "dost", "گھر": "ghar",
    "کام": "kaam", "زندگی": "zindagi", "محبت": "mohabbat", "خوش": "khush", "غم": "gham",
}

_CHAR_MAP: dict[str, str] = {
    "ا": "a", "آ": "aa", "أ": "a", "إ": "i",
    "ب": "b", "پ": "p", "ت": "t", "ٹ": "t", "ث": "s",
    "ج": "j", "چ": "ch", "ح": "h", "خ": "kh",
    "د": "d", "ڈ": "d", "ذ": "z",
    "ر": "r", "ڑ": "r", "ز": "z", "ژ": "zh",
    "س": "s", "ش": "sh", "ص": "s", "ض": "z",
    "ط": "t", "ظ": "z", "ع": "a", "غ": "gh",
    "ف": "f", "ق": "q", "ک": "k", "گ": "g",
    "ل": "l", "م": "m", "ن": "n", "ں": "n",
    "و": "o", "ہ": "h", "ھ": "h", "ء": "'",
    "ی": "i", "ے": "e",
    "؟": "?", "،": ",", "۔": ".",
}

_REVERSE_WORD_MAP: dict[str, str] = {roman: urdu for urdu, roman in _WORD_MAP.items()}

_ROMAN_MULTI_CHAR: list[tuple[str, str]] = [
    ("kh", "خ"), ("gh", "غ"), ("sh", "ش"), ("ch", "چ"), ("zh", "ژ"), ("aa", "آ"),
]
_ROMAN_SINGLE_CHAR: dict[str, str] = {
    "a": "ا", "b": "ب", "p": "پ", "t": "ت", "s": "س", "j": "ج", "h": "ہ",
    "d": "د", "z": "ز", "r": "ر", "f": "ف", "q": "ق", "k": "ک", "g": "گ",
    "l": "ل", "m": "م", "n": "ن", "o": "و", "u": "و", "i": "ی", "e": "ے",
    "w": "و", "y": "ی",
}

_TOKEN_RE = re.compile(r"\S+|\s+")
_TRAILING_PUNCT = "؟،۔?,.!"
_REVERSE_PUNCT_MAP: dict[str, str] = {"?": "؟", ",": "،", ".": "۔"}


def urdu_to_roman(text: str) -> str:
    """Convert Urdu (Nastaliq) text to informal Roman Urdu, word-dictionary first."""
    return "".join(_urdu_word_to_roman(tok) for tok in _TOKEN_RE.findall(text))


def roman_to_urdu(text: str) -> str:
    """Convert Roman Urdu text back to Urdu (Nastaliq) script, best-effort."""
    return "".join(_roman_word_to_urdu(tok) for tok in _TOKEN_RE.findall(text))


def _urdu_word_to_roman(token: str) -> str:
    """Romanize one whitespace-delimited token, using the word map when possible."""
    if token.isspace():
        return token
    core, trailing = _split_trailing(token, _TRAILING_PUNCT)
    mapped = _WORD_MAP.get(core)
    if mapped is None:
        mapped = "".join(_CHAR_MAP.get(ch, ch) for ch in core)
    trailing = "".join(_CHAR_MAP.get(ch, ch) for ch in trailing)
    return mapped + trailing


def _roman_word_to_urdu(token: str) -> str:
    """Convert one whitespace-delimited Roman token back to Urdu script."""
    if token.isspace():
        return token
    core, trailing = _split_trailing(token, ".,!?")
    mapped = _REVERSE_WORD_MAP.get(core.lower())
    if mapped is None:
        mapped = _romanize_chars(core.lower())
    trailing = "".join(_REVERSE_PUNCT_MAP.get(ch, ch) for ch in trailing)
    return mapped + trailing


def _romanize_chars(word: str) -> str:
    """Greedily match multi-character digraphs before falling back to single characters."""
    out: list[str] = []
    i = 0
    while i < len(word):
        matched = False
        for digraph, urdu_char in _ROMAN_MULTI_CHAR:
            if word.startswith(digraph, i):
                out.append(urdu_char)
                i += len(digraph)
                matched = True
                break
        if matched:
            continue
        out.append(_ROMAN_SINGLE_CHAR.get(word[i], word[i]))
        i += 1
    return "".join(out)


def _split_trailing(token: str, punctuation: str) -> tuple[str, str]:
    """Split a token into its core text and any trailing punctuation."""
    stripped = token.rstrip(punctuation)
    return stripped, token[len(stripped):]
