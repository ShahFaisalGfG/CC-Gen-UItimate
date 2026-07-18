# test_download_progress.py — unit tests for ccgen.utils.download_progress

from unittest.mock import MagicMock, patch

import argostranslate.networking as argos_networking
import faster_whisper.utils as fw_utils
import pytest

from ccgen.utils.download_progress import (
    _ReportingTqdm,
    _hf_tqdm_module,
    _report_bytes,
    _streaming_get,
    download_progress,
)


def _monotonic_sequence(values):
    """Return a side_effect function that yields `values` then repeats the last one."""
    iterator = iter(values)

    def _next_value(*_args, **_kwargs):
        try:
            return next(iterator)
        except StopIteration:
            return values[-1]

    return _next_value


class TestDownloadProgressPatching:
    def test_patches_fw_disabled_tqdm(self):
        original = fw_utils.disabled_tqdm
        with download_progress(lambda done, total: None):
            assert fw_utils.disabled_tqdm is _ReportingTqdm
        assert fw_utils.disabled_tqdm is original

    def test_patches_hf_tqdm_module(self):
        original = _hf_tqdm_module.tqdm
        with download_progress(lambda done, total: None):
            assert _hf_tqdm_module.tqdm is _ReportingTqdm
        assert _hf_tqdm_module.tqdm is original

    def test_patches_argos_networking_get(self):
        original = argos_networking.get
        with download_progress(lambda done, total: None):
            assert argos_networking.get is _streaming_get
        assert argos_networking.get is original

    def test_restores_all_patches_on_exception(self):
        original_fw = fw_utils.disabled_tqdm
        original_hf = _hf_tqdm_module.tqdm
        original_argos = argos_networking.get
        with pytest.raises(ValueError):
            with download_progress(lambda done, total: None):
                raise ValueError("boom")
        assert fw_utils.disabled_tqdm is original_fw
        assert _hf_tqdm_module.tqdm is original_hf
        assert argos_networking.get is original_argos

    def test_callback_none_is_complete_noop(self):
        original_fw = fw_utils.disabled_tqdm
        original_hf = _hf_tqdm_module.tqdm
        original_argos = argos_networking.get
        with download_progress(None):
            assert fw_utils.disabled_tqdm is original_fw
            assert _hf_tqdm_module.tqdm is original_hf
            assert argos_networking.get is original_argos

    def test_nested_context_restores_outer_callback(self):
        outer_calls = []
        inner_calls = []
        with download_progress(lambda done, total: outer_calls.append((done, total))):
            with download_progress(lambda done, total: inner_calls.append((done, total))):
                _report_bytes(1, 2)
            _report_bytes(3, 4)
        assert inner_calls == [(1, 2)]
        assert outer_calls == [(3, 4)]


class TestReportingTqdm:
    def test_forces_disable_true(self):
        with download_progress(lambda done, total: None):
            bar = _ReportingTqdm(total=100, disable=False)
            assert bar.disable is True
            bar.close()

    def test_update_throttles_report_count_by_time(self):
        # bar.n advances on every update() regardless of the disable flag (update() bypasses
        # tqdm's own disabled no-op counting), but reports are throttled by _REPORT_INTERVAL_S.
        reports = []
        with patch(
            "ccgen.utils.download_progress.time.monotonic",
            side_effect=_monotonic_sequence([100.0, 100.05, 100.3]),
        ):
            with download_progress(lambda done, total: reports.append((done, total))):
                bar = _ReportingTqdm(total=100)
                bar.update(10)
                bar.update(10)
                bar.update(10)
        assert reports == [(10, 100), (30, 100)]

    def test_close_forces_final_report(self):
        reports = []
        with patch(
            "ccgen.utils.download_progress.time.monotonic",
            side_effect=_monotonic_sequence([100.0, 100.01]),
        ):
            with download_progress(lambda done, total: reports.append((done, total))):
                bar = _ReportingTqdm(total=100)
                bar.update(10)
                bar.close()
        assert reports == [(10, 100), (10, 100)]

    def test_callback_exception_is_swallowed(self):
        def bad_callback(done, total):
            raise RuntimeError("callback exploded")

        with download_progress(bad_callback):
            bar = _ReportingTqdm(total=100)
            bar.update(10)
            bar.close()


class TestStreamingGet:
    def _make_response(self, chunks, content_length):
        response = MagicMock()
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        response.headers.get.return_value = content_length
        response.read.side_effect = chunks
        return response

    def test_returns_concatenated_chunks_with_growing_progress(self):
        response = self._make_response([b"abc", b"def", b""], "6")
        progress = []
        with patch("ccgen.utils.download_progress.urllib.request.urlopen", return_value=response):
            with download_progress(lambda done, total: progress.append((done, total))):
                result = _streaming_get("http://example.com/file")
        assert result == b"abcdef"
        assert progress == [(3, 6), (6, 6)]

    def test_missing_content_length_defaults_total_to_zero(self):
        response = self._make_response([b"ab", b""], None)
        progress = []
        with patch("ccgen.utils.download_progress.urllib.request.urlopen", return_value=response):
            with download_progress(lambda done, total: progress.append((done, total))):
                _streaming_get("http://example.com/file")
        assert progress == [(2, 0)]

    def test_returns_none_after_retries_exhausted(self):
        with patch(
            "ccgen.utils.download_progress.urllib.request.urlopen",
            side_effect=OSError("network unreachable"),
        ):
            result = _streaming_get("http://example.com/file", retry_count=1)
        assert result is None
