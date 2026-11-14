"""Tests for the pet's right-click menu (Chat, Idle / Wander, Hide Pet)."""
from ui.menus import PetMenu


def test_pet_menu_has_hide_pet(qapp):
    """``Hide Pet`` sits in the right-click menu and asks the app to hide the pet."""
    menu = PetMenu()
    texts = [action.text() for action in menu._menu.actions()]
    assert texts == ["Chat", "Idle", "Hide Pet"]     # no separator lines either
    fired = []
    menu.hide_requested.connect(lambda: fired.append(True))
    menu._hide.trigger()
    assert fired == [True]
