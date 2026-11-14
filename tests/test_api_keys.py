"""Tests for api_keys: reading order (environment first), saving, deleting, store failures."""
import keyring
import pytest
from keyring.errors import KeyringError

import api_keys


def test_no_key_by_default():
    """Nothing set anywhere -> empty key, source 'none'."""
    assert api_keys.gemini_api_key() == ""
    assert api_keys.key_source(api_keys.GEMINI) == "none"


def test_saved_key_is_read_at_use_time(fake_key_store):
    """A key saved after the app started is used at once (no restart)."""
    assert api_keys.gemini_api_key() == ""
    api_keys.save_key(api_keys.GEMINI, "  AIza-abc  ")
    assert api_keys.gemini_api_key() == "AIza-abc"
    assert api_keys.key_source(api_keys.GEMINI) == "saved"
    assert fake_key_store.store[("Lavenzure", "gemini_api_key")] == "AIza-abc"


def test_openai_key_has_its_own_slot(monkeypatch):
    """The OpenAI key is kept apart from the Gemini one and can come from OPENAI_API_KEY."""
    api_keys.save_key(api_keys.OPENAI, "sk-saved")
    assert api_keys.openai_api_key() == "sk-saved"
    assert api_keys.gemini_api_key() == ""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
    assert api_keys.openai_api_key() == "sk-env"


def test_environment_wins_over_saved_key(monkeypatch):
    """A key from the environment / .env (development) overrides the saved one."""
    api_keys.save_key(api_keys.TAVILY, "saved")
    monkeypatch.setenv("TAVILY_API_KEY", "from-env")
    assert api_keys.tavily_api_key() == "from-env"
    assert api_keys.key_source(api_keys.TAVILY) == "env"


def test_delete_removes_and_tolerates_missing_key():
    """Deleting works, and deleting twice is not an error."""
    api_keys.save_key(api_keys.GEMINI, "k")
    api_keys.delete_key(api_keys.GEMINI)
    assert api_keys.gemini_api_key() == ""
    api_keys.delete_key(api_keys.GEMINI)


def test_empty_key_is_refused():
    """Saving a blank key is a programming error."""
    with pytest.raises(ValueError):
        api_keys.save_key(api_keys.GEMINI, "   ")


def test_unknown_key_name_is_refused():
    """Only the known key names are accepted."""
    with pytest.raises(KeyError):
        api_keys.get_key("anthropic_api_key")


def test_store_failure_on_save_is_reported(monkeypatch):
    """No plain-text fallback: a failing key store raises KeyStoreError."""
    def broken(*_args):
        raise KeyringError("locked")

    monkeypatch.setattr(keyring, "set_password", broken)
    with pytest.raises(api_keys.KeyStoreError):
        api_keys.save_key(api_keys.GEMINI, "k")


def test_store_failure_on_read_means_no_key(monkeypatch):
    """A key store that cannot be read behaves like 'no key saved' (and the pet keeps running)."""
    def broken(*_args):
        raise KeyringError("locked")

    monkeypatch.setattr(keyring, "get_password", broken)
    assert api_keys.gemini_api_key() == ""
