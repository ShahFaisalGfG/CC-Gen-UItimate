# transliteration — transliteration engine registry

from typing import Callable

from ccgen.config.defaults import TransliterationDefaults
from ccgen.engines.transliteration.base import TransliterationEngine
from ccgen.engines.transliteration.neural_engine import NeuralEngine
from ccgen.engines.transliteration.rule_engine import RuleEngine

_ENGINES: dict[str, Callable[..., TransliterationEngine]] = {
    TransliterationDefaults.ENGINE_RULE: RuleEngine,
    TransliterationDefaults.ENGINE_NEURAL: NeuralEngine,
}


def create_engine(
    name: str,
    source_scheme: str = TransliterationDefaults.DEFAULT_SOURCE,
    target_scheme: str = TransliterationDefaults.DEFAULT_TARGET,
) -> TransliterationEngine:
    """Instantiate the named transliteration engine.

    Raises ValueError when the engine name is not registered.
    """
    engine_cls = _ENGINES.get(name)
    if engine_cls is None:
        raise ValueError(f"Unknown transliteration engine: '{name}'. Supported: {list(_ENGINES)}")
    return engine_cls(source_scheme=source_scheme, target_scheme=target_scheme)


__all__ = ["TransliterationEngine", "RuleEngine", "NeuralEngine", "create_engine"]
