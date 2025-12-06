# ui/widgets.py
import datetime
import re
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QLabel, QCheckBox, QLineEdit, QSizePolicy, QDialog, QApplication, QScrollArea
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Signal, QSize, QEvent
from PySide6.QtGui import QIcon
from config import AppConfig, ThemeColors, QuestStatus, FilterMode
from .style import create_custom_icon

class FilterSelectorWidget(QWidget):
    filter_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_expanded = False
        self.current_filter = FilterMode.ALL
        
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setFixedWidth(160) 
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.main_button = QPushButton()
        self.main_button.setObjectName("FilterMainBtn")
        self.main_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.main_button.clicked.connect(self.toggle_menu)
        self.main_button.setFixedHeight(36)
        
        btn_layout = QHBoxLayout(self.main_button)
        btn_layout.setContentsMargins(10, 0, 10, 0)
        
        self.icon_label = QLabel()
        self.icon_label.setPixmap(create_custom_icon("filter", ThemeColors.WHITE).pixmap(16, 16))
        self.icon_label.setFixedSize(16, 16)
        
        self.filter_label = QLabel(FilterMode.ALL)
        self.filter_label.setStyleSheet(f"color: {ThemeColors.WHITE}; font-weight: bold; font-size: 12px; border: none; background: transparent;")
        
        self.dropdown_icon = QLabel("▼")
        self.dropdown_icon.setStyleSheet(f"color: {ThemeColors.GOLD}; font-size: 10px; border: none; background: transparent;")
        
        btn_layout.addWidget(self.icon_label)
        btn_layout.addWidget(self.filter_label)
        btn_layout.addStretch() 
        btn_layout.addWidget(self.dropdown_icon)
        
        self.main_layout.addWidget(self.main_button)
        
        # --- Wrapper (QScrollArea) ---
        self.mask_container = QScrollArea()
        self.mask_container.setFrameShape(QFrame.Shape.NoFrame)
        self.mask_container.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.mask_container.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.mask_container.setWidgetResizable(True)
        self.mask_container.setStyleSheet("background: transparent;")
        self.mask_container.setMaximumHeight(0)
        self.mask_container.setVisible(False)
        
        # --- Content ---
        self.dropdown_container = QFrame()
        self.dropdown_container.setObjectName("FilterContainer")
        self.dropdown_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed) 
        
        self.list_layout = QVBoxLayout(self.dropdown_container)
        self.list_layout.setContentsMargins(5, 5, 5, 5)
        self.list_layout.setSpacing(2)
        
        self.options = [FilterMode.ALL, FilterMode.ACTIVE_ONLY, FilterMode.NOT_STARTED, FilterMode.IN_PROGRESS, FilterMode.COMPLETED]
        for opt in self.options:
            btn = QPushButton(opt)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(28) 
            btn.clicked.connect(lambda checked, o=opt: self.select_filter(o))
            self.list_layout.addWidget(btn)

        self.mask_container.setWidget(self.dropdown_container)
        self.main_layout.addWidget(self.mask_container)
        
        self.animation = QPropertyAnimation(self.mask_container, b"maximumHeight")
        self.animation.setDuration(250)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic) 
        self.animation.finished.connect(self._on_animation_finished)

        if QApplication.instance():
            QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event):
        if self.is_expanded and event.type() == QEvent.Type.MouseButtonPress:
            if not self.rect().contains(self.mapFromGlobal(event.globalPosition().toPoint())):
                self.collapse_menu()
        return super().eventFilter(obj, event)

    def toggle_menu(self):
        if self.is_expanded: self.collapse_menu()
        else: self.expand_menu()
            
    def expand_menu(self):
        self.dropdown_icon.setText("▲") 
        self.mask_container.setVisible(True)
        
        self.dropdown_container.adjustSize()
        target_h = self.dropdown_container.sizeHint().height()
        
        self.mask_container.setMinimumHeight(0)
        self.mask_container.setMaximumHeight(0) 
        
        self.animation.stop()
        self.animation.setStartValue(0)
        self.animation.setEndValue(target_h)
        self.animation.start()
        self.is_expanded = True
        self.main_button.setStyleSheet(self.main_button.styleSheet().replace("border-radius: 12px;", "border-top-left-radius: 12px; border-top-right-radius: 12px; border-bottom-left-radius: 0; border-bottom-right-radius: 0;"))
    
    def collapse_menu(self):
        if not self.is_expanded: return
        self.dropdown_icon.setText("▼")
        
        current_h = self.mask_container.height()
        self.mask_container.setMinimumHeight(0)
        self.mask_container.setMaximumHeight(current_h)
        
        self.animation.setStartValue(current_h)
        self.animation.setEndValue(0)
        self.animation.start()
        self.is_expanded = False
        self.main_button.setStyleSheet(self.main_button.styleSheet().replace("border-top-left-radius: 12px; border-top-right-radius: 12px; border-bottom-left-radius: 0; border-bottom-right-radius: 0;", "border-radius: 12px;"))

    def _on_animation_finished(self):
        if self.is_expanded:
            self.dropdown_container.adjustSize()
            h = self.dropdown_container.sizeHint().height()
            self.mask_container.setMinimumHeight(h)
            self.mask_container.setMaximumHeight(h)
        else:
            self.mask_container.setVisible(False)

    def select_filter(self, mode):
        self.current_filter = mode
        self.filter_label.setText(mode)
        self.filter_changed.emit(mode)
        self.collapse_menu()

class CampaignSelectorWidget(QWidget):
    campaign_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_expanded = False
        self.current_campaign = ""
        
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.main_button = QPushButton()
        self.main_button.setObjectName("ProfileMainBtn")
        self.main_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.main_button.clicked.connect(self.toggle_menu)
        self.main_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.main_button.setFixedHeight(45) 
        
        btn_layout = QHBoxLayout(self.main_button)
        btn_layout.setContentsMargins(15, 0, 15, 0)
        
        self.camp_label = QLabel("")
        self.camp_label.setStyleSheet(f"color: {ThemeColors.GOLD}; font-weight: bold; font-size: 16px; border: none; background: transparent; text-transform: uppercase; letter-spacing: 1px;")
        
        self.dropdown_icon = QLabel("▼")
        self.dropdown_icon.setStyleSheet(f"color: {ThemeColors.GOLD}; font-size: 12px; border: none; background: transparent;")
        
        btn_layout.addWidget(self.camp_label)
        btn_layout.addStretch() 
        btn_layout.addWidget(self.dropdown_icon)
        
        self.main_layout.addWidget(self.main_button)
        
        # --- Wrapper ---
        self.mask_container = QScrollArea()
        self.mask_container.setFrameShape(QFrame.Shape.NoFrame)
        self.mask_container.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.mask_container.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.mask_container.setWidgetResizable(True)
        self.mask_container.setStyleSheet("background: transparent;")
        self.mask_container.setMaximumHeight(0)
        self.mask_container.setVisible(False)
        
        # --- Content ---
        self.dropdown_container = QFrame()
        self.dropdown_container.setObjectName("ProfileContainer")
        self.dropdown_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed) 
        
        self.list_layout = QVBoxLayout(self.dropdown_container)
        self.list_layout.setContentsMargins(5, 5, 5, 5)
        self.list_layout.setSpacing(2)
        
        self.mask_container.setWidget(self.dropdown_container)
        self.main_layout.addWidget(self.mask_container)
        
        self.animation = QPropertyAnimation(self.mask_container, b"maximumHeight")
        self.animation.setDuration(250)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic) 
        self.animation.finished.connect(self._on_animation_finished)

        if QApplication.instance():
            QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event):
        if self.is_expanded and event.type() == QEvent.Type.MouseButtonPress:
            if not self.rect().contains(self.mapFromGlobal(event.globalPosition().toPoint())):
                self.collapse_menu()
        return super().eventFilter(obj, event)
        
    def update_options(self, campaigns, current):
        self.current_campaign = current
        self.camp_label.setText(current)
        
        while self.list_layout.count():
            child = self.list_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
        
        for c in campaigns:
            if c == current: continue
            btn = QPushButton(c)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(35)
            btn.clicked.connect(lambda checked, name=c: self.select_campaign(name))
            self.list_layout.addWidget(btn)
        
        self.dropdown_container.adjustSize()
        if self.is_expanded: self.expand_menu()

    def toggle_menu(self):
        if self.is_expanded: self.collapse_menu()
        else: self.expand_menu()
            
    def expand_menu(self):
        self.dropdown_icon.setText("▲") 
        self.mask_container.setVisible(True)
        
        if self.list_layout.count() <= 0: return
        
        self.dropdown_container.adjustSize()
        target_h = self.dropdown_container.sizeHint().height()
        self.mask_container.setMinimumHeight(0)
        self.mask_container.setMaximumHeight(0)
        
        self.animation.stop()
        self.animation.setStartValue(0)
        self.animation.setEndValue(target_h)
        self.animation.start()
        self.is_expanded = True
        self.main_button.setStyleSheet(self.main_button.styleSheet().replace("border-radius: 12px;", "border-top-left-radius: 12px; border-top-right-radius: 12px; border-bottom-left-radius: 0; border-bottom-right-radius: 0;"))
    
    def collapse_menu(self):
        if not self.is_expanded: return
        self.dropdown_icon.setText("▼")
        
        current_h = self.mask_container.height()
        self.mask_container.setMinimumHeight(0)
        self.mask_container.setMaximumHeight(current_h)
        
        self.animation.setStartValue(current_h)
        self.animation.setEndValue(0)
        self.animation.start()
        self.is_expanded = False
        self.main_button.setStyleSheet(self.main_button.styleSheet().replace("border-top-left-radius: 12px; border-top-right-radius: 12px; border-bottom-left-radius: 0; border-bottom-right-radius: 0;", "border-radius: 12px;"))

    def _on_animation_finished(self):
        if self.is_expanded:
            self.dropdown_container.adjustSize()
            h = self.dropdown_container.sizeHint().height()
            self.mask_container.setMinimumHeight(h)
            self.mask_container.setMaximumHeight(h)
        else:
            self.mask_container.setVisible(False)

    def select_campaign(self, name):
        self.current_campaign = name
        self.campaign_changed.emit(name)
        self.collapse_menu()

class ProfileSelectorWidget(QWidget):
    profile_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_expanded = False
        
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.main_button = QPushButton()
        self.main_button.setObjectName("ProfileMainBtn")
        self.main_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.main_button.clicked.connect(self.toggle_menu)
        self.main_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.main_button.setFixedHeight(40) 
        
        btn_layout = QHBoxLayout(self.main_button)
        btn_layout.setContentsMargins(15, 0, 15, 0)
        
        self.profile_name_label = QLabel("")
        self.profile_name_label.setStyleSheet(f"color: {ThemeColors.WHITE}; font-weight: bold; font-size: 14px; border: none; background: transparent;")
        
        self.dropdown_icon = QLabel("▼")
        self.dropdown_icon.setStyleSheet(f"color: {ThemeColors.GOLD}; font-size: 12px; border: none; background: transparent;")
        
        btn_layout.addWidget(self.profile_name_label)
        btn_layout.addStretch() 
        btn_layout.addWidget(self.dropdown_icon)
        
        self.main_layout.addWidget(self.main_button)
        
        # --- Wrapper ---
        self.mask_container = QScrollArea()
        self.mask_container.setFrameShape(QFrame.Shape.NoFrame)
        self.mask_container.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.mask_container.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.mask_container.setWidgetResizable(True)
        self.mask_container.setStyleSheet("background: transparent;")
        self.mask_container.setMaximumHeight(0)
        self.mask_container.setVisible(False)
        
        # --- Content ---
        self.dropdown_container = QFrame()
        self.dropdown_container.setObjectName("ProfileContainer")
        self.dropdown_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed) 
        
        self.list_layout = QVBoxLayout(self.dropdown_container)
        self.list_layout.setContentsMargins(5, 5, 5, 5)
        self.list_layout.setSpacing(2)
        
        self.mask_container.setWidget(self.dropdown_container)
        self.main_layout.addWidget(self.mask_container)
        
        self.animation = QPropertyAnimation(self.mask_container, b"maximumHeight")
        self.animation.setDuration(250)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic) 
        self.animation.finished.connect(self._on_animation_finished)

        if QApplication.instance():
            QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event):
        if self.is_expanded and event.type() == QEvent.Type.MouseButtonPress:
            if not self.rect().contains(self.mapFromGlobal(event.globalPosition().toPoint())):
                self.collapse_menu()
        return super().eventFilter(obj, event)
        
    def update_state(self, profiles, current_profile):
        self.profile_name_label.setText(current_profile)
        while self.list_layout.count():
            child = self.list_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
        
        for p in profiles:
            if p == current_profile: continue 
            btn = QPushButton(p)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(30)
            btn.clicked.connect(lambda checked, name=p: self.select_profile(name))
            self.list_layout.addWidget(btn)
        self.dropdown_container.adjustSize()
        if self.is_expanded: self.expand_menu()

    def toggle_menu(self):
        if self.is_expanded: self.collapse_menu()
        else: self.expand_menu()
            
    def expand_menu(self):
        self.dropdown_icon.setText("▲") 
        self.mask_container.setVisible(True)
        
        if self.list_layout.count() <= 0:
            self.collapse_menu(); return
            
        self.dropdown_container.adjustSize()
        target_h = self.dropdown_container.sizeHint().height()
        self.mask_container.setMinimumHeight(0)
        self.mask_container.setMaximumHeight(0)
        
        self.animation.stop()
        self.animation.setStartValue(0)
        self.animation.setEndValue(target_h)
        self.animation.start()
        self.is_expanded = True
        self.main_button.setStyleSheet(self.main_button.styleSheet().replace("border-radius: 12px;", "border-top-left-radius: 12px; border-top-right-radius: 12px; border-bottom-left-radius: 0; border-bottom-right-radius: 0;"))
    
    def collapse_menu(self):
        if not self.is_expanded: return
        self.dropdown_icon.setText("▼")
        
        current_h = self.mask_container.height()
        self.mask_container.setMinimumHeight(0)
        self.mask_container.setMaximumHeight(current_h)
        
        self.animation.setStartValue(current_h)
        self.animation.setEndValue(0)
        self.animation.start()
        self.is_expanded = False
        self.main_button.setStyleSheet(self.main_button.styleSheet().replace("border-top-left-radius: 12px; border-top-right-radius: 12px; border-bottom-left-radius: 0; border-bottom-right-radius: 0;", "border-radius: 12px;"))

    def _on_animation_finished(self):
        if self.is_expanded:
            self.dropdown_container.adjustSize()
            h = self.dropdown_container.sizeHint().height()
            self.mask_container.setMinimumHeight(h)
            self.mask_container.setMaximumHeight(h)
        else:
            self.mask_container.setVisible(False)

    def select_profile(self, name):
        self.profile_changed.emit(name)
        self.collapse_menu()
        
class QuestWidget(QFrame):
    status_changed = Signal(str, int)
    request_load = Signal(str, object) 

    def __init__(self, name, data, parent=None):
        super().__init__(parent)
        self.original_index = 0
        self.is_highlighted = False
        
        self.status = data.get("status", QuestStatus.NOT_STARTED) if isinstance(data, dict) else QuestStatus.NOT_STARTED
        self.timestamp = data.get("timestamp") if isinstance(data, dict) else None 
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4) 
        layout.setSpacing(10)

        self.checkbox = QCheckBox()
        self.checkbox.setTristate(True) 
        self.checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.checkbox.setFixedWidth(24) 
        self._update_check_state()
        self.checkbox.stateChanged.connect(self._on_check_change)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setContentsMargins(0,0,0,0)
        
        self.quest_button = QPushButton(name)
        self.quest_button.setObjectName("QuestLabel")
        self.quest_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.quest_button.clicked.connect(self._on_click) 
        self.quest_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        text_layout.addWidget(self.quest_button)
        
        self.timestamp_label = QLabel("")
        self.timestamp_label.setObjectName("TimeLabel")
        self.timestamp_label.setVisible(False)
        
        text_layout.addWidget(self.timestamp_label)
        layout.addWidget(self.checkbox)
        layout.addLayout(text_layout)
        layout.addStretch() 
        self._update_style()

    def refresh_data(self, data):
        self.status = data.get("status", QuestStatus.NOT_STARTED)
        self.timestamp = data.get("timestamp")
        
        self._update_check_state()
        self._update_style()
        self._update_timestamp_visibility()
             
    def _update_check_state(self):
        self.checkbox.blockSignals(True)
        if self.status == QuestStatus.COMPLETED: 
            self.checkbox.setCheckState(Qt.CheckState.Checked) 
        elif self.status == QuestStatus.IN_PROGRESS: 
            self.checkbox.setCheckState(Qt.CheckState.PartiallyChecked)
        else: 
            self.checkbox.setCheckState(Qt.CheckState.Unchecked)
            
        self.checkbox.blockSignals(False)

    def _on_check_change(self, state):
        if state == Qt.CheckState.Checked.value:
            self.status = QuestStatus.COMPLETED
        elif state == Qt.CheckState.PartiallyChecked.value:
            self.status = QuestStatus.IN_PROGRESS
        else:
            self.status = QuestStatus.NOT_STARTED
        
        self._update_style()
        
        if self.status == QuestStatus.COMPLETED:
             self.timestamp = datetime.datetime.now().strftime(AppConfig.DATE_FORMAT)
             self._set_timestamp_label_text()
        else:
             self.timestamp = None
        
        self._update_timestamp_visibility()
        
        self.status_changed.emit(self.quest_button.text(), self.status)
             
    def _set_timestamp_label_text(self):
        if self.timestamp:
            self.timestamp_label.setText(f"Completed: {self.timestamp}")
        else:
            self.timestamp_label.setText("Completed") 

    def _on_click(self):
        self.request_load.emit(self.quest_button.text(), self)

    def set_highlighted(self, active):
        self.is_highlighted = active
        self._update_timestamp_visibility()

    def _update_timestamp_visibility(self):
        if self.status == QuestStatus.COMPLETED and self.is_highlighted:
            self._set_timestamp_label_text()
            self.timestamp_label.setVisible(True)
        else:
            self.timestamp_label.setVisible(False)

    def _update_style(self):
        if self.status == QuestStatus.COMPLETED:
            self.quest_button.setStyleSheet(f"""
                QPushButton#QuestLabel {{
                    background-color: rgba(212, 175, 55, 0.15); color: #888; text-decoration: line-through;
                    border: 1px solid {ThemeColors.GOLD}; border-radius: 18px; text-align: left; padding: 8px 15px; max-width: 315px;
                }}
                QPushButton#QuestLabel:focus {{
                    border: 2px solid {ThemeColors.GOLD};
                }}
            """)
        elif self.status == QuestStatus.IN_PROGRESS:
            self.quest_button.setStyleSheet(f"""
                QPushButton#QuestLabel {{
                    background-color: rgba(76, 175, 80, 0.15); color: {ThemeColors.GREEN}; font-style: italic;
                    border: 1px solid {ThemeColors.GREEN}; border-radius: 18px; text-align: left; padding: 8px 15px; max-width: 315px;
                }}
                QPushButton#QuestLabel:focus {{
                    border: 2px solid {ThemeColors.GREEN};
                }}
            """)
        else:
            self.quest_button.setStyleSheet("")