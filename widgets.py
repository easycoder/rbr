import sys
from collections import namedtuple
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QPushButton,
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QDialog
)
from PySide6.QtGui import QIcon, QPixmap, QFont, QPalette, QBrush
from PySide6.QtCore import Qt, QTimer, QSize, Signal

Callback = namedtuple('Callback', ['name', 'text'])

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

    def animate_button(self):
        # Move the button 2 pixels down and right
        self.move(self.x() + 2, self.y() + 2)
        QTimer.singleShot(200, lambda: self.move(self.x() - 2, self.y() - 2))  # Move back after 200ms
        if self.onClick != None: self.program.run(self.onClick)
        elif self.fcb != None: self.fcb(self.name)

    def getIndex(self):
        return self.index

class IconButton(QPushButton):
    def __init__(self, program, name, height, text, icon, index=0):
        super().__init__()
        self.program = program
        self.name = name
        self.text = text
        self.index = index
        self.onClick = None
        self.clicked.connect(lambda: self.animate_button())

        self.setFixedSize(height, height)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color #ccc;
                border:none;
                border-radius:{int(height * 0.2)}px;  /* Rounded corners */
            }}
        """)

        self.setIcon(QIcon(icon))
        self.setIconSize(QSize(height * 0.8, height * 0.8))
    
    def setOnClick(self, onClick):
        self.onClick = onClick

    def animate_button(self):
        # Move the button 2 pixels down and right
        self.move(self.x() + 2, self.y() + 2)
        QTimer.singleShot(200, lambda: self.move(self.x() - 2, self.y() - 2))  # Move back after 200ms
        if self.onClick != None: self.program.run(self.onClick)

    def getIndex(self):
        return self.index

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

        # Icon on the left
        label = QLabel()
        label.setFixedSize(height, height)
        label.setAlignment(Qt.AlignVCenter | Qt.AlignHCenter)
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

    def animate_button(self, index):
        self.program.roomIndex = index
        # Move the button 2 pixels down and right
        self.move(self.x() + 2, self.y() + 2)
        QTimer.singleShot(200, lambda: self.move(self.x() - 2, self.y() - 2))  # Move back after 200ms
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

        # Icon 2: Edit
        self.editButton = IconButton(self.program, name, height * 3 // 4, 'edit', '/home/graham/dev/rbr/ui/main/edit.png', index)

        # Add elements to the row layout
        modePanelLayout.addWidget(self.modeButton)
        roomsLayout.addWidget(nameLabel, 1)  # Expand the name label to use all spare space
        roomsLayout.addWidget(temperatureButton)
        roomsLayout.addWidget(self.editButton)
    
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
        homeButton = IconButton(program, '-', height * 3 // 4, 'home', '/home/graham/dev/rbr/ui/main/RBRLogo.png')
        layout.addWidget(homeButton)

        # The title panel
        titlePanel = QWidget()
        titlePanel.setStyleSheet(f'''
        ''')
        titleLayout = QVBoxLayout(titlePanel)
        titleLayout.setSpacing(0)
        titleLayout.setContentsMargins(0, 0, 0, 0)
        title1 = QLabel('Room By Room')
        title1.setAlignment(Qt.AlignVCenter | Qt.AlignHCenter)
        title1.setStyleSheet(f'''
            font-size: {height * 0.6}px;
            margin: 0;
        ''')
        title2 = QLabel('Intelligent heating when and where you need it')
        title2.setAlignment(Qt.AlignVCenter | Qt.AlignHCenter)
        title2.setStyleSheet(f'''
            font-size: {height * 0.18}px;
            margin: 0;
        ''')
        titleLayout.addWidget(title1, 1)
        titleLayout.addWidget(title2, 1)

        layout.addWidget(titlePanel)

        #The Hamburger button
        self.hamburgerButton = IconButton(program, '-', height * 3 // 4, 'menu', '/home/graham/dev/rbr/ui/main/hamburger.png')
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
        
        dialog = QDialog(parent)
        dialog.setWindowTitle(title)
        dialog.setModal(True)
        dialog.setFixedWidth(300)
        layout = QVBoxLayout(dialog)
        self.dialog = dialog
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
        timer.start(500)  # 500ms delay
        while timer.isActive():
            QApplication.processEvents()
        self.dialog.accept()

    def show(self):
        # Show dialog and return result
        if self.dialog.exec() == QDialog.Accepted:
            return self.result
        return None

###############################################################################
# The Timed Mode widget
class TimedMode(QWidget):
    def __init__(self, program):
        super().__init__()
        self.program = program
        height = 200

        self.setStyleSheet("""
            background-color: transparent;
            border: none;
        """)

        mainLayout = QHBoxLayout(self)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.setSpacing(0)

        # Icon on the left
        label = QLabel()
        label.setFixedSize(height, height)
        label.setAlignment(Qt.AlignVCenter | Qt.AlignHCenter)
        pixmap = QPixmap('/home/graham/dev/rbr/ui/main/timed.png').scaled(height * 0.75, height * 0.75)
        label.setPixmap(pixmap)
        mainLayout.addWidget(label)

        # Widget on the right
        mainLayout.addWidget(QLabel('Dummy'))

###############################################################################
# The Operating Mode dialog
class Mode(QDialog):
    def __init__(self, program, parent=None, roomName="Unknown"):
        super().__init__(parent)

        self.setStyleSheet("""
            background-color: transparent;
            border: none;
            padding: 10px;
        """)

        self.program = program
        
        dialog = QDialog(parent)
        dialog.setWindowTitle('Operating mode')
        dialog.setModal(True)
        dialog.setFixedWidth(440)
        layout = QVBoxLayout(dialog)
        self.dialog = dialog
        self.result = None

        # Add modes
        self.timedMode = TimedMode(program)
        layout.addWidget(self.timedMode)

    def accept(self, action):
        self.result = action
        # Create a timer and wait for it
        timer = QTimer()
        timer.setSingleShot(True)
        timer.start(500)  # 500ms delay
        while timer.isActive():
            QApplication.processEvents()
        self.dialog.accept()

    def show(self):
        # Show dialog and return result
        if self.dialog.exec() == QDialog.Accepted:
            return self.result
        return None

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

        # Set the background image
        palette = QPalette()
        background_pixmap = QPixmap("/home/graham/dev/rbr/ui/main/backdrop.jpg")
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
