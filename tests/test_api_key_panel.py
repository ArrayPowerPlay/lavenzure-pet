"""Tests for the API-key box of the Settings window (check on a worker thread, save if valid)."""
from PySide6.QtCore import QThreadPool

import api_keys
from agent.key_check import CheckResult, KeyStatus
from conftest import pump
from ui.api_key_panel import ApiKeyPanel


def make_panel(qapp, result):
    """A panel whose key check always answers ``result``."""
    return ApiKeyPanel(api_keys.GEMINI, "Gemini API key", lambda key: result)


def press_save(qapp, panel, key):
    """Type ``key``, press Save and wait for the worker thread and the signal."""
    panel.entry.setText(key)
    panel.save_button.click()
    QThreadPool.globalInstance().waitForDone()
    pump(qapp, 0.1)


def test_valid_key_is_saved_and_reported(qapp):
    """A key the service accepts is stored, the box is cleared and ``changed`` fires."""
    panel = make_panel(qapp, CheckResult(KeyStatus.VALID, "Key works."))
    fired = []
    panel.changed.connect(lambda: fired.append(True))
    press_save(qapp, panel, "AIza-good")
    assert api_keys.gemini_api_key() == "AIza-good"
    assert panel.entry.text() == ""
    assert "saved" in panel.status.text()
    assert fired == [True]
    assert not panel.remove_button.isHidden()


def test_rejected_key_is_not_saved(qapp):
    """A key the service rejects is never stored; the reason is shown."""
    panel = make_panel(qapp, CheckResult(KeyStatus.INVALID, "Gemini doesn't accept this key."))
    fired = []
    panel.changed.connect(lambda: fired.append(True))
    press_save(qapp, panel, "AIza-bad")
    assert api_keys.gemini_api_key() == ""
    assert "doesn't accept" in panel.status.text()
    assert fired == []


def test_network_error_is_not_saved(qapp):
    """When the check cannot reach the internet nothing is saved."""
    panel = make_panel(qapp, CheckResult(KeyStatus.NETWORK, "Couldn't reach the internet."))
    press_save(qapp, panel, "AIza-maybe")
    assert api_keys.gemini_api_key() == ""


def test_save_needs_text(qapp):
    """The Save button stays disabled while the box is empty."""
    panel = make_panel(qapp, CheckResult(KeyStatus.VALID, "ok"))
    assert not panel.save_button.isEnabled()
    panel.entry.setText("x")
    assert panel.save_button.isEnabled()


def test_remove_deletes_saved_key(qapp):
    """Remove forgets the saved key and reports the change."""
    api_keys.save_key(api_keys.GEMINI, "AIza-old")
    panel = make_panel(qapp, CheckResult(KeyStatus.VALID, "ok"))
    fired = []
    panel.changed.connect(lambda: fired.append(True))
    assert not panel.remove_button.isHidden()
    panel.remove_button.click()
    assert api_keys.gemini_api_key() == ""
    assert panel.remove_button.isHidden()
    assert fired == [True]


def test_environment_key_is_announced(qapp, monkeypatch):
    """A key from the environment is called out, since it overrides the saved one."""
    monkeypatch.setenv("GEMINI_API_KEY", "from-env")
    panel = make_panel(qapp, CheckResult(KeyStatus.VALID, "ok"))
    assert "environment" in panel.status.text()


def test_show_toggle_reveals_the_text(qapp):
    """The Show button switches the entry between dots and plain text."""
    from PySide6.QtWidgets import QLineEdit

    panel = make_panel(qapp, CheckResult(KeyStatus.VALID, "ok"))
    assert panel.entry.echoMode() == QLineEdit.EchoMode.Password
    panel.show_button.click()
    assert panel.entry.echoMode() == QLineEdit.EchoMode.Normal
