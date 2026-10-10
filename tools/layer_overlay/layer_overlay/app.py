"""The overlay app: tray icon, layer overlay, NUM badge and cheat sheet.

A worker thread polls the keyboard (~30 ms), forwards the clock and the Claude
Code status to it, and emits the keyboard state to the GUI thread.
"""

from __future__ import annotations

import logging
import time

from PySide6.QtCore import QObject, QPointF, QRectF, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QCursor, QFont, QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget

from . import autostart, protocol
from .claude import ClaudeTracker, UdpListener
from .hid_link import ForeignTraffic, HidLink
from .render import KeymapData, paint_layer, paint_sheet

log = logging.getLogger(__name__)

SHOW_DELAY_MS = 200  # a layer must be held this long before the overlay shows
POLL_MS = 30
OVERLAY_WIDTH = 0.46  # of the screen width


class Worker(QThread):
    state = Signal(object)  # protocol.State | None
    keymap = Signal(object)  # list[list[int]] from VIA, matrix order

    def __init__(self, rows: int, cols: int, listener: UdpListener | None) -> None:
        super().__init__()
        self.rows, self.cols = rows, cols
        self.listener = listener
        self.tracker = ClaudeTracker()

    def run(self) -> None:  # noqa: C901 - one loop, kept in one place on purpose
        link = HidLink()
        last_state: protocol.State | None = None
        last_time = 0.0
        last_claude: protocol.ClaudeStatus | None = None
        last_claude_sent = 0.0
        while not self.isInterruptionRequested():
            if self.listener:
                for event in self.listener.poll():
                    self.tracker.handle(event)
            self.tracker.tick()

            if not link.connected:
                if last_state is not None:
                    last_state = None
                    self.state.emit(None)
                if not link.open():
                    self.msleep(1000)
                    continue
                last_time = last_claude_sent = 0.0
                try:
                    live = link.read_keymap(self.rows, self.cols)
                    if live:
                        self.keymap.emit(live)
                except ForeignTraffic:
                    pass

            if link.paused():
                self.msleep(200)
                continue
            try:
                current = link.get_state()
                if current is not None and current != last_state:
                    last_state = current
                    self.state.emit(current)
                now = time.monotonic()
                if now - last_time > 60:
                    link.transact(protocol.set_time())
                    last_time = now
                status = self.tracker.summary()
                if status != last_claude or now - last_claude_sent > 5:
                    link.transact(protocol.set_claude(status))
                    last_claude, last_claude_sent = status, now
            except ForeignTraffic:
                log.debug("VIA traffic seen, pausing")
            self.msleep(POLL_MS)
        link.close()


class OverlayWindow(QWidget):
    """Frameless, click-through, always-on-top drawing of one layer."""

    def __init__(self, data: KeymapData) -> None:
        super().__init__(
            None,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.WindowTransparentForInput,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.data = data
        self.layer = 0
        self.locked = False

    def show_layer(self, layer: int, locked: bool) -> None:
        self.layer, self.locked = layer, locked
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        geo = screen.availableGeometry()
        width = int(geo.width() * OVERLAY_WIDTH)
        height = int(width / self.data.aspect() * 1.18)
        self.setGeometry(geo.left() + (geo.width() - width) // 2, geo.bottom() - height - 40, width, height)
        self.update()
        self.show()
        self.raise_()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        p = QPainter(self)
        paint_layer(p, QRectF(self.rect()), self.data, self.layer, locked=self.locked)
        p.end()


class BadgeWindow(QWidget):
    """Small corner pill, e.g. 'NUM' while the numpad layer is toggled on."""

    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.WindowTransparentForInput,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.text = ""
        self.color = QColor("#3b82f6")

    def show_text(self, text: str, color: QColor) -> None:
        self.text, self.color = text, color
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        geo = screen.availableGeometry()
        self.setGeometry(geo.right() - 150, geo.bottom() - 70, 130, 44)
        self.update()
        self.show()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(17, 20, 28, 225))
        p.drawRoundedRect(QRectF(self.rect()), 22, 22)
        p.setBrush(self.color)
        p.drawEllipse(QPointF(24, 22), 7, 7)
        font = QFont()
        font.setBold(True)
        font.setPixelSize(18)
        p.setFont(font)
        p.setPen(QColor("#f8fafc"))
        p.drawText(QRectF(40, 0, 90, 44), Qt.AlignmentFlag.AlignVCenter, self.text)
        p.end()


class SheetWindow(QWidget):
    """Normal window with every layer: the cheat sheet."""

    def __init__(self, data: KeymapData) -> None:
        super().__init__(None, Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("Sofle layers")
        self.data = data
        width = 900
        layer_h = int(width / data.aspect() * 1.18)
        self.resize(width, layer_h * len(data.codes) + 10 * (len(data.codes) + 1))

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#0b0d12"))
        paint_sheet(p, QRectF(self.rect()).adjusted(10, 10, -10, -10), self.data)
        p.end()


def tray_icon(color: QColor, connected: bool) -> QIcon:
    pix = QPixmap(64, 64)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(17, 20, 28))
    p.drawRoundedRect(4, 12, 56, 40, 10, 10)
    p.setBrush(color if connected else QColor("#6b7280"))
    for i in range(3):
        p.drawRoundedRect(12 + i * 15, 22, 11, 9, 2, 2)
    p.drawRoundedRect(16, 36, 32, 8, 2, 2)
    p.end()
    return QIcon(pix)


class Controller(QObject):
    def __init__(self, data: KeymapData, sheet_only: bool = False) -> None:
        super().__init__()
        self.bundled = data
        self.data = data
        self.overlay = OverlayWindow(data)
        self.badge = BadgeWindow()
        self.sheet = SheetWindow(data)
        self.enabled = True
        self.last_pin: int | None = None
        self.pending_layer: int | None = None
        self.state: protocol.State | None = None
        self.delay = QTimer(self)
        self.delay.setSingleShot(True)
        self.delay.timeout.connect(self._show_pending)

        self.tray = QSystemTrayIcon(tray_icon(data.color(0), False))
        menu = QMenu()
        menu.addAction("Show all layers", self.toggle_sheet)
        self.enable_action = QAction("Overlay on held layers", menu, checkable=True, checked=True)
        self.enable_action.toggled.connect(self._set_enabled)
        menu.addAction(self.enable_action)
        self.autostart_action = QAction("Start at login", menu, checkable=True, checked=autostart.enabled())
        self.autostart_action.toggled.connect(lambda on: autostart.enable() if on else autostart.disable())
        menu.addAction(self.autostart_action)
        menu.addSeparator()
        menu.addAction("Quit", QApplication.quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.toggle_sheet() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.tray.setToolTip("Sofle: looking for keyboard")
        self.tray.show()
        if sheet_only:
            self.sheet.show()

    def _set_enabled(self, on: bool) -> None:
        self.enabled = on
        if not on:
            self.overlay.hide()

    def toggle_sheet(self) -> None:
        self.sheet.setVisible(not self.sheet.isVisible())

    def on_keymap(self, matrix_codes: list[list[int]]) -> None:
        live = self.bundled.with_live_keymap(matrix_codes)
        if live.differs_from(self.bundled):
            log.info("live keymap differs from keymap.c (VIA edits): showing the live one")
            self.data = live
            self.overlay.data = self.sheet.data = live

    def on_state(self, st: protocol.State | None) -> None:
        self.state = st
        if st is None:
            self.overlay.hide()
            self.badge.hide()
            self.tray.setIcon(tray_icon(self.data.color(0), False))
            self.tray.setToolTip("Sofle: not connected")
            self.last_pin = None
            return

        layer = min(st.highest_layer, len(self.data.names) - 1)
        name = self.data.names[layer]
        self.tray.setIcon(tray_icon(self.data.color(layer), True))
        self.tray.setToolTip(f"Sofle: {name}" + (" (locked)" if st.locked(layer) else ""))

        if self.last_pin is not None and st.pin_count != self.last_pin:
            self.toggle_sheet()
        self.last_pin = st.pin_count

        num = self.data.names.index("NUM") if "NUM" in self.data.names else None
        if num is not None and st.layer_on(num) and layer == num:
            self.badge.show_text("NUM", self.data.color(num))
        else:
            self.badge.hide()

        toggled_only = layer == num and not st.locked(layer)
        if layer == 0 or toggled_only or not self.enabled:
            self.delay.stop()
            self.pending_layer = None
            self.overlay.hide()
            return
        if self.overlay.isVisible():
            self.overlay.show_layer(layer, st.locked(layer))
        elif self.pending_layer != layer:
            self.pending_layer = layer
            self.delay.start(SHOW_DELAY_MS)

    def _show_pending(self) -> None:
        st = self.state
        if st is None or self.pending_layer is None:
            return
        layer = min(st.highest_layer, len(self.data.names) - 1)
        if layer == self.pending_layer:
            self.overlay.show_layer(layer, st.locked(layer))
        self.pending_layer = None


def run(sheet_only: bool = False) -> int:
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    data = KeymapData.bundled()

    try:
        listener: UdpListener | None = UdpListener()
    except OSError:
        log.error("UDP port busy: is the overlay already running? Claude Code status disabled.")
        listener = None

    controller = Controller(data, sheet_only=sheet_only)
    rows, cols = data.matrix_size
    worker = Worker(rows, cols, listener)
    worker.state.connect(controller.on_state, Qt.ConnectionType.QueuedConnection)
    worker.keymap.connect(controller.on_keymap, Qt.ConnectionType.QueuedConnection)
    worker.start()
    code = app.exec()
    worker.requestInterruption()
    worker.wait(2000)
    if listener:
        listener.close()
    return code
