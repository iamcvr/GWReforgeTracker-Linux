# ui/dialogs.py
import re
from PySide6.QtWidgets import QDialog, QVBoxLayout, QFrame, QLabel, QHBoxLayout, QPushButton, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView
from PySide6.QtCore import Qt, QTimer
from config import ThemeColors, AppConfig

class CustomDialog(QDialog):
    def __init__(self, title, message, parent=None, is_confirmation=True, show_input=False):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        container = QFrame()
        container.setStyleSheet(f"QFrame {{ background-color: #2b2b30; border: 1px solid #444; border-radius: 16px; }}")
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
        self.error_label = None
        
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
            self.input_field.setPlaceholderText("Enter profile name...")
            self.input_field.setMaxLength(AppConfig.MAX_PROFILE_NAME_LEN)
            self.input_field.setStyleSheet(f"QLineEdit {{ background-color: rgba(0, 0, 0, 0.4); border: 1px solid #555; border-radius: 8px; padding: 8px; color: #fff; font-size: 14px; }} QLineEdit:focus {{ border: 2px solid {ThemeColors.GOLD}; }}")
            self.input_field.textChanged.connect(self.validate_input)
            self.input_field.returnPressed.connect(self.on_return_pressed)
            c_layout.addWidget(self.input_field)
            
            self.error_label = QLabel("")
            self.error_label.setStyleSheet(f"color: {ThemeColors.RED}; font-size: 11px; border: none;")
            self.error_label.setVisible(False)
            c_layout.addWidget(self.error_label)
        
        btn_style = f"""
            QPushButton {{ background-color: rgba(212, 175, 55, 0.15); color: {ThemeColors.GOLD}; border: 1px solid {ThemeColors.GOLD}; border-radius: 12px; padding: 8px 20px; font-weight: 600; }}
            QPushButton:hover {{ background-color: rgba(212, 175, 55, 0.25); }}
        """
        if is_confirmation and not show_input:
             btn_style = btn_style.replace(ThemeColors.GOLD, ThemeColors.RED).replace("212, 175, 55", "255, 107, 107")
        
        self.accept_btn.setStyleSheet(btn_style)
        if show_input: self.accept_btn.setEnabled(False)
            
        btn_layout.addWidget(self.accept_btn)
        c_layout.addLayout(btn_layout)
        layout.addWidget(container)
        QTimer.singleShot(0, self._set_initial_focus)

    def _set_initial_focus(self):
        if self.input_field: self.input_field.setFocus()
        else: self.accept_btn.setFocus()
    
    def validate_input(self, text):
        if self.input_field:
            text = text.strip()
            is_valid_chars = bool(re.match(r'^[a-zA-Z0-9 _-]+$', text)) if text else False
            is_valid_len = 0 < len(text) <= AppConfig.MAX_PROFILE_NAME_LEN
            
            error_msg = ""
            if len(text) > 0 and not is_valid_chars: error_msg = "Invalid characters. Use A-Z, 0-9, space, '-', '_'"
            
            if error_msg:
                self.error_label.setText(error_msg)
                self.error_label.setVisible(True)
            else:
                self.error_label.setVisible(False)

            self.accept_btn.setEnabled(is_valid_chars and is_valid_len)

    def on_return_pressed(self):
        if self.accept_btn.isEnabled(): self.accept()

    def get_input_text(self):
        return self.input_field.text() if self.input_field else ""

class HistoryDialog(QDialog):
    def __init__(self, data_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quest History")
        self.resize(600, 700)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint)
        self.setStyleSheet(f"""
            QDialog {{ background-color: #1e1e24; color: {ThemeColors.WHITE}; font-family: "{AppConfig.FONT_FAMILY}"; }}
            QTableWidget {{ background-color: rgba(0,0,0,0.2); border: 1px solid #444; border-radius: 8px; gridline-color: #333; }}
            QHeaderView::section {{ background-color: #2b2b30; color: {ThemeColors.GOLD}; padding: 8px; border: none; font-weight: bold; }}
            QTableWidget::item {{ padding: 5px; }}
            /* UPDATED: Alternating row colors for readability */
            QTableWidget::item:alternate {{ background-color: rgba(255,255,255,0.03); }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        header = QLabel("Quest Completion History")
        header.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {ThemeColors.WHITE}; margin-bottom: 10px;")
        layout.addWidget(header)
        
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Quest Name", "Date Completed"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        
        self.table.setRowCount(len(data_list))
        for row, (name, date) in enumerate(data_list):
            name_item = QTableWidgetItem(name)
            date_item = QTableWidgetItem(date if date else "Unknown")
            name_item.setForeground(Qt.GlobalColor.white)
            date_item.setForeground(Qt.GlobalColor.lightGray)
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, date_item)
            
        layout.addWidget(self.table)
        
        close_btn = QPushButton("Close")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet(f"""
            QPushButton {{ background-color: rgba(255,255,255,0.1); color: #fff; border: 1px solid #555; border-radius: 8px; padding: 8px 16px; }}
            QPushButton:hover {{ background-color: rgba(255,255,255,0.2); }}
        """)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)