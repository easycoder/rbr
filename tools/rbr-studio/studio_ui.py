"""studio_ui.py — the Studio's view-pane plugin.

The widget half is deliberately generic: it displays the newest frame served at
a URL and knows nothing about RBR, Playwright or the scenario runner. That part
could move to AllSpeak's own plugins later. The plumbing that starts the
screencast and produces the frames lives in scenario_runner, and the shell
decides which URL to point the pane at.

Loaded from a script as:

    load plugin Studio_UI from studio_ui.py

Vocabulary:

    viewpane ViewPane
    create ViewPane [size W H]
    set the source of ViewPane to <url>
    clear ViewPane
    place ViewPane in <layout|panes|tabs> [as <title>]

The pane polls the URL with QtNetwork and keeps the last frame, so it survives
the runner closing after a run; a missing or refused URL leaves the last frame
on screen rather than blanking it.
"""

import json

from PySide6.QtCore import QTimer, QUrl, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import QLayout, QSizePolicy, QSplitter, QTabWidget, QWidget

from allspeak import Handler, language
from allspeak.as_classes import ECValue
from allspeak.as_gclasses import ECWidget
from allspeak.as_graphics import ECLayout, ECPanes, ECTable, ECTabs

###############################################################################
# The widget

class StudioView(QWidget):
    """A pane that shows the newest JPEG/PNG fetched from a URL."""

    def __init__(self):
        super().__init__()
        self.setMinimumSize(160, 320)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAutoFillBackground(True)
        # The PWA viewport is 390x844, so the pane's natural shape is the page's.
        self._aspect = 390 / 844
        self._adjusting = False
        self._url = ""
        self._frame = None
        self._busy = False
        self._timer = QTimer(self)
        self._timer.setInterval(120)
        self._timer.timeout.connect(self._poll)
        self._net = QNetworkAccessManager(self)

    def setSource(self, url):
        url = str(url or "").strip()
        if url == self._url:
            return
        self._url = url
        # A new source is a new run (the runner's port changes), so the old
        # frame is stale. Clearing also makes the waiting state honest.
        self._frame = None
        self.update()
        if url:
            self._timer.start()
            self._poll()
        else:
            self._timer.stop()

    def clear(self):
        self.setSource("")

    def setAspect(self, value):
        """Set the pane's width/height ratio (the page is 390x844)."""
        try:
            aspect = float(value)
        except (TypeError, ValueError):
            return
        if aspect > 1:
            aspect = aspect / 1000
        if aspect < 0.2 or aspect > 1.0:
            aspect = 390 / 844
        self._aspect = aspect
        self._adjust()

    def _adjust(self):
        if self._adjusting or self.height() <= 0:
            return
        wanted = max(120, int(self.height() * self._aspect))
        if abs(self.width() - wanted) > 2:
            self._adjusting = True
            self.setFixedWidth(wanted)
            self._adjusting = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._adjust()

    def _poll(self):
        if not self._url or self._busy:
            return
        self._busy = True
        request = QNetworkRequest(QUrl(self._url))
        request.setAttribute(QNetworkRequest.Attribute.CacheLoadControlAttribute,
                             QNetworkRequest.CacheLoadControl.AlwaysNetwork)
        reply = self._net.get(request)
        reply.finished.connect(lambda r=reply: self._done(r))

    def _done(self, reply):
        self._busy = False
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                data = bytes(reply.readAll())
                if data:
                    image = QImage.fromData(data)
                    if not image.isNull():
                        self._frame = image
                        self.update()
        finally:
            reply.deleteLater()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#1A1A1A"))
        if self._frame is None:
            painter.setPen(QColor("#999999"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No view")
            return
        scaled = self._frame.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation)
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        painter.drawImage(x, y, scaled)


class ECStudioView(ECWidget):
    """Value storage for a `viewpane` symbol (the widget is the value)."""

    def __init__(self):
        super().__init__()

    def setWidget(self, widget):
        super().setValue(widget)

    def getWidget(self):
        return super().getValue()


###############################################################################
# The plugin

class Studio_UI(Handler):
    def __init__(self, compiler):
        Handler.__init__(self, compiler)

    def getName(self):
        return 'studio_ui'

    def modifyValue(self, value):
        return value

    def compileValue(self):
        return None

    # viewpane {symbol}
    def k_viewpane(self, command):
        self.compiler.addValueType()
        return self.compileVariable(command, 'ECStudioView')

    def r_viewpane(self, command):
        return self.nextPC()

    # create {viewpane} [size W H]
    def k_create(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            cls = self.getObject(record)
            if isinstance(cls, ECStudioView):
                command['name'] = record['name']
                command['object'] = cls
                if language.matches_word(self.peek(), 'size'):
                    self.nextToken()
                    command['width'] = self.nextValue()
                    command['height'] = self.nextValue()
                self.add(command)
                return True
        return False

    def r_create(self, command):
        record = self.getVariable(command['name'])
        cls = self.getObject(record)
        widget = StudioView()
        if 'width' in command and 'height' in command:
            widget.setMinimumSize(int(self.textify(command['width'])),
                                  int(self.textify(command['height'])))
        cls.setWidget(widget)
        return self.nextPC()

    # set the source of {viewpane} to {value}
    def k_set(self, command):
        self.skipArticles()
        if language.matches_word(self.peek(), 'source'):
            what = 'source'
        elif language.matches_word(self.peek(), 'aspect'):
            what = 'aspect'
        else:
            return False
        self.nextToken()
        self.skipWord('of')
        if not self.nextIsSymbol():
            return False
        record = self.getSymbolRecord()
        if not self.isObjectType(record, ECStudioView):
            return False
        self.skipWord('to')
        command['what'] = what
        command['target'] = record['name']
        command['value'] = self.nextValue()
        self.add(command)
        return True

    def r_set(self, command):
        target = self.getInnerObject(self.getVariable(command['target']))
        if command['what'] == 'aspect':
            target.setAspect(self.textify(command['value']))
        else:
            target.setSource(self.textify(command['value']))
        return self.nextPC()

    # clear {viewpane}
    def k_clear(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            if self.isObjectType(record, ECStudioView):
                command['name'] = record['name']
                self.add(command)
                return True
        return False

    def r_clear(self, command):
        target = self.getInnerObject(self.getVariable(command['name']))
        target.clear()
        return self.nextPC()

    # measure sizes of {panes} into {variable}
    #
    # The graphics domain can set a splitter's sizes but cannot read them back,
    # so a window that wants to restore its layout needs this small reader. The
    # reply is a JSON array of widths, which `set sizes of` accepts.
    def k_measure(self, command):
        self.skipArticles()
        if not language.matches_word(self.peek(), 'sizes'):
            return False
        self.nextToken()
        self.skipWord('of')
        if not self.nextIsSymbol():
            return False
        record = self.getSymbolRecord()
        if not self.isObjectType(record, ECPanes):
            return False
        command['source'] = record['name']
        self.skipWord('into')
        if not self.nextIsSymbol():
            return False
        dest = self.getSymbolRecord()
        command['target'] = dest['name']
        self.add(command)
        return True

    def r_measure(self, command):
        pane = self.getInnerObject(self.getVariable(command['source']))
        dest = self.getVariable(command['target'])
        self.putSymbolValue(dest, ECValue(type=str, content=json.dumps(pane.sizes())))
        return self.nextPC()

    # hide column {index} of {table} / show column {index} of {table}
    #
    # A table column cannot be hidden by a zero width: QHeaderView clamps a
    # section to its minimum size, so a zero-width column keeps a visible
    # header. These two commands use setColumnHidden, which is the real thing.
    # They are Studio-side helpers rather than part of the view pane.
    def k_hide(self, command):
        return self._column_visibility(command, False)

    def k_show(self, command):
        return self._column_visibility(command, True)

    def _column_visibility(self, command, visible):
        self.skipArticles()
        if not language.matches_word(self.peek(), 'column'):
            return False
        self.nextToken()
        command['index'] = self.nextValue()
        self.skipWord('of')
        if not self.nextIsSymbol():
            return False
        record = self.getSymbolRecord()
        if not self.isObjectType(record, ECTable):
            return False
        command['target'] = record['name']
        command['visible'] = visible
        self.add(command)
        return True

    def r_hide(self, command):
        return self._column_visibility_run(command)

    def r_show(self, command):
        return self._column_visibility_run(command)

    def _column_visibility_run(self, command):
        target = self.getInnerObject(self.getVariable(command['target']))
        target.setColumnHidden(int(self.textify(command['index'])),
                               not command['visible'])
        return self.nextPC()

    # place {viewpane} in {layout|panes|tabs} [as {title}]
    #
    # A separate verb because graphics' `add` only accepts its own core widget
    # types; this keeps a plugin widget out of the core type check.
    def k_place(self, command):
        if not self.nextIsSymbol():
            return False
        record = self.getSymbolRecord()
        if not self.isObjectType(record, ECStudioView):
            return False
        command['widget'] = record['name']
        self.skipWord('in')
        if not self.nextIsSymbol():
            return False
        target = self.getSymbolRecord()
        if not self.isObjectType(target, (ECLayout, ECPanes, ECTabs)):
            return False
        command['target'] = target['name']
        if language.matches_word(self.peek(), 'as'):
            self.nextToken()
            command['title'] = self.nextValue()
        self.add(command)
        return True

    def r_place(self, command):
        widget = self.getInnerObject(self.getVariable(command['widget']))
        target = self.getInnerObject(self.getVariable(command['target']))
        if isinstance(target, QTabWidget):
            title = self.textify(command['title']) if 'title' in command else 'View'
            target.addTab(widget, str(title))
        elif isinstance(target, (QLayout, QSplitter)):
            target.addWidget(widget)
        return self.nextPC()
