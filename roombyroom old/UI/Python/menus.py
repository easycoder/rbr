# Example PySide6 main window with a menu bar and several menus + items

import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow,  QFileDialog, QMessageBox, QTextEdit
)
from PySide6.QtGui import QKeySequence, QAction
from PySide6.QtCore import Qt

class MenuWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Menu Window Example")
        self.setMinimumSize(800, 600)

        # Central widget (simple text editor for demo)
        self.editor = QTextEdit(self)
        self.setCentralWidget(self.editor)

        # Status bar
        self.statusBar().showMessage("Ready")

        # Build menus
        self._create_actions()
        self._create_menus()

    def _create_actions(self):
        # File actions
        self.newAct = QAction("New", self, shortcut=QKeySequence.New, triggered=self.file_new)
        self.openAct = QAction("Open...", self, shortcut=QKeySequence.Open, triggered=self.file_open)
        self.saveAct = QAction("Save...", self, shortcut=QKeySequence.Save, triggered=self.file_save)
        self.exitAct = QAction("Exit", self, shortcut="Ctrl+Q", triggered=self.close)

        # Edit actions
        self.undoAct = QAction("Undo", self, shortcut=QKeySequence.Undo, triggered=self.editor.undo)
        self.redoAct = QAction("Redo", self, shortcut=QKeySequence.Redo, triggered=self.editor.redo)
        self.cutAct = QAction("Cut", self, shortcut=QKeySequence.Cut, triggered=self.editor.cut)
        self.copyAct = QAction("Copy", self, shortcut=QKeySequence.Copy, triggered=self.editor.copy)
        self.pasteAct = QAction("Paste", self, shortcut=QKeySequence.Paste, triggered=self.editor.paste)

        # View actions
        self.toggleStatusAct = QAction("Toggle Status Bar", self, checkable=True, checked=True)
        self.toggleStatusAct.triggered.connect(self._toggle_status_bar)

        # Help actions
        self.aboutAct = QAction("About", self, triggered=self.show_about)

    def _create_menus(self):
        menubar = self.menuBar()

        # File menu
        fileMenu = menubar.addMenu("&File")
        fileMenu.addAction(self.newAct)
        fileMenu.addAction(self.openAct)
        fileMenu.addAction(self.saveAct)
        fileMenu.addSeparator()
        fileMenu.addAction(self.exitAct)

        # Edit menu
        editMenu = menubar.addMenu("&Edit")
        editMenu.addAction(self.undoAct)
        editMenu.addAction(self.redoAct)
        editMenu.addSeparator()
        editMenu.addAction(self.cutAct)
        editMenu.addAction(self.copyAct)
        editMenu.addAction(self.pasteAct)

        # View menu
        viewMenu = menubar.addMenu("&View")
        viewMenu.addAction(self.toggleStatusAct)

        # Help menu
        helpMenu = menubar.addMenu("&Help")
        helpMenu.addAction(self.aboutAct)

    # File handlers
    def file_new(self):
        self.editor.clear()
        self.statusBar().showMessage("New file", 3000)

    def file_open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "Text Files (*.txt);;All Files (*)")
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.editor.setPlainText(f.read())
                self.statusBar().showMessage(f"Opened: {path}", 4000)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open file:\n{e}")

    def file_save(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "Text Files (*.txt);;All Files (*)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self.editor.toPlainText())
                self.statusBar().showMessage(f"Saved: {path}", 4000)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save file:\n{e}")

    # View handlers
    def _toggle_status_bar(self, checked):
        if checked:
            self.statusBar().show()
        else:
            self.statusBar().hide()

    # Help handlers
    def show_about(self):
        QMessageBox.information(self, "About", "MenuWindow Example\nPySide6 demo")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MenuWindow()
    win.show()
    sys.exit(app.exec())
