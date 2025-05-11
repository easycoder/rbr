from PySide6.QtWidgets import (QApplication, QWidget, QPushButton, QHBoxLayout, 
                              QVBoxLayout, QStackedWidget, QSpacerItem, QSizePolicy,
                              QGraphicsDropShadowEffect)
from PySide6.QtGui import QIcon, QFont
from PySide6.QtCore import Qt, QTimer, QSize
import sys

class BasicKeyboardButton(QPushButton):
    def __init__(self, width, height, text=None, icon=None, onClick=None):
        super().__init__()
        self._text = text
        self._onClick = onClick
        self._original_pos = None
        
        self.setFixedSize(width, height)
        self.setText(text)
        self.setIcon(icon)
        
        # Style the button
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: white;
                border-radius: {int(height * 0.2)}px;
                border: none;
            }}
            QPushButton:pressed {{
                background-color: #e0e0e0;
            }}
        """)
        
        # Set font size
        font = self.font()
        font.setPixelSize(int(height * 0.5))
        self.setFont(font)
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(5)
        shadow.setXOffset(2)
        shadow.setYOffset(2)
        shadow.setColor(Qt.gray)
        self.setGraphicsEffect(shadow)
        
        # Connect click signal
        self.clicked.connect(self._handle_click)
    
    def setText(self, text):
        self._text = text
        super().setText(text)
    
    def setIcon(self, icon):
        if icon is not None:
            icon_size = int(self.height() * 0.6)
            super().setIcon(QIcon(icon))
            super().setIconSize(QSize(icon_size, icon_size))
        else:
            super().setIcon(QIcon())
    
    def onClick(self, cb):
        self._onClick = cb
    
    def _handle_click(self):
        # Animation: move down and right
        self._original_pos = self.pos()
        self.move(self.pos().x() + 2, self.pos().y() + 2)
        
        # Timer to move back
        QTimer.singleShot(200, self._reset_position)
        
        # Call callback if exists
        if callable(self._onClick):
            if self._text is not None:
                self._onClick(self._text)
            else:
                self._onClick()
    
    def _reset_position(self):
        if self._original_pos is not None:
            self.move(self._original_pos)

class DefaultKeyboardButton(BasicKeyboardButton):
    def __init__(self, width, text, onClick):
        super().__init__(width, width, text, None, onClick)
    
    def onClick(self, cb):
        super().onClick(cb)

class SpecialKeyboardButton(BasicKeyboardButton):
    def __init__(self, width, height, icon, text, onClick):
        super().__init__(width, height, None, icon)
    
    def onClick(self, cb):
        super().onClick(cb)

class KeyboardRow(QHBoxLayout):
    def __init__(self, widgets):
        super().__init__()
        self.setSpacing(5)
        for widget in widgets:
            if isinstance(widget, QSpacerItem):
                self.addItem(widget)
            else:
                self.addWidget(widget)

class KeyboardView(QVBoxLayout):
    def __init__(self, rows):
        super().__init__()
        self.setSpacing(5)
        for row in rows:
            self.addLayout(row)

class Keyboard(QStackedWidget):
    def __init__(self, views):
        super().__init__()
        for view in views:
            widget = QWidget()
            widget.setLayout(view)
            self.addWidget(widget)
    
    def setCurrentIndex(self, v=0):
        super().setCurrentIndex(v)

# Test program
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Create main window
    window = QWidget()
    window.setFixedSize(600, 350)
    window.setStyleSheet("background-color: #ccc;")
    main_layout = QVBoxLayout(window)
    main_layout.setContentsMargins(10, 10, 10, 10)
    
    # Standard height for buttons
    standard_height = int(window.height() * 0.15)
    
    # Callback functions
    currentView = 0
    
    def onClickChar(keycode):
        print(keycode)
    
    def onClickShift():
        global currentView
        print("Shift")
        if currentView == 0:
            keyboard.setCurrentIndex(1)
            currentView = 1
        elif currentView == 1:
            keyboard.setCurrentIndex(0)
            currentView = 0
    
    def onClickBack():
        print("Back")
    
    # Prepare keyboard views
    keyboardViews = []
    
    # Layout 0 (lowercase)
    rowList0 = []
    
    # Row 1: 1234567890
    buttons = [DefaultKeyboardButton(standard_height, char, onClickChar) for char in "1234567890"]
    rowList0.append(KeyboardRow(buttons))
    
    # Row 2: qwertyuiop
    buttons = [DefaultKeyboardButton(standard_height, char, onClickChar) for char in "qwertyuiop"]
    rowList0.append(KeyboardRow(buttons))
    
    # Row 3: asdfghjkl with stretches
    widgets = []
    widgets.append(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
    buttons = [DefaultKeyboardButton(standard_height, char, onClickChar) for char in "asdfghjkl"]
    widgets.extend(buttons)
    widgets.append(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
    rowList0.append(KeyboardRow(widgets))
    
    # Row 4: zxcvbnm with shift and back
    widgets = []
    shift_btn = SpecialKeyboardButton(int(standard_height * 1.5), standard_height, "up.png", "Shift", onClickShift)
    widgets.append(shift_btn)
    widgets.append(QSpacerItem(int(standard_height * 0.05), 0, QSizePolicy.Fixed, QSizePolicy.Minimum))
    buttons = [DefaultKeyboardButton(standard_height, char, onClickChar) for char in "zxcvbnm"]
    widgets.extend(buttons)
    widgets.append(QSpacerItem(int(standard_height * 0.05), 0, QSizePolicy.Fixed, QSizePolicy.Minimum))
    back_btn = SpecialKeyboardButton(int(standard_height * 1.5), standard_height, "back.png", "Back", onClickBack)
    widgets.append(back_btn)
    rowList0.append(KeyboardRow(widgets))
    
    keyboardView0 = KeyboardView(rowList0)
    keyboardViews.append(keyboardView0)
    
    # Layout 1 (uppercase)
    rowList1 = []
    
    # Row 1: 1234567890
    buttons = [DefaultKeyboardButton(standard_height, char, onClickChar) for char in "1234567890"]
    rowList1.append(KeyboardRow(buttons))
    
    # Row 2: QWERTYUIOP
    buttons = [DefaultKeyboardButton(standard_height, char, onClickChar) for char in "QWERTYUIOP"]
    rowList1.append(KeyboardRow(buttons))
    
    # Row 3: ASDFGHJKL with stretches
    widgets = []
    widgets.append(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
    buttons = [DefaultKeyboardButton(standard_height, char, onClickChar) for char in "ASDFGHJKL"]
    widgets.extend(buttons)
    widgets.append(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
    rowList1.append(KeyboardRow(widgets))
    
    # Row 4: ZXCVBNM with shift and back
    widgets = []
    shift_btn = SpecialKeyboardButton(int(standard_height * 1.5), standard_height, "up.png", "Shift", onClickShift)
    widgets.append(shift_btn)
    widgets.append(QSpacerItem(int(standard_height * 0.05), 0, QSizePolicy.Fixed, QSizePolicy.Minimum))
    buttons = [DefaultKeyboardButton(standard_height, char, onClickChar) for char in "ZXCVBNM"]
    widgets.extend(buttons)
    widgets.append(QSpacerItem(int(standard_height * 0.05), 0, QSizePolicy.Fixed, QSizePolicy.Minimum))
    back_btn = SpecialKeyboardButton(int(standard_height * 1.5), standard_height, "back.png", "Back", onClickBack)
    widgets.append(back_btn)
    rowList1.append(KeyboardRow(widgets))
    
    keyboardView1 = KeyboardView(rowList1)
    keyboardViews.append(keyboardView1)
    
    # Create keyboard with both views
    keyboard = Keyboard(keyboardViews)
    keyboard.setCurrentIndex(0)
    
    # Add to window
    main_layout.addWidget(keyboard)
    
    window.show()
    sys.exit(app.exec())