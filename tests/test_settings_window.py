"""Tests for the Settings window's chat-AI choice (provider switch + one key box per provider)."""
from ui.settings_window import SettingsWindow


def test_only_the_chosen_provider_shows_its_key_box(qapp):
    """Gemini selected -> Gemini box visible, OpenAI box hidden; switching swaps them."""
    window = SettingsWindow(provider="gemini")
    window.show()
    assert window.key_panels["gemini"].isVisible()
    assert not window.key_panels["openai"].isVisible()
    window.provider_buttons["openai"].setChecked(True)
    assert window.key_panels["openai"].isVisible()
    assert not window.key_panels["gemini"].isVisible()


def test_provider_choice_is_reported(qapp):
    """Picking a provider emits ``provider_changed`` with its code."""
    window = SettingsWindow(provider="gemini")
    seen = []
    window.provider_changed.connect(seen.append)
    window.provider_buttons["openai"].setChecked(True)
    assert seen == ["openai"]


def test_tavily_box_is_always_there(qapp):
    """Web search is optional but always configurable."""
    window = SettingsWindow(provider="openai")
    window.show()
    assert window.tavily_panel.isVisible()
