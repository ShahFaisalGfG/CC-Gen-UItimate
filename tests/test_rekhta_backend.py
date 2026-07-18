# test_rekhta_backend.py — unit tests for ccgen.engines.transliteration.rekhta_backend

from collections import OrderedDict
from unittest.mock import MagicMock, patch

import pytest

from ccgen.engines.transliteration.rekhta_backend import RekhtaBackend, _CharTransformer


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


class TestConvertBeforeLoad:
    def test_raises_runtime_error(self):
        backend = RekhtaBackend()
        with pytest.raises(RuntimeError, match="Call load"):
            backend.convert("text")


class TestLoad:
    def test_wraps_all_three_downloads_in_one_progress_context(self):
        call_order = []
        vocab_size = 6

        def fake_hub_download(_repo_id, filename):
            call_order.append(f"download:{filename}")
            return f"/fake/{filename}"

        template = _CharTransformer(vocab_size, vocab_size)
        checkpoint = {
            "model_state_dict": OrderedDict(
                (f"module.{name}", tensor) for name, tensor in template.state_dict().items()
            ),
        }
        mock_sp = MagicMock()
        mock_sp.get_piece_size.return_value = vocab_size

        backend = RekhtaBackend()
        with patch(
            "ccgen.engines.transliteration.rekhta_backend.hf_hub_download",
            side_effect=fake_hub_download,
        ):
            with patch(
                "ccgen.engines.transliteration.rekhta_backend.download_progress",
                side_effect=_tracking_download_progress(call_order),
            ):
                with patch(
                    "ccgen.engines.transliteration.rekhta_backend.spm.SentencePieceProcessor",
                    return_value=mock_sp,
                ):
                    with patch(
                        "ccgen.engines.transliteration.rekhta_backend.torch.load",
                        return_value=checkpoint,
                    ):
                        backend.load()

        assert call_order == [
            "enter",
            "download:h2u_2.0.pt",
            "download:devanagari_bpe.model",
            "download:nastaaliq_bpe.model",
            "exit",
        ]
        assert isinstance(backend._model, _CharTransformer)

    def test_download_failure_raises_runtime_error_with_cause(self):
        backend = RekhtaBackend()
        with patch(
            "ccgen.engines.transliteration.rekhta_backend.hf_hub_download",
            side_effect=OSError("network unreachable"),
        ):
            with pytest.raises(RuntimeError, match="model load failed") as exc_info:
                backend.load()
        assert isinstance(exc_info.value.__cause__, OSError)


class TestConvertEndToEnd:
    def test_generates_output_using_real_tiny_model(self):
        vocab_size = 8
        model = _CharTransformer(
            vocab_size, vocab_size,
            d_model=8, nhead=2, num_layers=1, dim_feedforward=16, max_len=8,
        )
        model.eval()
        backend = RekhtaBackend()
        backend._model = model
        backend._src_sp = MagicMock()
        backend._src_sp.encode.return_value = [4, 5]
        backend._tgt_sp = MagicMock()
        backend._tgt_sp.decode.return_value = "converted-text"

        with patch("ccgen.engines.transliteration.rekhta_backend._MAX_LEN", 4):
            result = backend.convert("source text")

        assert result == "converted-text"
        backend._src_sp.encode.assert_called_once_with("source text")
        backend._tgt_sp.decode.assert_called_once()
