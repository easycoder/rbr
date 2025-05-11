from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QSpacerItem,
    QSizePolicy, QGraphicsDropShadowEffect, QStackedWidget
)
from PySide6.QtGui import QFont, QIcon, QColor
from PySide6.QtCore import QTimer

class KeyboardButton(QPushButton):
    def __init__(self, width, height, text, icon=None, onClick=None):
        super().__init__()
        self.setFixedSize(width, height)
        self._text = text
        self._icon = icon
        self._callback = onClick

        if text is not None:
            self.setText(text)
        if icon is not None:
            self.setIcon(QIcon(icon))
            self.setIconSize(self.size())

        self.setFont(QFont("Arial", height // 2))
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: white;
                border-radius: {int(height * 0.2)}px;
            }}
            QPushButton:pressed {{
                background-color: #f0f0f0;
            }}
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setOffset(2, 2)
        shadow.setColor(QColor(200, 200, 200))
        self.setGraphicsEffect(shadow)
        self.clicked.connect(self._on_click)

    def _on_click(self):
        self.move(self.x() + 2, self.y() + 2)
        QTimer.singleShot(200, lambda: self.move(self.x() - 2, self.y() - 2))
        if self._callback:
            self._callback(self._text)

    def setText(self, text):
        self._text = text
        super().setText(text)

    def setIcon(self, icon):
        self._icon = icon
        super().setIcon(QIcon(icon))

    def onClick(self, cb):
        self._callback = cb

class KeyboardRow(QHBoxLayout):
    def __init__(self, widgets):
        super().__init__()
        for widget in widgets:
            if isinstance(widget, QSpacerItem):
                self.addSpacerItem(widget)
            elif widget == 'stretch':
                self.addStretch()
            else:
                self.addWidget(widget)

class KeyboardView(QVBoxLayout):
    def __init__(self, rows):
        super().__init__()
        for row in rows:
            self.addLayout(row)

class Keyboard(QStackedWidget):
    def __init__(self, views):
        super().__init__()
        for v in views:
            w = QWidget()
            w.setLayout(v)
            self.addWidget(w)
        self.setCurrentIndex(0)

    def setCurrentIndex(self, v=0):
        super().setCurrentIndex(v)

#-------------------------------------------------------------------------------

def onClickChar(keycode):
    print(keycode)

def onClickShift(keycode=None):
    global currentView
    print('Shift')
    if currentView == 0:
        keyboard.setCurrentIndex(1)
        currentView = 1
    elif currentView == 1:
        keyboard.setCurrentIndex(0)
        currentView = 0

def onClickNumbers(keycode=None):
    global currentView
    print('Numbers')
    keyboard.setCurrentIndex(2)
    currentView = 2

def onClickLetters(keycode=None):
    global currentView
    print('Letters')
    keyboard.setCurrentIndex(3)
    currentView = 3

def onClickBack(keycode=None):
    print('Back')

def onClickSpace(keycode=None):
    print('Space')

def onClickEnter(keycode=None):
    print('Enter')

def onClickSymbols(keycode=None):
    global currentView
    print('Symbols')
    keyboard.setCurrentIndex(3)
    currentView = 3

if __name__ == '__main__':
    app = QApplication([])
    keyboardViews = []
    currentView = 0
    standard_height = int(0.15 * 350)

    # Layout 0
    rowList0 = []
    row1 = [KeyboardButton(standard_height, standard_height, c, None, onClickChar) for c in '1234567890']
    rowList0.append(KeyboardRow(row1))
    row2 = [KeyboardButton(standard_height, standard_height, c, None, onClickChar) for c in 'qwertyuiop']
    rowList0.append(KeyboardRow(row2))
    widgets3 = ['stretch']
    widgets3 += [KeyboardButton(standard_height, standard_height, c, None, onClickChar) for c in 'asdfghjkl']
    widgets3.append('stretch')
    rowList0.append(KeyboardRow(widgets3))
    widgets4 = []
    widgets4.append(KeyboardButton(int(1.5 * standard_height), standard_height, None, "up.png", onClickShift))
    widgets4.append(QSpacerItem(int(0.05 * standard_height), standard_height, QSizePolicy.Fixed, QSizePolicy.Minimum))
    widgets4 += [KeyboardButton(standard_height, standard_height, c, None, onClickChar) for c in 'zxcvbnm']
    widgets4.append(QSpacerItem(int(0.05 * standard_height), standard_height, QSizePolicy.Fixed, QSizePolicy.Minimum))
    widgets4.append(KeyboardButton(int(1.5 * standard_height), standard_height, None, "back.png", onClickBack))
    rowList0.append(KeyboardRow(widgets4))
    widgets5 = []
    widgets5.append(KeyboardButton(int(1.5 * standard_height), standard_height, None, "numbers.png", onClickNumbers))
    widgets5.append(QSpacerItem(int(0.05 * standard_height), standard_height, QSizePolicy.Fixed, QSizePolicy.Minimum))
    widgets5.append(KeyboardButton(standard_height, standard_height, ',', None, onClickChar))
    widgets5.append(KeyboardButton(int(6 * standard_height), standard_height, None, "space.png", onClickSpace))
    widgets5.append(KeyboardButton(standard_height, standard_height, '.', None, onClickChar))
    widgets5.append(QSpacerItem(int(0.05 * standard_height), standard_height, QSizePolicy.Fixed, QSizePolicy.Minimum))
    widgets5.append(KeyboardButton(int(1.5 * standard_height), standard_height, None, "enter.png", onClickEnter))
    rowList0.append(KeyboardRow(widgets5))
    view0 = KeyboardView(rowList0)
    keyboardViews.append(view0)

    # Layout 1
    rowList1 = []
    row1u = [KeyboardButton(standard_height, standard_height, c, None, onClickChar) for c in '1234567890']
    rowList1.append(KeyboardRow(row1u))
    row2u = [KeyboardButton(standard_height, standard_height, c, None, onClickChar) for c in 'QWERTYUIOP']
    rowList1.append(KeyboardRow(row2u))
    widgets3u = ['stretch']
    widgets3u += [KeyboardButton(standard_height, standard_height, c, None, onClickChar) for c in 'ASDFGHJKL']
    widgets3u.append('stretch')
    rowList1.append(KeyboardRow(widgets3u))
    widgets4u = []
    widgets4u.append(KeyboardButton(int(1.5 * standard_height), standard_height, None, "up.png", onClickShift))
    widgets4u.append(QSpacerItem(int(0.05 * standard_height), standard_height, QSizePolicy.Fixed, QSizePolicy.Minimum))
    widgets4u += [KeyboardButton(standard_height, standard_height, c, None, onClickChar) for c in 'ZXCVBNM']
    widgets4u.append(QSpacerItem(int(0.05 * standard_height), standard_height, QSizePolicy.Fixed, QSizePolicy.Minimum))
    widgets4u.append(KeyboardButton(int(1.5 * standard_height), standard_height, None, "back.png", onClickBack))
    rowList1.append(KeyboardRow(widgets4u))
    widgets5u = []
    widgets5u.append(KeyboardButton(int(1.5 * standard_height), standard_height, None, "numbers.png", onClickNumbers))
    widgets5u.append(QSpacerItem(int(0.05 * standard_height), standard_height, QSizePolicy.Fixed, QSizePolicy.Minimum))
    widgets5u.append(KeyboardButton(standard_height, standard_height, ',', None, onClickChar))
    widgets5u.append(KeyboardButton(int(6 * standard_height), standard_height, None, "space.png", onClickSpace))
    widgets5u.append(KeyboardButton(standard_height, standard_height, '.', None, onClickChar))
    widgets5u.append(QSpacerItem(int(0.05 * standard_height), standard_height, QSizePolicy.Fixed, QSizePolicy.Minimum))
    widgets5u.append(KeyboardButton(int(1.5 * standard_height), standard_height, None, "enter.png", onClickEnter))
    rowList1.append(KeyboardRow(widgets5u))
    view1 = KeyboardView(rowList1)
    keyboardViews.append(view1)

    # Layout 2
    rowList2 = []
    row1_2 = [KeyboardButton(standard_height, standard_height, c, None, onClickChar) for c in '1234567890']
    rowList2.append(KeyboardRow(row1_2))
    row2_2 = [KeyboardButton(standard_height, standard_height, c, None, onClickChar) for c in '@#£&_-()=%']
    rowList2.append(KeyboardRow(row2_2))
    widgets3_2 = []
    widgets3_2.append(KeyboardButton(int(1.5 * standard_height), standard_height, None, "symbols.png", onClickSymbols))
    widgets3_2.append(QSpacerItem(int(0.05 * standard_height), standard_height, QSizePolicy.Fixed, QSizePolicy.Minimum))
    chars = list('"*') + ["'"] + list(':/!?+')
    widgets3_2 += [KeyboardButton(standard_height, standard_height, c, None, onClickChar) for c in chars]
    widgets3_2.append(QSpacerItem(int(0.05 * standard_height), standard_height, QSizePolicy.Fixed, QSizePolicy.Minimum))
    widgets3_2.append(KeyboardButton(int(1.5 * standard_height), standard_height, None, "back.png", onClickBack))
    rowList2.append(KeyboardRow(widgets3_2))
    view2 = KeyboardView(rowList2)
    keyboardViews.append(view2)

    # Layout 3
    rowList3 = []
    row1_3 = [KeyboardButton(standard_height, standard_height, c, None, onClickChar) for c in '$€¥¢©®µ~¿¡']
    rowList3.append(KeyboardRow(row1_3))
    row2_3 = [KeyboardButton(standard_height, standard_height, c, None, onClickChar) for c in '¼½¾[]{}<>^']
    rowList3.append(KeyboardRow(row2_3))
    widgets3_3 = []
    widgets3_3.append(KeyboardButton(int(1.5 * standard_height), standard_height, None, "numbers.png", onClickShift))
    widgets3_3.append(QSpacerItem(int(0.05 * standard_height), standard_height, QSizePolicy.Fixed, QSizePolicy.Minimum))
    widgets3_3 += [KeyboardButton(standard_height, standard_height, c, None, onClickChar) for c in '`;÷\\∣|¬±']
    widgets3_3.append(QSpacerItem(int(0.05 * standard_height), standard_height, QSizePolicy.Fixed, QSizePolicy.Minimum))
    widgets3_3.append(KeyboardButton(int(1.5 * standard_height), standard_height, None, "back.png", onClickBack))
    rowList3.append(KeyboardRow(widgets3_3))
    view3 = KeyboardView(rowList3)
    keyboardViews.append(view3)

    keyboard = Keyboard(keyboardViews)

    window = QWidget()
    window.setWindowTitle("Keyboard Test")
    window.setGeometry(100, 100, 600, 350)
    window.setStyleSheet("background-color: #ccc;")
    layout = QVBoxLayout(window)
    layout.addWidget(keyboard)
    window.setLayout(layout)
    window.show()
    app.exec()