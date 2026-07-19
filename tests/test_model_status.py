# test_model_status.py — unit tests for ccgen.utils.model_status

from unittest.mock import MagicMock, patch

from ccgen.utils.model_status import (
    neural_translit_cached,
    translation_pair_cached,
    whisper_cached,
)


class _FakeRepo:
    def __init__(self, repo_id, repo_path):
        self.repo_id = repo_id
        self.repo_path = repo_path


class _FakePackage:
    def __init__(self, from_code, to_code):
        self.from_code = from_code
        self.to_code = to_code


def _fake_cache(repo_ids, repo_path="/nonexistent"):
    """Build a fake huggingface_hub CacheInfo-like object with the given repo ids.

    `repo_path` defaults to a directory with no `blobs/*.incomplete` files, so callers
    that only care about presence/absence don't need to think about completeness.
    """
    cache_info = MagicMock()
    cache_info.repos = [_FakeRepo(repo_id, repo_path) for repo_id in repo_ids]
    return cache_info


class TestWhisperCached:
    def test_known_model_present_in_cache(self):
        cache = _fake_cache(["Systran/faster-whisper-tiny"])
        with patch("ccgen.utils.model_status.scan_cache_dir", return_value=cache):
            assert whisper_cached("tiny") is True

    def test_known_model_absent_from_cache(self):
        with patch("ccgen.utils.model_status.scan_cache_dir", return_value=_fake_cache([])):
            assert whisper_cached("tiny") is False

    def test_unknown_model_name_skips_cache_scan(self):
        mock_scan = MagicMock()
        with patch("ccgen.utils.model_status.scan_cache_dir", mock_scan):
            assert whisper_cached("not-a-real-model") is False
        mock_scan.assert_not_called()


class TestNeuralTranslitCached:
    def test_ur_to_roman_both_repos_cached(self):
        repos = ["Mavkif/m2m100_rup_tokenizer_both", "Mavkif/m2m100_rup_ur_to_rur"]
        with patch("ccgen.utils.model_status.scan_cache_dir", return_value=_fake_cache(repos)):
            assert neural_translit_cached("ur", "roman") is True

    def test_ur_to_roman_missing_tokenizer_repo(self):
        cache = _fake_cache(["Mavkif/m2m100_rup_ur_to_rur"])
        with patch("ccgen.utils.model_status.scan_cache_dir", return_value=cache):
            assert neural_translit_cached("ur", "roman") is False

    def test_roman_to_ur_both_repos_cached(self):
        repos = ["Mavkif/m2m100_rup_tokenizer_both", "Mavkif/m2m100_rup_rur_to_ur"]
        with patch("ccgen.utils.model_status.scan_cache_dir", return_value=_fake_cache(repos)):
            assert neural_translit_cached("roman", "ur") is True

    def test_hi_to_ur_uses_rekhta_repo(self):
        cache = _fake_cache(["rekhtalabs/hi-2-ur-translit"])
        with patch("ccgen.utils.model_status.scan_cache_dir", return_value=cache):
            assert neural_translit_cached("hi", "ur") is True

    def test_pa_to_ur_uses_rekhta_repo(self):
        with patch("ccgen.utils.model_status.scan_cache_dir", return_value=_fake_cache([])):
            assert neural_translit_cached("pa", "ur") is False

    def test_unsupported_pair_skips_cache_scan(self):
        mock_scan = MagicMock()
        with patch("ccgen.utils.model_status.scan_cache_dir", mock_scan):
            assert neural_translit_cached("bn", "roman") is False
        mock_scan.assert_not_called()


class TestTranslationPairCached:
    def test_explicit_source_requires_exact_match(self):
        installed = [_FakePackage("en", "es")]
        with patch(
            "ccgen.utils.model_status.argostranslate.package.get_installed_packages",
            return_value=installed,
        ):
            assert translation_pair_cached("en", "es") is True
            assert translation_pair_cached("fr", "es") is False

    def test_empty_source_matches_any_installed_target(self):
        installed = [_FakePackage("fr", "es")]
        with patch(
            "ccgen.utils.model_status.argostranslate.package.get_installed_packages",
            return_value=installed,
        ):
            assert translation_pair_cached("", "es") is True
            assert translation_pair_cached("", "de") is False

    def test_get_installed_packages_exception_returns_false(self):
        with patch(
            "ccgen.utils.model_status.argostranslate.package.get_installed_packages",
            side_effect=RuntimeError("packages index unreadable"),
        ):
            assert translation_pair_cached("en", "es") is False


class TestRepoCachedErrorHandling:
    def test_scan_cache_dir_exception_returns_false(self):
        with patch(
            "ccgen.utils.model_status.scan_cache_dir",
            side_effect=OSError("cache dir missing"),
        ):
            assert whisper_cached("tiny") is False


class TestRepoCachedIncompleteDownload:
    def test_stray_incomplete_blob_reports_not_cached(self, tmp_path):
        # An app crash or force-close mid-download leaves the small metadata files
        # resolved but the large weight file as a stray `.incomplete` blob with no
        # snapshot symlink - scan_cache_dir() still lists the repo, so this must not
        # read as "downloaded" even though some files are genuinely present.
        (tmp_path / "blobs").mkdir()
        (tmp_path / "blobs" / "abc123.incomplete").write_bytes(b"partial")
        cache = _fake_cache(["Systran/faster-whisper-tiny"], repo_path=str(tmp_path))
        with patch("ccgen.utils.model_status.scan_cache_dir", return_value=cache):
            assert whisper_cached("tiny") is False

    def test_no_incomplete_blob_reports_cached(self, tmp_path):
        (tmp_path / "blobs").mkdir()
        (tmp_path / "blobs" / "abc123").write_bytes(b"complete")
        cache = _fake_cache(["Systran/faster-whisper-tiny"], repo_path=str(tmp_path))
        with patch("ccgen.utils.model_status.scan_cache_dir", return_value=cache):
            assert whisper_cached("tiny") is True
