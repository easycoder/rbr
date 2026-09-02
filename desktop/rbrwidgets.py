#   rbrwidgets.py — PWA-style widget classes for the RBR desktop app.
#
# Mirrors the design language of the new-ui web PWA (see
# new-ui/resources/css/tokens.css): white cards on a light page, accent
# orange #E86A33, rounded corners, status chips. Everything here is
# RBR-specific presentation — no AllSpeak-core changes are involved.
#
# Each class is a plain PySide6 widget. The AllSpeak plugin (rbr_ui.py)
# wraps them as custom variable types.

import json
import os

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from allspeak.as_gclasses import ECWidget

###############################################################################
# Design tokens — mirror of new-ui/resources/css/tokens.css

ACCENT = '#E86A33'
ACCENT_HOVER = '#D95A24'
ACCENT_8 = '#E86A3314'
TEXT_PRIMARY = '#1A1A1A'
TEXT_SECONDARY = '#666666'
TEXT_MUTED = '#999999'
SURFACE_CARD = '#FFFFFF'
SURFACE_SUNK = '#F4F5F7'
SURFACE_PILL = '#FAFAFA'
CHIP_OK_BG = '#E6EFF7'
CHIP_OK_FG = '#2F75B5'
CHIP_WARN_BG = '#FFF4E0'
CHIP_WARN_FG = '#C78A1A'
CHIP_NEUTRAL_BG = '#F1F3F5'
CHIP_NEUTRAL_FG = '#999999'
BORDER_HAIRLINE = '#ECECEC'
BORDER_DIVIDER_SOFT = '#F3F3F3'
SCROLL_BG = '#F4F5F7'

RADIUS_CARD = 16
RADIUS_CHIP = 12
RADIUS_BUTTON = 12

ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')


def tinted_pixmap(name, color, size=18):
    """Load an SVG icon from assets and tint it with `color`."""
    path = os.path.join(ASSET_DIR, name)
    pixmap = QPixmap(path)
    if pixmap.isNull():
        return QPixmap(size, size)
    tinted = QPixmap(pixmap.size())
    tinted.fill(Qt.GlobalColor.transparent)
    painter = QPainter(tinted)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
    painter.drawPixmap(0, 0, pixmap)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(tinted.rect(), QColor(color))
    painter.end()
    return tinted.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation)


def format_temp(hundredths):
    """Map temperature in integer hundredths of a degree to '21.5'."""
    if hundredths in (None, '', -1):
        return '--.-'
    try:
        return f'{float(hundredths) / 100.0:.1f}'
    except (TypeError, ValueError):
        return '--.-'


def display_mode(mode, advance):
    """Human-readable mode name, honouring the advance override."""
    if mode == 'timed' and advance not in ('', '-', 'C'):
        return 'Advance'
    names = {'timed': 'Timed', 'boost': 'Boost', 'on': 'On', 'off': 'Off'}
    return names.get(mode, 'Off')


def chip_style(mode, relay):
    """(icon name, background, foreground) for a room's status chip."""
    if mode == 'boost':
        return 'boost.svg', ACCENT_8, ACCENT
    if mode in ('on', 'advance') or relay == 'on':
        return 'flame.svg', ACCENT_8, ACCENT
    if mode == 'timed':
        return 'clock.svg', CHIP_OK_BG, CHIP_OK_FG
    return 'off.svg', CHIP_NEUTRAL_BG, CHIP_NEUTRAL_FG


###############################################################################
# RBRWidget — AllSpeak EC wrapper base (value storage for the plugin)

class RBRWidget(ECWidget):
    def __init__(self):
        super().__init__()

    def setContent(self, content):
        if self.values is None:
            self.index = 0
            self.elements = 1
            self.values = [None]
        self.values[self.index] = content

    # The widget itself is stored as the value
    def setWidget(self, widget):
        super().setValue(widget)

    def getWidget(self):
        return super().getValue()


###############################################################################
# EC wrapper classes — one per AllSpeak variable type (distinct names from
# the QWidget classes they wrap)

class ECRBRRoom(RBRWidget):
    pass


class ECRBRWin(RBRWidget):
    pass


class ECRBRTopBar(RBRWidget):
    pass


class ECRBRProfiles(RBRWidget):
    pass


class ECRBRSheet(RBRWidget):
    pass


class ECRBRSchedSheet(RBRWidget):
    pass


class ECRBRProfileSheet(RBRWidget):
    pass


class ECRBRRoomsSheet(RBRWidget):
    pass


class ECRBRCalendarSheet(RBRWidget):
    pass


class ECRBRButton(RBRWidget):
    pass


###############################################################################
# RBRButton — a clickable pushbutton with a pluggable callback

class RBRButton(QPushButton):
    def __init__(self, text='', icon=None, parent=None):
        super().__init__(text, parent)
        self.clickCallback = None
        if icon is not None:
            self.setIcon(icon)
            self.setIconSize(QSize(18, 18))
        if text:
            font = self.font()
            font.setPointSize(13)
            font.setWeight(QFont.Weight.DemiBold)
            self.setFont(font)
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def setClickCallback(self, cb):
        self.clickCallback = cb
        self.clicked.connect(cb)


###############################################################################
# TopBar — house mark, app name + system id, heartbeat dot, hamburger

class TopBar(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(64)
        self.setStyleSheet(f'background-color: {SURFACE_CARD}; border-bottom: 1px solid {BORDER_HAIRLINE};')

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(12)

        # House mark
        mark = QLabel()
        mark.setFixedSize(38, 38)
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setPixmap(tinted_pixmap('house.svg', '#FFFFFF', 20))
        mark.setStyleSheet(f'background-color: {ACCENT}; border-radius: 11px;')
        layout.addWidget(mark)

        # App name + system id
        textColumn = QVBoxLayout()
        textColumn.setSpacing(0)
        self.appName = QLabel('Room By Room')
        appFont = self.appName.font()
        appFont.setPointSize(16)
        appFont.setWeight(QFont.Weight.Bold)
        self.appName.setFont(appFont)
        self.appName.setStyleSheet(f'color: {TEXT_PRIMARY}; background: transparent; border: none;')
        textColumn.addWidget(self.appName)
        self.systemId = QLabel('')
        idFont = self.systemId.font()
        idFont.setPointSize(10)
        idFont.setWeight(QFont.Weight.Medium)
        self.systemId.setFont(idFont)
        self.systemId.setStyleSheet(f'color: {TEXT_SECONDARY}; background: transparent; border: none;')
        textColumn.addWidget(self.systemId)
        layout.addLayout(textColumn)

        layout.addStretch(1)

        # Heartbeat dot — pulses accent on every map reply
        self.heart = QLabel()
        self.heart.setFixedSize(12, 12)
        self.heart.setStyleSheet(f'background-color: {CHIP_NEUTRAL_FG}; border-radius: 6px;')
        self._pulseTimer = QTimer(self)
        self._pulseTimer.setInterval(250)
        self._pulseTimer.timeout.connect(self._heartbeatPulse)
        self._pulseCount = 0
        layout.addWidget(self.heart)

        # Calling-for-heat pill — shows when any room is calling for heat,
        # mirroring the web PWA's summary ("N rooms calling for heat" or
        # the room name for a single caller). Hidden when nothing calls.
        self.calling = QLabel('')
        cf = self.calling.font()
        cf.setPointSize(9)
        cf.setWeight(QFont.Weight.DemiBold)
        self.calling.setFont(cf)
        self.calling.setStyleSheet(
            f'background-color: {ACCENT_8}; color: {ACCENT}; border-radius: 9px; padding: 2px 8px;')
        self.calling.hide()
        layout.addWidget(self.calling)

        # Request-relay indicator — small chip, visible while a boiler
        # request relay is configured
        self.request = QLabel('')
        rf = self.request.font()
        rf.setPointSize(9)
        rf.setWeight(QFont.Weight.DemiBold)
        self.request.setFont(rf)
        self.request.setStyleSheet(
            f'background-color: {CHIP_WARN_BG}; color: {CHIP_WARN_FG}; border-radius: 9px; padding: 2px 8px;')
        self.request.hide()
        layout.addWidget(self.request)

        # Hamburger
        self.hamburger = RBRButton()
        self.hamburger.setFixedSize(38, 38)
        self.hamburger.setIcon(tinted_pixmap('hamburger.png', '#555555', 18))
        self.hamburger.setIconSize(QSize(18, 18))
        self.hamburger.setStyleSheet(
            f'QPushButton {{ background-color: rgba(0,0,0,0.04); border: none; border-radius: 12px; }}'
            f'QPushButton:hover {{ background-color: rgba(0,0,0,0.08); }}')
        layout.addWidget(self.hamburger)

    def setSystemName(self, name):
        self.systemId.setText(name)

    def setCalling(self, text):
        """Show the calling-for-heat pill (mirrors the PWA summary). Empty
        text hides it. Long text is elided so the pill can't overflow the
        fixed-width top bar."""
        if text:
            fm = self.calling.fontMetrics()
            self.calling.setText(fm.elidedText(text, Qt.TextElideMode.ElideRight, 180))
            self.calling.show()
        else:
            self.calling.hide()

    def setRequest(self, name):
        if name:
            self.request.setText(name)
            self.request.show()
        else:
            self.request.hide()

    def setClickCallback(self, cb):
        self.hamburger.setClickCallback(cb)

    def setHeartbeat(self, active):
        """Pulse the dot on every map reply (active) so the liveness signal
        is actually visible; rest to the neutral grey when idle."""
        if active:
            self._pulseCount = 0
            if not self._pulseTimer.isActive():
                self._pulseTimer.start()
        else:
            self._pulseTimer.stop()
            self.heart.setStyleSheet(
                f'background-color: {CHIP_NEUTRAL_FG}; border-radius: 6px;')

    def _heartbeatPulse(self):
        # A blink per reply: bright -> disappear -> bright (3 ticks), then
        # rest bright so the dot reads "alive" between pulses. The dim state
        # is SURFACE_CARD (the top bar's own white) so the dot vanishes
        # completely without shifting the layout.
        self._pulseCount += 1
        color = ACCENT if self._pulseCount % 2 == 1 else SURFACE_CARD
        self.heart.setStyleSheet(
            f'background-color: {color}; border-radius: 6px;')
        if self._pulseCount >= 3:
            self._pulseTimer.stop()
            self.heart.setStyleSheet(
                f'background-color: {ACCENT}; border-radius: 6px;')


###############################################################################
# ProfileBar — horizontal row of profile pills

class ProfileBar(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet('background: transparent;')
        self.row = QHBoxLayout(self)
        self.row.setContentsMargins(0, 0, 0, 0)
        self.row.setSpacing(8)
        self.pills = []
        self.clickCallback = None

    def setClickCallback(self, cb):
        self.clickCallback = cb

    def setProfiles(self, names, selected=0):
        # Remove existing pills
        for pill in self.pills:
            self.row.removeWidget(pill)
            pill.deleteLater()
        self.pills = []
        for i, name in enumerate(names):
            pill = QPushButton(name)
            pill.setFixedHeight(34)
            pill.setCursor(Qt.CursorShape.PointingHandCursor)
            font = pill.font()
            font.setPointSize(11)
            font.setWeight(QFont.Weight.DemiBold)
            pill.setFont(font)
            if i == selected:
                pill.setStyleSheet(
                    f'QPushButton {{ background-color: {ACCENT}; color: white; border: none; border-radius: 17px; padding: 0 16px; }}')
            else:
                pill.setStyleSheet(
                    f'QPushButton {{ background-color: {SURFACE_PILL}; color: {TEXT_SECONDARY}; border: 1px solid {BORDER_HAIRLINE}; border-radius: 17px; padding: 0 16px; }}'
                    f'QPushButton:hover {{ background-color: {CHIP_NEUTRAL_BG}; }}')
            index = i
            pill.clicked.connect(lambda checked=False, idx=index: self._onPill(idx))
            self.row.addWidget(pill)
            self.pills.append(pill)

    def _onPill(self, index):
        if self.clickCallback is not None:
            self.clickCallback(index)


###############################################################################
# RoomCard — PWA room card: chip, name/tags, subline, temperature, chevron,
# plus an expansion block with mode control (Timed/On/Off/Boost), target
# steppers and boost durations.

class RoomCard(QFrame):
    MODES = (('Timed', 'timed'), ('On', 'on'), ('Off', 'off'), ('Boost', 'boost'))
    BOOSTS = (('30 min', 30), ('1 hr', 60), ('2 hr', 120))

    def __init__(self, spec=None, index=0):
        super().__init__()
        self.spec = spec or {}
        self.index = index
        self.clickCallback = None
        self.pending = None
        self._currentTarget = None
        self.setStyleSheet(f'background-color: {SURFACE_CARD}; border-radius: {RADIUS_CARD}px;')
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.card = QVBoxLayout(self)
        self.card.setContentsMargins(16, 14, 16, 14)
        self.card.setSpacing(10)

        # Rest row
        self.restRow = QHBoxLayout()
        self.restRow.setSpacing(12)

        self.chip = QLabel()
        self.chip.setFixedSize(38, 38)
        self.chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.restRow.addWidget(self.chip)

        textCol = QVBoxLayout()
        textCol.setSpacing(2)
        self.nameLabel = QLabel('')
        nameFont = self.nameLabel.font()
        nameFont.setPointSize(13)
        nameFont.setWeight(QFont.Weight.DemiBold)
        self.nameLabel.setFont(nameFont)
        self.nameLabel.setStyleSheet(f'color: {TEXT_PRIMARY}; background: transparent; border: none;')
        textCol.addWidget(self.nameLabel)
        self.subline = QLabel('')
        subFont = self.subline.font()
        subFont.setPointSize(10)
        self.subline.setFont(subFont)
        self.subline.setStyleSheet(f'color: {TEXT_MUTED}; background: transparent; border: none;')
        textCol.addWidget(self.subline)
        self.restRow.addLayout(textCol, 1)

        self.tempLabel = QLabel('--.-°')
        tempFont = self.tempLabel.font()
        tempFont.setPointSize(24)
        tempFont.setWeight(QFont.Weight.Bold)
        self.tempLabel.setFont(tempFont)
        self.tempLabel.setStyleSheet(f'color: {TEXT_PRIMARY}; background: transparent; border: none;')
        self.restRow.addWidget(self.tempLabel)

        self.chevron = QLabel()
        self.chevron.setFixedSize(20, 20)
        self.chevron.setPixmap(tinted_pixmap('chevron.svg', TEXT_MUTED, 14))
        self.restRow.addWidget(self.chevron)

        self.card.addLayout(self.restRow)

        # Expansion block (mode control) — hidden until the rest row is tapped
        self.expansion = QWidget()
        self.expansion.setVisible(False)
        self.expansionLayout = QVBoxLayout(self.expansion)
        self.expansionLayout.setContentsMargins(0, 0, 0, 0)
        self.expansionLayout.setSpacing(8)
        self.card.addWidget(self.expansion)

        if self.spec:
            self.render(self.spec)

    # ---- click plumbing ----------------------------------------------------

    def setClickCallback(self, cb):
        self.clickCallback = cb

    def mouseReleaseEvent(self, event):
        # Single-open expansion: tapping a closed card closes any other
        # open card first (mirrors the web PWA); tapping the open card
        # closes it. The window reference is set by addRoomCard.
        window = getattr(self, 'expansionWindow', None)
        if window is not None:
            window.onRoomCardClicked(self)
        else:
            self.toggleExpansion()
        if self.clickCallback is not None:
            self.clickCallback(self.index)
        super().mouseReleaseEvent(event)

    def _tap(self, pending):
        self.pending = pending
        if self.clickCallback is not None:
            self.clickCallback(self.index)

    def getPending(self):
        pending = self.pending
        self.pending = None
        if pending is None:
            return None
        pending.setdefault('index', self.index)
        return pending

    def toggleExpansion(self):
        self.expansion.setVisible(not self.expansion.isVisible())

    def isExpanded(self):
        return self.expansion.isVisible()

    # ---- expansion build ---------------------------------------------------

    def _clearLayout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
            child = item.layout()
            if child is not None:
                self._clearLayout(child)

    def _pill(self, text, active):
        btn = QPushButton(text)
        btn.setFixedHeight(34)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        font = btn.font()
        font.setPointSize(11)
        font.setWeight(QFont.Weight.DemiBold)
        btn.setFont(font)
        if active:
            btn.setStyleSheet(
                f'QPushButton {{ background-color: {ACCENT}; color: white; border: none; border-radius: 17px; padding: 0 14px; }}')
        else:
            btn.setStyleSheet(
                f'QPushButton {{ background-color: {SURFACE_PILL}; color: {TEXT_SECONDARY}; border: 1px solid {BORDER_HAIRLINE}; border-radius: 17px; padding: 0 14px; }}'
                f'QPushButton:hover {{ background-color: {CHIP_NEUTRAL_BG}; }}')
        return btn

    def _targetString(self):
        if self._currentTarget is not None:
            return self._currentTarget
        target = self.spec.get('target')
        if target in (None, ''):
            return '20.0'
        try:
            return f'{float(target):.1f}'
        except (TypeError, ValueError):
            return '20.0'

    def _stepTarget(self, delta_tenths):
        try:
            tenths = int(round(float(self._targetString()) * 10)) + delta_tenths
        except (TypeError, ValueError):
            tenths = 200
        tenths = max(50, min(300, tenths))
        self._currentTarget = f'{tenths / 10.0:.1f}'
        # Local feedback: update the label immediately so taps don't look
        # dead while the controller's map reply is on its way (or offline).
        if hasattr(self, 'targetLabel'):
            self.targetLabel.setText(self._currentTarget + '°')
        return self._currentTarget

    def buildExpansion(self, spec):
        self._clearLayout(self.expansionLayout)
        mode = spec.get('mode', 'off')
        relay = spec.get('relay', 'off')
        advance = spec.get('advance', '-')

        # Mode pills
        modeRow = QHBoxLayout()
        modeRow.setSpacing(8)
        for label, m in self.MODES:
            active = (m == mode) or (m == 'on' and relay == 'on')
            btn = self._pill(label, active)
            btn.clicked.connect(lambda checked=False, mm=m: self._tap({'action': 'mode', 'mode': mm}))
            modeRow.addWidget(btn)
        self.expansionLayout.addLayout(modeRow)

        # Target steppers — visible only in On and Boost (mirrors the PWA's
        # steady-state target-tile visibility). Hidden in Timed mode: the
        # schedule owns the setpoint there, so an editable target is wrong.
        # Hidden in Off: nothing to adjust until a mode is applied.
        if mode in ('on', 'boost'):
            targetRow = QHBoxLayout()
            targetRow.setSpacing(8)
            down = self._pill('−', False)
            down.setFixedWidth(44)
            down.clicked.connect(lambda: self._tap({'action': 'target', 'target': self._stepTarget(-5)}))
            targetRow.addWidget(down)
            self.targetLabel = QLabel(self._targetString() + '°')
            tf = self.targetLabel.font()
            tf.setPointSize(13)
            tf.setWeight(QFont.Weight.Bold)
            self.targetLabel.setFont(tf)
            self.targetLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.targetLabel.setStyleSheet(f'color: {TEXT_PRIMARY}; background: transparent; border: none;')
            targetRow.addWidget(self.targetLabel, 1)
            up = self._pill('+', False)
            up.setFixedWidth(44)
            up.clicked.connect(lambda: self._tap({'action': 'target', 'target': self._stepTarget(5)}))
            targetRow.addWidget(up)
            self.expansionLayout.addLayout(targetRow)

        # Advance toggle (timed mode)
        if mode == 'timed':
            advText = 'Cancel advance' if advance not in ('-', '', 'C') else 'Advance'
            adv = self._pill(advText, advance not in ('-', '', 'C'))
            adv.clicked.connect(lambda: self._tap({'action': 'advance'}))
            self.expansionLayout.addWidget(adv)

        # Boost durations (boost mode)
        if mode == 'boost':
            boostRow = QHBoxLayout()
            boostRow.setSpacing(8)
            for label, minutes in self.BOOSTS:
                b = self._pill(label, False)
                b.clicked.connect(lambda checked=False, mm=minutes: self._tap({'action': 'boost', 'duration': mm}))
                boostRow.addWidget(b)
            self.expansionLayout.addLayout(boostRow)

        # Edit schedule — always present (mirrors the PWA's room-row
        # `room-<i>-edit-schedule` button). Opens the schedule editor sheet.
        # Font matches the room pills (_pill: 11pt DemiBold).
        edit = QPushButton('Edit schedule')
        edit.setFixedHeight(40)
        edit.setCursor(Qt.CursorShape.PointingHandCursor)
        ef = edit.font()
        ef.setPointSize(11)
        ef.setWeight(QFont.Weight.DemiBold)
        edit.setFont(ef)
        edit.setStyleSheet(
            f'QPushButton {{ background-color: {SURFACE_CARD}; color: {TEXT_PRIMARY}; '
            f'border: 1px solid {BORDER_HAIRLINE}; border-radius: 12px; padding: 0 14px; }}'
            f'QPushButton:hover {{ background-color: {CHIP_NEUTRAL_BG}; }}')
        edit.clicked.connect(lambda: self._tap({'action': 'editschedule'}))
        self.expansionLayout.addWidget(edit)

    # ---- rendering ---------------------------------------------------------

    def render(self, spec):
        """Render a room dictionary from the controller's map."""
        self.spec = spec
        self._currentTarget = None
        mode = spec.get('mode', 'off')
        relay = spec.get('relay', 'off')
        status = spec.get('status', 'good')
        advance = spec.get('advance', '-')

        icon, bg, fg = chip_style(mode, relay)
        self.chip.setPixmap(tinted_pixmap(icon, fg, 18))
        self.chip.setStyleSheet(f'background-color: {bg}; border-radius: 12px;')

        name = spec.get('name', 'Room')
        fm = self.nameLabel.fontMetrics()
        self.nameLabel.setText(fm.elidedText(name, Qt.TextElideMode.ElideRight, 200))

        sub = spec.get('statusMessage', '')
        if not sub:
            target = spec.get('target')
            modeText = display_mode(mode, advance)
            sub = f'{modeText}' + (f' · {target}°' if target not in (None, '', 0) else '')
        subfm = self.subline.fontMetrics()
        self.subline.setText(subfm.elidedText(sub, Qt.TextElideMode.ElideRight, 240))

        self.tempLabel.setText(f'{format_temp(spec.get("temperature"))}°')

        # Refresh the expansion controls (mode may have changed)
        self.buildExpansion(spec)

    def getExpansion(self):
        return self.expansion

    def getExpansionLayout(self):
        return self.expansionLayout


###############################################################################
# SheetRow — one tappable menu row. A plain QWidget (NOT a QPushButton): the
# button style's sizeHint ignores a child layout, which collapsed the rows and
# squeezed the labels to zero height (blank menu items). A QWidget sizes from
# its layout, so the labels keep their natural height.

class SheetRow(QWidget):
    def __init__(self, rowId, parent=None):
        super().__init__(parent)
        self.rowId = rowId
        self._clicked = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            f'SheetRow {{ background: transparent; border: none; '
            f'border-top: 1px solid {BORDER_DIVIDER_SOFT}; }}'
            f'SheetRow:hover {{ background-color: {CHIP_NEUTRAL_BG}; }}')

    def setClickCallback(self, cb):
        self._clicked = cb

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._clicked is not None:
            self._clicked(self.rowId)
        super().mouseReleaseEvent(event)


###############################################################################
# Sheet — scrim + panel overlay (menu and dialogs)

class Sheet(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f'background-color: rgba(0,0,0,0.35);')
        self.hide()
        self.clickCallback = None
        self.rows = []

        self.wrap = QVBoxLayout(self)
        self.wrap.setContentsMargins(0, 0, 0, 0)

        self.wrap.addStretch(1)

        self.panel = QWidget()
        self.panel.setStyleSheet(f'background-color: {SURFACE_CARD}; border-radius: 24px 24px 0 0;')
        self.panelLayout = QVBoxLayout(self.panel)
        self.panelLayout.setContentsMargins(16, 16, 16, 24)
        self.panelLayout.setSpacing(0)
        self.wrap.addWidget(self.panel)

    def mousePressEvent(self, event):
        # Clicking the scrim (outside the panel) dismisses the sheet, so the
        # app never stays stuck behind an open overlay.
        if self.panel.geometry().contains(event.position().toPoint()):
            return
        self.hide()
        super().mousePressEvent(event)

    def setClickCallback(self, cb):
        self.clickCallback = cb
        self.pendingRow = ''

    def setTitle(self, title):
        label = QLabel(title)
        font = label.font()
        font.setPointSize(15)
        font.setWeight(QFont.Weight.Bold)
        label.setFont(font)
        label.setStyleSheet(f'color: {TEXT_PRIMARY}; background: transparent; border: none;')
        self.panelLayout.addWidget(label)
        self.panelLayout.addSpacing(8)

    def addRow(self, label, sub='', rowId=''):
        row = SheetRow(rowId)
        rowLayout = QHBoxLayout(row)
        rowLayout.setContentsMargins(4, 12, 4, 12)
        textCol = QVBoxLayout()
        textCol.setSpacing(1)
        labelEl = QLabel(label)
        labelFont = labelEl.font()
        labelFont.setPointSize(12)
        labelFont.setWeight(QFont.Weight.Medium)
        labelEl.setFont(labelFont)
        labelEl.setStyleSheet(f'color: {TEXT_PRIMARY}; background: transparent; border: none;')
        textCol.addWidget(labelEl)
        if sub:
            subEl = QLabel(sub)
            subFont = subEl.font()
            subFont.setPointSize(10)
            subEl.setFont(subFont)
            subEl.setStyleSheet(f'color: {TEXT_MUTED}; background: transparent; border: none;')
            textCol.addWidget(subEl)
        rowLayout.addLayout(textCol)
        rowLayout.addStretch(1)
        chev = QLabel()
        chev.setPixmap(tinted_pixmap('chevron.svg', TEXT_MUTED, 14))
        rowLayout.addWidget(chev)
        self.rows.append(row)
        row.setClickCallback(lambda rid: self._onRow(rid))
        self.panelLayout.addWidget(row)

    def addInput(self, label='', initial=''):
        """A labelled text-input row (used by the name/request/add dialogs)."""
        wrap = QWidget()
        wrapLayout = QVBoxLayout(wrap)
        wrapLayout.setContentsMargins(4, 10, 4, 4)
        wrapLayout.setSpacing(4)
        if label:
            lab = QLabel(label)
            labFont = lab.font()
            labFont.setPointSize(11)
            labFont.setWeight(QFont.Weight.Medium)
            lab.setFont(labFont)
            lab.setStyleSheet(f'color: {TEXT_SECONDARY}; background: transparent; border: none;')
            wrapLayout.addWidget(lab)
        self.input = QLineEdit(initial)
        self.input.setFixedHeight(36)
        self.input.setStyleSheet(
            f'QLineEdit {{ background-color: {SURFACE_SUNK}; border: 1px solid {BORDER_HAIRLINE}; border-radius: 10px; padding: 0 10px; color: {TEXT_PRIMARY}; }}'
            f'QLineEdit:focus {{ border: 1px solid {ACCENT}; }}')
        wrapLayout.addWidget(self.input)
        self.panelLayout.addWidget(wrap)

    def getInput(self):
        return self.input.text() if hasattr(self, 'input') else ''

    def setInput(self, text):
        if hasattr(self, 'input'):
            self.input.setText(text)

    def _onRow(self, rowId):
        self.pendingRow = rowId
        if self.clickCallback is not None:
            self.clickCallback(rowId)

    def getPendingRow(self):
        row = self.pendingRow
        self.pendingRow = ''
        return row

    def clearRows(self):
        for row in self.rows:
            self.panelLayout.removeWidget(row)
            row.deleteLater()
        self.rows = []

    def setKeyboardClearance(self, px):
        """Raise the panel above the virtual keyboard: a bottom margin on
        the wrap layout pushes the panel (and its input + Save/Cancel rows)
        up so the keyboard doesn't obscure them. px=0 restores."""
        if px > 0:
            self.wrap.setContentsMargins(0, 0, 0, px)
        else:
            self.wrap.setContentsMargins(0, 0, 0, 0)


###############################################################################
# ScheduleSheet — the per-room schedule editor (periods of a timed mode).
# Mirrors the web PWA's schedule editor (schedule-editor.json /
# schedule-period.json): a profile pill with a picker to switch the profile
# being edited, a scrollable list of period cards (On-at / Off-at / Target
# steppers + delete), an Add-period button, and Save / Cancel rows.
#
# The widget is pure presentation — the app script owns the working copy of
# the periods (rendered back via `set periods`) and the profiles snapshot.
# Every user action is queued as an event drained via `get pending`:
#
#   {'event':'step',  'period':i, 'field':'start'|'off'|'target',
#    'delta': ±15 min or ±5 tenths}
#   {'event':'delete','period':i}
#   {'event':'add'}
#   {'event':'profile','index':k}
#   {'event':'save'} / {'event':'cancel'}
#
# Subclasses Sheet so the scrim, panel chrome, title and Save/Cancel rows
# behave exactly like the other desktop dialog sheets.

class _ProfilePill(QWidget):
    """The 'PROFILE <name> ⌄' selector row — a tappable pill that toggles
    the profile picker. A proper subclass so Qt dispatches the tap
    reliably (instance-level monkeypatches of virtuals are not guaranteed)."""

    def __init__(self, on_tap):
        super().__init__()
        self._on_tap = on_tap
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            f'QWidget {{ background: transparent; border: 1px solid {BORDER_HAIRLINE}; '
            f'border-radius: 12px; }}')
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)
        label = QLabel('Profile')
        lf = label.font()
        lf.setPointSize(10)
        lf.setWeight(QFont.Weight.DemiBold)
        label.setFont(lf)
        label.setStyleSheet(f'color: {TEXT_MUTED}; background: transparent; border: none;')
        layout.addWidget(label)
        layout.addStretch(1)
        self.value = QLabel('')
        vf = self.value.font()
        vf.setPointSize(13)
        vf.setWeight(QFont.Weight.Medium)
        self.value.setFont(vf)
        self.value.setStyleSheet(
            f'color: {TEXT_PRIMARY}; background: transparent; border: none;')
        layout.addWidget(self.value)
        chev = QLabel()
        chev.setPixmap(tinted_pixmap('chevron.svg', TEXT_MUTED, 12))
        layout.addWidget(chev)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_tap()
        super().mouseReleaseEvent(event)


class ScheduleSheet(Sheet):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.events = []              # queued pending events
        self._pickerOpen = False
        self._profileNames = []
        self._selectedProfile = 0
        self._titleWidgets = []

        # Profile selector pill ('PROFILE <name> ⌄'); tapping toggles the picker
        self._pill = _ProfilePill(self._togglePicker)
        self._pillValue = self._pill.value
        self.panelLayout.addWidget(self._pill)
        self.panelLayout.addSpacing(8)

        # Profile picker — hidden until the pill is tapped
        self._picker = QWidget()
        self._pickerLayout = QVBoxLayout(self._picker)
        self._pickerLayout.setContentsMargins(0, 0, 0, 0)
        self._pickerLayout.setSpacing(6)
        self._picker.hide()
        self.panelLayout.addWidget(self._picker)
        self.panelLayout.addSpacing(12)

        # Scrollable period list
        self._periodScroll = QScrollArea()
        self._periodScroll.setWidgetResizable(True)
        self._periodScroll.setFrameShape(QFrame.Shape.NoFrame)
        self._periodScroll.setStyleSheet(
            f'QScrollArea {{ background: transparent; border: none; }}')
        self._periodScroll.setMaximumHeight(420)
        self._periodList = QWidget()
        self._periodList.setStyleSheet('background: transparent;')
        self._periodListLayout = QVBoxLayout(self._periodList)
        self._periodListLayout.setContentsMargins(0, 0, 4, 0)
        self._periodListLayout.setSpacing(10)
        self._periodScroll.setWidget(self._periodList)
        self.panelLayout.addWidget(self._periodScroll)
        self.panelLayout.addSpacing(12)

        # Add-period button
        add = QPushButton('+ Add period')
        add.setFixedHeight(40)
        add.setCursor(Qt.CursorShape.PointingHandCursor)
        af = add.font()
        af.setPointSize(12)
        af.setWeight(QFont.Weight.Medium)
        add.setFont(af)
        add.setStyleSheet(
            f'QPushButton {{ background: transparent; border: 1px dashed {BORDER_HAIRLINE}; '
            f'border-radius: 12px; color: {TEXT_PRIMARY}; }}'
            f'QPushButton:hover {{ background-color: {CHIP_NEUTRAL_BG}; }}')
        add.clicked.connect(lambda: self._emit({'event': 'add'}))
        self.panelLayout.addWidget(add)
        self.panelLayout.addSpacing(12)

        # Save / Cancel — side by side in one row, mirroring the PWA's
        # schedule-editor $Buttons (Cancel outline, Save accent-filled).
        buttons = QHBoxLayout()
        buttons.setSpacing(10)

        def action_button(text, accent):
            b = QPushButton(text)
            b.setFixedHeight(44)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            bf = b.font()
            bf.setPointSize(12)
            bf.setWeight(QFont.Weight.DemiBold if accent else QFont.Weight.Medium)
            b.setFont(bf)
            if accent:
                b.setStyleSheet(
                    f'QPushButton {{ background-color: {ACCENT}; color: white; border: none; '
                    f'border-radius: 12px; }}'
                    f'QPushButton:hover {{ background-color: {ACCENT_HOVER}; }}')
            else:
                b.setStyleSheet(
                    f'QPushButton {{ background-color: {SURFACE_CARD}; color: {TEXT_PRIMARY}; '
                    f'border: 1px solid {BORDER_HAIRLINE}; border-radius: 12px; }}'
                    f'QPushButton:hover {{ background-color: {CHIP_NEUTRAL_BG}; }}')
            return b

        cancel = action_button('Cancel', False)
        cancel.clicked.connect(lambda: self._emit({'event': 'cancel'}))
        buttons.addWidget(cancel, 1)
        save = action_button('Save', True)
        save.clicked.connect(lambda: self._emit({'event': 'save'}))
        buttons.addWidget(save, 1)
        self.panelLayout.addLayout(buttons)

    # ---- event queue -------------------------------------------------------

    def _emit(self, event):
        self.events.append(event)
        if self.clickCallback is not None:
            self.clickCallback(None)

    def getPending(self):
        """Pop the oldest queued user action, or {} when idle."""
        if not self.events:
            return {}
        return self.events.pop(0)

    def _onRow(self, rowId):
        # No rows are added to a ScheduleSheet (Save/Cancel are buttons);
        # the inherited hook stays in case rows are ever used.
        self._emit({'event': rowId})

    def mousePressEvent(self, event):
        # Tapping the scrim behaves like the Cancel row: queue a cancel
        # event so the app handler closes the editing session cleanly, and
        # hide (matching the other dialog sheets' dismiss-on-scrim).
        if self.panel.geometry().contains(event.position().toPoint()):
            return
        self._emit({'event': 'cancel'})
        self.hide()

    # ---- title / profile ---------------------------------------------------

    def setTitle(self, title):
        # The title lives above the profile pill; replace it on re-open
        # (each open sets 'Schedule for <room>').
        for w in self._titleWidgets:
            self.panelLayout.removeWidget(w)
            w.deleteLater()
        label = QLabel(title)
        font = label.font()
        font.setPointSize(15)
        font.setWeight(QFont.Weight.Bold)
        label.setFont(font)
        label.setStyleSheet(f'color: {TEXT_PRIMARY}; background: transparent; border: none;')
        self._titleWidgets = [label]
        self.panelLayout.insertWidget(0, label)

    def setProfile(self, name):
        """Label of the profile being edited."""
        if self._pillValue is not None:
            self._pillValue.setText(name)

    def setProfiles(self, names, selected=0):
        """Populate the profile picker pills; highlight `selected`."""
        self._profileNames = list(names)
        self._selectedProfile = selected
        while self._pickerLayout.count():
            item = self._pickerLayout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        for i, name in enumerate(self._profileNames):
            p = QPushButton(name)
            p.setFixedHeight(34)
            p.setCursor(Qt.CursorShape.PointingHandCursor)
            pf = p.font()
            pf.setPointSize(11)
            pf.setWeight(QFont.Weight.DemiBold)
            p.setFont(pf)
            if i == selected:
                p.setStyleSheet(
                    f'QPushButton {{ background: transparent; border: 1px solid {ACCENT}; '
                    f'border-radius: 10px; color: {ACCENT}; }}')
            else:
                p.setStyleSheet(
                    f'QPushButton {{ background: transparent; border: 1px solid {BORDER_HAIRLINE}; '
                    f'border-radius: 10px; color: {TEXT_PRIMARY}; }}'
                    f'QPushButton:hover {{ background-color: {CHIP_NEUTRAL_BG}; }}')
            index = i
            p.clicked.connect(lambda checked=False, idx=index: self._onProfilePill(idx))
            self._pickerLayout.addWidget(p)

    def _togglePicker(self):
        self._pickerOpen = not self._pickerOpen
        self._picker.setVisible(self._pickerOpen)

    def _onProfilePill(self, index):
        self._pickerOpen = False
        self._picker.setVisible(False)
        self._emit({'event': 'profile', 'index': index})

    # ---- period cards ------------------------------------------------------

    def setPeriods(self, periods):
        """Rebuild the period cards from a list of {start, off, target}."""
        while self._periodListLayout.count():
            item = self._periodListLayout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        for i, period in enumerate(periods):
            self._periodListLayout.addWidget(self._buildPeriodCard(i, period))

    def _buildPeriodCard(self, index, period):
        card = QWidget()
        card.setStyleSheet(
            f'QWidget {{ background-color: {SURFACE_CARD}; border: 1px solid {BORDER_HAIRLINE}; '
            f'border-radius: 12px; }}')
        col = QVBoxLayout(card)
        col.setContentsMargins(14, 12, 14, 12)
        col.setSpacing(10)

        def stepper(text):
            b = QPushButton(text)
            b.setFixedSize(30, 30)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            bf = b.font()
            bf.setPointSize(14)
            bf.setWeight(QFont.Weight.DemiBold)
            b.setFont(bf)
            b.setStyleSheet(
                f'QPushButton {{ background: transparent; border: 1px solid {BORDER_HAIRLINE}; '
                f'border-radius: 8px; color: {TEXT_PRIMARY}; }}'
                f'QPushButton:hover {{ background-color: {CHIP_NEUTRAL_BG}; }}')
            return b

        def value_label(text):
            lab = QLabel(text)
            lab.setMinimumWidth(60)
            lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lf = lab.font()
            lf.setPointSize(15)
            lf.setWeight(QFont.Weight.DemiBold)
            lab.setFont(lf)
            lab.setStyleSheet(f'color: {TEXT_PRIMARY}; background: transparent; border: none;')
            return lab

        def field_row(label_text, value, field):
            row = QHBoxLayout()
            row.setSpacing(10)
            lab = QLabel(label_text)
            llf = lab.font()
            llf.setPointSize(10)
            llf.setWeight(QFont.Weight.DemiBold)
            lab.setFont(llf)
            lab.setStyleSheet(f'color: {TEXT_MUTED}; background: transparent; border: none;')
            row.addWidget(lab)
            row.addStretch(1)
            minus = stepper('−')
            minus.clicked.connect(lambda checked=False, f=field: self._emit(
                {'event': 'step', 'period': index, 'field': f,
                 'delta': -15 if f != 'target' else -5}))
            row.addWidget(minus)
            row.addWidget(value)
            plus = stepper('+')
            plus.clicked.connect(lambda checked=False, f=field: self._emit(
                {'event': 'step', 'period': index, 'field': f,
                 'delta': 15 if f != 'target' else 5}))
            row.addWidget(plus)
            return row

        on_label = value_label(str(period.get('start', '06:00')))
        off_label = value_label(str(period.get('off', '08:00')))
        temp_label = value_label(str(period.get('target', '21.0')) + '°')
        col.addLayout(field_row('On at', on_label, 'start'))
        col.addLayout(field_row('Off at', off_label, 'off'))
        col.addLayout(field_row('Target', temp_label, 'target'))

        delete = QPushButton('Delete period')
        delete.setCursor(Qt.CursorShape.PointingHandCursor)
        df = delete.font()
        df.setPointSize(11)
        delete.setFont(df)
        delete.setStyleSheet(
            f'QPushButton {{ background: transparent; border: 1px solid {BORDER_HAIRLINE}; '
            f'border-radius: 6px; color: #C8392E; padding: 4px 10px; }}'
            f'QPushButton:hover {{ background-color: {CHIP_NEUTRAL_BG}; }}')
        delete.clicked.connect(lambda checked=False: self._emit(
            {'event': 'delete', 'period': index}))
        delRow = QHBoxLayout()
        delRow.addStretch(1)
        delRow.addWidget(delete)
        col.addLayout(delRow)
        return card


###############################################################################
# ProfileSheet — the profile manager (add / rename / delete / select).
# Mirrors the PWA's profile list: one row per profile with a selectable body,
# a pencil (rename) and an ✕ (delete); an Add-profile button below. Row taps
# and buttons queue events drained via `get pending`:
#
#   {'event':'select','index':i}   {'event':'rename','index':i}
#   {'event':'delete','index':i}   {'event':'add'}
#   {'event':'up'|'down','index':i}   (profile reorder)
#
# Edits apply immediately — the app ships one `Update Profiles` uirequest per
# action and the next map push re-renders the rows (`set profiles`). The
# weekly calendar is NOT edited here (a later phase); while the calendar is
# on the rows are dimmed and the app blocks row-tap selection.
#
# Subclasses Sheet so scrim/panel/title behave like the other sheets. Row
# actions have no chevron affordance (they are buttons, not navigation).

class ProfileSheet(Sheet):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.events = []
        self._calendarOn = False
        self._rowNames = []
        self._rowStyles = {}   # name_btn id() -> normal stylesheet (re-applied off dim)

        self._caption = QLabel('')
        cf = self._caption.font()
        cf.setPointSize(10)
        self._caption.setFont(cf)
        self._caption.setWordWrap(True)
        self._caption.setStyleSheet(
            f'color: {TEXT_MUTED}; background: transparent; border: none;')
        self.panelLayout.addWidget(self._caption)
        self.panelLayout.addSpacing(10)

        self._rowsBox = QVBoxLayout()
        self._rowsBox.setContentsMargins(0, 0, 0, 0)
        self._rowsBox.setSpacing(8)
        self.panelLayout.addLayout(self._rowsBox)
        self.panelLayout.addSpacing(12)

        add = QPushButton('+ Add profile')
        add.setFixedHeight(40)
        add.setCursor(Qt.CursorShape.PointingHandCursor)
        af = add.font()
        af.setPointSize(12)
        af.setWeight(QFont.Weight.Medium)
        add.setFont(af)
        add.setStyleSheet(
            f'QPushButton {{ background: transparent; border: 1px dashed {BORDER_HAIRLINE}; '
            f'border-radius: 12px; color: {TEXT_PRIMARY}; }}'
            f'QPushButton:hover {{ background-color: {CHIP_NEUTRAL_BG}; }}')
        add.clicked.connect(lambda: self._emit({'event': 'add'}))
        self.panelLayout.addWidget(add)

    # ---- event queue -------------------------------------------------------

    def _emit(self, event):
        self.events.append(event)
        if self.clickCallback is not None:
            self.clickCallback(None)

    def getPending(self):
        """Pop the oldest queued user action, or {} when idle."""
        if not self.events:
            return {}
        return self.events.pop(0)

    # ---- state -------------------------------------------------------------

    def setCalendar(self, on):
        """Display-only calendar state: dims the rows and explains why row
        taps are blocked (calendar editing arrives in a later phase)."""
        self._calendarOn = on
        if on:
            self._caption.setText(
                'The calendar chooses the active profile, so manual selection '
                'is off. You can still add, rename or delete profiles.')
        else:
            self._caption.setText('Tap a profile to make it active. ↑↓ reorder, pencil renames, ✕ deletes.')
        self._applyDim()

    def setProfiles(self, names, selected=0):
        """Rebuild the profile rows; `selected` gets the accent highlight."""
        while self._rowsBox.count():
            item = self._rowsBox.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._rowNames = []
        for i, name in enumerate(names):
            row = QWidget()
            rowLayout = QHBoxLayout(row)
            rowLayout.setContentsMargins(0, 0, 0, 0)
            rowLayout.setSpacing(8)

            name_btn = QPushButton(name)
            name_btn.setFixedHeight(44)
            name_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            nf = name_btn.font()
            nf.setPointSize(12)
            nf.setWeight(QFont.Weight.Medium)
            name_btn.setFont(nf)
            if i == selected:
                name_btn.setStyleSheet(
                    f'QPushButton {{ background-color: {ACCENT_8}; color: {TEXT_PRIMARY}; '
                    f'border: 1.5px solid {ACCENT}; border-radius: 12px; padding: 0 12px; '
                    f'text-align: left; }}')
            else:
                name_btn.setStyleSheet(
                    f'QPushButton {{ background-color: {SURFACE_CARD}; color: {TEXT_PRIMARY}; '
                    f'border: 1px solid {BORDER_HAIRLINE}; border-radius: 12px; padding: 0 12px; '
                    f'text-align: left; }}'
                    f'QPushButton:hover {{ background-color: {CHIP_NEUTRAL_BG}; }}')
            index = i

            # Save the normal stylesheet so dimming can be undone.
            self._rowNames.append(name_btn)
            self._rowStyles[id(name_btn)] = name_btn.styleSheet()

            total = len(names)

            def _arrow(text, tip, enabled):
                b = QPushButton(text)
                b.setFixedSize(38, 44)
                b.setCursor(Qt.CursorShape.PointingHandCursor)
                bf = b.font()
                bf.setPointSize(12)
                bf.setWeight(QFont.Weight.DemiBold)
                b.setFont(bf)
                b.setToolTip(tip)
                b.setEnabled(enabled)
                b.setStyleSheet(
                    f'QPushButton {{ background-color: {SURFACE_CARD}; color: {TEXT_SECONDARY}; '
                    f'border: 1px solid {BORDER_HAIRLINE}; border-radius: 12px; }}'
                    f'QPushButton:hover {{ background-color: {CHIP_NEUTRAL_BG}; }}'
                    f'QPushButton:disabled {{ color: {BORDER_HAIRLINE}; border-color: {BORDER_HAIRLINE}; }}')
                return b

            up_btn = _arrow('↑', 'Move profile up', i > 0)
            down_btn = _arrow('↓', 'Move profile down', i < total - 1)
            up_btn.clicked.connect(lambda checked=False, idx=index: self._emit(
                {'event': 'up', 'index': idx}))
            down_btn.clicked.connect(lambda checked=False, idx=index: self._emit(
                {'event': 'down', 'index': idx}))

            def _small(text, color, tip):
                b = QPushButton(text)
                b.setFixedSize(38, 44)
                b.setCursor(Qt.CursorShape.PointingHandCursor)
                bf = b.font()
                bf.setPointSize(14)
                b.setFont(bf)
                b.setToolTip(tip)
                b.setStyleSheet(
                    f'QPushButton {{ background-color: {SURFACE_CARD}; color: {color}; '
                    f'border: 1px solid {BORDER_HAIRLINE}; border-radius: 12px; }}'
                    f'QPushButton:hover {{ background-color: {CHIP_NEUTRAL_BG}; }}')
                return b

            rename_btn = _small('✎', TEXT_SECONDARY, 'Rename profile')
            delete_btn = _small('✕', '#C8392E', 'Delete profile')
            name_btn.clicked.connect(lambda checked=False, idx=index: self._emit(
                {'event': 'select', 'index': idx}))
            rename_btn.clicked.connect(lambda checked=False, idx=index: self._emit(
                {'event': 'rename', 'index': idx}))
            delete_btn.clicked.connect(lambda checked=False, idx=index: self._emit(
                {'event': 'delete', 'index': idx}))

            rowLayout.addWidget(up_btn)
            rowLayout.addWidget(down_btn)
            rowLayout.addWidget(name_btn, 1)
            rowLayout.addWidget(rename_btn)
            rowLayout.addWidget(delete_btn)
            self._rowsBox.addWidget(row)
        self._applyDim()

    def _applyDim(self):
        # While the calendar runs, row taps are blocked by the app (which
        # shows an explanatory notice) — but the rows must stay ENABLED so
        # the tap still arrives. Dim visually only (muted text + hairline,
        # no accent) and restore the normal styles when the calendar is off.
        for name_btn in self._rowNames:
            if self._calendarOn:
                name_btn.setStyleSheet(
                    f'QPushButton {{ background-color: {SURFACE_CARD}; color: {TEXT_MUTED}; '
                    f'border: 1px solid {BORDER_HAIRLINE}; border-radius: 12px; padding: 0 12px; '
                    f'text-align: left; }}')
            else:
                name_btn.setStyleSheet(self._rowStyles.get(id(name_btn), ''))


###############################################################################
# RoomsSheet — the room manager (reorder / add). Mirrors the PWA's room-list
# editing inside its Devices editor: one row per room with move-up / move-down
# buttons (disabled at the ends) and an Add-room button. Row actions queue
# events drained via `get pending`:
#
#   {'event':'up'|'down','index':i}   {'event':'add'}
#   {'event':'rename'|'delete','index':i}
#
# Reorders apply immediately — the app swaps the room in EVERY profile's
# parallel rooms array and ships one `Update Profiles` uirequest; the next
# map push re-renders the rows (`set rooms`). Room rename/delete are not
# here yet (like profiles-reorder, a later phase).
#
# Subclasses Sheet so scrim/panel/title behave like the other sheets.

class RoomsSheet(Sheet):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.events = []
        self._rowNames = []

        self._caption = QLabel('Use the arrows to change the room order; '
                               'the order applies to every profile.')
        cf = self._caption.font()
        cf.setPointSize(10)
        self._caption.setFont(cf)
        self._caption.setWordWrap(True)
        self._caption.setStyleSheet(
            f'color: {TEXT_MUTED}; background: transparent; border: none;')
        self.panelLayout.addWidget(self._caption)
        self.panelLayout.addSpacing(10)

        self._rowsBox = QVBoxLayout()
        self._rowsBox.setContentsMargins(0, 0, 0, 0)
        self._rowsBox.setSpacing(8)
        self.panelLayout.addLayout(self._rowsBox)
        self.panelLayout.addSpacing(12)

        add = QPushButton('+ Add room')
        add.setFixedHeight(40)
        add.setCursor(Qt.CursorShape.PointingHandCursor)
        af = add.font()
        af.setPointSize(12)
        af.setWeight(QFont.Weight.Medium)
        add.setFont(af)
        add.setStyleSheet(
            f'QPushButton {{ background: transparent; border: 1px dashed {BORDER_HAIRLINE}; '
            f'border-radius: 12px; color: {TEXT_PRIMARY}; }}'
            f'QPushButton:hover {{ background-color: {CHIP_NEUTRAL_BG}; }}')
        add.clicked.connect(lambda: self._emit({'event': 'add'}))
        self.panelLayout.addWidget(add)

    # ---- event queue -------------------------------------------------------

    def _emit(self, event):
        self.events.append(event)
        if self.clickCallback is not None:
            self.clickCallback(None)

    def getPending(self):
        """Pop the oldest queued user action, or {} when idle."""
        if not self.events:
            return {}
        return self.events.pop(0)

    # ---- rows --------------------------------------------------------------

    def setRooms(self, names):
        """Rebuild the room rows; up/down are disabled at the ends."""
        while self._rowsBox.count():
            item = self._rowsBox.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._rowNames = []
        total = len(names)
        for i, name in enumerate(names):
            row = QWidget()
            rowLayout = QHBoxLayout(row)
            rowLayout.setContentsMargins(0, 0, 0, 0)
            rowLayout.setSpacing(8)

            name_label = QLabel(name)
            nf = name_label.font()
            nf.setPointSize(12)
            nf.setWeight(QFont.Weight.Medium)
            name_label.setFont(nf)
            name_label.setStyleSheet(
                f'color: {TEXT_PRIMARY}; background: transparent; border: none;')

            def arrow(text, tip, enabled):
                b = QPushButton(text)
                b.setFixedSize(38, 44)
                b.setCursor(Qt.CursorShape.PointingHandCursor)
                bf = b.font()
                bf.setPointSize(12)
                bf.setWeight(QFont.Weight.DemiBold)
                b.setFont(bf)
                b.setToolTip(tip)
                b.setEnabled(enabled)
                b.setStyleSheet(
                    f'QPushButton {{ background-color: {SURFACE_CARD}; color: {TEXT_SECONDARY}; '
                    f'border: 1px solid {BORDER_HAIRLINE}; border-radius: 12px; }}'
                    f'QPushButton:hover {{ background-color: {CHIP_NEUTRAL_BG}; }}'
                    f'QPushButton:disabled {{ color: {BORDER_HAIRLINE}; border-color: {BORDER_HAIRLINE}; }}')
                return b

            index = i
            up = arrow('↑', 'Move up', i > 0)
            down = arrow('↓', 'Move down', i < total - 1)
            up.clicked.connect(lambda checked=False, idx=index: self._emit(
                {'event': 'up', 'index': idx}))
            down.clicked.connect(lambda checked=False, idx=index: self._emit(
                {'event': 'down', 'index': idx}))

            def small(text, color, tip):
                b = QPushButton(text)
                b.setFixedSize(38, 44)
                b.setCursor(Qt.CursorShape.PointingHandCursor)
                sf = b.font()
                sf.setPointSize(14)
                b.setFont(sf)
                b.setToolTip(tip)
                b.setStyleSheet(
                    f'QPushButton {{ background-color: {SURFACE_CARD}; color: {color}; '
                    f'border: 1px solid {BORDER_HAIRLINE}; border-radius: 12px; }}'
                    f'QPushButton:hover {{ background-color: {CHIP_NEUTRAL_BG}; }}')
                return b

            rename_btn = small('✎', TEXT_SECONDARY, 'Rename room')
            delete_btn = small('✕', '#C8392E', 'Delete room')
            rename_btn.clicked.connect(lambda checked=False, idx=index: self._emit(
                {'event': 'rename', 'index': idx}))
            delete_btn.clicked.connect(lambda checked=False, idx=index: self._emit(
                {'event': 'delete', 'index': idx}))

            rowLayout.addWidget(up)
            rowLayout.addWidget(down)
            rowLayout.addWidget(name_label, 1)
            rowLayout.addWidget(rename_btn)
            rowLayout.addWidget(delete_btn)
            self._rowsBox.addWidget(row)
            self._rowNames.append(name_label)


###############################################################################
# CalendarSheet — the weekly calendar editor. Mirrors the calendar block of
# the PWA's profile sheet: an ON/OFF toggle for the calendar feature and one
# row per weekday (Monday-first, matching calendar-data day0=Mon) showing the
# profile assigned to that day, with an ✎ that opens an inline picker of the
# profiles. Actions queue events drained via `get pending`:
#
#   {'event':'toggle'}
#   {'event':'assign','day':0..6,'index':<profile index>}
#
# Each action applies immediately — the app ships one `Update Profiles`
# uirequest with the calendar fields (calendar on/off, calendar-data with the
# edited day) and the next map push repaints the rows (`set calendar`,
# `set profiles`, `set days`). When the calendar is on, the controller picks
# the active profile by weekday; manual profile selection only applies when
# it is off.
#
# Subclasses Sheet so scrim/panel/title behave like the other sheets.

class CalendarSheet(Sheet):
    DAY_LABELS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')

    def __init__(self, parent=None):
        super().__init__(parent)
        self.events = []
        self._calendarOn = False
        self._profileNames = []
        self._rows = []            # (nameLabel, picker, pickerLayout) per day

        caption = QLabel('Choose which profile runs on each day. The calendar '
                         'takes over profile selection while it is on.')
        cf = caption.font()
        cf.setPointSize(10)
        caption.setFont(cf)
        caption.setWordWrap(True)
        caption.setStyleSheet(
            f'color: {TEXT_MUTED}; background: transparent; border: none;')
        self.panelLayout.addWidget(caption)
        self.panelLayout.addSpacing(10)

        self._toggle = QPushButton()
        self._toggle.setFixedHeight(44)
        self._toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle.clicked.connect(lambda: self._emit({'event': 'toggle'}))
        self.panelLayout.addWidget(self._toggle)
        self.panelLayout.addSpacing(12)

        for day, label in enumerate(CalendarSheet.DAY_LABELS):
            row = QWidget()
            col = QVBoxLayout(row)
            col.setContentsMargins(0, 0, 0, 0)
            col.setSpacing(4)

            head = QHBoxLayout()
            head.setSpacing(8)
            day_label = QLabel(label)
            dlf = day_label.font()
            dlf.setPointSize(10)
            dlf.setWeight(QFont.Weight.DemiBold)
            day_label.setFont(dlf)
            day_label.setFixedWidth(34)
            day_label.setStyleSheet(
                f'color: {TEXT_MUTED}; background: transparent; border: none;')
            head.addWidget(day_label)

            name_label = QLabel('—')
            nlf = name_label.font()
            nlf.setPointSize(12)
            nlf.setWeight(QFont.Weight.Medium)
            name_label.setFont(nlf)
            name_label.setStyleSheet(
                f'color: {TEXT_PRIMARY}; background: transparent; border: none;')
            head.addWidget(name_label, 1)

            edit = QPushButton('✎')
            edit.setFixedSize(38, 38)
            edit.setCursor(Qt.CursorShape.PointingHandCursor)
            eef = edit.font()
            eef.setPointSize(14)
            edit.setFont(eef)
            edit.setToolTip(f'Assign {label}')
            edit.setStyleSheet(
                f'QPushButton {{ background-color: {SURFACE_CARD}; color: {TEXT_SECONDARY}; '
                f'border: 1px solid {BORDER_HAIRLINE}; border-radius: 12px; }}'
                f'QPushButton:hover {{ background-color: {CHIP_NEUTRAL_BG}; }}')
            edit.clicked.connect(lambda checked=False, d=day: self._togglePicker(d))
            head.addWidget(edit)
            col.addLayout(head)

            picker = QWidget()
            pickerLayout = QVBoxLayout(picker)
            pickerLayout.setContentsMargins(0, 0, 0, 0)
            pickerLayout.setSpacing(4)
            pickerHeader = QHBoxLayout()
            pick = QLabel('Pick a profile')
            pf = pick.font()
            pf.setPointSize(10)
            pick.setFont(pf)
            pick.setStyleSheet(
                f'color: {TEXT_MUTED}; background: transparent; border: none;')
            pickerHeader.addWidget(pick)
            pickerHeader.addStretch(1)
            close = QPushButton('✕')
            close.setFixedSize(28, 28)
            close.setCursor(Qt.CursorShape.PointingHandCursor)
            close.setStyleSheet(
                f'QPushButton {{ background-color: {SURFACE_CARD}; color: {TEXT_SECONDARY}; '
                f'border: 1px solid {BORDER_HAIRLINE}; border-radius: 8px; }}'
                f'QPushButton:hover {{ background-color: {CHIP_NEUTRAL_BG}; }}')
            close.clicked.connect(lambda checked=False, d=day: self._closePicker(d))
            pickerHeader.addWidget(close)
            pickerLayout.addLayout(pickerHeader)
            picker.hide()
            col.addWidget(picker)

            self._rows.append((name_label, picker, pickerLayout))
            self.panelLayout.addWidget(row)
            self.panelLayout.addSpacing(6)
        self._applyToggleStyle()

    # ---- event queue -------------------------------------------------------

    def _emit(self, event):
        self.events.append(event)
        if self.clickCallback is not None:
            self.clickCallback(None)

    def getPending(self):
        """Pop the oldest queued user action, or {} when idle."""
        if not self.events:
            return {}
        return self.events.pop(0)

    # ---- state -------------------------------------------------------------

    def setCalendar(self, on):
        self._calendarOn = on
        self._applyToggleStyle()

    def _applyToggleStyle(self):
        tf = self._toggle.font()
        tf.setPointSize(12)
        tf.setWeight(QFont.Weight.DemiBold)
        self._toggle.setFont(tf)
        if self._calendarOn:
            self._toggle.setText('Calendar ON')
            self._toggle.setStyleSheet(
                f'QPushButton {{ background-color: {ACCENT}; color: white; border: none; '
                f'border-radius: 12px; }}'
                f'QPushButton:hover {{ background-color: {ACCENT_HOVER}; }}')
        else:
            self._toggle.setText('Calendar OFF')
            self._toggle.setStyleSheet(
                f'QPushButton {{ background-color: {SURFACE_CARD}; color: {TEXT_PRIMARY}; '
                f'border: 1px solid {BORDER_HAIRLINE}; border-radius: 12px; }}'
                f'QPushButton:hover {{ background-color: {CHIP_NEUTRAL_BG}; }}')

    def setDays(self, days):
        """Repaint the day rows' assignments (7 display names, '' = none)."""
        for i, (name_label, _picker, _layout) in enumerate(self._rows):
            value = days[i] if i < len(days) and days[i] else '—'
            name_label.setText(value)

    def setProfiles(self, names, selected=0):
        """Populate every day picker with one pill per profile."""
        self._profileNames = list(names)
        for _label, _picker, layout in self._rows:
            # clear existing pills (keep the header row)
            items = [layout.itemAt(j) for j in range(layout.count())]
            for item in items[1:]:
                w = item.widget()
                if w is not None:
                    layout.removeItem(item)
                    w.setParent(None)
                    w.deleteLater()
            for p, name in enumerate(self._profileNames):
                pill = QPushButton(name)
                pill.setFixedHeight(32)
                pill.setCursor(Qt.CursorShape.PointingHandCursor)
                plf = pill.font()
                plf.setPointSize(11)
                plf.setWeight(QFont.Weight.DemiBold)
                pill.setFont(plf)
                pill.setStyleSheet(
                    f'QPushButton {{ background-color: {SURFACE_CARD}; color: {TEXT_PRIMARY}; '
                    f'border: 1px solid {BORDER_HAIRLINE}; border-radius: 9px; padding: 0 10px; '
                    f'text-align: left; }}'
                    f'QPushButton:hover {{ background-color: {CHIP_NEUTRAL_BG}; }}')
                pill.clicked.connect(lambda checked=False, d=_picker, pp=p: self._onPick(d, pp))
                layout.addWidget(pill)

    # ---- pickers -----------------------------------------------------------

    def _onPick(self, picker_widget, profile_index):
        # Close this day's picker and queue the assignment.
        picker_widget.hide()
        day = self._rowDay(picker_widget)
        self._emit({'event': 'assign', 'day': day, 'index': profile_index})

    def _rowDay(self, picker_widget):
        for i, (_l, picker, _lay) in enumerate(self._rows):
            if picker is picker_widget:
                return i
        return 0

    def _togglePicker(self, day):
        want_open = self._rows[day][1].isHidden()
        for _l, picker, _lay in self._rows:
            picker.hide()
        if want_open:
            self._rows[day][1].show()

    def _closePicker(self, day):
        self._rows[day][1].hide()


###############################################################################
# RBRMainWindow — the app window: top bar + scrollable room list + sheet stack

class RBRMainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.topBar = None
        self.profileBar = None
        self.sheets = []
        self.roomsLayout = QVBoxLayout()
        # Index of the room whose expansion is open (None = none). Survives
        # re-renders so a panel stays open across map pushes — the app
        # rebuilds every card on each push, and addRoomCard re-opens the
        # matching card (the PWA keeps the open panel too). Only rest-row
        # clicks change it; mode-pill taps don't, so the panel stays open
        # while the target is adjusted after a mode change.
        self.expandedIndex = None
        self.setStyleSheet(f'background-color: {SCROLL_BG};')

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.content = QVBoxLayout()
        self.content.setContentsMargins(0, 0, 0, 0)
        self.content.setSpacing(0)

        # Top bar (added by the app via setTopBar)
        self.topBarSlot = QVBoxLayout()
        self.topBarSlot.setContentsMargins(0, 0, 0, 0)
        self.content.addLayout(self.topBarSlot)

        # Scroll area for the room list
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet(f'QScrollArea {{ background-color: {SCROLL_BG}; border: none; }}')
        inner = QWidget()
        inner.setStyleSheet(f'background-color: {SCROLL_BG};')
        self.scroll.setWidget(inner)

        page = QVBoxLayout(inner)
        page.setContentsMargins(16, 14, 16, 16)
        page.setSpacing(10)
        if self.profileBar is not None:
            page.addWidget(self.profileBar)
        self.roomsContainer = QWidget()
        self.roomsContainer.setStyleSheet(f'background-color: {SCROLL_BG};')
        self.roomsContainer.setLayout(self.roomsLayout)
        self.roomsLayout.setContentsMargins(0, 0, 0, 0)
        self.roomsLayout.setSpacing(10)
        page.addWidget(self.roomsContainer)
        page.addStretch(1)
        self.content.addWidget(self.scroll, 1)

        outer.addLayout(self.content)

    def setTopBar(self, topBar):
        self.topBar = topBar
        self.topBarSlot.addWidget(topBar)

    def setProfileBar(self, profileBar):
        self.profileBar = profileBar
        # Profile bar lives at the top of the scroll page; the first room
        # render places it (see addRoomCard).

    def addRoomCard(self, card):
        # Re-insert the profile bar at the top on every render (clearRooms
        # leaves it in place — see clearRooms).
        if self.profileBar is not None and self.profileBar.parent() is None:
            self.roomsLayout.insertWidget(0, self.profileBar)
        # Give the card a back-reference so rest-row taps can enforce the
        # single-open expansion (see onRoomCardClicked).
        card.expansionWindow = self
        self.roomsLayout.addWidget(card)
        # Re-open the expansion that was open before a re-render (the app
        # rebuilds all cards on every map push). Manual closes and switches
        # are tracked in onRoomCardClicked.
        if self.expandedIndex is not None and card.index == self.expandedIndex:
            if card.expansion.isHidden():
                card.toggleExpansion()

    def onRoomCardClicked(self, card):
        """Single-open expansion: only one room's expansion is visible at a
        time. Tapping the open card closes it; tapping a closed card closes
        any other open card and opens this one. Mode-pill taps never come
        through here (the pill accepts the click), so the panel stays open
        across a mode change + re-render."""
        if card.isExpanded():
            card.toggleExpansion()
            self.expandedIndex = None
            return
        for i in range(self.roomsLayout.count()):
            item = self.roomsLayout.itemAt(i)
            other = item.widget()
            if other is None or other is card or other is self.profileBar:
                continue
            if getattr(other, 'isExpanded', lambda: False)():
                other.toggleExpansion()
        card.toggleExpansion()
        self.expandedIndex = card.index

    def clearRooms(self):
        while self.roomsLayout.count():
            item = self.roomsLayout.takeAt(0)
            widget = item.widget()
            if widget is None:
                continue
            if widget is self.profileBar:
                # Detach the profile bar completely so the next addRoomCard
                # re-inserts it at the top. takeAt alone leaves it parented
                # but no longer in a layout — invisible and never restored.
                widget.setParent(None)
                continue
            widget.setParent(None)
            widget.deleteLater()

    def setSystemName(self, name):
        if self.topBar is not None:
            self.topBar.setSystemName(name)

    def setRequest(self, name):
        if self.topBar is not None:
            self.topBar.setRequest(name)

    def setCalling(self, text):
        if self.topBar is not None:
            self.topBar.setCalling(text)

    def setHeartbeat(self, active):
        if self.topBar is not None:
            self.topBar.setHeartbeat(active)

    def showSheet(self, sheet):
        sheet.setParent(self)
        sheet.setGeometry(self.rect())
        sheet.raise_()
        sheet.show()

    def addSheet(self, sheet):
        """Register a sheet with the window without showing it."""
        sheet.setParent(self)
        sheet.setGeometry(self.rect())
        sheet.hide()

    def hideSheet(self, sheet):
        sheet.hide()