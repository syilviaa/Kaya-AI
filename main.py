#!/usr/bin/env python3
import sys
from PyQt5.QtWidgets import QApplication
from listener import KayaListener
from analyzer import Analyzer
from app import KayaApp
import server


def main():
    print("--- Kaya Health Monitor (Windows) ---")
    analyzer = Analyzer()
    listener = KayaListener(on_event=analyzer.ingest)
    listener.start()
    server.start(analyzer, port=9876)
    qt_app  = QApplication(sys.argv)
    kaya_app = KayaApp(analyzer)
    kaya_app.show_dashboard()
    sys.exit(qt_app.exec_())


if __name__ == "__main__":
    main()
