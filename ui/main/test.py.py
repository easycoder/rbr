# ...existing code...

from PySide6.QtWidgets import QSpacerItem

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Room List")
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)

        # Set the background image
        palette = QPalette()
        background_pixmap = QPixmap("backdrop.jpg")
        palette.setBrush(QPalette.Window, QBrush(background_pixmap))
        self.setPalette(palette)

        # Panel for rows
        panel = QWidget()
        panel.setStyleSheet("background-color: #888;")
        panel_height = ROW_COUNT * ROW_HEIGHT + (ROW_COUNT - 1) * ROW_SPACING
        panel.setFixedHeight(panel_height)
        panel.setFixedWidth(WINDOW_WIDTH)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setSpacing(ROW_SPACING)
        panel_layout.setContentsMargins(0, 0, 0, 0)

        # Add rows
        for _ in range(ROW_COUNT):
            row = Row()
            panel_layout.addWidget(row)

        # Main layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Add top spacer
        top_spacer = QWidget()
        top_spacer.setFixedHeight(10)
        top_spacer.setStyleSheet("background-color: #ffffcc; border: none;")
        main_layout.addWidget(top_spacer)

        main_layout.addWidget(panel)

        # Add bottom spacer
        bottom_spacer = QWidget()
        bottom_spacer.setFixedHeight(10)
        bottom_spacer.setStyleSheet("background-color: #ffffcc; border: none;")
        main_layout.addWidget(bottom_spacer)

        main_layout.addStretch(1)  # Reveal background in unused space

        self.setCentralWidget(main_widget)
# ...existing code...