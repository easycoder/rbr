import sys, os, json
import html
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
    QSizePolicy,
    QToolBar
)
from PySide6.QtGui import QAction, QKeySequence, QTextCursor
from PySide6.QtCore import Qt, QTimer, QProcess


class ConsoleWriter:
    """A tiny stdout/stderr proxy that forwards text into the QTextEdit console.

    write() may be called from the main thread (we keep all calls on the main
    thread) but to be safe we use QTimer.singleShot to schedule appends on the
    Qt event loop.
    """
    def __init__(self, console, autoscroll_getter=None, html_color=None):
        self.console = console
        # callable that returns True/False for autoscroll
        self.autoscroll_getter = autoscroll_getter or (lambda: True)
        # optional HTML color for this writer (e.g. 'red' for stderr)
        self.html_color = html_color

    def write(self, text):
        if text is None or text == '':
            return
        try:
            def _append():
                try:
                    if self.html_color:
                        # escape and convert newlines to <br>
                        esc = html.escape(text)
                        html_text = esc.replace('\n', '<br>')
                        self.console.moveCursor(QTextCursor.End)
                        self.console.insertHtml(f"<span style='color: {self.html_color};'>" + html_text + "</span>")
                    else:
                        cursor = self.console.textCursor()
                        cursor.movePosition(QTextCursor.End)
                        self.console.setTextCursor(cursor)
                        self.console.insertPlainText(text)
                    try:
                        if self.autoscroll_getter():
                            try:
                                self.console.ensureCursorVisible()
                            except Exception:
                                pass
                    except Exception:
                        pass
                except Exception:
                    try:
                        if self.html_color:
                            self.console.append(text)
                        else:
                            self.console.insertPlainText(text)
                    except Exception:
                        pass
            QTimer.singleShot(0, _append)
        except Exception:
            try:
                # best-effort fallback
                self.console.append(text)
                try:
                    self.console.ensureCursorVisible()
                except Exception:
                    pass
            except Exception:
                pass

    def flush(self):
        return
	
class Object():
    pass

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

        #######################################################################
        # Add a line to the right-hand column
        def addLine(self, spec):
            class Label(QLabel):
                def __init__(self, text, fixed_width=None, align=Qt.AlignLeft, on_click=spec.onClick):
                    super().__init__()
                    self.setText(text)
                    # remove QLabel's internal margins/padding to reduce top/bottom space
                    self.setMargin(0)
                    self.setContentsMargins(0, 0, 0, 0)
                    self.setStyleSheet("padding:0px; margin:0px; font-family: mono")
                    fm = self.fontMetrics()
                    # set a compact fixed height based on font metrics
                    self.setFixedHeight(fm.height())
                    # optional fixed width (used for the lino column)
                    if fixed_width is not None:
                        self.setFixedWidth(fixed_width)
                    # align horizontally (keep vertically centered)
                    self.setAlignment(align | Qt.AlignVCenter)
                    # optional click callback
                    self._on_click = on_click

                def mousePressEvent(self, event):
                    if self._on_click:
                        try:
                            self._on_click()
                        except Exception:
                            pass
                    super().mousePressEvent(event)

            spec.label = self
            panel = QWidget()
            # ensure the panel itself has no margins
            try:
                panel.setContentsMargins(0, 0, 0, 0)
            except Exception:
                pass
            # tidy layout: remove spacing/margins so lines sit flush
            layout = QHBoxLayout(panel)
            layout.setSpacing(0)
            layout.setContentsMargins(0, 0, 0, 0)
            self.layout = layout
            # make panel take minimal vertical space
            panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            # compute width to fit a 4-digit line number using this widget's font
            fm_main = self.fontMetrics()
            width_4 = fm_main.horizontalAdvance('0000') + 8

            # create the red blob (always present). We'll toggle its opacity
            # by changing the stylesheet (rgba alpha 255/0). Do NOT store it
            # on the MainRightColumn instance — keep it per-line.
            blob = QLabel()
            blob_size = 10
            blob.setFixedSize(blob_size, blob_size)

            def set_blob_visible(widget, visible):
                alpha = 255 if visible else 0
                widget.setStyleSheet(f"background-color: rgba(255,0,0,{alpha}); border-radius: {blob_size//2}px; margin:0px; padding:0px;")
                widget._blob_visible = visible
                # force repaint
                widget.update()

            # attach methods to this blob so callers can toggle it via spec.label
            blob.showBlob = lambda: set_blob_visible(blob, True)
            blob.hideBlob = lambda: set_blob_visible(blob, False)

            # initialize according to spec flag
            if spec.bp:
                blob.showBlob()
            else:
                blob.hideBlob()

            # expose the blob to the outside via spec['label'] so onClick can call showBlob/hideBlob
            spec.label = blob

            # create the line-number label; clicking it reports back to the caller
            lino_label = Label(str(spec.lino+1), fixed_width=width_4, align=Qt.AlignRight,
                               on_click=lambda: spec.onClick(spec.lino))
            lino_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            # create the text label for the line itself
            text_label = Label(spec.line, fixed_width=None, align=Qt.AlignLeft)
            text_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            layout.addWidget(lino_label)
            layout.addSpacing(10)
            layout.addWidget(blob, 0, Qt.AlignVCenter)
            layout.addSpacing(3)
            layout.addWidget(text_label)
            self.inner_layout.addWidget(panel)
            return panel
        
        def showBlob(self):
            self.blob.setStyleSheet("background-color: red; border-radius: 5px; margin:0px; padding:0px;")
        
        def hideBlob(self):
            self.blob.setStyleSheet("background-color: none; border-radius: 5px; margin:0px; padding:0px;")
        
        def addStretch(self):
            self.layout.addStretch()

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

            # Run actions (disabled until a script is opened)
            # The text will be updated to include the script name when available
            self.runAct = QAction("Run", self.parent)
            self.runAct.setEnabled(False)
            try:
                self.runAct.triggered.connect(self.parent.run_script)
            except Exception:
                pass

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

            # Run menu
            runMenu = menubar.addMenu("&Run")
            runMenu.addAction(self.runAct)

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

    ###########################################################################
    # Initialiser for main window
    def __init__(self, width=800, height=600, ratio=0.2):
        super().__init__()
        self.setWindowTitle("RBR Debugger")
        self.setMinimumSize(width, height)

        # try to load saved geometry from ~/.rbrdebug.conf
        cfg_path = os.path.join(os.path.expanduser("~"), ".rbrdebug.conf")
        initial_width = width
        # default console height (pixels) if not stored in cfg
        console_height = 150
        try:
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                x = int(cfg.get("x", 0))
                y = int(cfg.get("y", 0))
                w = int(cfg.get("width", width))
                h = int(cfg.get("height", height))
                ratio =float(cfg.get("ratio", ratio))
                # load console height if present
                console_height = int(cfg.get("console_height", console_height))
                # Apply loaded geometry
                self.setGeometry(x, y, w, h)
                initial_width = w
        except Exception:
            # ignore errors and continue with defaults
            initial_width = width

        # Create main menus and keep a reference so we can update the Run action
        self.menus = self.MainMenus(self)

        # track currently loaded script path (None when no script)
        self.current_script_path = None

        # toolbar with Run / Stop / Clear
        try:
            self.toolbar = QToolBar("Main")
            # add the Run action from the menus so menu and toolbar share the same QAction
            if hasattr(self.menus, 'runAct'):
                self.toolbar.addAction(self.menus.runAct)
            # stop action
            self.stopAct = QAction("Stop", self)
            self.stopAct.setEnabled(False)
            self.stopAct.triggered.connect(self.stop_script)
            self.toolbar.addAction(self.stopAct)
            # clear console
            self.clearAct = QAction("Clear Console", self)
            self.clearAct.triggered.connect(lambda: getattr(self, 'console', None) and self.console.clear())
            self.toolbar.addAction(self.clearAct)
            # autoscroll toggle (default on)
            self.autoScroll = True
            self.autoScrollAct = QAction("Auto-scroll", self)
            self.autoScrollAct.setCheckable(True)
            self.autoScrollAct.setChecked(True)
            self.autoScrollAct.triggered.connect(lambda checked: setattr(self, 'autoScroll', checked))
            self.toolbar.addAction(self.autoScrollAct)
            self.addToolBar(self.toolbar)
        except Exception:
            # non-fatal: toolbar is convenience only
            pass

        # process handle for running scripts
        self._proc = None
        # in-process Program instance and writer
        self._program = None
        self._writer = None
        self._orig_stdout = None
        self._orig_stderr = None
        self._flush_timer = None

        # Keep a ratio so proportions are preserved when window is resized
        self.ratio = ratio

        # Central horizontal splitter (left/right)
        self.hsplitter = QSplitter(Qt.Horizontal, self)
        self.hsplitter.setHandleWidth(8)
        self.hsplitter.splitterMoved.connect(self.on_splitter_moved)

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

        # Add panes to horizontal splitter
        self.hsplitter.addWidget(left)
        self.hsplitter.addWidget(right)

        # Initial sizes (proportional) for horizontal splitter
        total = initial_width
        self.hsplitter.setSizes([int(self.ratio * total), int((1 - self.ratio) * total)])

        # Create a vertical splitter so we can add a resizable console panel at the bottom
        self.vsplitter = QSplitter(Qt.Vertical, self)
        self.vsplitter.setHandleWidth(6)
        # top: the existing horizontal splitter
        self.vsplitter.addWidget(self.hsplitter)

        # bottom: console panel
        console_frame = QFrame()
        console_frame.setFrameShape(QFrame.StyledPanel)
        console_layout = QVBoxLayout(console_frame)
        console_layout.setContentsMargins(4, 4, 4, 4)
        # simple read-only text console for script output and messages
        from PySide6.QtWidgets import QTextEdit
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        console_layout.addWidget(self.console)
        self.vsplitter.addWidget(console_frame)

        # Set initial vertical sizes: prefer saved console_height if available
        try:
            total_h = int(h) if 'h' in locals() else max(300, self.height())
            ch = max(50, min(total_h - 50, console_height))
            self.vsplitter.setSizes([int(total_h - ch), int(ch)])
        except Exception:
            pass

        # Use the vertical splitter as the central widget
        self.setCentralWidget(self.vsplitter)

    def on_splitter_moved(self, pos, index):
        # Update stored ratio when user drags the splitter
        left_width = self.hsplitter.widget(0).width()
        total = max(1, sum(w.width() for w in (self.hsplitter.widget(0), self.hsplitter.widget(1))))
        self.ratio = left_width / total

    def resizeEvent(self, event):
        # Preserve the proportional widths when the window is resized
        total_width = max(1, self.width())
        left_w = max(0, int(self.ratio * total_width))
        right_w = max(0, total_width - left_w)
        self.hsplitter.setSizes([left_w, right_w])
        super().resizeEvent(event)

    ###########################################################################
    # File->Open handler
    def file_open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "ECS Files (*.ecs)")
        if path:
            def process():
                with open(path, "r", encoding="utf-8") as f:
                    self.parse(f.read())
                    # remember current script and update Run menu
                    try:
                        self.current_script_path = path
                    except Exception:
                        self.current_script_path = None
                    try:
                        self.update_run_menu()
                    except Exception:
                        pass
                self.statusBar().showMessage("")
                # for token in self.tokens: print(token)
            try:
                self.statusBar().showMessage(f"Opening: {path}")
                QTimer.singleShot(10, process)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open file:\n{e}")

    ###########################################################################
    # Parse a script into the right-hand column
    def parse(self, script):
        self.tokens = []
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
            if len(line) > 0:
                line = line.replace("\t", "   ")
                line = self.coloriseLine(line, lino)
            else:
                # still need to call coloriseLine to keep token list in sync
                self.coloriseLine(line, lino)
            lineSpec = Object()
            lineSpec.lino = lino
            lineSpec.line = line
            lineSpec.bp = False
            lineSpec.onClick = self.onClickLino
            lino += 1
            self.scriptLines.append(lineSpec)
            lineSpec.panel = self.rightColumn.addLine(lineSpec)
        self.rightColumn.addStretch()
    
    ###########################################################################
    # Colorise a line of script for HTML display
    def coloriseLine(self, line, lino=None):
        output = ''

        # Preserve leading spaces (render as &nbsp; except the first)
        if len(line) > 0 and line[0] == ' ':
            output += '<span>'
            n = 0
            while n < len(line) and line[n] == ' ': n += 1
            output += '&nbsp;' * (n - 1)
            output += '</span>'

        # Find the first unquoted ! (not inside backticks)
        comment_start = None
        in_backtick = False
        for idx, c in enumerate(line):
            if c == '`':
                in_backtick = not in_backtick
            elif c == '!' and not in_backtick:
                comment_start = idx
                break

        if comment_start is not None:
            code_part = line[:comment_start]
            comment_part = line[comment_start:]
        else:
            code_part = line
            comment_part = None

        # Tokenize code_part as before (respecting backticks)
        tokens = []
        i = 0
        L = len(code_part)
        while i < L:
            if code_part[i].isspace():
                i += 1
                continue
            if code_part[i] == '`':
                j = code_part.find('`', i + 1)
                if j == -1:
                    tokens.append(code_part[i:])
                    break
                else:
                    tokens.append(code_part[i:j+1])
                    i = j + 1
            else:
                j = i
                while j < L and not code_part[j].isspace():
                    j += 1
                tokens.append(code_part[i:j])
                i = j

        # Colour code tokens and generate a list of elements
        for token in tokens:
            if token == '':
                continue
            elif token[0].isupper():
                esc = html.escape(token)
                element = f'&nbsp;<span style="color: blue; font-weight: bold;">{esc}</span>'
            elif token[0].isdigit():
                esc = html.escape(token)
                element = f'&nbsp;<span style="color: green;">{esc}</span>'
            elif token[0] == '`':
                esc = html.escape(token)
                element = f'&nbsp;<span style="color: purple;">{esc}</span>'
            else:
                esc = html.escape(token)
                element = f'&nbsp;<span>{esc}</span>'
            output += element
            # Append (line number, token) tuple to self.tokens
            item = Object()
            item.lino = lino + 1 if lino is not None else 1
            item.token = token
            self.tokens.append(item)
        # Colour comment if present
        if comment_part is not None:
            esc = html.escape(comment_part)
            output += f'<span style="color: peru;">&nbsp;{esc}</span>'

        return output
    
    ###########################################################################
    # Here when the user clicks a line number
    def onClickLino(self, lino):
        lineSpec = self.scriptLines[lino]
        lineSpec.bp = not lineSpec.bp
        if lineSpec.bp: lineSpec.label.showBlob()
        else: lineSpec.label.hideBlob()

    ###########################################################################
    # Run menu helpers
    def update_run_menu(self):
        """Update the Run action label and enabled state based on current script."""
        try:
            runAct = getattr(self.menus, 'runAct', None)
            if runAct is None:
                return
            if self.current_script_path:
                name = os.path.basename(self.current_script_path)
                runAct.setText(f"Run {name}")
                runAct.setEnabled(True)
            else:
                runAct.setText("Run")
                runAct.setEnabled(False)
        except Exception:
            pass

    def run_script(self):
        """Run the currently loaded script in-process via easycoder.Program.

        This runs the ECS script using the workspace `easycoder` package by
        creating a Program instance and driving its `flushCB()` from a
        QTimer. stdout/stderr are redirected into the console while the
        program is running. If `easycoder` cannot be imported, fall back to
        the previous subprocess approach.
        """
        if not getattr(self, 'current_script_path', None):
            QMessageBox.information(self, "Run", "No script loaded.")
            return

        # Prevent starting when something (proc or program) is already running
        if getattr(self, '_proc', None) is not None or getattr(self, '_program', None) is not None:
            QMessageBox.information(self, "Run", "A script is already running.")
            return

        # Try to run in-process using easycoder.Program
        try:
            from easycoder import Program
        except Exception as exc:
            # Fall back to subprocess runner if easycoder not importable
            try:
                proc = QProcess(self)
                proc.setProcessChannelMode(QProcess.SeparateChannels)
                proc.readyReadStandardOutput.connect(self._on_proc_stdout)
                proc.readyReadStandardError.connect(self._on_proc_stderr)
                proc.finished.connect(self._on_proc_finished)
                executable = sys.executable or 'python3'
                # run a short inline script that imports easycoder and runs the Program
                inline = ("from easycoder import Program; Program(r'%s').start()" %
                          (self.current_script_path.replace("'", "\\'")))
                proc.start(executable, ['-c', inline])
                self._proc = proc
                if hasattr(self, 'stopAct'):
                    self.stopAct.setEnabled(True)
                self.update_run_menu()
                try:
                    self.console.append(f"Running (subprocess): {self.current_script_path}\n")
                    try:
                        if getattr(self, 'autoScroll', True):
                            self.console.ensureCursorVisible()
                    except Exception:
                        pass
                except Exception:
                    pass
                return
            except Exception as e:
                QMessageBox.critical(self, "Run Error", f"Could not start script (subprocess fallback):\n{e}")
                return

        # In-process path
        try:
            # create writer and redirect stdout/stderr
            # create separate writers for stdout/stderr so we can style stderr
            self._orig_stdout = sys.stdout
            self._orig_stderr = sys.stderr
            self._writer = ConsoleWriter(self.console, autoscroll_getter=lambda: getattr(self, 'autoScroll', True), html_color=None)
            self._err_writer = ConsoleWriter(self.console, autoscroll_getter=lambda: getattr(self, 'autoScroll', True), html_color='red')
            sys.stdout = self._writer
            sys.stderr = self._err_writer

            # Create and start the Program (parent=self so no internal main loop)
            program = Program(self.current_script_path)
            # Mark external control so Program won't spawn its own loop
            try:
                program.setExternalControl()
            except Exception:
                pass
            self._program = program
            # mark program for external control so it won't enter its own main loop
            try:
                program.setExternalControl()
            except Exception:
                pass
            # Start without a parent to avoid Program.releaseParent trying to
            # access attributes on our GUI object (which can raise and prevent
            # the program from setting running=False on exit).
            program.start(parent=None)

            # Start a timer to call flushCB() regularly so the program runs
            self._flush_timer = QTimer(self)
            self._flush_timer.timeout.connect(self._flush_tick)
            self._flush_timer.start(10)

            if hasattr(self, 'stopAct'):
                self.stopAct.setEnabled(True)
            self.update_run_menu()
            try:
                self.console.append(f"Running (in-process): {self.current_script_path}\n")
                try:
                    if getattr(self, 'autoScroll', True):
                        self.console.ensureCursorVisible()
                except Exception:
                    pass
            except Exception:
                pass
        except Exception as e:
            # restore stdout/stderr on error
            try:
                if self._orig_stdout is not None:
                    sys.stdout = self._orig_stdout
                if self._orig_stderr is not None:
                    sys.stderr = self._orig_stderr
            except Exception:
                pass
            QMessageBox.critical(self, "Run Error", f"Could not start in-process: {e}")

    def _flush_tick(self):
        """Call the Program.flushCB and detect program completion."""
        try:
            if not getattr(self, '_program', None):
                return
            try:
                self._program.flushCB()
            except Exception:
                # If flushCB raises, ensure we stop
                pass
            # If program not running any more, finish
            if not getattr(self._program, 'running', False):
                self._on_program_finished()
        except Exception:
            pass

    def _on_proc_stdout(self):
        if not self._proc:
            return
        try:
            data = self._proc.readAllStandardOutput().data().decode('utf-8', errors='replace')
            if data:
                self.console.moveCursor(self.console.textCursor().End)
                self.console.insertPlainText(data)
                self.console.ensureCursorVisible()
        except Exception:
            pass

    def _on_proc_stderr(self):
        if not self._proc:
            return
        try:
            data = self._proc.readAllStandardError().data().decode('utf-8', errors='replace')
            if data:
                # prefix stderr lines for visibility
                self.console.moveCursor(self.console.textCursor().End)
                self.console.insertPlainText(data)
                self.console.ensureCursorVisible()
        except Exception:
            pass

    def _on_proc_finished(self, exit_code, exit_status=None):
        try:
            self.console.append(f"\nProcess finished (exit {exit_code})\n")
        except Exception:
            pass
        try:
            if hasattr(self, 'stopAct'):
                self.stopAct.setEnabled(False)
        except Exception:
            pass
        # clear process handle
        try:
            self._proc = None
        except Exception:
            self._proc = None

    def _on_program_finished(self):
        try:
            self.console.append("\nProgram finished\n")
        except Exception:
            pass
        # stop flush timer
        try:
            if self._flush_timer is not None:
                self._flush_timer.stop()
                self._flush_timer = None
        except Exception:
            pass
        # restore stdout/stderr
        try:
            if self._orig_stdout is not None:
                sys.stdout = self._orig_stdout
            if self._orig_stderr is not None:
                sys.stderr = self._orig_stderr
        except Exception:
            pass
        try:
            if hasattr(self, 'stopAct'):
                self.stopAct.setEnabled(False)
        except Exception:
            pass
        self._program = None
        self._writer = None
        self._orig_stdout = None
        self._orig_stderr = None

    def stop_script(self):
        """Stop the running script if any."""
        try:
            # If running as subprocess
            if getattr(self, '_proc', None) is not None:
                try:
                    self._proc.terminate()
                    QTimer.singleShot(2000, lambda: self._proc.kill() if self._proc else None)
                except Exception:
                    pass
                return
            # If running in-process via easycoder.Program
            if getattr(self, '_program', None) is not None:
                try:
                    self._program.kill()
                except Exception:
                    pass
                # perform cleanup similar to finished
                try:
                    self._on_program_finished()
                except Exception:
                    pass
                return
        except Exception:
            pass

    ###########################################################################
    # Override closeEvent to save window geometry
    def closeEvent(self, event):
        """Save window position and size to ~/.rbrdebug.conf as JSON on exit."""
        cfg = {
            "x": self.x(),
            "y": self.y(),
            "width": self.width(),
            "height": self.height(),
            "ratio": self.ratio
        }
        # try to persist console height (bottom pane) if present
        try:
            ch = None
            if hasattr(self, 'vsplitter'):
                sizes = self.vsplitter.sizes()
                if len(sizes) >= 2:
                    ch = int(sizes[1])
            if ch is not None:
                cfg['console_height'] = ch
        except Exception:
            pass
        try:
            cfg_path = os.path.join(os.path.expanduser("~"), ".rbrdebug.conf")
            # Attempt to stop any running program before closing
            try:
                self.stop_script()
            except Exception:
                pass
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception as exc:
            # best-effort only; avoid blocking shutdown
            try:
                self.statusBar().showMessage(f"Could not save config: {exc}", 3000)
            except Exception:
                pass
        super().close()

###############################################################################
# Main entry point
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = DebugMainWindow()
    w.show()
    sys.exit(app.exec())