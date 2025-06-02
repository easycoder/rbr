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
from widgets import IconButton, IconAndWidgetButton, Room, Banner, Profiles

# This is the package that handles the RBR user interface.

class RBR_UI(Handler):

    def __init__(self, compiler):
        Handler.__init__(self, compiler)

    def getName(self):
        return 'rbr_ui'

    def clearWidget(self, widget):
        layout = widget.layout()
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                child_widget = item.widget()
                if child_widget is not None:
                    child_widget.setParent(None)
                    child_widget.deleteLater()
                else:
                    # If it's a layout, clear it recursively
                    child_layout = item.layout()
                    if child_layout is not None:
                        clear_widget(child_layout)
    
    #   Init the main content of a window
    def initContent(self, record, window, contentLayout):

        w = record['width']

        # Add the main banner
        contentLayout.addWidget(Banner(w))

        # Add the system name and Profiles button
        profiles = Profiles(w)
        contentLayout.addWidget(profiles)

        # Panel for rows
        panel = QWidget()
        panel.setStyleSheet('''
            background: transparent;
            border: none;
            margin: 5px;
            padding: 0;
        ''')
        roomsLayout = QVBoxLayout(panel)
        roomsLayout.setSpacing(0)
        roomsLayout.setContentsMargins(0, 0, 0, 0)
        contentLayout.addWidget(panel)

        record['profiles'] = profiles
        record['rooms'] = roomsLayout

        return

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
            record = self.getVariable(command['room'])
            room = record['value'][record['index']]
            window = self.getVariable(command['window'])
            rooms = window['rooms']
            rooms.addWidget(room)
        return self.nextPC()

    # clear {rbrwin}
    def k_clear(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            if record['keyword']== 'rbrwin':
                command['name'] = record['name']
                self.add(command)
            return True
        return False
    
    def r_clear(self, command):
        record = self.getVariable(command['name'])
        window = record['window']
        content = record['content']
        contentLayout = record['contentLayout']
        self.clearWidget(content)
        self.initContent(record, window, contentLayout)
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
            record['width'] = w
            record['height'] = h

            # Set the background image
            palette = QPalette()
            background_pixmap = QPixmap("/home/graham/dev/rbr/ui/main/backdrop.jpg")
            palette.setBrush(QPalette.Window, QBrush(background_pixmap))
            window.setPalette(palette)

            # Panel for the main components
            content = QWidget()
            content.setStyleSheet('''
                background-color: #fff;
                margin:0;
            ''')
            contentLayout = QVBoxLayout(content)
            contentLayout.setSpacing(0)

            self.initContent(record, window, contentLayout)

            # Main layout
            mainWidget = QWidget()
            mainLayout = QVBoxLayout(mainWidget)
            mainLayout.setContentsMargins(0, 0, 0, 0)
            mainLayout.addWidget(content)
            mainLayout.addStretch(1)

            window.setCentralWidget(mainWidget)

            record['window'] = window
            record['contentLayout'] = contentLayout
            record['content'] = content
            return self.nextPC()
        
        elif keyword == 'room':
            name = self.getRuntimeValue(command['name'])
            mode = self.getRuntimeValue(command['mode'])
            height = self.getRuntimeValue(command['height'])
            room = Room(name, mode, height)
            if not 'rooms' in record:
                record['value'][record['index']] = room
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

   # set attribute {attr} [of] {window}/{room} [to] {value}
    def k_set(self, command):
        if self.nextIs('attribute'):
            command['attribute'] = self.nextValue()
            self.skip('of')
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                keyword = record['keyword']
                if keyword in ['rbrwin', 'room']:
                    command['name'] = record['name']
                    self.skip('to')
                    command['value'] = self.nextValue()
                    self.add(command)
                    return True
        return False
    
    def r_set(self, command):
        if 'attribute' in command:
            attribute = self.getRuntimeValue(command['attribute'])
            record = self.getVariable(command['name'])
            value = self.getRuntimeValue(command['value'])
            keyword = record['keyword']
            if keyword == 'rbrwin':
                if attribute == 'system name':
                    profiles = record['profiles']
                    profiles.setSystemName(value)
                elif attribute == 'profile':
                    profiles = record['profiles']
                    profiles.setProfile(value)
            elif keyword == 'room':
                room = record['value'][record['index']]
                if attribute == 'temperature':
                    room.setTemperature(value)
            return self.nextPC()
        return 0

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
