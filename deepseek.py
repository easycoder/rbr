import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, 
                              QVBoxLayout, QPushButton, QFrame, QLabel)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QColor

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Set window size and title
        self.setWindowTitle("Deepseek")
        self.setFixedSize(600, 1024)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create background label with image
        self.background = QLabel(central_widget)
        self.background.setPixmap(QPixmap("ui/main/backdrop.jpg").scaled(
            self.width(), self.height(), 
            Qt.AspectRatioMode.IgnoreAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        ))
        self.background.setGeometry(0, 0, self.width(), self.height())
        
        # Create a yellow panel (frame)
        yellow_panel = QFrame(central_widget)
        yellow_panel.setStyleSheet("""
            background-color: yellow;
            border-radius: 10px;
        """)
        yellow_panel.setFixedSize(200, 200)
        
        # Center the yellow panel in the window
        yellow_panel.move(
            (self.width() - yellow_panel.width()) // 2,
            (self.height() - yellow_panel.height()) // 2
        )
        
        # Create a layout for the buttons inside the yellow panel
        button_layout = QVBoxLayout(yellow_panel)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        button_layout.setSpacing(10)
        
        # Create three blue buttons
        button1 = QPushButton("One")
        button2 = QPushButton("Two")
        button3 = QPushButton("Three")
        
        # Style the buttons with blue background
        button_style = """
            QPushButton {
                background-color: blue;
                color: white;
                border: none;
                padding: 8px;
                min-width: 60px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0000cc;
            }
        """
        
        button1.setStyleSheet(button_style)
        button2.setStyleSheet(button_style)
        button3.setStyleSheet(button_style)
        
        # Add buttons to the layout
        button_layout.addWidget(button1)
        button_layout.addWidget(button2)
        button_layout.addWidget(button3)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Verify the backdrop image exists
    try:
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"Error loading background image: {e}")
        sys.exit(1)