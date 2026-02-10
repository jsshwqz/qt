#!/usr/bin/env python3
import sys
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Window Test - PyQt5 GUI')
        self.setGeometry(200, 200, 600, 400)
        self.setStyleSheet('background-color: #2E7D32; color: white; font-size: 24px;')
        
        layout = QVBoxLayout(self)
        
        label = QLabel('If you see this window, PyQt5 GUI works!')
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet('color: white; font-weight: bold;')
        layout.addWidget(label)
        
        self.setLayout(layout)

def main():
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
