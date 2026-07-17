# captions — caption/transcription engine registry

from typing import Callable

from ccgen.config.defaults import ComputeDefaults, ModelDefaults
from ccgen.engines.captions.base import CaptionEngine
from ccgen.engines.captions.whisper_engine import WhisperEngine

_ENGINES: dict[str, Callable[..., CaptionEngine]] = {
    "whisper": WhisperEngine,
}


def create_engine(
    name: str = "whisper",
    model_name: str = ModelDefaults.DEFAULT_MODEL,
    device: str = ComputeDefaults.DEFAULT_DEVICE,
    compute_type: str = ComputeDefaults.DEFAULT_COMPUTE_TYPE,
) -> CaptionEngine:
    """Instantiate the named caption engine.

    Raises ValueError when the engine name is not registered.
    """
    engine_cls = _ENGINES.get(name)
    if engine_cls is None:
        raise ValueError(f"Unknown caption engine: '{name}'. Supported: {list(_ENGINES)}")
    return engine_cls(model_name=model_name, device=device, compute_type=compute_type)


__all__ = ["CaptionEngine", "WhisperEngine", "create_engine"]
