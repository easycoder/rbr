import sys
from collections import namedtuple
from keyboard import VirtualKeyboard
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QPushButton,
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QDialog,
    QSizePolicy,
    QGridLayout
)
from PySide6.QtGui import QIcon, QPixmap, QFont, QPalette, QBrush
from PySide6.QtCore import Qt, QTimer, QSize, Signal

###############################################################################
# Some style definitions
def defaultQFrameStyle():
    return '{' + f'''
        background-color: #ffc;
        border: 1px solid #888;
        border-radius: 10px;
        ''' + '}'

def defaultGrayFrameStyle():
    return '{' + f'''
        background-color: #ccc;
        border: 1px solid #888;
        border-radius: 10px;
        ''' + '}'

def borderlessQFrameStyle():
    return '{' + f'''
        background-color: #ccc;
        border: none;
        ''' + '}'

def invisibleQFrameStyle():
    return '{' + f'''
        background-color: #ffc;
        border: none;
        ''' + '}'

def defaultQLabelStyle(size):
    return '{' + f'''
        background-color: #ccc;
        border: 1px solid #888;
        border-radius: 10px;
        padding: 10px;
        font-size: {size}px;
        font-weight: bold;
        ''' + '}'

def borderlessQLabelStyle(size):
    return '{' + f'''
        background-color: #ccc;
        border: none;
        padding: 10px;
        font-size: {size}px;
        font-weight: bold;
        ''' + '}'

def defaultIconStyle():
    return '{' + f'''
        background-color: #ccc;
        border: 1px solid #888;
        border-radius: 10px;
        ''' + '}'

def borderlessIconStyle():
    return '{' + f'''
        background-color: #ccc;
        border: none;
        ''' + '}'

###############################################################################
# An expanding label
class ExpandingLabel(QLabel):
    def __init__(self, text=''):
        super().__init__(text)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAlignment(Qt.AlignCenter)

###############################################################################
# A generic icon
class GenericIcon(ExpandingLabel):
    def __init__(self, icon, size):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap(icon).scaled(size, size)
        self.setPixmap(pixmap)

###############################################################################
# A button just containing tezt

class TextButton(QPushButton):
    def __init__(self, program, name, height, text, index=0):
        super().__init__()
        self.program = program
        self.name = name
        self.text = text
        self.index = index
        self.onClick = None
        self.fcb = None
        self.clicked.connect(lambda: self.animate_button())

        self.setFixedHeight(height)
        self.setStyleSheet(f"""
            QPushButton {{
                padding: 5px;
                background-color: #ccc;
                border: 1px solid black;
                border-radius: {height // 5}px;
                font-size: {height * 0.35}px;
                font-weight: bold;
            }}
        """)

        self.setText(text)
    
    # Callback to EC script
    def setOnClick(self, onClick):
        self.onClick = onClick
    
    # Function callback
    def setFCB(self, fcb):
        self.fcb = fcb
    
    def moveBack(self):
        try: self.move(self.x() - 2, self.y() - 2)
        except: pass

    def animate_button(self):
        # Move the button 2 pixels down and right
        self.move(self.x() + 2, self.y() + 2)
        QTimer.singleShot(200, lambda: self.moveBack())  # Move back after 200ms
        if self.onClick != None: self.program.run(self.onClick)
        elif self.fcb != None: self.fcb(self.name)

    def getIndex(self):
        return self.index

###############################################################################
# A button containing an icon

class IconButton(QPushButton):
    def __init__(self, program, height, icon, index=0):
        super().__init__()
        self.program = program
        self.index = index
        self.onClick = None
        self.fcb = None
        self.clicked.connect(lambda: self.animate_button(self.index))

        if height != None:
            self.setFixedSize(height, height)
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color #ccc;
                    border:none;
                    border-radius:{int(height * 0.2)}px;  /* Rounded corners */
                }}
            """)
            self.setIconSize(QSize(height * 0.8, height * 0.8))

        self.setIcon(QIcon(icon))
    
    # Function callback
    def setFCB(self, fcb):
        self.fcb = fcb
    
    def setOnClick(self, onClick):
        self.onClick = onClick
    
    def moveBack(self):
        try: self.move(self.x() - 2, self.y() - 2)
        except: pass

    def animate_button(self, index):
        if index != None: self.program.roomIndex = index
        # Move the button 2 pixels down and right
        self.move(self.x() + 2, self.y() + 2)
        QTimer.singleShot(200, lambda: self.moveBack())
        print('fcb:',self.fcb)
        if self.onClick != None: self.program.run(self.onClick)
        elif self.fcb != None: self.fcb()

    def getIndex(self):
        return self.index

###############################################################################
# A button with text/icon and a widget.

class IconAndWidgetButton(QWidget):
    clicked = Signal()

    def __init__(self, program, name, height, widthFactor, text, image, widget, index=0):
        super().__init__()

        self.setStyleSheet("""
            background-color: transparent;
            border: none;
        """)

        self.program = program
        self.name = name
        self.text = text
        self.index = index
        self.onClick = None
        self.clicked.connect(lambda: self.animate_button(self.index))

        self.setFixedSize(height*widthFactor, height)
        mainLayout = QHBoxLayout(self)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.setSpacing(0)

        # icon on the left
        label = ExpandingLabel()
        label.setFixedSize(height, height)
        pixmap = QPixmap(image).scaled(height * 0.75, height * 0.75)
        label.setPixmap(pixmap)
        mainLayout.addWidget(label)

        # Widget on the right
        mainLayout.addWidget(widget, alignment=Qt.AlignVCenter)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
    
    def setOnClick(self, onClick):
        self.onClick = onClick
    
    def moveBack(self):
        try: self.move(self.x() - 2, self.y() - 2)
        except: pass

    def animate_button(self, index):
        self.program.roomIndex = index
        # Move the button 2 pixels down and right
        self.move(self.x() + 2, self.y() + 2)
        QTimer.singleShot(200, lambda: self.moveBack())
        if self.onClick != None: self.program.run(self.onClick)

    def getIndex(self):
        return self.index

###############################################################################
# A row of room information
class Room(QFrame):

    def __init__(self, program, name, mode, height, index=0):
        super().__init__()
        self.program = program
        self.name = name
        self.mode = mode
        self.temperature = 0
        self.index = index

        self.setStyleSheet("""
            background-color: #ffc;
            border: 1px solid gray;
            border-radius: 10px;
        """)

        self.setFixedHeight(height)  # Each row is 1/12 the height of the window

        roomsLayout = QHBoxLayout(self)
        roomsLayout.setSpacing(0)  # No spacing between elements
        roomsLayout.setContentsMargins(0, 0, 0, 0)

        modePanel = QWidget()
        modePanel.setStyleSheet('''
            background-color: #ccc;
            border: 1px solid gray;
        ''')
        roomsLayout.addWidget(modePanel)
        modePanelLayout = QHBoxLayout(modePanel)
        modePanelLayout.setSpacing(0)
        modePanelLayout.setContentsMargins(5, 0, 0, 0)
        # modePanelLayout.setAlignment(Qt.AlignTop)

        # Icon 1: Mode
        label = QLabel(f'{mode[0].upper()}{mode[1:]}')
        label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        label.setStyleSheet(f"""
            background-color: none;
            border: none;
            font-size: {height // 5}px;
            font-weight: bold;
        """)
        # label.setFixedSize(height * 1.2, height * 0.6)
        if not mode in ['timed', 'boost', 'advance', 'on', 'off']: mode = 'off'
        icon = f'/home/graham/dev/rbr/ui/main/{mode}.png'
        self.modeButton = IconAndWidgetButton(self.program, name, height * 0.8, 2.5, mode, icon, label, index)

        # Room name label
        nameLabel = QLabel(name)
        nameLabel.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        nameLabel.setStyleSheet('''
            background-color: transparent;
            border: none;
        ''')
        font = QFont()
        font.setPointSize(16)  # Adjust font size to fit at least 20 characters
        font.setBold(True)  # Make the font bold
        nameLabel.setFont(font)

        # Button with white text and blue background
        temperatureButton = QPushButton('----°C')
        temperatureButton.setStyleSheet('color: white; background-color: blue; border: none;')
        temperatureButton.setFixedSize(height * 1.2, height * 0.6)  # Adjust button size
        temperatureButton.setFont(font)  # Use the same font as the label
        self.temperatureButton = temperatureButton

        # Icon 2: Tools
        self.toolsButton = IconButton(self.program, height * 3 // 4, '/home/graham/dev/rbr/ui/main/edit.png', index)

        # Add elements to the row layout
        modePanelLayout.addWidget(self.modeButton)
        roomsLayout.addWidget(nameLabel, 1)  # Expand the name label to use all spare space
        roomsLayout.addWidget(temperatureButton)
        roomsLayout.addWidget(self.toolsButton)
    
    def setTemperature(self, value):
        self.temperature = value
        self.temperatureButton.setText(f'{value}°C')
    
    def getName(self):
        return self.name
    
    def getMode(self):
        return self.mode
    
    def getTemperature(self):
        return self.temperature

    def getIndex(self):
        return self.index

###############################################################################
# The banner at the top of the window
class Banner(QLabel):
    def __init__(self, program, width):
        super().__init__()
        self.setStyleSheet(f'''
            background: transparent;
            margin-bottom: 5px;
            padding: 0;
            color: black;
            font-family: Times;
            font-weight: bold;
            text-align: center;
        ''')
        height = width * 80 / 600
        self.setFixedSize(width, height)

        # The gradient label
        pixmap = QPixmap("/home/graham/dev/rbr/ui/main/gradient.png")
        self.setPixmap(pixmap)

        layout = QHBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # The home buttom
        homeButton = IconButton(program, height * 3 // 4, '/home/graham/dev/rbr/ui/main/RBRLogo.png')
        layout.addWidget(homeButton)

        # The title panel
        titlePanel = QWidget()
        titlePanel.setStyleSheet(f'''
        ''')
        titleLayout = QVBoxLayout(titlePanel)
        titleLayout.setSpacing(0)
        titleLayout.setContentsMargins(0, 0, 0, 0)
        title1 = ExpandingLabel('Room By Room')
        title1.setStyleSheet(f'''
            font-size: {height * 0.6}px;
            margin: 0;
        ''')
        title2 = ExpandingLabel('Intelligent heating when and where you need it')
        title2.setStyleSheet(f'''
            font-size: {height * 0.18}px;
            margin: 0;
        ''')
        titleLayout.addWidget(title1, 1)
        titleLayout.addWidget(title2, 1)

        layout.addWidget(titlePanel)

        #The Hamburger button
        self.hamburgerButton = IconButton(program, height * 3 // 4, '/home/graham/dev/rbr/ui/main/hamburger.png')
        layout.addWidget(self.hamburgerButton)
    
    def getElement(self, name):
        if name == 'hamburger': return self.hamburgerButton
        return None

###############################################################################
# The Profiles bar
class Profiles(QWidget):
    def __init__(self, program, width):
        super().__init__()
        self.program = program

        self.setStyleSheet(f'''
            background: transparent;
            margin: 0;
            padding: 0;
            color: black;
            font-family: Times;
            font-weight: bold;
            text-align: center;
        ''')
        height = width * 60 / 600

        layout = QHBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        systemName = QLabel('System')
        systemName.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        systemName.setStyleSheet(f'''
            font-size: {height * 0.4}px;
            margin-left: 10px;
        ''')
        layout.addWidget(systemName, 1)
        self.systemName = systemName

        profileButton = TextButton(program, '-', height * 0.7, 'Profile: Default')
        profileButton.setStyleSheet(f'''
            margin-right: 10px;
            background-color: #ccc;
            font-size: {height // 3}px;
            border: 1px solid black;
            margin-bottom: 5px;
            padding-left: 5px;
            padding-right: 5px;
        ''')
        layout.addWidget(profileButton)
        self.profileButton = profileButton

    def getElement(self, name):
        if name == 'systemName': return self.systemName
        return None
    
    def setSystemName(self, name):
        self.systemName.setText(name)
    
    def setProfile(self, name):
        self.profileButton.setText(f'Profile: {name}')

###############################################################################
# A popup menu
class Menu(QDialog):
    def __init__(self, program, height, parent=None, title="Select Action", actions=None):
        super().__init__(parent)
        self.program = program
        
#        dialog = QDialog(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedWidth(300)
        layout = QVBoxLayout(self)
#        self.dialog = dialog
        self.result = None

        # Add action buttons
        for action in actions:
            button = TextButton(program, action, height, action)
            button.setFCB(self.accept)
            layout.addWidget(button)

    def accept(self, action):
        self.result = action
        # Create a timer and wait for it
        timer = QTimer()
        timer.setSingleShot(True)
        timer.start(300)
        while timer.isActive():
            QApplication.processEvents()
        super().accept()

    def show(self):
        # Show dialog and return result
        if self.exec() == QDialog.Accepted:
            return self.result
        return None

###############################################################################
# A frame widget containing a number of widgets
class WidgetSet(QFrame):
    def __init__(self, widgets, horizontal=True, margins=(5, 5, 5, 5), spacing=5):
        super().__init__()

        # Set frame properties
        self.setFrameStyle(QFrame.Box | QFrame.Plain)
        self.setLineWidth(1)
        
        # Main widget layout
        layout = QHBoxLayout(self) if horizontal else QVBoxLayout(self)
        layout.setContentsMargins(margins[0], margins[1], margins[2], margins[3])
        layout.setSpacing(spacing)

        # Add the widgets
        for widget in widgets: layout.addWidget(widget)

###############################################################################
# A generic Mode widget
class GenericMode(QWidget):
    def __init__(self):
        super().__init__()
        self.styles = {}
    
    def setStyles(self):
        # Set the styles of each widget type in the set.
        # Don't forget that a base style includes all subclasses,
        # so a separate definition must be provided for each subclass type.
        # For example, QLabel is a subclass of QFrame so it needs its own definition
        if not 'QFrame' in self.styles: self.styles['QFrame'] = defaultQFrameStyle()
        if not 'QLabel' in self.styles: self.styles['QLabel'] = defaultQLabelStyle(20)

        stylesheet = '\n'.join(f"{key} {value}" for key, value in self.styles.items())
        # print('Stylesheet:', stylesheet)
        self.setStyleSheet(stylesheet)

    # The left-hand panel, with label and icon
    # This animates when clicked
    class GenericModeLeft(WidgetSet):
        clicked = Signal()

        def __init__(self, widgets, horizontal=True, margins=(5, 5, 5, 5), spacing=10, fcb=None):
            super().__init__(widgets, horizontal, margins, spacing)
            self.fcb = fcb
            self.clicked.connect(lambda: self.animate())
            self.setObjectName('GenericModeLeft')

        # Generate a signal when the widget is clicked
        def mousePressEvent(self, event):
            if event.button() == Qt.LeftButton:
                self.clicked.emit()
            super().mousePressEvent(event)
        
        def moveBack(self):
            try: self.move(self.x() - 2, self.y() - 2)
            except: pass

        def animate(self):
            # Move the widget 2 pixels down and right
            self.move(self.x() + 2, self.y() + 2)
            QTimer.singleShot(200, lambda: self.moveBack())  # Move back after 200ms
            if self.fcb != None: self.fcb()

    # A generic mode label
    class GenericModeLabel(ExpandingLabel):
        def __init__(self, text, height=50):
            super().__init__(text)
            if height != None: self.setFixedHeight(height)
            self.setObjectName('GenericModeLabel')

    # A bordered label
    class BorderedLabel(ExpandingLabel):
        def __init__(self, text):
            super().__init__(text)
            self.setObjectName('BorderedLabel')

    # A generic mode icon
    class GenericModeIcon(GenericIcon):
        def __init__(self, icon, size):
            super().__init__(icon, size)
            self.setObjectName('GenericModeIcon')

    # The right-hand panel
    class GenericModeRight(WidgetSet):
        def __init__(self, widgets, horizontal=True, margins=(0, 0, 0, 0), spacing=5):
            super().__init__(widgets, horizontal, margins, spacing)
            self.setObjectName('GenericModeRight')

    # Create a lwyout and add left and right widgets
    def setupMode(self, left, right):
        mainLayout = QHBoxLayout(self)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.setSpacing(0)
        
        self.styles['QFrame#GenericModeLeft'] = defaultGrayFrameStyle()
        self.styles['QLabel#GenericModeLabel'] = borderlessQLabelStyle(20)
        self.styles['QLabel#BorderedLabel'] = defaultQLabelStyle(20)
        self.styles['QLabel#GenericModeIcon'] = borderlessIconStyle()
        self.styles['QFrame#GenericModeRight'] = invisibleQFrameStyle()

        content = WidgetSet((left, right), horizontal=True)
        content.setFixedSize(500, 150)
        mainLayout.addWidget(content)

        self.setStyles()

###############################################################################
# The Timed Mode widget
class TimedMode(GenericMode):

    # The advance button
    class AdvanceButton(TextButton):
        def __init__(self, program, text, fcb):
            super().__init__(program, text, 70, text)
            self.setFixedHeight(136)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.setFCB(self.onFCB)
            self.fcb = fcb

        def onFCB(self, name):
            self.fcb()

    # The icon on the right panel
    class EditIcon(IconButton):
        def __init__(self, program, icon, fcb=None):
            super().__init__(program, height=None, icon=icon)
            self.setFixedHeight(136)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.setStyleSheet('''
                background-color: #ccc;
                border: 1px solid #888;
                border-radius: 10px;
            ''')
            self.setIconSize(QSize(50, 50))

    # The main class for the widget
    def __init__(self, program, parent):
        super().__init__()
        self.program = program
        self.parent = parent

        # Do the left-hand panel, with a label and an icon
        top = self.GenericModeLabel('Timed')
        top.setFixedHeight(40)
        bottom = self.GenericModeIcon('/home/graham/dev/rbr/ui/main/timed.png', 50)
        bottom.setFixedHeight(70)

        # Create the left panel
        left = self.GenericModeLeft((top, bottom), horizontal=False, fcb=parent.timedModeSelected)
        left.setFixedWidth(150)

        # Do the right-hand panel
        panel = QWidget()
        panel.setStyleSheet('background: transparent;')
        gridLayout = QGridLayout(panel)
        gridLayout.setSpacing(5)
        gridLayout.setContentsMargins(0,0,0,0)
        
        # Create the content
        advance = self.AdvanceButton(program, 'Advance', self.advance)
        self.styles['QLabel#EditIcon'] = defaultIconStyle()
        edit = self.EditIcon(program, '/home/graham/dev/rbr/ui/main/edit.png')
        edit.setFCB(self.advance)
        
        # Add buttons to grid
        gridLayout.addWidget(advance, 0, 0)
        gridLayout.addWidget(edit, 0, 1)

        right = self.GenericModeRight([panel], horizontal=False)

        self.setupMode(left, right)
    
    def advance(self, _):
        self.parent.advanceSelected()

###############################################################################
# The Boost Mode widget
class BoostMode(GenericMode):

    # A generic boost button
    class BoostButton(TextButton):
        def __init__(self, program, text, fcb):
            super().__init__(program, text, 65, text)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.setFCB(self.onFCB)
            self.fcb = fcb

        def onFCB(self, name):
            self.fcb()

    # The main class for the widget
    def __init__(self, program, parent):
        super().__init__()
        self.program = program
        self.parent = parent

        # Do the left-hand panel, with a label and an icon
        top = self.GenericModeLabel('Boost')
        top.setFixedHeight(40)
        bottom = self.GenericModeIcon('/home/graham/dev/rbr/ui/main/boost.png', 50)
        bottom.setFixedHeight(70)

        # Create the left panel
        left = self.GenericModeLeft((top, bottom), horizontal=False, fcb=parent.boostModeSelected)
        left.setFixedWidth(150)

        # Do the right-hand panel
        panel = QWidget()
        panel.setStyleSheet('background: transparent;')
        gridLayout = QGridLayout(panel)
        gridLayout.setSpacing(5)
        gridLayout.setContentsMargins(0,0,0,0)
        
        # Create 4 boost buttons in a 2x2 grid
        boostOff = self.BoostButton(program, "Off", self.boostOff)
        boost30 = self.BoostButton(program, "30 min", self.boost30)
        boost60 = self.BoostButton(program, "1 hour", self.boost60)
        boost120 = self.BoostButton(program, "2 hours", self.boost120)
        
        # Add buttons to grid
        gridLayout.addWidget(boostOff, 0, 0)
        gridLayout.addWidget(boost30, 0, 1)
        gridLayout.addWidget(boost60, 1, 0)
        gridLayout.addWidget(boost120, 1, 1)

        right = self.GenericModeRight([panel], horizontal=False)

        self.setupMode(left, right)

    def boostOff(self, _):
        self.parent.boostOffSelected()

    def boost30(self, _):
        self.parent.boost30Selected()

    def boost60(self, _):
        self.parent.boost60Selected()

    def boost120(self, _):
        self.parent.boost120Selected()

###############################################################################
# The On Mode widget
class OnMode(GenericMode):

    # The plus/minus buttons
    class PlusMinusButton(IconButton):
        def __init__(self, program, icon, fcb=None):
            super().__init__(program, height=None, icon=icon)
            self.setFixedHeight(136)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.setStyleSheet('''
                background-color: #ccc;
                border: 1px solid #888;
                border-radius: 10px;
            ''')
            self.setIconSize(QSize(50, 50))

    # The 'setting' label
    class SettingLabel(ExpandingLabel):
        def __init__(self, text):
            super().__init__(text)
            self.setObjectName('SettingLabel')

    # The main class for the widget
    def __init__(self, program, parent):
        super().__init__()
        self.program = program
        self.parent = parent

        # Do the left-hand panel, with a label and an icon
        top = self.GenericModeLabel('On')
        top.setFixedHeight(40)
        bottom = self.GenericModeIcon('/home/graham/dev/rbr/ui/main/on.png', 50)
        bottom.setFixedHeight(70)

        # Create the left panel
        left = self.GenericModeLeft((top, bottom), horizontal=False, fcb=parent.onModeSelected)
        left.setFixedWidth(150)

        # Do the right-hand panel
        panel = QWidget()
        panel.setStyleSheet('background: transparent;')
        gridLayout = QGridLayout(panel)
        gridLayout.setSpacing(0)
        gridLayout.setContentsMargins(0,0,0,0)
        
        # Create the buttons and text
        upButton = self.PlusMinusButton(program, '/home/graham/dev/rbr/ui/main/blueminus.png')
        self.styles['QLabel#SettingLabel'] = borderlessQLabelStyle(20)
        self.settingLabel = self.SettingLabel('0.0°C')
        downButton = self.PlusMinusButton(program, '/home/graham/dev/rbr/ui/main/redplus.png')
        
        # Add buttons to grid
        gridLayout.addWidget(upButton, 0, 0)
        gridLayout.addWidget(self.settingLabel, 0, 1)
        gridLayout.addWidget(downButton, 0, 2)

        right = self.GenericModeRight([panel], horizontal=False)

        self.setupMode(left, right)
    
    def getSettinglabel(self):
        return self.settingLabel

###############################################################################
# The Off Mode widget
class OffMode(GenericMode):

    # The main class for the widget
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        # Do the left-hand panel, with a label and an icon
        top = self.GenericModeLabel('Off')
        top.setFixedHeight(40)
        bottom = self.GenericModeIcon('/home/graham/dev/rbr/ui/main/off.png', 50)
        bottom.setFixedHeight(70)

        # Create the left panel
        left = self.GenericModeLeft((top, bottom), horizontal=False, fcb=parent.offModeSelected)
        left.setFixedWidth(150)

        # Do the right-hand panel
        right = self.BorderedLabel('Permanently\nOff')

        self.setupMode(left, right)

###############################################################################
# The Operating Mode dialog
class ModeDialog(QDialog):
    def __init__(self, program):
        super().__init__(program.parent.program.rbrwin)

        self.program = program
        self.setStyleSheet('''
            background-color: white;
        ''')
        
        self.setWindowTitle('Operating mode')
        self.setModal(True)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        self.result = None

        # Add modes
        modes = []
        mode = TimedMode(program, self)
        modes.append(mode)
        layout.addWidget(mode)
        mode = BoostMode(program, self)
        modes.append(mode)
        layout.addWidget(mode)
        mode = OnMode(program, self)
        modes.append(mode)
        layout.addWidget(mode)
        mode = OffMode(self)
        modes.append(mode)
        layout.addWidget(mode)

        # Add Cancel button
        cancelButton = TextButton(program, 'Cancel', 40, 'Cancel')
        cancelButton.setFCB(self.reject)
        layout.addWidget(cancelButton)
    
    def timedModeSelected(self):
        self.accept('timed')
    
    def boostModeSelected(self):
        self.accept('boost')
    
    def onModeSelected(self):
        self.accept('on')
    
    def offModeSelected(self):
        self.accept('off')
    
    def advanceSelected(self):
        self.accept('advance')
    
    def editSelected(self):
        self.accept('edit')
    
    def boostOffSelected(self):
        self.accept('boost off')
    
    def boost30Selected(self):
        self.accept('boost 30')
    
    def boost60Selected(self):
        self.accept('boost 60')
    
    def boost120Selected(self):
        self.accept('boost 120')

    def accept(self, result):
        self.result = result
        # Create a timer and wait for it
        timer = QTimer()
        timer.setSingleShot(True)
        timer.start(300)  # 300ms delay
        while timer.isActive():
            QApplication.processEvents()
        super().accept()
    
    def reject(self, value):
        super().reject()

    def show(self):
        # Show dialog and return result
        if self.exec() == QDialog.Accepted:
            return self.result
        return None

###############################################################################
# The keyboard
class Keyboard(QDialog):
    def __init__(self, program, receiver, parent=None):
        super().__init__(parent)
        self.program = program
        
        self.setWindowTitle('')
        self.setModal(True)
        self.setFixedSize(500, 250)
        self.setStyleSheet("background-color: #ccc;")
        layout = QVBoxLayout(self)
        self.result = None

        # Add the keyboard
        layout.addWidget(VirtualKeyboard(42, receiver, self.onFinished))
        
        # Position at bottom of parent window
        if parent:
            y = parent.y() + parent.height - 42
            self.move(0, y)

        self.exec()
    
    def onFinished(self):
        self.reject()

###############################################################################
# The RBR Main Window
class RBRWindow(QMainWindow):
    def __init__(self, program, title, x, y, w, h):
        super().__init__()
        self.program = program
        self.setWindowTitle(title)
        self.setGeometry(x, y, w, h)
        self.width = w
        self.height = h

        if title == '': self.setWindowFlags(Qt.borderlessWindowHint)

        # Set the background image
        palette = QPalette()
        background_pixmap = QPixmap('/home/graham/dev/rbr/ui/main/backdrop.jpg')
        palette.setBrush(QPalette.Window, QBrush(background_pixmap))
        self.setPalette(palette)

        # Panel for the main components
        content = QWidget()
        content.setStyleSheet('''
            background-color: #fff;
            margin:0;
        ''')
        contentLayout = QVBoxLayout(content)
        contentLayout.setSpacing(0)
        self.contentLayout = contentLayout
        self.content = content

        self.initContent()

        # Main layout
        mainWidget = QWidget()
        mainLayout = QVBoxLayout(mainWidget)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.addWidget(content)
        mainLayout.addStretch(1)

        self.setCentralWidget(mainWidget)

    def initContent(self):
        # Add the main banner
        banner = Banner(self.program, self.width)
        self.contentLayout.addWidget(banner)
        self.banner = banner

        # Add the system name and Profiles button
        profiles = Profiles(self.program, self.width)
        self.contentLayout.addWidget(profiles)
        self.profiles = profiles

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
        self.contentLayout.addWidget(panel)
        self.rooms = roomsLayout
    
    def getElement(self, name):
        if name == 'banner': return self.banner
        elif name == 'profiles': return self.profiles
        elif name == 'rooms': return self.rooms
        else: return None
