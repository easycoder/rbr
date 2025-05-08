from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QGraphicsDropShadowEffect, QSpacerItem, QSizePolicy
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFont, QColor, QIcon


class RoundedButton(QPushButton):
    def __init__(self, width, height, text):
        super().__init__(text)
        self.setFixedSize(width, height)
        self.setFont(QFont("Arial", height // 2))
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: white;
                border-radius: {height // 5}px;
            }}
            QPushButton:pressed {{
                background-color: #f0f0f0;
            }}
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setOffset(2, 2)
        shadow.setColor(QColor(200, 200, 200))
        self.setGraphicsEffect(shadow)
        self.callback = None

        self.clicked.connect(self._on_click)

    def _on_click(self):
        self.move(self.x() + 2, self.y() + 2)
        QTimer.singleShot(200, lambda: self.move(self.x() - 2, self.y() - 2))
        if self.callback:
            self.callback(self.text())

    def setWidth(self, width):
        self.setFixedSize(width, self.height())

    def setText(self, text):
        super().setText(text)

    def setCallback(self, cb):
        self.callback = cb


class KeyboardWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Keyboard")
        self.setGeometry(100, 100, 600, 300)

        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)

        # Define rows of buttons
        rows = [
            "1234567890",
            "QWERTYUIOP",
            "ASDFGHJKL",
            "ZXCVBNM"
        ]

        for row in rows[:-1]:
            row_layout = QHBoxLayout()
            row_layout.setAlignment(Qt.AlignCenter)
            for label in row:
                button = RoundedButton(50, 50, label)
                button.setCallback(self.on_button_click)
                row_layout.addWidget(button)
            main_layout.addLayout(row_layout)

        # Fourth row with additional buttons and spacers
        fourth_row_layout = QHBoxLayout()
        fourth_row_layout.setAlignment(Qt.AlignCenter)

        # Add the left button with the graphic
        left_button = RoundedButton(75, 50, "")
        left_button.setIcon(QIcon("up.png"))
        left_button.setIconSize(left_button.size())
        fourth_row_layout.addWidget(left_button)

        # Add a 3-pixel spacer
        left_spacer = QSpacerItem(3, 50, QSizePolicy.Fixed, QSizePolicy.Minimum)
        fourth_row_layout.addSpacerItem(left_spacer)

        # Add the rest of the buttons
        for label in rows[-1]:
            button = RoundedButton(50, 50, label)
            button.setCallback(self.on_button_click)
            fourth_row_layout.addWidget(button)

        # Add a 3-pixel spacer
        right_spacer = QSpacerItem(3, 50, QSizePolicy.Fixed, QSizePolicy.Minimum)
        fourth_row_layout.addSpacerItem(right_spacer)

        # Add the right button with the graphic
        right_button = RoundedButton(75, 50, "")
        right_button.setIcon(QIcon("back.png"))
        right_button.setIconSize(right_button.size())
        fourth_row_layout.addWidget(right_button)

        main_layout.addLayout(fourth_row_layout)

        self.setLayout(main_layout)

    def on_button_click(self, key):
        print(f"Button clicked: {key}")


if __name__ == "__main__":
    app = QApplication([])
    keyboard = KeyboardWidget()
    keyboard.show()
    app.exec()
