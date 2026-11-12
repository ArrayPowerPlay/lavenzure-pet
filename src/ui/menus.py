"""Small pop-up menus in the pet's own style (cream paper, dark maroon ink, rounded corners).

- ``themed_menu()`` builds an empty styled ``QMenu`` (also used by the tray icon).
- ``PetMenu`` is the right-click menu of the pet itself: ``Chat`` and ``Idle`` / ``Wander``.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, QPoint, Qt, Signal
from PySide6.QtWidgets import QMenu

MENU_STYLE = """
QMenu {
    background: #fff8ea;
    border: 2px solid #6c0e16;
    border-radius: 12px;
    padding: 6px 4px;
    font-family: "Segoe UI", "Arial";
    font-size: 10pt;
    color: #6c0e16;
}
QMenu::item {
    padding: 6px 26px 6px 18px;
    border-radius: 8px;
    margin: 1px 4px;
}
QMenu::item:selected {
    background: #ffd98a;
}
QMenu::item:disabled {
    color: #b9958f;
}
QMenu::separator {
    height: 1px;
    background: #e8cdb8;
    margin: 4px 12px;
}
"""


def themed_menu(parent=None) -> QMenu:
    """An empty ``QMenu`` with the cream / maroon look and real rounded corners."""
    menu = QMenu(parent)
    menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.FramelessWindowHint
                        | Qt.WindowType.NoDropShadowWindowHint)
    menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    menu.setStyleSheet(MENU_STYLE)
    return menu


class PetMenu(QObject):
    """Right-click menu of the pet: ``Chat`` opens the chat bubble; ``Idle`` makes the pet lie
    down and sleep, and while it rests the same item reads ``Wander`` (roam again)."""

    chat_requested = Signal()
    rest_requested = Signal(bool)   # True = Idle (rest), False = Wander

    def __init__(self) -> None:
        """Build the menu once; ``popup`` updates the Idle / Wander label each time."""
        super().__init__()
        self._menu = themed_menu()
        self._chat = self._menu.addAction("Chat")
        self._chat.triggered.connect(self.chat_requested.emit)
        self._rest = self._menu.addAction("Idle")
        self._rest.triggered.connect(self._on_rest)
        self._resting = False

    def popup(self, pos: QPoint, resting: bool) -> None:
        """Show the menu at global ``pos``; ``resting`` = the pet is currently in Idle mode."""
        self._resting = resting
        self._rest.setText("Wander" if resting else "Idle")
        self._menu.popup(pos)

    def is_visible(self) -> bool:
        """True while the menu is on screen."""
        return self._menu.isVisible()

    def _on_rest(self) -> None:
        """Toggle between Idle and Wander."""
        self.rest_requested.emit(not self._resting)
