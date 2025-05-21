from easycoder import Handler, FatalError, RuntimeError
from PySide6.QtWidgets import (
    QApplication, 
    QMainWindow, 
    QLabel, 
    QPushButton, 
    QWidget, 
    QHBoxLayout, 
    QVBoxLayout, 
    QSpacerItem, 
    QSizePolicy
)
from PySide6.QtGui import QPixmap, QFont, QPalette, QBrush
from PySide6.QtCore import Qt

# This is the package that handles the RBR user interface.

class Room(QWidget):

    def __init__(self, command, roomlist):
        super().__init__()
        name = command['program'].getRuntimeValue(command['name'])
        mode = command['program'].getRuntimeValue(command['mode'])
        height = roomlist['height']
        self.setFixedHeight(height)  # Each row is 1/12 the height of the window
        self.setStyleSheet("background-color: #ffffcc; border: 2px solid gray;")  # Set background and border

        row_layout = QHBoxLayout(self)
        row_layout.setContentsMargins(10, 0, 10, 0)  # Add margins for spacing
        row_layout.setSpacing(10)  # Add spacing between elements

        # Icon 1
        mode = command['program'].getRuntimeValue(command['mode'])
        if not mode in ['timed', 'boost', 'advance', 'on', 'off']: mode = 'off'
        icon = f'/home/graham/dev/rbr/ui/main/{mode}.png'
        mode_icon = QLabel()
        mode_pixmap = QPixmap(icon).scaled(height * 3 // 4, height * 3 // 4, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        mode_icon.setPixmap(mode_pixmap)
        mode_icon.setStyleSheet("border-left: none; border-right: none;")

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
        row_layout.addWidget(mode_icon, 1)
        # row_layout.addWidget(name_label, 1)  # Expand the name label to use all spare space
        # row_layout.addWidget(button)
        row_layout.addWidget(edit_icon)

        roomlist['names'].append(name)
        roomlist['modes'].append(mode)

class RBR_UI(Handler):

    def __init__(self, compiler):
        Handler.__init__(self, compiler)

    def getName(self):
        return 'rbr_ui'

    #############################################################################
    # Keyword handlers

    # add room to {roomlist} name {name} mode {mode}
    # add {roomlist} to {layout}
    def k_add(self, command):
        if self.nextIs('room'):
            self.skip('to')
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                if record['keyword'] == 'roomlist':
                    command['roomlist'] = record['name']
                    while True:
                        token = self.peek()
                        if token in ['name', 'mode']:
                            self.nextToken()
                            if token == 'name':
                                command['name'] = self.nextValue()
                            elif token == 'mode':
                                command['mode'] = self.nextValue()
                        else: break
                    self.add(command)
                    return True

        elif self.isSymbol():
            record = self.getSymbolRecord()
            keyword = record['keyword']
            if keyword == 'roomlist':
                command['roomlist'] = record['name']
                self.skip('to')
                if self.nextIsSymbol():
                    record = self.getSymbolRecord()
                    keyword = record['keyword']
                    if keyword == 'layout':
                        command['layout'] = record['name']
                        self.add(command)
                        return True
        return False
        
    def r_add(self, command):
        if 'layout' in command:
            roomlist = self.getVariable(command['roomlist'])
            layout = self.getVariable(command['layout'])
            for room in roomlist['rooms']:
                layout['widget'].addWidget(room)
        else:
            record = self.getVariable(command['roomlist'])
            room = Room(command, record)
            record['rooms'].append(room)
        return self.nextPC()

    # create {rbrwin} at {left} {top} size {width} {height}
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
            
            # Set the background image
            palette = QPalette()
            background_pixmap = QPixmap("/home/graham/dev/rbr/ui/main/backdrop.jpg")
            palette.setBrush(QPalette.Window, QBrush(background_pixmap))
            window.setPalette(palette)
            record['window'] = window
            record['width'] = w
            record['height'] = h
            return self.nextPC()
        return 0

    # init {roomlist}
    def k_init(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            keyword = record['keyword']
            if keyword == 'roomlist':
                command['name'] = record['name']
                while True:
                    token = self.peek()
                    if token == 'height':
                        self.nextToken()
                        height = self.nextValue()
                        if height == None: FatalError(self.compiler, 'Compile error')
                        command['height'] = height
                    else: break
                self.add(command)
                return True
        return False
        
    def r_init(self, command):
        record = self.getVariable(command['name'])
        record['height'] = self.getRuntimeValue(command['height'])
        record['rooms'] = []
        record['names'] = []
        record['modes'] = []
        return self.nextPC()

    def k_rbrwin(self, command):
        return self.compileVariable(command, False)

    def r_rbrwin(self, command):
        return self.nextPC()

    def k_roomlist(self, command):
        return self.compileVariable(command, False)

    def r_roomlist(self, command):
        return self.nextPC()

   # set [the] layout of {rbrwin} to {layout}
    def k_set(self, command):
        self.skip('the')
        token = self.nextToken()
        command['what'] = token
        if token == 'layout':
            self.skip('of')
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                if record['keyword'] == 'rbrwin':
                    command['name'] = record['name']
                    self.skip('to')
                    if self.nextIsSymbol():
                        record = self.getSymbolRecord()
                        command['layout'] = record['name']
                        self.add(command)
                        return True
        return False
    
    def r_set(self, command):
        what = command['what']
        if what == 'layout':
            window = self.getVariable(command['name'])['window']
            content = self.getVariable(command['layout'])['widget']
            container = QWidget()
            container.setLayout(content)
            window.setCentralWidget(container)
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
