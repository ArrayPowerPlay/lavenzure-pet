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


def test_autostart_switch_is_reported_when_the_user_clicks_it(qapp):
    """Ticking "Start with Windows" emits the new state; it starts off by default."""
    window = SettingsWindow()
    assert not window.autostart_box.isChecked()
    seen = []
    window.autostart_toggled.connect(seen.append)
    window.autostart_box.setChecked(True)
    assert seen == [True]


def test_set_autostart_shows_the_real_state_without_reporting_it(qapp):
    """The app syncing the switch with the registry is not a user choice."""
    window = SettingsWindow()
    seen = []
    window.autostart_toggled.connect(seen.append)
    window.set_autostart(True)
    assert window.autostart_box.isChecked()
    assert seen == []


def test_window_is_short_and_scrolls(qapp):
    """All the options sit in a scroll area, so the window stays shorter than its content."""
    from PySide6.QtWidgets import QScrollArea

    window = SettingsWindow()
    window.show()
    scroll = window.findChild(QScrollArea)
    assert scroll is not None
    assert window.height() <= 540
    assert scroll.widget().sizeHint().height() > scroll.viewport().height()
    window.close()


def test_outfit_buttons_start_on_the_current_outfit_and_report_a_pick(qapp):
    """Round 47 (H5.6): Settings > Outfit offers Normal / Xmas, starts on the outfit worn and
    reports a new pick."""
    window = SettingsWindow(outfit="xmas")
    assert set(window.outfit_buttons) == {"normal", "xmas"}
    assert window.outfit_buttons["xmas"].isChecked()
    picked = []
    window.outfit_changed.connect(picked.append)
    window.outfit_buttons["normal"].setChecked(True)
    assert picked == ["normal"]
    window.close()


def test_outfit_setting_defaults_to_normal_and_is_remembered(tmp_path):
    """Without a saved choice the pet wears its normal look (``character.outfit``); a pick is
    saved and read back next time."""
    from user_settings import UserSettings

    path = tmp_path / "settings.json"
    settings = UserSettings(path)
    assert settings.get("outfit") == "normal"
    settings.set("outfit", "xmas")
    assert UserSettings(path).get("outfit") == "xmas"
