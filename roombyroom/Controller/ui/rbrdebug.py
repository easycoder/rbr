import sys, os, json
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QSplitter,
    QFileDialog,
    QMessageBox,
    QScrollArea,
    QSizePolicy
)
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtCore import Qt, QTimer

class DebugMainWindow(QMainWindow):

    ###########################################################################
    # The left-hand column of the main window
    class MainLeftColumn(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            layout = QVBoxLayout(self)
            layout.addWidget(QLabel("Left column"))
            layout.addStretch()
    
    ###########################################################################
    # The right-hand column of the main window
    class MainRightColumn(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)

            # Create a scroll area - its content widget holds the lines
            self.scroll = QScrollArea(self)
            self.scroll.setWidgetResizable(True)

            # Ensure this widget and the scroll area expand to fill available space
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            self.content = QWidget()
            # let the content expand horizontally but have flexible height
            self.content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

            self.inner_layout = QVBoxLayout(self.content)
            # spacing and small top/bottom margins to separate lines
            self.inner_layout.setSpacing(0)
            self.inner_layout.setContentsMargins(0, 0, 0, 0)

            self.scroll.setWidget(self.content)

            # outer layout for this widget contains only the scroll area
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.addWidget(self.scroll)
            # ensure the scroll area gets the stretch so it fills the parent
            main_layout.setStretch(0, 1)

        def addLine(self, lino, line):
            class Label(QLabel):
                def __init__(self, text):
                    super().__init__()
                    self.setText(text)
                    # remove QLabel's internal margins/padding to reduce top/bottom space
                    self.setMargin(0)
                    self.setContentsMargins(0, 0, 0, 0)
                    self.setStyleSheet("padding:0px; margin:0px; background:yellow")
                    fm = self.fontMetrics()
                    self.setFixedHeight(fm.height())

            panel = QWidget()
            layout = QHBoxLayout(panel)
            layout.addWidget(Label(str(lino)))
            layout.addWidget(Label(line))
            self.inner_layout.addWidget(panel)

        def addStretch(self):
            self.inner_layout.addStretch()

    ###########################################################################
    # The main window menus
    class MainMenus():
        def __init__(self, parent):
            self.parent = parent
            self.createActions()
            self.createMenus()

        def createActions(self):

            # File actions
            self.openAct = QAction("Open...", self.parent)
            self.openAct.setShortcut(QKeySequence.Open)
            self.openAct.triggered.connect(self.parent.file_open)

            self.exitAct = QAction("Exit", self.parent)
            self.exitAct.setShortcut("Ctrl+Q")
            self.exitAct.triggered.connect(self.parent.closeEvent)

            # View actions
            self.toggleStatusAct = QAction("Toggle Status Bar", self.parent)
            self.toggleStatusAct.setCheckable(True)
            self.toggleStatusAct.setChecked(True)
            self.toggleStatusAct.triggered.connect(self._toggle_status_bar)

            # Help actions
            self.aboutAct = QAction("About", self.parent)
            self.aboutAct.triggered.connect(self.show_about)

        def createMenus(self):
            menubar = self.parent.menuBar()

            # File menu
            fileMenu = menubar.addMenu("&File")
            fileMenu.addAction(self.openAct)
            fileMenu.addSeparator()
            fileMenu.addAction(self.exitAct)

            # View menu
            viewMenu = menubar.addMenu("&View")
            viewMenu.addAction(self.toggleStatusAct)

            # Help menu
            helpMenu = menubar.addMenu("&Help")
            helpMenu.addAction(self.aboutAct)

        def _toggle_status_bar(self, checked):
            if checked:
                self.parent.statusBar().show()
            else:
                self.parent.statusBar().hide()

        def show_about(self):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self.parent, "About", "RBR Debugger")

    # Initialiser for main window
    def __init__(self, width=800, height=600, ratio=0.2):
        super().__init__()
        self.setWindowTitle("RBR Debugger")
        self.setMinimumSize(width, height)

        # try to load saved geometry from ~/.rbrdebug.conf
        cfg_path = os.path.join(os.path.expanduser("~"), ".rbrdebug.conf")
        initial_width = width
        try:
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                x = int(cfg.get("x", 0))
                y = int(cfg.get("y", 0))
                w = int(cfg.get("width", width))
                h = int(cfg.get("height", height))
                ratio =float(cfg.get("ratio", ratio))
                # Apply loaded geometry
                self.setGeometry(x, y, w, h)
                initial_width = w
        except Exception:
            # ignore errors and continue with defaults
            initial_width = width

        self.MainMenus(self)

        # Keep a ratio so proportions are preserved when window is resized
        self.ratio = ratio

        # Central splitter (horizontal -> two columns)
        self.splitter = QSplitter(Qt.Horizontal, self)
        self.splitter.setHandleWidth(8)
        self.splitter.splitterMoved.connect(self.on_splitter_moved)

        # Left pane
        left = QFrame()
        left.setFrameShape(QFrame.StyledPanel)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(8, 8, 8, 8)
        self.leftColumn = self.MainLeftColumn()
        left_layout.addWidget(self.leftColumn)
        left_layout.addStretch()

        # Right pane
        right = QFrame()
        right.setFrameShape(QFrame.StyledPanel)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 8, 8, 8)
        self.rightColumn = self.MainRightColumn()
        # Give the rightColumn a stretch factor so its scroll area fills the vertical space
        right_layout.addWidget(self.rightColumn, 1)

        # Add panes to splitter
        self.splitter.addWidget(left)
        self.splitter.addWidget(right)

        # Initial sizes (proportional)
        total = initial_width
        self.splitter.setSizes([int(self.ratio * total), int((1 - self.ratio) * total)])

        self.setCentralWidget(self.splitter)

    def on_splitter_moved(self, pos, index):
        # Update stored ratio when user drags the splitter
        left_width = self.splitter.widget(0).width()
        total = max(1, sum(w.width() for w in (self.splitter.widget(0), self.splitter.widget(1))))
        self.ratio = left_width / total

    def resizeEvent(self, event):
        # Preserve the proportional widths when the window is resized
        total_width = max(1, self.width())
        left_w = max(0, int(self.ratio * total_width))
        right_w = max(0, total_width - left_w)
        self.splitter.setSizes([left_w, right_w])
        super().resizeEvent(event)

    def file_open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "ECS Files (*.ecs)")
        if path:
            def process():
                with open(path, "r", encoding="utf-8") as f:
                    self.parse(f.read())
                self.statusBar().showMessage("")
            try:
                self.statusBar().showMessage(f"Opening: {path}")
                QTimer.singleShot(10, process)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open file:\n{e}")

    def parse(self, script):
        self.scriptLines = []
        # Clear existing lines from the right column layout
        layout = self.rightColumn.inner_layout
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Parse and add new lines
        lino = 0
        for line in script.splitlines():
            lino += 1
            line = line.replace("\t", " " * 3)
            # print(line)
            self.scriptLines.append(line)
            self.rightColumn.addLine(lino, line)
        self.rightColumn.addStretch()

    def closeEvent(self, event):
        """Save window position and size to ~/.rbrdebug.conf as JSON on exit."""
        cfg = {
            "x": self.x(),
            "y": self.y(),
            "width": self.width(),
            "height": self.height(),
            "ratio": self.ratio
        }
        try:
            cfg_path = os.path.join(os.path.expanduser("~"), ".rbrdebug.conf")
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception as exc:
            # best-effort only; avoid blocking shutdown
            try:
                self.statusBar().showMessage(f"Could not save config: {exc}", 3000)
            except Exception:
                pass
        super().close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = DebugMainWindow()
    w.show()
    sys.exit(app.exec())