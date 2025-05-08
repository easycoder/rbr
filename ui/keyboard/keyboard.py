from PySide6.QtWidgets import QApplication, QPushButton, QHBoxLayout, QWidget
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt
from key import RoundedButton

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Keyboard Example")
        self.setFixedSize(600, 100)

        # Create a horizontal layout for the row of buttons
        layout = QHBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        # Create buttons with labels 1 to 0
        labels = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]
        for label in labels:
            button = RoundedButton(50, label)
            layout.addWidget(button)

if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
