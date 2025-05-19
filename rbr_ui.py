from easycoder import Handler, FatalError, RuntimeError
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QLabel, QPushButton, QWidget, QHBoxLayout, QSpacerItem, QSizePolicy
)
from PySide6.QtGui import QPixmap, QFont, QPalette, QBrush
from PySide6.QtCore import Qt

# This is the package that handles the RBR user interface.

class Room(QWidget):

    def __init__(self, height):
        super(Room, self).__init__()
        self.setFixedHeight(height)  # Each row is 1/12 the height of the window
        self.setStyleSheet("background-color: #ffffcc; border: 2px solid gray;")  # Set background and border

        row_layout = QHBoxLayout(self)
        row_layout.setContentsMargins(10, 0, 10, 0)  # Add margins for spacing
        row_layout.setSpacing(10)  # Add spacing between elements

        # Icon 1: Clock
        clock_icon = QLabel()
        clock_pixmap = QPixmap("/home/graham/dev/rbr/ui/main/clock.png").scaled(height * 3 // 4, height * 3 // 4, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        clock_icon.setPixmap(clock_pixmap)
        clock_icon.setStyleSheet("border-left: none; border-right: none;")

        # Name label
        name_label = QLabel("Room Name")
        name_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        name_label.setStyleSheet("background-color: transparent; border: none;")  # Transparent background
        font = QFont()
        font.setPointSize(16)  # Adjust font size to fit at least 20 characters
        font.setBold(True)  # Make the font bold
        name_label.setFont(font)

        # Button with white text and blue background
        button = QPushButton("20.0°C")
        button.setStyleSheet("color: white; background-color: blue; border: none;")
        button.setFixedSize(80, 40)  # Adjust button size
        button.setFont(font)  # Use the same font as the label

        # Icon 2: Edit
        edit_icon = QLabel()
        edit_pixmap = QPixmap("/home/graham/dev/rbr/ui/main/edit.png").scaled(height * 3 // 4, height * 3 // 4, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        edit_icon.setPixmap(edit_pixmap)
        edit_icon.setStyleSheet("border-left: none; border-right: none;")

        # Add elements to the row layout
        row_layout.addWidget(clock_icon)
        row_layout.addWidget(name_label, 1)  # Expand the name label to use all spare space
        row_layout.addWidget(button)
        row_layout.addWidget(edit_icon)

class RBR_UI(Handler):

    def __init__(self, compiler):
        Handler.__init__(self, compiler)

    def getName(self):
        return 'points'

    #############################################################################
    # Keyword handlers

    # create the main UI
    def k_create(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            command['name'] = record['name']
            keyword = record['keyword']
            if keyword == 'rbrwin':
                command['title'] = 'Default'
                x = None
                y = None
                w = self.compileConstant(600)
                h = self.compileConstant(1024)
                while True:
                    token = self.peek()
                    if token in ['title', 'at', 'size']:
                        self.nextToken()
                        if token == 'title': command['title'] = self.nextValue()
                        elif token == 'at':
                            x = self.nextValue()
                            y = self.nextValue()
                        elif token == 'size':
                            w = self.nextValue()
                            h = self.nextValue()
                        else: return False
                    else: break
                command['x'] = x
                command['y'] = y
                command['w'] = w
                command['h'] = h
                self.add(command)
                return True
        return False

    def r_create(self, command):
        record = self.getVariable(command['name'])
        keyword = record['keyword']
        if keyword == 'rbrwin':
            window = QMainWindow()
            window.setWindowTitle(self.getRuntimeValue(command['title']))
            w = self.getRuntimeValue(command['w'])
            h = self.getRuntimeValue(command['h'])
            x = command['x']
            y = command['y']
            if x == None: x = (self.program.screenWidth - w) / 2
            else: x = self.getRuntimeValue(x)
            if y == None: y = (self.program.screenHeight - h) / 2
            else: y = self.getRuntimeValue(x)
            window.setGeometry(x, y, w, h)
            record = self.getVariable(command['name'])
            
            # Set the background image
            palette = QPalette()
            background_pixmap = QPixmap("/home/graham/dev/rbr/ui/main/backdrop.jpg")
            palette.setBrush(QPalette.Window, QBrush(background_pixmap))
            window.setPalette(palette)

            # Main layout
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.setSpacing(10)  # Set spacing between rows to 10

            # Create 5 rows
            for _ in range(5):
                row = Room(h // 12)
                layout.addWidget(row)

            # Add a stretch below the last row
            layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

            window.setCentralWidget(widget)
            record['window'] = window
            record['height'] = h
            record['layout'] = layout
            return self.nextPC()
        return 0

    def k_rbrwin(self, command):
        return self.compileVariable(command, False)

    def r_rbrwin(self, command):
        return self.nextPC()

    def k_room(self, command):
        return self.compileVariable(command, False)

    def r_room(self, command):
        return self.nextPC()

    # show {rbrwin}
    def k_show(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            keyword = record['keyword']
            if keyword == 'rbrwin':
                command['window'] = record['name']
                self.add(command)
                return True
        return False
        
    def r_show(self, command):
        window = self.getVariable(command['window'])['window']
        window.show()
        return self.nextPC()

    #############################################################################
    # Compile a value in this domain
    def compileValue(self):
        return None

    #############################################################################
    # Modify a value or leave it unchanged.
    def modifyValue(self, value):
        return value

    #############################################################################
    # Value handlers

    def v_none(self, v):
        return None

    #############################################################################
    # Compile a condition
    def compileCondition(self):
        condition = {}
        return condition

    #############################################################################
    # Condition handlers
