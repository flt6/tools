from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QTabWidget, QVBoxLayout, QWidget,QGraphicsDropShadowEffect,QLabel
from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtGui import QPainter, QBrush, QColor, QMouseEvent, QCursor,QPixmap
import sys
import json
import os

class CircularButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(100, 100)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("""
            CircularButton {
                background-color: rgba(1, 160, 196, 50);
                border-radius: 50px;
            }
            QLabel{
                color: rgba(255, 255, 255, 100);
                font-size: 30px;
                font-weight: bold;
                text-align: center;
                margin-top: 30px;
                margin-bottom: 30px;
            }
        """)
        self.text=QLabel(self)
        self.text.setText("教材")
        self.text.setAlignment(Qt.AlignCenter)
        self.text.setGeometry(0, 0, 100, 100)
        self.setToolTip("Click to open the main interface")
        self.dragging = False
        self.drag_position = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor(0, 0, 0, 128)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, self.width(), self.height())
        super().paintEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.pos()
            QTimer.singleShot(200, self.check_drag)  # Check for dragging after a short delay
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_position:
            self.dragging = True
            self.move(self.mapToParent(event.pos() - self.drag_position))

    def mouseReleaseEvent(self, event):
        if self.dragging:
            self.dragging = False
        else:
            self.hide()
            self.parent().show_rounded_interface(self)
        self.drag_position = None
        super().mouseReleaseEvent(event)

    def check_drag(self):
        if self.drag_position:
            distance = (self.drag_position - QCursor.pos()).manhattanLength()
            if distance > 5:
                self.dragging = True

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setGeometry(300, 300, 300, 550)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.circular_button = CircularButton(self)
        self.circular_button.move(250, 150)
        self.circular_button.show()

        self.rounded_widget = RoundedWidget(self)
        self.rounded_widget.hide()

    def show_rounded_interface(self, circular_button):
        # Move the main window near the circular button
        button_pos = circular_button.mapToGlobal(QPoint(0, 0))
        old = self.geometry().getRect()
        self.setGeometry(button_pos.x() - 250, button_pos.y() - 150, old[2], old[3])
        self.rounded_widget.show()

    def hide_rounded_interface(self):
        self.rounded_widget.hide()
        self.circular_button.show()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.LeftButton:
            self.move(self.pos() + event.globalPosition().toPoint() - self.drag_position)
            self.drag_position = event.globalPosition().toPoint()
            event.accept()

class RoundedWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setGeometry(50, 50, 200, 450)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("""
            QPushButton{
                background-color: rgba(200, 200, 200, 180);
                border-radius: 20px;
            }
        """)
        
        self.shadow_effect = QGraphicsDropShadowEffect(self)
        self.shadow_effect.setBlurRadius(20)
        self.shadow_effect.setOffset(0, 0)
        self.shadow_effect.setColor(QColor(0, 0, 0, 160))
        self.setGraphicsEffect(self.shadow_effect)

        self.layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget()
        self.layout.addWidget(self.tab_widget)

        self.close_button = QPushButton("Close", self)
        self.close_button.setStyleSheet("font-size: 16px; padding: 10px;")
        self.close_button.clicked.connect(self.close)
        self.layout.addWidget(self.close_button)
        
        self.close_program_button = QPushButton("Exit Program", self)
        self.close_program_button.setStyleSheet("font-size: 16px; padding: 10px;")
        self.close_program_button.clicked.connect(self.close_program)
        self.layout.addWidget(self.close_program_button)

        self.config = self.load_config()
        self.create_tabs()

    def load_config(self):
        with open('config.json', 'r', encoding='utf-8') as file:
            return json.load(file)

    def create_tabs(self):
        for subject, files in self.config.items():
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            for title, path in files.items():
                button = QPushButton(title)
                button.setStyleSheet("font-size: 16px; padding: 10px;")
                button.clicked.connect(self.create_button_handler(path))
                tab_layout.addWidget(button)
            self.tab_widget.addTab(tab, subject)

    def create_button_handler(self, path):
        return lambda: self.open_file(path)

    def open_file(self, path):
        os.startfile(path)

    def close(self):
        self.parent().hide_rounded_interface()
    
    def close_program(self):
        QApplication.instance().quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
