from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QSpacerItem,
    QSizePolicy, QGraphicsDropShadowEffect, QStackedWidget
)
from PySide6.QtGui import QFont, QIcon, QColor
from PySide6.QtCore import QTimer

class BasicKeyboardButton(QPushButton):
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

class DefaultKeyboardButton(BasicKeyboardButton):
    def __init__(self, width, text, onClick=None):
        super().__init__(width, width, text, None, onClick)

    def onClick(self, cb):
        self._callback = cb

class SpecialKeyboardButton(BasicKeyboardButton):
    def __init__(self, width, height, icon, onClick=None):
        super().__init__(width, height, None, icon, onClick)

    def onClick(self, cb):
        self._callback = cb

class KeyboardRow(QHBoxLayout):
    def __init__(self, widgets):
        super().__init__()
        for widget in widgets:
            if isinstance(widget, QSpacerItem):
                self.addSpacerItem(widget)
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

class KeyboardTest:
    def __init__(self):
        self.keyboardViews = []
        self.currentView = 0

    def onClickChar(self, keycode):
        print(keycode)

    def onClickShift(self, _=None):
        print('Shift')
        if self.currentView == 0:
            self.keyboard.setCurrentIndex(1)
            self.currentView = 1
        elif self.currentView == 1:
            self.keyboard.setCurrentIndex(0)
            self.currentView = 0

    def onClickSymbols(self, _=None):
        print('Symbols')
        self.keyboard.setCurrentIndex(3)
        self.currentView = 3

    def onClickNumber(self, _=None):
        print('Numbers')
        self.keyboard.setCurrentIndex(2)
        self.currentView = 2

    def onClickBack(self, _=None):
        print('Back')

if __name__ == '__main__':
    app = QApplication([])
    test = KeyboardTest()
    standard_height = int(0.15 * 350)

    # Layout 0
    rowList0 = []
    row1 = [DefaultKeyboardButton(standard_height, c, onClick=test.onClickChar) for c in '1234567890']
    rowList0.append(KeyboardRow(row1))
    row2 = [DefaultKeyboardButton(standard_height, c, onClick=test.onClickChar) for c in 'qwertyuiop']
    rowList0.append(KeyboardRow(row2))
    widgets3 = [QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)]
    widgets3 += [DefaultKeyboardButton(standard_height, c, onClick=test.onClickChar) for c in 'asdfghjkl']
    widgets3.append(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
    rowList0.append(KeyboardRow(widgets3))
    widgets4 = []
    widgets4.append(SpecialKeyboardButton(int(1.5 * standard_height), standard_height, "up.png", onClick=test.onClickShift))
    widgets4.append(QSpacerItem(int(0.05 * standard_height), standard_height, QSizePolicy.Fixed, QSizePolicy.Minimum))
    widgets4 += [DefaultKeyboardButton(standard_height, c, onClick=test.onClickChar) for c in 'zxcvbnm']
    widgets4.append(QSpacerItem(int(0.05 * standard_height), standard_height, QSizePolicy.Fixed, QSizePolicy.Minimum))
    widgets4.append(SpecialKeyboardButton(int(1.5 * standard_height), standard_height, "back.png", onClick=test.onClickBack))
    rowList0.append(KeyboardRow(widgets4))
    view0 = KeyboardView(rowList0)
    test.keyboardViews.append(view0)

    # Layout 1
    rowList1 = []
    row1u = [DefaultKeyboardButton(standard_height, c, onClick=test.onClickChar) for c in '1234567890']
    rowList1.append(KeyboardRow(row1u))
    row2u = [DefaultKeyboardButton(standard_height, c, onClick=test.onClickChar) for c in 'QWERTYUIOP']
    rowList1.append(KeyboardRow(row2u))
    widgets3u = [QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)]
    widgets3u += [DefaultKeyboardButton(standard_height, c, onClick=test.onClickChar) for c in 'ASDFGHJKL']
    widgets3u.append(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
    rowList1.append(KeyboardRow(widgets3u))
    widgets4u = []
    widgets4u.append(SpecialKeyboardButton(int(1.5 * standard_height), standard_height, "up.png", onClick=test.onClickShift))
    widgets4u.append(QSpacerItem(int(0.05 * standard_height), standard_height, QSizePolicy.Fixed, QSizePolicy.Minimum))
    widgets4u += [DefaultKeyboardButton(standard_height, c, onClick=test.onClickChar) for c in 'ZXCVBNM']
    widgets4u.append(QSpacerItem(int(0.05 * standard_height), standard_height, QSizePolicy.Fixed, QSizePolicy.Minimum))
    widgets4u.append(SpecialKeyboardButton(int(1.5 * standard_height), standard_height, "back.png", onClick=test.onClickBack))
    rowList1.append(KeyboardRow(widgets4u))
    view1 = KeyboardView(rowList1)
    test.keyboardViews.append(view1)

    # Layout 2
    rowList2 = []
    row1_2 = [DefaultKeyboardButton(standard_height, c, onClick=test.onClickChar) for c in '1234567890']
    rowList2.append(KeyboardRow(row1_2))
    row2_2 = [DefaultKeyboardButton(standard_height, c, onClick=test.onClickChar) for c in '@#£&_-()=%']
    rowList2.append(KeyboardRow(row2_2))
    widgets3_2 = []
    widgets3_2.append(SpecialKeyboardButton(int(1.5 * standard_height), standard_height, "symbols.png", onClick=test.onClickShift))
    widgets3_2.append(QSpacerItem(int(0.05 * standard_height), standard_height, QSizePolicy.Fixed, QSizePolicy.Minimum))
    chars = list('"*') + ["'"] + list(':/!?+')
    widgets3_2 += [DefaultKeyboardButton(standard_height, c, onClick=test.onClickChar) for c in chars]
    widgets3_2.append(QSpacerItem(int(0.05 * standard_height), standard_height, QSizePolicy.Fixed, QSizePolicy.Minimum))
    widgets3_2.append(SpecialKeyboardButton(int(1.5 * standard_height), standard_height, "back.png", onClick=test.onClickBack))
    rowList2.append(KeyboardRow(widgets3_2))
    view2 = KeyboardView(rowList2)
    test.keyboardViews.append(view2)

    # Layout 3
    rowList3 = []
    row1_3 = [DefaultKeyboardButton(standard_height, c, onClick=test.onClickChar) for c in '$€¥¢©®µ~¿¡']
    rowList3.append(KeyboardRow(row1_3))
    row2_3 = [DefaultKeyboardButton(standard_height, c, onClick=test.onClickChar) for c in '¼½¾[]{}<>^']
    rowList3.append(KeyboardRow(row2_3))
    widgets3_3 = []
    widgets3_3.append(SpecialKeyboardButton(int(1.5 * standard_height), standard_height, "numbers.png", onClick=test.onClickShift))
    widgets3_3.append(QSpacerItem(int(0.05 * standard_height), standard_height, QSizePolicy.Fixed, QSizePolicy.Minimum))
    widgets3_3 += [DefaultKeyboardButton(standard_height, c, onClick=test.onClickChar) for c in '`;÷\\∣|¬±']
    widgets3_3.append(QSpacerItem(int(0.05 * standard_height), standard_height, QSizePolicy.Fixed, QSizePolicy.Minimum))
    widgets3_3.append(SpecialKeyboardButton(int(1.5 * standard_height), standard_height, "back.png", onClick=test.onClickBack))
    rowList3.append(KeyboardRow(widgets3_3))
    view3 = KeyboardView(rowList3)
    test.keyboardViews.append(view3)

    keyboard = Keyboard(test.keyboardViews)
    test.keyboard = keyboard

    window = QWidget()
    window.setWindowTitle("Keyboard Test")
    window.setGeometry(100, 100, 600, 350)
    window.setStyleSheet("background-color: #ccc;")
    layout = QVBoxLayout(window)
    layout.addWidget(keyboard)
    window.setLayout(layout)
    window.show()
    app.exec()