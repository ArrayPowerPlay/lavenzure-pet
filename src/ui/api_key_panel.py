"""One API-key box for the Settings window: type a key, check it, save it.

``ApiKeyPanel`` shows a masked entry (with a Show toggle), a Save button and a status line. Pressing
Save asks the service whether the key works (``agent.key_check``, on a worker thread so the window
never freezes) and stores it with ``api_keys`` ONLY when the answer is "valid"; the result is shown
right under the entry. A saved key works at once (no restart). The panel also says when a key from
the environment / ``.env`` (development) is overriding the saved one. Keys are never logged.

The panel emits ``changed`` after a key was saved or removed; the app uses it to rebuild the chat
model.
"""
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import api_keys
from agent.key_check import CheckResult, KeyStatus


class _CheckSignals(QObject):
    """Carries the result of a background check back to the UI thread."""

    done = Signal(object)  # CheckResult


class _CheckTask(QRunnable):
    """Runs one key check on the thread pool."""

    def __init__(self, check: Callable[[str], CheckResult], key: str,
                 signals: _CheckSignals) -> None:
        """Remember what to check and where to report."""
        super().__init__()
        self._check, self._key, self._signals = check, key, signals

    def run(self) -> None:
        """Do the (slow, networked) check and report the result."""
        try:
            result = self._check(self._key)
        except Exception:  # noqa: BLE001 - never let a worker thread die silently
            result = CheckResult(KeyStatus.ERROR, "Something went wrong while checking the key.")
        self._signals.done.emit(result)


class ApiKeyPanel(QWidget):
    """Entry + Save/Remove + status line for one API key (see the module doc)."""

    changed = Signal()

    def __init__(self, key_name: str, title: str, check: Callable[[str], CheckResult],
                 help_html: str = "", optional: bool = False) -> None:
        """``key_name`` is one of the ``api_keys`` names, ``check`` the function that asks the
        service, ``help_html`` a small link line (where to get a key), ``optional`` says the app
        works without this key."""
        super().__init__()
        self._key_name = key_name
        self._check = check
        self._signals = _CheckSignals(self)
        self._signals.done.connect(self._on_checked)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        heading = QLabel(title + ("  (optional)" if optional else ""))
        heading.setObjectName("section")
        layout.addWidget(heading)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        self.entry = QLineEdit()
        self.entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.entry.setPlaceholderText("Paste your key here")
        self.entry.textChanged.connect(self._update_buttons)
        self.entry.returnPressed.connect(self._on_save)
        self.show_button = QPushButton("Show")
        self.show_button.setObjectName("small")
        self.show_button.setCheckable(True)
        self.show_button.toggled.connect(self._on_show_toggled)
        row.addWidget(self.entry, 1)
        row.addWidget(self.show_button)
        layout.addLayout(row)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        self.save_button = QPushButton("Save")
        self.save_button.setObjectName("small")
        self.save_button.clicked.connect(self._on_save)
        self.remove_button = QPushButton("Remove")
        self.remove_button.setObjectName("small")
        self.remove_button.clicked.connect(self._on_remove)
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.remove_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self.status = QLabel("")
        self.status.setObjectName("note")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        if help_html:
            help_label = QLabel(help_html)
            help_label.setObjectName("note")
            help_label.setOpenExternalLinks(True)
            layout.addWidget(help_label)

        self._busy = False
        self._checking_key = ""
        self.refresh()

    def refresh(self, message: str | None = None) -> None:
        """Re-read where the key comes from and update the status line (``message`` replaces the
        default text, e.g. a check result)."""
        source = api_keys.key_source(self._key_name)
        self.remove_button.setVisible(source == "saved")
        if message is None:
            message = {
                "env": "Using the key from your environment (.env); it overrides a saved one.",
                "saved": "A key is saved. Paste a new one to replace it.",
                "none": "No key yet.",
            }[source]
        self.status.setText(message)
        self._update_buttons()

    def _update_buttons(self) -> None:
        """Save needs some text and no check in progress."""
        self.save_button.setEnabled(bool(self.entry.text().strip()) and not self._busy)
        self.remove_button.setEnabled(not self._busy)

    def _on_show_toggled(self, shown: bool) -> None:
        """Show / hide the typed characters."""
        self.entry.setEchoMode(QLineEdit.EchoMode.Normal if shown else QLineEdit.EchoMode.Password)
        self.show_button.setText("Hide" if shown else "Show")

    def _on_save(self) -> None:
        """Start checking the typed key on a worker thread."""
        key = self.entry.text().strip()
        if not key or self._busy:
            return
        self._busy = True
        self.status.setText("Checking the key...")
        self._update_buttons()
        self._checking_key = key
        QThreadPool.globalInstance().start(_CheckTask(self._check, key, self._signals))

    def _on_checked(self, result: CheckResult) -> None:
        """The check finished: save a valid key, otherwise show why it was not saved."""
        key, self._checking_key = self._checking_key, ""
        self._busy = False
        if not result.ok:
            self.refresh(result.message)
            return
        try:
            api_keys.save_key(self._key_name, key)
        except api_keys.KeyStoreError as exc:
            self.refresh(f"The key works but could not be saved: {exc}")
            return
        self.entry.clear()
        self.refresh("Key works and is saved.")
        self.changed.emit()

    def _on_remove(self) -> None:
        """Delete the saved key."""
        try:
            api_keys.delete_key(self._key_name)
        except api_keys.KeyStoreError as exc:
            self.refresh(str(exc))
            return
        self.refresh("Key removed.")
        self.changed.emit()
