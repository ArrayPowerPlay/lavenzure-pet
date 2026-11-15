"""Small always-on-top bubble shown above the pet for click reactions, jokes, reminders and alerts.

The bubble is its own top-level window. While visible it re-centres itself over the pet's head on
every frame, so it travels along when the pet walks, floats, jumps or is dragged.

Festive greetings (round 46) use the same window with a bigger, decorated look
(``show_greeting``): the occasion's emoji on both sides of a large bold title, a smaller warm
line under it, centred, in a cream card with a red border.

The window itself is transparent and the card is painted by hand (``paintEvent``): an
anti-aliased rounded rectangle, so its rounded corners show the desktop behind them instead of a
square of window background (round 47). The style sheets only set the font, text colour,
padding and a transparent border of the card's width (so the text keeps its place).
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from html import escape

from PySide6.QtCore import QPoint, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QTextDocument
from PySide6.QtWidgets import QLabel

FOLLOW_INTERVAL_MS = 16  # ~60 fps, same rate as the pet



@dataclass(frozen=True)
class Card:
    """How the bubble's card is painted: fill, border colour, border width and corner radius
    (pixels)."""

    fill: QColor
    border: QColor
    border_w: int
    radius: float


# Normal lines (click reactions, ambient lines) vs. sticky ones (reminders, alerts), which are
# drawn a bit bigger so they are easy to notice and read (round 28).
NORMAL_CARD = Card(QColor(255, 250, 230), QColor("#d08a2e"), 1, 8.0)
STICKY_CARD = Card(QColor(255, 250, 230), QColor("#d08a2e"), 2, 10.0)
GREETING_CARD = Card(QColor(255, 251, 240), QColor("#c8202f"), 3, 22.0)   # round 47: rounder
NORMAL_STYLE = ("border: 1px solid transparent; padding: 6px 10px; color: #3a2410; "
                "font-size: 12px;")
STICKY_STYLE = ("border: 2px solid transparent; padding: 10px 14px; color: #3a2410; "
                "font-size: 15px;")
NORMAL_MAX_W, STICKY_MAX_W = 240, 320
GREETING_STYLE = "border: 3px solid transparent; padding: 12px 20px;"
GREETING_MAX_W = 310     # the warm line wraps into a compact card; the title never wraps
GREETING_TITLE = "font-size: 22px; font-weight: 700; color: #c8202f; white-space: nowrap;"
GREETING_LINE = "font-size: 14px; color: #2e6b3a;"
_NO_LIMIT = 16_777_215   # Qt's QWIDGETSIZE_MAX: "no size limit"


class SpeechBubble(QLabel):
    """Word-wrapped label that follows a moving anchor point (the top of the pet's head).

    ``anchor_fn`` returns the global screen point the bubble should sit above.
    """

    def __init__(self, anchor_fn: Callable[[], QPoint]) -> None:
        """Create the hidden bubble window; nothing shows until ``show_text``."""
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        # Only the rounded card is drawn (``paintEvent``); the corners outside it stay see-through.
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(NORMAL_STYLE)
        self._card = NORMAL_CARD
        self._lift = 0           # extra pixels between the anchor and the bubble (greetings)
        self.setWordWrap(True)
        self.setMaximumWidth(NORMAL_MAX_W)
        self.hide()
        self._anchor_fn = anchor_fn

        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self.hide)

        self._follow_timer = QTimer(self)
        self._follow_timer.setInterval(FOLLOW_INTERVAL_MS)
        self._follow_timer.timeout.connect(self._follow)

    def show_text(self, text: str, auto_hide_ms: int | None = 4000) -> None:
        """Show ``text`` above the pet.

        ``auto_hide_ms=None`` keeps the bubble visible until ``hide()`` is called (alerts,
        reminders) and uses the bigger sticky look.
        """
        sticky = auto_hide_ms is None
        self.setStyleSheet(STICKY_STYLE if sticky else NORMAL_STYLE)
        self._card = STICKY_CARD if sticky else NORMAL_CARD
        self._lift = 0
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.setText(text)
        if sticky:
            self._fit(STICKY_MAX_W, 2 * (14 + 2))
        else:
            self._fit(NORMAL_MAX_W, 2 * (10 + 1))
        self._follow()
        self.show()
        self.raise_()
        self._follow_timer.start()
        self._auto_hide_timer.stop()
        if auto_hide_ms is not None:
            self._auto_hide_timer.start(auto_hide_ms)

    def show_greeting(self, emoji: str, title: str, line: str, auto_hide_ms: int = 7000,
                      lift: int = 0) -> None:
        """Show a festive greeting: ``emoji`` on both sides of a big bold ``title`` with a
        smaller ``line`` under it (see the module doc). It hides by itself. ``lift`` raises
        the card that many pixels higher than a plain bubble, so the big opaque card sits
        above the leaping flame tips instead of covering them (round 47)."""
        self.setStyleSheet(GREETING_STYLE)
        self._card = GREETING_CARD
        self._lift = max(0, int(lift))
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText(f'<div align="center" style="{GREETING_TITLE}">{emoji} {escape(title)} '
                     f'{emoji}</div><div align="center" style="{GREETING_LINE}">'
                     f'{escape(line)}</div>')
        self._fit_rich(GREETING_MAX_W, 2 * (20 + 3))
        self._follow()
        self.show()
        self.raise_()
        self._follow_timer.start()
        self._auto_hide_timer.start(auto_hide_ms)

    def _fit_rich(self, max_width: int, frame_w: int) -> None:
        """Like ``_fit`` for rich text: measure the laid-out text (not its markup) and size the
        bubble to it, wrapping only past ``max_width``."""
        self.ensurePolished()
        self.setMinimumSize(0, 0)
        self.setMaximumSize(_NO_LIMIT, _NO_LIMIT)
        doc = QTextDocument()
        doc.setDefaultFont(self.font())
        doc.setDocumentMargin(0)
        doc.setHtml(self.text())
        doc.setTextWidth(max_width - frame_w)
        width = min(max_width, int(doc.idealWidth()) + frame_w + 4)
        self.setFixedWidth(width)
        self.setFixedHeight(self.heightForWidth(width))

    def _fit(self, max_width: int, frame_w: int) -> None:
        """Size the bubble to its text: one line as wide as the text needs, wrapping only past
        ``max_width`` (``frame_w`` = horizontal padding + border). A plain ``adjustSize`` on a
        word-wrapped label wraps far too early. The size limits of the previous text are lifted
        first: otherwise the label keeps the height of an earlier, longer line and a short line
        gets a big empty bubble."""
        self.ensurePolished()   # apply the style sheet's font before measuring
        self.setMinimumSize(0, 0)
        self.setMaximumSize(_NO_LIMIT, _NO_LIMIT)
        metrics = self.fontMetrics()
        natural = max(metrics.horizontalAdvance(line) for line in self.text().split("\n"))
        width = min(max_width, natural + frame_w + 2)
        self.setFixedWidth(width)
        self.setFixedHeight(self.heightForWidth(width))

    def is_sticky(self) -> bool:
        """True while a bubble without auto-hide (an alert) is on screen."""
        return self.isVisible() and not self._auto_hide_timer.isActive()

    def _follow(self) -> None:
        """Centre the bubble horizontally over the anchor (the middle of the pet) and put it
        just above, kept inside the screen's available area."""
        anchor = self._anchor_fn()
        screen = self.screen().availableGeometry()
        x = anchor.x() - self.width() // 2
        x = max(screen.left(), min(x, screen.right() - self.width()))
        y = max(screen.top(), anchor.y() - self.height() - 4 - self._lift)
        if (x, y) != (self.x(), self.y()):
            self.move(x, y)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        """Paint the rounded card (anti-aliased, border fully inside the window), then let the
        label draw its text on top."""
        card = self._card
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        half = card.border_w / 2
        rect = QRectF(self.rect()).adjusted(half, half, -half, -half)
        painter.setPen(QPen(card.border, card.border_w))
        painter.setBrush(card.fill)
        painter.drawRoundedRect(rect, card.radius - half, card.radius - half)
        painter.end()
        super().paintEvent(event)

    def hideEvent(self, event) -> None:  # noqa: N802 - Qt override
        """Stop following (and any pending auto-hide) once hidden."""
        super().hideEvent(event)
        self._follow_timer.stop()
        self._auto_hide_timer.stop()
