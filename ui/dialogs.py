# ui/dialogs.py
from PySide6.QtWidgets import QDialog, QVBoxLayout, QFrame, QLabel, QHBoxLayout, QPushButton, QLineEdit
from PySide6.QtCore import Qt
from config import ThemeColors

class CustomDialog(QDialog):
    def __init__(self, title, message, parent=None, is_confirmation=True, show_input=False):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{ background-color: #2b2b30; border: 1px solid #444; border-radius: 16px; }}
        """)
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(25, 25, 25, 25)
        c_layout.setSpacing(15)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {ThemeColors.GOLD}; border: none;")
        c_layout.addWidget(title_label)
        
        if message:
            msg_label = QLabel(message)
            msg_label.setWordWrap(True)
            msg_label.setStyleSheet(f"color: {ThemeColors.WHITE}; font-size: 14px; border: none; margin-bottom: 5px;")
            c_layout.addWidget(msg_label)
        
        self.input_field = None
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        if is_confirmation or show_input:
            self.reject_btn = QPushButton("No" if not show_input else "Cancel")
            self.reject_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.reject_btn.setStyleSheet(f"""
                QPushButton {{ background-color: rgba(76, 175, 80, 0.15); color: {ThemeColors.GREEN}; border: 1px solid {ThemeColors.GREEN}; border-radius: 12px; padding: 8px 20px; font-weight: 600; }}
                QPushButton:hover {{ background-color: rgba(76, 175, 80, 0.25); }}
            """)
            self.reject_btn.clicked.connect(self.reject)
            btn_layout.addWidget(self.reject_btn)
        
        self.accept_btn = QPushButton("Yes" if is_confirmation and not show_input else ("Create" if show_input else "OK"))
        self.accept_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.accept_btn.clicked.connect(self.accept)
        
        if show_input:
            self.input_field = QLineEdit()
            self.input_field.setPlaceholderText("Enter name...")
            self.input_field.setStyleSheet(f"""
                QLineEdit {{ background-color: rgba(0, 0, 0, 0.4); border: 1px solid #555; border-radius: 8px; padding: 8px; color: #fff; font-size: 14px; }}
                QLineEdit:focus {{ border: 1px solid {ThemeColors.GOLD}; }}
            """)
            self.input_field.textChanged.connect(self.validate_input)
            self.input_field.returnPressed.connect(self.on_return_pressed)
            c_layout.addWidget(self.input_field)
        
        if is_confirmation and not show_input:
             btn_style = f"""
                QPushButton {{ background-color: rgba(255, 107, 107, 0.15); color: {ThemeColors.RED}; border: 1px solid {ThemeColors.RED}; border-radius: 12px; padding: 8px 20px; font-weight: 600; }}
                QPushButton:hover {{ background-color: rgba(255, 107, 107, 0.25); }}
             """
        else:
             btn_style = f"""
                QPushButton {{ background-color: rgba(212, 175, 55, 0.15); color: {ThemeColors.GOLD}; border: 1px solid {ThemeColors.GOLD}; border-radius: 12px; padding: 8px 20px; font-weight: 600; }}
                QPushButton:hover {{ background-color: rgba(212, 175, 55, 0.25); }}
             """
        
        self.accept_btn.setStyleSheet(btn_style)
        if show_input:
            self.accept_btn.setEnabled(False)
            self.accept_btn.setStyleSheet("""
                QPushButton { background-color: rgba(100, 100, 100, 0.15); color: #888; border: 1px solid #555; border-radius: 12px; padding: 8px 20px; font-weight: 600; }
            """)
            
        btn_layout.addWidget(self.accept_btn)
        c_layout.addLayout(btn_layout)
        layout.addWidget(container)
    
    def validate_input(self, text):
        if self.input_field:
            has_text = len(text.strip()) > 0
            self.accept_btn.setEnabled(has_text)
            if has_text:
                self.accept_btn.setStyleSheet(f"""
                QPushButton {{ background-color: rgba(212, 175, 55, 0.15); color: {ThemeColors.GOLD}; border: 1px solid {ThemeColors.GOLD}; border-radius: 12px; padding: 8px 20px; font-weight: 600; }}
                QPushButton:hover {{ background-color: rgba(212, 175, 55, 0.25); }}
                """)
            else:
                self.accept_btn.setStyleSheet("""
                QPushButton { background-color: rgba(100, 100, 100, 0.15); color: #888; border: 1px solid #555; border-radius: 12px; padding: 8px 20px; font-weight: 600; }
                """)

    def on_return_pressed(self):
        if self.accept_btn.isEnabled(): self.accept()

    def get_input_text(self):
        return self.input_field.text() if self.input_field else ""