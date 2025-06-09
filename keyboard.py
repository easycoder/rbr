from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QWidget, QStackedWidget, QSpacerItem, QSizePolicy
)
from PySide6.QtGui import QFont, QIcon
from PySide6.QtCore import Qt, QTimer

class TextReceiver():
    def __init__(self, field):
        self.field = field

    def add_character(self, char):
        """
        Add a character to the text field.
        
        :param char: A single character to add to the field.
        """
        char = char.replace('&&', '&')
        if len(char) == 1:
            self.field.setText(self.field.text() + char)
        else:
            raise ValueError("Only single characters are allowed.")

    def backspace(self):
        """
        Remove the last character from the text field.
        If the field is already empty, do nothing.
        """
        current_text = self.field.text()
        if current_text:
            self.field.setText(current_text[:-1])

    def get_content(self):
        """
        Return the current content of the text field.
        
        :return: The current text in the field.
        """
        return self.field.text()
        
class KeyboardButton(QPushButton):
    def __init__(self, width, height, onClick, text=None, icon=None):
        if text != None: text = text.replace('&','&&')
        super().__init__(text)
        self.setFixedSize(width, height)
        self.setFont(QFont("Arial", height // 2))  # Font size is half the button height
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: white;
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

class KeyboardRow(QHBoxLayout):
    def __init__(self, items):
        super().__init__()
        for item in items:
            if isinstance(item, QWidget):
                self.addWidget(item)
            elif isinstance(item, QSpacerItem):
                self.addSpacerItem(item)

class KeyboardView(QVBoxLayout):
    def __init__(self, rows):
        super().__init__()
        for row in rows:
            self.addLayout(row)

class VirtualKeyboard(QStackedWidget):
    def __init__(self, buttonHeight, textField, onFinished=None):
        super().__init__()
        self.buttonHeight = buttonHeight
        self.textField = textField
        self.onFinished = onFinished

        # Create the 4 keyboard layouts
        self.addKeyboardLayout0()
        self.addKeyboardLayout1()
        self.addKeyboardLayout2()
        self.addKeyboardLayout3()

    def addKeyboardLayout0(self):
        rowList = []

        # Row 1: Numbers
        # row1 = KeyboardRow([KeyboardButton(self.buttonHeight, self.buttonHeight, self.onClickChar, char) for char in '1234567890'])
        # rowList.append(row1)

        # Row 2: QWERTY
        row2 = KeyboardRow([KeyboardButton(self.buttonHeight, self.buttonHeight, self.onClickChar, char) for char in 'qwertyuiop'])
        rowList.append(row2)

        # Row 3: ASDFGHJKL with horizontal stretches
        row3 = KeyboardRow([
            QSpacerItem(20, 40, QSizePolicy.Expanding, QSizePolicy.Minimum),
            *[KeyboardButton(self.buttonHeight, self.buttonHeight, self.onClickChar, char) for char in 'asdfghjkl'],
            QSpacerItem(20, 40, QSizePolicy.Expanding, QSizePolicy.Minimum)
        ])
        rowList.append(row3)

        # Row 4: Shift, ZXC..., Backspace
        row4 = KeyboardRow([
            KeyboardButton(self.buttonHeight * 1.5, self.buttonHeight, self.onClickShift, None, "/home/graham/dev/rbr/ui/main/up.png"),
            QSpacerItem(self.buttonHeight * 0.05, 0, QSizePolicy.Fixed, QSizePolicy.Minimum),
            *[KeyboardButton(self.buttonHeight, self.buttonHeight, self.onClickChar, char) for char in 'zxcvbnm'],
            QSpacerItem(self.buttonHeight * 0.05, 0, QSizePolicy.Fixed, QSizePolicy.Minimum),
            KeyboardButton(self.buttonHeight * 1.5, self.buttonHeight, self.onClickBack, None, "/home/graham/dev/rbr/ui/main/back.png")
        ])
        rowList.append(row4)

        # Row 5: Numbers, Space, Enter
        row5 = KeyboardRow([
            KeyboardButton(self.buttonHeight * 1.5, self.buttonHeight, self.onClickNumbers, None, "/home/graham/dev/rbr/ui/main/numbers.png"),
            QSpacerItem(self.buttonHeight * 0.05, 0, QSizePolicy.Fixed, QSizePolicy.Minimum),
            KeyboardButton(self.buttonHeight, self.buttonHeight, self.onClickChar, ","),
            KeyboardButton(self.buttonHeight * 5, self.buttonHeight, self.onClickSpace, None, "/home/graham/dev/rbr/ui/main/space.png"),
            KeyboardButton(self.buttonHeight, self.buttonHeight, self.onClickChar, "."),
            QSpacerItem(self.buttonHeight * 0.05, 0, QSizePolicy.Fixed, QSizePolicy.Minimum),
            KeyboardButton(self.buttonHeight * 1.5, self.buttonHeight, self.onClickEnter, None, "/home/graham/dev/rbr/ui/main/enter.png")
        ])
        rowList.append(row5)

        # Add the rows to the KeyboardView
        keyboardView = KeyboardView(rowList)
        container = QWidget()
        container.setLayout(keyboardView)
        self.addWidget(container)

    def addKeyboardLayout1(self):
        rowList = []

        # Row 1: Numbers
        # row1 = KeyboardRow([KeyboardButton(self.buttonHeight, self.buttonHeight, self.onClickChar, char) for char in '1234567890'])
        # rowList.append(row1)

        # Row 2: Uppercase QWERTY
        row2 = KeyboardRow([KeyboardButton(self.buttonHeight, self.buttonHeight, self.onClickChar, char) for char in 'QWERTYUIOP'])
        rowList.append(row2)

        # Row 3: Uppercase ASDFGHJKL with horizontal stretches
        row3 = KeyboardRow([
            QSpacerItem(20, 40, QSizePolicy.Expanding, QSizePolicy.Minimum),
            *[KeyboardButton(self.buttonHeight, self.buttonHeight, self.onClickChar, char) for char in 'ASDFGHJKL'],
            QSpacerItem(20, 40, QSizePolicy.Expanding, QSizePolicy.Minimum)
        ])
        rowList.append(row3)

        # Row 4: Shift, Uppercase ZXC..., Backspace
        row4 = KeyboardRow([
            KeyboardButton(self.buttonHeight * 1.5, self.buttonHeight, self.onClickShift, None, "/home/graham/dev/rbr/ui/main/up.png"),
            QSpacerItem(self.buttonHeight * 0.05, 0, QSizePolicy.Fixed, QSizePolicy.Minimum),
            *[KeyboardButton(self.buttonHeight, self.buttonHeight, self.onClickChar, char) for char in 'ZXCVBNM'],
            QSpacerItem(self.buttonHeight * 0.05, 0, QSizePolicy.Fixed, QSizePolicy.Minimum),
            KeyboardButton(self.buttonHeight * 1.5, self.buttonHeight, self.onClickBack, None, "/home/graham/dev/rbr/ui/main/back.png")
        ])
        rowList.append(row4)

        # Row 5: Numbers, Space, Enter
        row5 = KeyboardRow([
            KeyboardButton(self.buttonHeight * 1.5, self.buttonHeight, self.onClickNumbers, None, "/home/graham/dev/rbr/ui/main/numbers.png"),
            QSpacerItem(self.buttonHeight * 0.05, 0, QSizePolicy.Fixed, QSizePolicy.Minimum),
            KeyboardButton(self.buttonHeight, self.buttonHeight, self.onClickChar, ","),
            KeyboardButton(self.buttonHeight * 5, self.buttonHeight, self.onClickSpace, None, "/home/graham/dev/rbr/ui/main/space.png"),
            KeyboardButton(self.buttonHeight, self.buttonHeight, self.onClickChar, "."),
            QSpacerItem(self.buttonHeight * 0.05, 0, QSizePolicy.Fixed, QSizePolicy.Minimum),
            KeyboardButton(self.buttonHeight * 1.5, self.buttonHeight, self.onClickEnter, None, "/home/graham/dev/rbr/ui/main/enter.png")
        ])
        rowList.append(row5)

        # Add the rows to the KeyboardView
        keyboardView = KeyboardView(rowList)
        container = QWidget()
        container.setLayout(keyboardView)
        self.addWidget(container)

    def addKeyboardLayout2(self):
        rowList = []

        # Row 1: Numbers
        row1 = KeyboardRow([KeyboardButton(self.buttonHeight, self.buttonHeight, self.onClickChar, char) for char in '1234567890'])
        rowList.append(row1)

        # Row 2: Symbols
        row2 = KeyboardRow([KeyboardButton(self.buttonHeight, self.buttonHeight, self.onClickChar, char) for char in '@#£&_-()=%'])
        rowList.append(row2)

        # Row 3: Symbols with horizontal stretches
        row3 = KeyboardRow([
            KeyboardButton(self.buttonHeight, self.buttonHeight, self.onClickSymbols, None, "/home/graham/dev/rbr/ui/main/symbols.png"),
            QSpacerItem(self.buttonHeight * 0.05, 0, QSizePolicy.Fixed, QSizePolicy.Minimum),
            *[KeyboardButton(self.buttonHeight, self.buttonHeight, self.onClickChar, char) for char in '"*\'/:!?+'],
            QSpacerItem(self.buttonHeight * 0.05, 0, QSizePolicy.Fixed, QSizePolicy.Minimum),
            KeyboardButton(self.buttonHeight, self.buttonHeight, self.onClickBack, None, "/home/graham/dev/rbr/ui/main/back.png")
        ])
        rowList.append(row3)

        # Row 4: Numbers, Space, Enter
        row4 = KeyboardRow([
            KeyboardButton(self.buttonHeight * 1.5, self.buttonHeight, self.onClickLetters, None, "/home/graham/dev/rbr/ui/main/letters.png"),
            QSpacerItem(self.buttonHeight * 0.05, 0, QSizePolicy.Fixed, QSizePolicy.Minimum),
            KeyboardButton(self.buttonHeight, self.buttonHeight, self.onClickChar, ","),
            KeyboardButton(self.buttonHeight * 6, self.buttonHeight, self.onClickSpace, None, "/home/graham/dev/rbr/ui/main/space.png"),
            KeyboardButton(self.buttonHeight, self.buttonHeight, self.onClickChar, "."),
            QSpacerItem(self.buttonHeight * 0.05, 0, QSizePolicy.Fixed, QSizePolicy.Minimum),
            KeyboardButton(self.buttonHeight * 1.5, self.buttonHeight, self.onClickEnter, None, "/home/graham/dev/rbr/ui/main/enter.png")
        ])
        rowList.append(row4)

        # Add the rows to the KeyboardView
        keyboardView = KeyboardView(rowList)
        container = QWidget()
        container.setLayout(keyboardView)
        self.addWidget(container)

    def addKeyboardLayout3(self):
        rowList = []

        # Row 1: Extended symbols
        row1 = KeyboardRow([KeyboardButton(self.buttonHeight, self.buttonHeight, self.onClickChar, char) for char in '$€¥¢©®µ~¿¡'])
        rowList.append(row1)

        # Row 2: Additional symbols
        row2 = KeyboardRow([KeyboardButton(self.buttonHeight, self.buttonHeight, self.onClickChar, char) for char in '¼½¾[]{}<>^'])
        rowList.append(row2)

        # Row 3: Symbols with horizontal stretches
        row3 = KeyboardRow([
            KeyboardButton(self.buttonHeight, self.buttonHeight, self.onClickNumbers, None, "/home/graham/dev/rbr/ui/main/numbers.png"),
            QSpacerItem(self.buttonHeight * 0.05, 0, QSizePolicy.Fixed, QSizePolicy.Minimum),
            *[KeyboardButton(self.buttonHeight, self.buttonHeight, self.onClickChar, char) for char in '`;÷\\∣|¬±'],
            QSpacerItem(self.buttonHeight * 0.05, 0, QSizePolicy.Fixed, QSizePolicy.Minimum),
            KeyboardButton(self.buttonHeight, self.buttonHeight, self.onClickBack, None, "/home/graham/dev/rbr/ui/main/back.png")
        ])
        rowList.append(row3)

        # Row 4: Numbers, Space, Enter
        row4 = KeyboardRow([
            KeyboardButton(self.buttonHeight, self.buttonHeight, self.onClickLetters, None, "/home/graham/dev/rbr/ui/main/letters.png"),
            QSpacerItem(self.buttonHeight * 0.05, 0, QSizePolicy.Fixed, QSizePolicy.Minimum),
            KeyboardButton(self.buttonHeight, self.buttonHeight, self.onClickChar, ","),
            KeyboardButton(self.buttonHeight * 3, self.buttonHeight, self.onClickSpace, None, "/home/graham/dev/rbr/ui/main/space.png"),
            QSpacerItem(self.buttonHeight * 0.05, 0, QSizePolicy.Fixed, QSizePolicy.Minimum),
            *[KeyboardButton(self.buttonHeight, self.buttonHeight, self.onClickChar, char) for char in '✕§¶°'],
            KeyboardButton(self.buttonHeight, self.buttonHeight, self.onClickEnter, None, "/home/graham/dev/rbr/ui/main/enter.png")
        ])
        rowList.append(row4)

        # Add the rows to the KeyboardView
        keyboardView = KeyboardView(rowList)
        container = QWidget()
        container.setLayout(keyboardView)
        self.addWidget(container)

    # Callback functions
    def onClickChar(self,keycode):
        # print(f"Key pressed: {keycode}")
        self.textField.add_character(keycode)

    def onClickShift(self,keycode):
        # print("Shift pressed")
        if self.currentIndex() == 0:
            self.setCurrentIndex(1)
        elif self.currentIndex() == 1:
            self.setCurrentIndex(0)

    def onClickLetters(self,keycode):
        # print("Letters pressed")
        self.setCurrentIndex(0)

    def onClickNumbers(self,keycode):
        # print("Numbers pressed")
        self.setCurrentIndex(2)

    def onClickSymbols(self,keycode):
        # print("Symbols pressed")
        self.setCurrentIndex(3)

    def onClickBack(self,keycode):
        # print("Backspace pressed")
        self.textField.backspace()

    def onClickSpace(self,keycode):
        # print("Space pressed")
        self.textField.add_character(' ')

    def onClickEnter(self,keycode):
        # print("Enter pressed")
        # print(self.textField.get_content())
        if self.onFinished: self.onFinished()

if __name__ == "__main__":
    app = QApplication([])

    # Create the main window
    mainWindow = QMainWindow()
    mainWindow.setWindowTitle("Virtual Keyboard")
    mainWindow.setFixedSize(600, 300)
    mainWindow.setStyleSheet("background-color: #ccc;")

    # Compute the standard button height
    standardHeight = int(400 * 0.12)
    height=standardHeight * 0.75

    # Create the text field
    textField = QLineEdit()
    
    textField.setReadOnly(True)  # Make the field non-editable by the user
    textField.setFixedHeight(height)  # Set the height of the field

    # Set a suitable font size based on the height
    font = textField.font()
    font.setPointSize(int(height * 0.4))  # Adjust font size relative to height
    textField.setFont(font)

    # Center-align the text
    textField.setAlignment(Qt.AlignCenter)
    receiver = TextReceiver(textField)

    # Create the virtual keyboard
    virtualKeyboard = VirtualKeyboard(standardHeight, receiver)

    # Set the keyboard as the central widget
    mainWidget = QWidget()
    layout = QVBoxLayout(mainWidget)
    layout.addWidget(textField)
    layout.addWidget(virtualKeyboard)
    mainWindow.setCentralWidget(mainWidget)

    # Show the main window
    mainWindow.show()
    app.exec()
    