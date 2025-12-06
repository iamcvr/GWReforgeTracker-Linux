# main.py
import sys
import argparse
import logging
from PySide6.QtWidgets import QApplication, QMessageBox
from config import AppConfig
from ui.main_window import GuildWarsTracker
import os

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description=AppConfig.APP_TITLE)
    parser.add_argument("--profile", type=str, help="Name of the profile to load on startup")
    parser.add_argument("--auto-close", action="store_true", help="Close application when Guild Wars exits")
    args = parser.parse_args()

    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    try:
        tracker_window = GuildWarsTracker(profile_name=args.profile, auto_close=args.auto_close)
        tracker_window.show()
        sys.exit(app.exec())
    except Exception as e:
        logging.critical(f"Application Crash: {e}", exc_info=True)
        if not QApplication.instance():
            app = QApplication(sys.argv)
        QMessageBox.critical(None, "Fatal Error", f"The application encountered a critical error and must close.\n\nError: {str(e)}")
        sys.exit(1)