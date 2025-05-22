from easycoder import Handler, FatalError, RuntimeError
from PySide6.QtWidgets import (
    QApplication, 
    QMainWindow, 
    QLabel, 
    QPushButton, 
    QWidget, 
    QFrame,
    QHBoxLayout, 
    QVBoxLayout, 
    QSpacerItem, 
    QSizePolicy
)
from PySide6.QtGui import QPixmap, QFont, QPalette, QBrush
from PySide6.QtCore import Qt
from widgets import IconButton, IconAndWidgetButton, Room, Banner

# This is the package that handles the RBR user interface.

class RBR_UI(Handler):

    def __init__(self, compiler):
        Handler.__init__(self, compiler)

    def getName(self):
        return 'rbr_ui'

    #############################################################################
    # Keyword handlers

    # add {room} to {rbrwin}
    def k_add(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            keyword = record['keyword']
            if keyword == 'room':
                command['room'] = record['name']
                self.skip('to')
                if self.nextIsSymbol():
                    record = self.getSymbolRecord()
                    keyword = record['keyword']
                    if keyword == 'rbrwin':
                        command['window'] = record['name']
                        self.add(command)
                        return True

        return False
        
    def r_add(self, command):
        if 'room' in command:
            room = self.getVariable(command['room'])['room']
            window = self.getVariable(command['window'])
            rooms = window['rooms']
            rooms.addWidget(room)
        return self.nextPC()

    # create {rbrwin} at {left} {top} size {width} {height}
    # create {room} {name} {mode} {height}
    def k_create(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            command['varname'] = record['name']
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

            elif keyword == 'room':
                while True:
                    token = self.peek()
                    if token in ['name', 'mode', 'height']:
                        self.nextToken()
                        if token == 'name':
                            command['name'] = self.nextValue()
                        elif token == 'mode':
                            command['mode'] = self.nextValue()
                        elif token == 'height':
                            command['height'] = self.nextValue()
                    else: break
                self.add(command)
                return True
        return False

    def r_create(self, command):
        record = self.getVariable(command['varname'])
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

            # Panel for the main components
            content = QWidget()
            content.setStyleSheet('''
                background-color: #fff;
                border-radius: 10px;
                margin:5px;
            ''')
            contentLayout = QVBoxLayout(content)
            contentLayout.addWidget(Banner(w))

            # Panel for rows
            panel = QWidget()
            panel.setStyleSheet('''
                background: transparent;
                border: none;
                margin: 5px;
            ''')
            roomsLayout = QVBoxLayout(panel)
            roomsLayout.setSpacing(2)
            roomsLayout.setContentsMargins(5, 5, 5, 5)
            contentLayout.addWidget(panel)

            # Main layout
            mainWidget = QWidget()
            mainLayout = QVBoxLayout(mainWidget)
            mainLayout.setContentsMargins(0, 0, 0, 0)
            mainLayout.addWidget(content)
            mainLayout.addStretch(1)

            window.setCentralWidget(mainWidget)

            record['window'] = window
            record['rooms'] = roomsLayout
            record['width'] = w
            record['height'] = h
            return self.nextPC()
        
        elif keyword == 'room':
            name = self.getRuntimeValue(command['name'])
            mode = self.getRuntimeValue(command['mode'])
            height = self.getRuntimeValue(command['height'])
            room = Room(name, mode, height)
            record['room'] = room
            return self.nextPC()

        return 0

    def k_rbrwin(self, command):
        return self.compileVariable(command, False)

    def r_rbrwin(self, command):
        return self.nextPC()

    def k_room(self, command):
        return self.compileVariable(command, False, 'gui')

    def r_room(self, command):
        return self.nextPC()

   # set [the] layout of {rbrwin} to {layout}
    def k_set(self, command):
        return False
    
    def r_set(self, command):
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
