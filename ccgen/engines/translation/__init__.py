# translation — translation engine registry

from typing import Callable

from ccgen.config.defaults import TranslationDefaults
from ccgen.engines.translation.argos_engine import ArgosEngine
from ccgen.engines.translation.base import TranslationEngine

_ENGINES: dict[str, Callable[..., TranslationEngine]] = {
    "argos": ArgosEngine,
}


def create_engine(
    name: str = "argos",
    source_lang: str = TranslationDefaults.DEFAULT_SOURCE_LANG,
    target_lang: str = TranslationDefaults.DEFAULT_TARGET_LANG,
) -> TranslationEngine:
    """Instantiate the named translation engine.

    Raises ValueError when the engine name is not registered.
    """
    engine_cls = _ENGINES.get(name)
    if engine_cls is None:
        raise ValueError(f"Unknown translation engine: '{name}'. Supported: {list(_ENGINES)}")
    return engine_cls(source_lang=source_lang, target_lang=target_lang)


__all__ = ["TranslationEngine", "ArgosEngine", "create_engine"]
