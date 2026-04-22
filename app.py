import sys
import os
import time
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QSystemTrayIcon, QMenu
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import Qt, QUrl, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtWebChannel import QWebChannel
import pystray
from PIL import Image, ImageDraw
import threading


def create_icon_image():
    size = 64
    image = Image.new('RGB', (size, size), color='white')
    draw = ImageDraw.Draw(image)
    margin = 10
    draw.ellipse([margin, margin, size-margin, size-margin],
                 fill='#1e88e5', outline='#1e88e5')
    draw.text((size//2 - 10, size//2 - 8), 'K', fill='white')
    return image


class KayaApp(QMainWindow):
    def __init__(self, analyzer):
        super().__init__()
        self.analyzer = analyzer
        self.setWindowTitle("Kaya Health Monitor")
        self.setGeometry(100, 100, 500, 850)
        self.setMinimumSize(450, 800)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #0f1117;
                border: none;
            }
            QWidget {
                background-color: #0f1117;
                color: #dde1ea;
            }
        """)

        central_widget = QWidget()
        central_widget.setStyleSheet("background-color: #0f1117;")
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.web_view = QWebEngineView()
        self.web_view.setStyleSheet("background-color: #0f1117;")
        layout.addWidget(self.web_view)

        static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
        dashboard_path = os.path.join(static_dir, "index.html")

        if os.path.exists(dashboard_path):
            self.web_view.load(QUrl.fromLocalFile(os.path.abspath(dashboard_path)))
        else:
            self.web_view.load(QUrl("http://localhost:9876/"))

        self.channel = QWebChannel()
        self.web_view.page().setWebChannel(self.channel)

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(self._create_icon()))

        tray_menu = QMenu()
        show_action = tray_menu.addAction("Show Dashboard")
        show_action.triggered.connect(self.show_dashboard)

        reset_action = tray_menu.addAction("Reset")
        reset_action.triggered.connect(self.reset_analyzer)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

        self.tray_icon.activated.connect(self._on_tray_activated)

        self._hidden = True

    def _create_icon(self):
        image = create_icon_image()
        image_path = os.path.join(os.path.expanduser("~/.kaya"), "icon.png")
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        image.save(image_path)
        return QIcon(image_path)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
                self._hidden = True
            else:
                self.show_dashboard()

    def show_dashboard(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self._hidden = False

    def reset_analyzer(self):
        self.analyzer.reset()

    def quit_app(self):
        self.tray_icon.hide()
        sys.exit(0)

    def closeEvent(self, event):
        if self.tray_icon.isVisible():
            self.hide()
            self._hidden = True
            event.ignore()
        else:
            event.accept()
