# test_model_cache.py - unit tests for ccgen.engines.model_cache

from unittest.mock import MagicMock

from ccgen.engines.model_cache import ModelCache, release_all


class TestModelCache:
    def test_loader_runs_once_per_key(self):
        cache = ModelCache("test")
        loader = MagicMock(return_value="model")
        assert cache.get_or_load("a", loader) == "model"
        assert cache.get_or_load("a", loader) == "model"
        loader.assert_called_once()

    def test_capacity_one_evicts_previous_model(self):
        cache = ModelCache("test")
        cache.get_or_load("a", lambda: "A")
        cache.get_or_load("b", lambda: "B")
        loader = MagicMock(return_value="A2")
        assert cache.get_or_load("a", loader) == "A2"
        loader.assert_called_once()

    def test_release_all_clears_every_cache(self):
        cache = ModelCache("test")
        cache.get_or_load("a", lambda: "A")
        release_all()
        loader = MagicMock(return_value="A")
        cache.get_or_load("a", loader)
        loader.assert_called_once()

    def test_failed_load_is_not_cached(self):
        cache = ModelCache("test")
        failing = MagicMock(side_effect=RuntimeError("boom"))
        try:
            cache.get_or_load("a", failing)
        except RuntimeError:
            pass
        assert cache.get_or_load("a", lambda: "ok") == "ok"
