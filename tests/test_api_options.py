# test_api_options.py - tests for GET /options (UI dropdown option lists)

import pytest
from fastapi.testclient import TestClient

from ccgen.api.app import app
from ccgen.config.defaults import LanguageOptions, ModelDefaults, TransliterationDefaults


@pytest.fixture
def client():
    return TestClient(app)


class TestGetOptions:
    def test_status_ok(self, client):
        assert client.get("/options").status_code == 200

    def test_response_shape(self, client):
        data = client.get("/options").json()
        expected_keys = {
            "models", "languages", "translation_targets",
            "translit_schemes", "translit_engines",
        }
        assert set(data.keys()) == expected_keys
        for key in expected_keys:
            assert isinstance(data[key], list)

    def test_models_match_defaults(self, client):
        data = client.get("/options").json()
        assert data["models"] == ModelDefaults.SUPPORTED_MODELS

    def test_languages_are_label_code_items(self, client):
        data = client.get("/options").json()
        assert len(data["languages"]) == len(LanguageOptions.TRANSCRIPTION)
        for item in data["languages"]:
            assert set(item.keys()) == {"label", "code"}

    def test_auto_detect_code_is_empty_string(self, client):
        data = client.get("/options").json()
        auto = next(item for item in data["languages"] if item["label"] == "Auto-detect")
        assert auto["code"] == ""

    def test_translation_targets_match_defaults(self, client):
        data = client.get("/options").json()
        codes = [item["code"] for item in data["translation_targets"]]
        assert codes == [code for _, code in LanguageOptions.TRANSLATION_TARGETS]

    def test_translit_schemes_match_defaults(self, client):
        data = client.get("/options").json()
        codes = [item["code"] for item in data["translit_schemes"]]
        assert codes == [code for _, code in TransliterationDefaults.SCHEMES]

    def test_translit_engines_match_defaults(self, client):
        data = client.get("/options").json()
        codes = [item["code"] for item in data["translit_engines"]]
        assert codes == [code for _, code in TransliterationDefaults.ENGINES]
