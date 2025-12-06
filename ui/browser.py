# ui/browser.py
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PySide6.QtGui import QPainterPath, QRegion
from PySide6.QtCore import QRect
import logging

class CustomWebPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, msg, line, source):
        pass

class RoundedWebEngineView(QWebEngineView):
    def resizeEvent(self, event):
        path = QPainterPath()
        rect = QRect(0, 0, self.width(), self.height())
        path.addRoundedRect(rect, 24, 24)
        region = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)
        super().resizeEvent(event)

    def closeEvent(self, event):
        try:
            self.page().profile().clearHttpCache()
            logging.info("WebEngine cache cleared on close.")
        except Exception as e: 
            logging.error(f"Failed to clear WebEngine cache on close: {e}")
        super().closeEvent(event)