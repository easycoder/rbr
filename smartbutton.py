from PySide6.QtWidgets import QPushButton
from PySide6.QtGui import QFont, QIcon
from PySide6.QtCore import Qt, QTimer

class SmartButton(QPushButton):
    def __init__(self, width, height, onClick, text=None, icon=None):
        if text != None: text = text.replace('&','&&')
        super().__init__(text)
        self.setFixedSize(width, height)
        self.setFont(QFont("Arial", height // 2))  # Font size is half the button height
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: light-gray;
                border: none;
                border-radius: {int(height * 0.2)}px;  /* Rounded corners */
            }}
            QPushButton:pressed {{
                background-color: #ddd;  /* Slightly darker background when pressed */
            }}
        """)

        if icon:
            self.setIcon(QIcon(icon))
            self.setIconSize(self.size())

        self.clicked.connect(lambda: self.animate_button(onClick, text))

    def animate_button(self, onClick, text):
        # Move the button 2 pixels down and right
        self.move(self.x() + 2, self.y() + 2)
        QTimer.singleShot(200, lambda: self.move(self.x() - 2, self.y() - 2))  # Move back after 200ms
        onClick(text)
