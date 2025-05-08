from PySide6.QtWidgets import QApplication, QPushButton, QGraphicsDropShadowEffect, QVBoxLayout, QWidget
from PySide6.QtGui import QColor, QFont
from PySide6.QtCore import QTimer, Qt

class RoundedButton(QPushButton):
    def __init__(self, size=50, text="A", parent=None):
        super().__init__(text, parent)
        self.setFixedSize(size, size)  # Set the button size
        self.setFont(QFont("Arial", 25))  # Set the font size to 25 pixels
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: white;
                border: none;
                border-radius: 5px;  /* Rounded corners */
            }}
            QPushButton:pressed {{
                background-color: #ddd;  /* Slightly darker background when pressed */
            }}
        """)

        # Add a light shadow to the right and bottom of the button
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(10)
        shadow.setOffset(3, 3)  # Shadow offset to the right and bottom
        shadow.setColor(QColor(0, 0, 0, 80))  # Light shadow color
        self.setGraphicsEffect(shadow)

        # Initialize callback
        self.callback = None

        # Connect the button click to the animation
        self.clicked.connect(self.animate_button)

    def animate_button(self):
        # Move the button 2 pixels down and to the right
        self.move(self.x() + 2, self.y() + 2)

        # Wait 200ms, then move the button back to its original position
        QTimer.singleShot(200, lambda: self.move(self.x() - 2, self.y() - 2))

        # Call the callback function if set
        if self.callback:
            self.callback(self.text())

    def setWidth(self, width):
        """Set the width (and height) of the button."""
        self.setFixedSize(width, width)

    def setText(self, text):
        """Set the text of the button."""
        super().setText(text)

    def setCallback(self, cb):
        """Set a function to call when the button is clicked."""
        self.callback = cb

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rounded Button Example")
        self.setFixedSize(200, 200)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        # Create the rounded button
        button = RoundedButton()
        button.setCallback(lambda key: print(f"Button clicked: {key}"))
        layout.addWidget(button)

if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
