# rekhta_backend.py - vendored Hindi (Devanagari) -> Urdu (Nastaliq) transliteration model
#
# rekhtalabs/hi-2-ur-translit ships as a raw PyTorch checkpoint plus two SentencePiece
# tokenizers, not a standard transformers-format repo, so the model architecture (copied
# verbatim from the model card, verified by running it) is vendored here rather than loaded
# generically via AutoModel.
#
# License note: the upstream repo tags "license: other" with an empty LICENSE file, so usage
# terms are undefined. Included per explicit product decision; revisit if a clearly-licensed
# alternative for this direction becomes available.

import logging
from collections import OrderedDict
from typing import Callable, Optional

import sentencepiece as spm
import torch
from huggingface_hub import hf_hub_download
from torch import nn

from ccgen.config.defaults import ModelRepos
from ccgen.engines.model_cache import ModelCache
from ccgen.utils.callbacks import JobCancelled, emit_status
from ccgen.utils.download_progress import download_progress, retry_hf_load

_log = logging.getLogger(__name__)

_REPO_ID = ModelRepos.REKHTA
_CHECKPOINT_FILE = "h2u_2.0.pt"
_SRC_TOKENIZER_FILE = "devanagari_bpe.model"
_TGT_TOKENIZER_FILE = "nastaaliq_bpe.model"
_MAX_LEN = 128
_BOS_ID = 2
_EOS_ID = 3


class _PositionalEncoding(nn.Module):
    """Sinusoidal positional encoding, matching the trained checkpoint's shape."""

    def __init__(self, d_model: int, max_len: int = 5000) -> None:
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2) * (-torch.log(torch.tensor(10000.0)) / d_model))
        pe[:, 0::2] = torch.sin(position.float() * div_term)
        pe[:, 1::2] = torch.cos(position.float() * div_term)
        self.pe = pe.unsqueeze(0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.pe[:, :x.size(1)].to(x.device)


class _CharTransformer(nn.Module):
    """Character-level Transformer encoder-decoder matching the checkpoint's trained shape."""

    def __init__(
        self,
        src_vocab_size: int,
        tgt_vocab_size: int,
        d_model: int = 256,
        nhead: int = 4,
        num_layers: int = 3,
        dim_feedforward: int = 512,
        max_len: int = _MAX_LEN,
    ) -> None:
        super().__init__()
        self.src_tok_emb = nn.Embedding(src_vocab_size, d_model)
        self.tgt_tok_emb = nn.Embedding(tgt_vocab_size, d_model)
        self.pos_encoder = _PositionalEncoding(d_model, max_len)
        self.transformer = nn.Transformer(
            d_model=d_model,
            nhead=nhead,
            num_encoder_layers=num_layers,
            num_decoder_layers=num_layers,
            dim_feedforward=dim_feedforward,
            batch_first=True,
        )
        self.out = nn.Linear(d_model, tgt_vocab_size)

    def forward(self, src: torch.Tensor, tgt: torch.Tensor) -> torch.Tensor:
        return self.decode(tgt, self.encode(src))

    def encode(self, src: torch.Tensor) -> torch.Tensor:
        """Run the encoder once; its output is reused for every decoding step."""
        return self.transformer.encoder(self.pos_encoder(self.src_tok_emb(src)))

    def decode(self, tgt: torch.Tensor, memory: torch.Tensor) -> torch.Tensor:
        """Return next-token logits for every target position given the encoder memory."""
        tgt = self.pos_encoder(self.tgt_tok_emb(tgt))
        tgt_mask = nn.Transformer.generate_square_subsequent_mask(tgt.size(1)).to(memory.device)
        return self.out(self.transformer.decoder(tgt, memory, tgt_mask=tgt_mask))


_Loaded = tuple[_CharTransformer, spm.SentencePieceProcessor, spm.SentencePieceProcessor]
_rekhta_models: ModelCache[_Loaded] = ModelCache("Rekhta Hindi->Urdu")


class RekhtaBackend:
    """Downloads, caches, and runs the rekhtalabs Hindi -> Urdu checkpoint."""

    def __init__(self) -> None:
        self._model: Optional[_CharTransformer] = None
        self._src_sp: Optional[spm.SentencePieceProcessor] = None
        self._tgt_sp: Optional[spm.SentencePieceProcessor] = None

    def load(
        self,
        progress_cb: Optional[Callable[[str], None]] = None,
        progress_num_cb: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        """Download (on first use) and load the checkpoint and tokenizers into memory.

        Raises RuntimeError when the download or checkpoint load fails.
        """
        try:
            self._model, self._src_sp, self._tgt_sp = _rekhta_models.get_or_load(
                _REPO_ID, lambda: self._load_files(progress_cb, progress_num_cb)
            )
            emit_status(progress_cb, "Hindi→Urdu model ready.")
            _log.info("Rekhta Hindi→Urdu model ready")
        except JobCancelled:
            raise
        except Exception as e:
            _log.error("Rekhta model load failed: %r", e, exc_info=True)
            raise RuntimeError(f"Hindi→Urdu model load failed: {e}") from e

    def _load_files(
        self,
        progress_cb: Optional[Callable[[str], None]],
        progress_num_cb: Optional[Callable[[int, int], None]],
    ) -> _Loaded:
        """Read the checkpoint and both tokenizers from disk (downloading them on first use)."""
        checkpoint_path, src_tok_path, tgt_tok_path = self._resolve_paths(progress_cb, progress_num_cb)
        src_sp = spm.SentencePieceProcessor(model_file=src_tok_path)  # type: ignore[reportCallIssue]
        tgt_sp = spm.SentencePieceProcessor(model_file=tgt_tok_path)  # type: ignore[reportCallIssue]
        model = _CharTransformer(
            src_vocab_size=src_sp.get_piece_size(),  # type: ignore[reportAttributeAccessIssue]
            tgt_vocab_size=tgt_sp.get_piece_size(),  # type: ignore[reportAttributeAccessIssue]
        )
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
        state_dict = OrderedDict(
            (k.replace("module.", ""), v) for k, v in checkpoint["model_state_dict"].items()
        )
        model.load_state_dict(state_dict)
        model.eval()
        return model, src_sp, tgt_sp

    def _resolve_paths(
        self,
        progress_cb: Optional[Callable[[str], None]],
        progress_num_cb: Optional[Callable[[int, int], None]],
    ) -> tuple[str, str, str]:
        """Return cached checkpoint/tokenizer paths, downloading them over the network on first use."""
        try:
            return (
                hf_hub_download(_REPO_ID, _CHECKPOINT_FILE, local_files_only=True),
                hf_hub_download(_REPO_ID, _SRC_TOKENIZER_FILE, local_files_only=True),
                hf_hub_download(_REPO_ID, _TGT_TOKENIZER_FILE, local_files_only=True),
            )
        except OSError:
            emit_status(progress_cb, "Downloading Hindi→Urdu transliteration model...")
            with download_progress(progress_num_cb):
                return (
                    retry_hf_load(lambda: hf_hub_download(_REPO_ID, _CHECKPOINT_FILE)),
                    retry_hf_load(lambda: hf_hub_download(_REPO_ID, _SRC_TOKENIZER_FILE)),
                    retry_hf_load(lambda: hf_hub_download(_REPO_ID, _TGT_TOKENIZER_FILE)),
                )

    def convert(self, text: str) -> str:
        """Transliterate one string of Devanagari text into Urdu (Nastaliq) script.

        Text longer than the model's input window is converted in word-aligned chunks instead
        of being cut off. Raises RuntimeError when load() has not been called first.
        """
        if self._model is None or self._src_sp is None or self._tgt_sp is None:
            raise RuntimeError("Call load() before convert().")
        ids = self._src_sp.encode(text)  # type: ignore[reportAttributeAccessIssue]
        if len(ids) <= _MAX_LEN - 2:
            return self._convert_ids(ids)
        return " ".join(self._convert_ids(self._src_sp.encode(chunk)) for chunk in self._chunks(text))  # type: ignore[reportAttributeAccessIssue]

    def _chunks(self, text: str) -> list[str]:
        """Group words into chunks whose encodings fit the model's input window."""
        chunks: list[str] = []
        current: list[str] = []
        for word in text.split():
            candidate = " ".join(current + [word])
            if current and len(self._src_sp.encode(candidate)) > _MAX_LEN - 2:  # type: ignore[union-attr]
                chunks.append(" ".join(current))
                current = [word]
            else:
                current.append(word)
        if current:
            chunks.append(" ".join(current))
        return chunks

    def _convert_ids(self, ids: list[int]) -> str:
        """Greedy-decode one encoded chunk, running the encoder only once."""
        assert self._model is not None and self._tgt_sp is not None
        src_tensor = torch.tensor([_BOS_ID] + ids[: _MAX_LEN - 2] + [_EOS_ID]).unsqueeze(0)
        tgt_ids = [_BOS_ID]
        with torch.no_grad():
            memory = self._model.encode(src_tensor)
            for _ in range(_MAX_LEN):
                logits = self._model.decode(torch.tensor(tgt_ids).unsqueeze(0), memory)
                next_id = int(torch.argmax(logits[0, -1, :]).item())
                if next_id == _EOS_ID:
                    break
                tgt_ids.append(next_id)
        return self._tgt_sp.decode(tgt_ids[1:])  # type: ignore[reportAttributeAccessIssue]
