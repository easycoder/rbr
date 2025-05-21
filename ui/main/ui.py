from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QLabel, QPushButton, QWidget, QHBoxLayout, QSizePolicy, QSpacerItem
)
from PySide6.QtGui import QPixmap, QFont, QPalette, QBrush
from PySide6.QtCore import Qt
import sys

ROW_COUNT = 5
WINDOW_WIDTH = 600
WINDOW_HEIGHT = 1024
ROW_HEIGHT = WINDOW_HEIGHT // 12
ICON_HEIGHT = int(ROW_HEIGHT * 0.75)
ROW_SPACING = 10

class Row(QWidget):
    def __init__(self, name="Room Name", temp="20.0°C"):
        super().__init__()
        self.setFixedHeight(ROW_HEIGHT)
        self.setStyleSheet("background-color: #ffffcc; border: 2px solid gray;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Icon 1: Clock
        clock_icon = QLabel()
        clock_pixmap = QPixmap("timed.png").scaled(ICON_HEIGHT, ICON_HEIGHT, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        clock_icon.setPixmap(clock_pixmap)
        clock_icon.setStyleSheet("border: none;")

        # Name label
        name_label = QLabel(name)
        name_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        name_label.setStyleSheet("border: none;")
        font = QFont()
        font.setBold(True)
        # Estimate font size to fit at least 20 chars in available width
        button_width = 100
        icon_space = 2 * ICON_HEIGHT + button_width + 40  # 2 icons + button + margins
        available_width = WINDOW_WIDTH - icon_space
        font.setPointSize(max(10, available_width // 20 // 1.7))  # 1.7 is a fudge factor for char width
        name_label.setFont(font)

        # Button
        button = QPushButton(temp)
        button.setStyleSheet("color: white; background-color: blue; border: 1px solid black;")
        button.setFixedHeight(int(ICON_HEIGHT * 0.9))
        button.setFont(font)
        button.setMinimumWidth(button_width)

        # Icon 2: Edit
        edit_icon = QLabel()
        edit_pixmap = QPixmap("edit.png").scaled(ICON_HEIGHT, ICON_HEIGHT, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        edit_icon.setPixmap(edit_pixmap)
        edit_icon.setStyleSheet("border: none;")

        layout.addWidget(clock_icon)
        layout.addWidget(name_label, 1)
        layout.addWidget(button)
        layout.addWidget(edit_icon)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Room List")
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)

        # Set the background image
        palette = QPalette()
        background_pixmap = QPixmap("backdrop.jpg")
        palette.setBrush(QPalette.Window, QBrush(background_pixmap))
        self.setPalette(palette)

        # Main layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Add top spacer
        spacer = QWidget()
        spacer.setFixedHeight(10)
        spacer.setStyleSheet("background-color: #ffffcc; border: none;")
        main_layout.addWidget(spacer)

        # Panel for rows
        panel = QWidget()
        panel.setStyleSheet("background-color: #888;")
        panel_height = ROW_COUNT * ROW_HEIGHT + (ROW_COUNT - 1) * ROW_SPACING
        panel.setFixedHeight(panel_height)
        panel.setFixedWidth(WINDOW_WIDTH)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setSpacing(ROW_SPACING)
        panel_layout.setContentsMargins(0, 0, 0, 0)

        # Add rows
        for _ in range(ROW_COUNT):
            row = Row()
            panel_layout.addWidget(row)

        main_layout.addWidget(panel)

        # Add bottom spacer
        main_layout.addWidget(spacer)

        main_layout.addStretch(1)  # Reveal background in unused space

        self.setCentralWidget(main_widget)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())