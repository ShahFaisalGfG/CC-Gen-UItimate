# test_download_progress.py — unit tests for ccgen.utils.download_progress

import threading
from unittest.mock import MagicMock, patch

import argostranslate.networking as argos_networking
import faster_whisper.utils as fw_utils
import pytest
from huggingface_hub import constants as hf_constants

from ccgen.utils.download_progress import (
    _HF_DOWNLOAD_CHUNK_SIZE,
    DownloadCancelled,
    _ReportingTqdm,
    _hf_snapshot_module,
    _hf_tqdm_module,
    _report_bytes,
    _streaming_get,
    cancellable,
    download_progress,
    retry_hf_load,
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

    def test_patches_hf_snapshot_module_hf_tqdm(self):
        # huggingface_hub._snapshot_download does `from .utils.tqdm import tqdm as hf_tqdm` at
        # import time and passes a caller's tqdm_class straight through for its aggregate
        # byte-progress bar - patching only huggingface_hub.utils.tqdm's own `tqdm` attribute
        # (test_patches_hf_tqdm_module above) never reaches this already-bound name, which is
        # exactly what left Whisper model downloads (routed through snapshot_download) with no
        # progress reporting at all.
        original = _hf_snapshot_module.hf_tqdm
        with download_progress(lambda done, total: None):
            assert _hf_snapshot_module.hf_tqdm is _ReportingTqdm
        assert _hf_snapshot_module.hf_tqdm is original

    def test_patches_argos_networking_get(self):
        original = argos_networking.get
        with download_progress(lambda done, total: None):
            assert argos_networking.get is _streaming_get
        assert argos_networking.get is original

    def test_shrinks_hf_download_chunk_size(self):
        # huggingface_hub's http_get() fires exactly one tqdm.update() per chunk read, so its
        # 10 MB default can cover a large fraction of a small model in a single jump - showing
        # as "stuck" then leaping to 100%. Shrinking it while active makes real transfers
        # report much more often.
        original = hf_constants.DOWNLOAD_CHUNK_SIZE
        with download_progress(lambda done, total: None):
            assert hf_constants.DOWNLOAD_CHUNK_SIZE == _HF_DOWNLOAD_CHUNK_SIZE
            assert hf_constants.DOWNLOAD_CHUNK_SIZE < original
        assert hf_constants.DOWNLOAD_CHUNK_SIZE == original

    def test_restores_all_patches_on_exception(self):
        original_fw = fw_utils.disabled_tqdm
        original_hf = _hf_tqdm_module.tqdm
        original_hf_snapshot = _hf_snapshot_module.hf_tqdm
        original_argos = argos_networking.get
        original_chunk_size = hf_constants.DOWNLOAD_CHUNK_SIZE
        with pytest.raises(ValueError):
            with download_progress(lambda done, total: None):
                raise ValueError("boom")
        assert fw_utils.disabled_tqdm is original_fw
        assert _hf_tqdm_module.tqdm is original_hf
        assert _hf_snapshot_module.hf_tqdm is original_hf_snapshot
        assert argos_networking.get is original_argos
        assert hf_constants.DOWNLOAD_CHUNK_SIZE == original_chunk_size

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

    def test_update_throttles_within_interval_but_not_across_it(self):
        # bar.n advances on every update() regardless of the disable flag (update() bypasses
        # tqdm's own disabled no-op counting). Shrinking huggingface_hub's download chunk
        # size (see _HF_DOWNLOAD_CHUNK_SIZE) means real downloads now report far more often,
        # so a modest throttle keeps the UI from being flooded: calls within
        # _REPORT_INTERVAL_S of the last report are dropped, calls at or past it get through.
        reports = []
        with patch(
            "ccgen.utils.download_progress.time.monotonic",
            side_effect=_monotonic_sequence([100.0, 100.05, 100.3]),
        ):
            with download_progress(lambda done, total: reports.append((done, total))):
                bar = _ReportingTqdm(total=100, unit="B")
                bar.update(10)  # t=100.0, first call - always reports
                bar.update(10)  # t=100.05, within the interval - dropped
                bar.update(10)  # t=100.3, past the interval - reports
        assert reports == [(10, 100), (30, 100)]

    def test_close_forces_final_report(self):
        reports = []
        with patch(
            "ccgen.utils.download_progress.time.monotonic",
            side_effect=_monotonic_sequence([100.0, 100.01]),
        ):
            with download_progress(lambda done, total: reports.append((done, total))):
                bar = _ReportingTqdm(total=100, unit="B")
                bar.update(10)
                bar.close()
        assert reports == [(10, 100), (10, 100)]

    def test_callback_exception_is_swallowed(self):
        def bad_callback(done, total):
            raise RuntimeError("callback exploded")

        with download_progress(bad_callback):
            bar = _ReportingTqdm(total=100, unit="B")
            bar.update(10)
            bar.close()

    def test_non_byte_bar_is_never_reported(self):
        # snapshot_download drives a second bar through this same class for its
        # "Fetching N files" count (no unit="B" kwarg) alongside the real byte-progress
        # bar - reporting it would flash a misleading (0, file_count) after a download
        # already reached 100%, so only unit="B" bars may reach the callback.
        reports = []
        with download_progress(lambda done, total: reports.append((done, total))):
            bar = _ReportingTqdm(total=4)
            bar.update(1)
            bar.close()
        assert reports == []

    def test_reports_when_updated_from_a_different_thread(self):
        # huggingface_hub's snapshot_download fans per-file downloads out onto its own
        # ThreadPoolExecutor - the bar is constructed on the thread inside
        # download_progress()'s `with` block, but update()/close() fire from a worker
        # thread that never had `_state.callback` set on it.
        reports = []
        with download_progress(lambda done, total: reports.append((done, total))):
            bar = _ReportingTqdm(total=100, unit="B")
            worker = threading.Thread(target=lambda: (bar.update(50), bar.close()))
            worker.start()
            worker.join()
        assert reports == [(50, 100), (50, 100)]

    def test_update_raises_when_cancelled(self):
        with download_progress(lambda done, total: None):
            with cancellable(lambda: True):
                bar = _ReportingTqdm(total=100, unit="B")
                with pytest.raises(DownloadCancelled):
                    bar.update(10)

    def test_update_does_not_raise_when_not_cancelled(self):
        with download_progress(lambda done, total: None):
            with cancellable(lambda: False):
                bar = _ReportingTqdm(total=100, unit="B")
                bar.update(10)  # must not raise


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

    def test_raises_cancelled_without_retrying(self):
        response = self._make_response([b"ab", b"cd", b""], "4")
        with patch("ccgen.utils.download_progress.urllib.request.urlopen", return_value=response):
            with download_progress(lambda done, total: None):
                with cancellable(lambda: True):
                    with pytest.raises(DownloadCancelled):
                        _streaming_get("http://example.com/file", retry_count=3)
        response.read.assert_called_once()  # bailed after the first chunk, no retry attempts


class TestRetryHfLoad:
    def test_returns_result_on_first_success(self):
        result = retry_hf_load(lambda: "loaded")
        assert result == "loaded"

    def test_retries_after_transient_failure(self):
        attempts = {"count": 0}

        def flaky():
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise OSError("cold download race")
            return "loaded"

        with patch("ccgen.utils.download_progress.time.sleep"):
            result = retry_hf_load(flaky)
        assert result == "loaded"
        assert attempts["count"] == 3

    def test_raises_last_error_after_exhausting_attempts(self):
        def always_fails():
            raise OSError("still failing")

        with patch("ccgen.utils.download_progress.time.sleep"):
            with pytest.raises(OSError, match="still failing"):
                retry_hf_load(always_fails, attempts=2)

    def test_does_not_sleep_after_final_attempt(self):
        with patch("ccgen.utils.download_progress.time.sleep") as mock_sleep:
            with pytest.raises(OSError):
                retry_hf_load(lambda: (_ for _ in ()).throw(OSError("boom")), attempts=2)
        assert mock_sleep.call_count == 1

    def test_reraises_cancelled_without_retrying(self):
        attempts = {"count": 0}

        def cancels_immediately():
            attempts["count"] += 1
            raise DownloadCancelled("cancelled")

        with patch("ccgen.utils.download_progress.time.sleep") as mock_sleep:
            with pytest.raises(DownloadCancelled):
                retry_hf_load(cancels_immediately, attempts=3)
        assert attempts["count"] == 1
        mock_sleep.assert_not_called()


class TestCancellable:
    def test_activates_cancel_check_for_nested_bars(self):
        with download_progress(lambda done, total: None):
            with cancellable(lambda: True):
                bar = _ReportingTqdm(total=100, unit="B")
                assert bar._cancel_check is not None
                assert bar._cancel_check()

    def test_none_is_complete_noop(self):
        with download_progress(lambda done, total: None):
            with cancellable(None):
                bar = _ReportingTqdm(total=100, unit="B")
                assert bar._cancel_check is None

    def test_restores_previous_check_on_exit(self):
        with download_progress(lambda done, total: None):
            with cancellable(lambda: False):
                with cancellable(lambda: True):
                    bar = _ReportingTqdm(total=100, unit="B")
                    assert bar._cancel_check is not None
                    assert bar._cancel_check() is True
                bar = _ReportingTqdm(total=100, unit="B")
                assert bar._cancel_check is not None
                assert bar._cancel_check() is False
