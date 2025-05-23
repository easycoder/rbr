import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QPushButton,
    QFrame,
    QHBoxLayout,
    QVBoxLayout
)
from PySide6.QtGui import QIcon, QPixmap, QFont, QPalette, QBrush
from PySide6.QtCore import Qt, QTimer, QSize, Signal

class TextButton(QPushButton):
    def __init__(self, height, text):
        super().__init__()
        self.onClick = self.nothing
        self.clicked.connect(lambda: self.animate_button(self.onClick, text))

        self.setFixedHeight(height)
        self.setStyleSheet(f"""
            QPushButton {{
                padding: 5px;
                background-color: #ccc;
                border:1px solid black;
                border-radius:{height // 5}px;
            }}
        """)

        self.setText(text)

    def nothing(self, text):
        print('Click',text)
        pass
    
    def setOnClick(self, onClick):
        self.onClick = onClick

    def animate_button(self, onClick, text):
        # Move the button 2 pixels down and right
        self.move(self.x() + 2, self.y() + 2)
        QTimer.singleShot(200, lambda: self.move(self.x() - 2, self.y() - 2))  # Move back after 200ms
        onClick(text)

class IconButton(QPushButton):
    def __init__(self, height, text, icon):
        super().__init__()
        self.onClick = self.nothing
        self.clicked.connect(lambda: self.animate_button(self.onClick, text))

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

    def nothing(self, text):
        print('Click',text)
        pass
    
    def setOnClick(self, onClick):
        self.onClick = onClick

    def animate_button(self, onClick, text):
        # Move the button 2 pixels down and right
        self.move(self.x() + 2, self.y() + 2)
        QTimer.singleShot(200, lambda: self.move(self.x() - 2, self.y() - 2))  # Move back after 200ms
        onClick(text)

class IconAndWidgetButton(QWidget):
    clicked = Signal()

    def __init__(self, height, widthFactor, text, image, widget):
        super().__init__()

        self.setStyleSheet("""
            background-color: transparent;
            border: none;
        """)

        self.onClick = self.nothing
        self.clicked.connect(lambda: self.animate_button(self.onClick, text))

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

    def nothing(self, text):
        print('Click',text)
        pass
    
    def setOnClick(self, onClick):
        self.onClick = onClick

    def animate_button(self, onClick, text):
        # Move the button 2 pixels down and right
        self.move(self.x() + 2, self.y() + 2)
        QTimer.singleShot(200, lambda: self.move(self.x() - 2, self.y() - 2))  # Move back after 200ms
        onClick(text)

###############################################################################
# A row of room information
class Room(QFrame):

    def __init__(self, name, mode, height):
        super().__init__()
        self.name = name
        self.mode = mode

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
        modeButton = IconAndWidgetButton(height * 0.8, 2.5, mode, icon, label)

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
        button = QPushButton("20.0°C")
        button.setStyleSheet("color: white; background-color: blue; border: none;")
        button.setFixedSize(height * 1.2, height * 0.6)  # Adjust button size
        button.setFont(font)  # Use the same font as the label

        # Icon 2: Edit
        editButton = IconButton(height * 3 // 4, 'edit', '/home/graham/dev/rbr/ui/main/edit.png')

        # Add elements to the row layout
        modePanelLayout.addWidget(modeButton)
        roomsLayout.addWidget(nameLabel, 1)  # Expand the name label to use all spare space
        roomsLayout.addWidget(button)
        roomsLayout.addWidget(editButton)

###############################################################################
# The banner at the top of the window
class Banner(QLabel):
    def __init__(self, width):
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
        homeButton = IconButton(height * 3 // 4, 'home', '/home/graham/dev/rbr/ui/main/RBRLogo.png')
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
        hamburgerButton = IconButton(height * 3 // 4, 'menu', '/home/graham/dev/rbr/ui/main/hamburger.png')
        layout.addWidget(hamburgerButton)

###############################################################################
# The Profiles bar
class Profiles(QWidget):
    def __init__(self, width):
        super().__init__()
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

        profileButton = TextButton(height * 0.7, 'Profile: Default')
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

###############################################################################
# Test code
class MainWindow(QMainWindow):
    def __init__(self, width, height):
        super().__init__()
        self.setWindowTitle("Room List")
        self.setFixedSize(width, height)

        # Set the background image
        palette = QPalette()
        background_pixmap = QPixmap("/home/graham/dev/rbr/ui/main/backdrop.jpg")
        palette.setBrush(QPalette.Window, QBrush(background_pixmap))
        self.setPalette(palette)

        # Panel for rows
        panel = QWidget()
        panel.setStyleSheet('''
            background-color: #fff;
            border-radius: 10px;
            margin:5px;
        ''')
        panelLayout = QVBoxLayout(panel)
        panelLayout.setSpacing(2)
        panelLayout.setContentsMargins(5, 5, 5, 5)

        # Add rows
        panelLayout.addWidget(Room('Room 1', 'timed', 1024/12))
        panelLayout.addWidget(Room('Room 2', 'boost', 1024/12))
        panelLayout.addWidget(Room('Room 3', 'advance', 1024/12))
        panelLayout.addWidget(Room('Room 4', 'on', 1024/12))
        panelLayout.addWidget(Room('Room 5', 'off', 1024/12))

        # Main layout
        mainWidget = QWidget()
        mainLayout = QVBoxLayout(mainWidget)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.addWidget(panel)
        mainLayout.addStretch(1)

        self.setCentralWidget(mainWidget)

if __name__ == "__main__":
    app = QApplication()
    window = MainWindow(600, 1024)
    window.show()
    sys.exit(app.exec())