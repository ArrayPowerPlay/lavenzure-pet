"""Make sure only one Lavenzure runs at a time (e.g. autostart + a manual start).

- A ``QLockFile`` in the temp folder decides who is first. Qt detects stale locks left by a crashed
  run (by process id), so a crash never blocks the next start.
- The first instance also opens a ``QLocalServer``. A second start connects to it, sends
  ``show-chat`` and exits, so starting the app again simply brings up the chat window.
"""
from __future__ import annotations

import getpass
import logging
import re

from PySide6.QtCore import QDir, QLockFile, QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

log = logging.getLogger(__name__)

MESSAGE_SHOW_CHAT = b"show-chat"


def _instance_name() -> str:
    """Per-user name shared by the lock file and the local server."""
    try:
        user = getpass.getuser()
    except Exception:  # noqa: BLE001 - getuser can fail in unusual environments
        user = "user"
    return "lavenzure-pet-" + re.sub(r"[^A-Za-z0-9_-]", "_", user)


class SingleInstance(QObject):
    """Owns the lock + local server for the primary instance.

    Use ``acquire()`` once at startup: it returns True for the first instance; otherwise it pings
    the running instance and returns False (the caller should exit). ``activated`` is emitted in
    the primary instance whenever a later start pings it.
    """

    activated = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        """Prepare (but do not take) the lock and server for this user."""
        super().__init__(parent)
        self._name = _instance_name()
        self._lock = QLockFile(QDir.temp().absoluteFilePath(self._name + ".lock"))
        self._lock.setStaleLockTime(0)  # only a dead owner process makes the lock stale
        self._server: QLocalServer | None = None

    def acquire(self) -> bool:
        """Become the primary instance, or notify the existing one and return False."""
        if not self._lock.tryLock(200):
            log.info("Another Lavenzure is already running; asking it to open the chat.")
            self._ping_primary()
            return False
        QLocalServer.removeServer(self._name)  # clean a stale server left by a crash
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._on_new_connection)
        if not self._server.listen(self._name):
            # Still the only instance (we hold the lock); just can't receive pings.
            log.warning("Single-instance server failed to listen: %s", self._server.errorString())
        return True

    def _ping_primary(self) -> None:
        """Send the show-chat message to the running instance (best effort)."""
        socket = QLocalSocket()
        socket.connectToServer(self._name)
        if socket.waitForConnected(1000):
            socket.write(MESSAGE_SHOW_CHAT)
            socket.waitForBytesWritten(1000)
            socket.disconnectFromServer()
        else:
            log.warning("Could not reach the running instance: %s", socket.errorString())

    def _on_new_connection(self) -> None:
        """Read a ping from a later start and emit ``activated`` if it asks for the chat."""
        while self._server is not None and self._server.hasPendingConnections():
            conn = self._server.nextPendingConnection()

            def _read(conn=conn) -> None:
                """Handle the message once its bytes arrive, then close the connection."""
                if bytes(conn.readAll()).strip() == MESSAGE_SHOW_CHAT:
                    log.info("A second start was detected; opening the chat instead.")
                    self.activated.emit()
                conn.disconnectFromServer()

            conn.readyRead.connect(_read)
            conn.disconnected.connect(conn.deleteLater)
