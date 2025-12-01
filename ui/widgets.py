# ui/widgets.py
import datetime
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QLabel, QCheckBox, QLineEdit, QSizePolicy, QDialog
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Signal, QSize
from PySide6.QtGui import QIcon
from config import AppConfig, ThemeColors, QuestStatus, FilterMode
from .style import create_custom_icon

class FilterSelectorWidget(QWidget):
    filter_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_expanded = False
        self.current_filter = FilterMode.ALL
        
        # PERFORMANCE: Fixed size policy prevents layout thrashing horizontally
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setFixedWidth(150) 
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop) # Ensure top alignment internally
        
        self.main_button = QPushButton()
        self.main_button.setObjectName("FilterMainBtn") # Styled in style.py
        self.main_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.main_button.clicked.connect(self.toggle_menu)
        self.main_button.setFixedHeight(36)
        
        btn_layout = QHBoxLayout(self.main_button)
        btn_layout.setContentsMargins(10, 0, 10, 0)
        
        # Icon
        self.icon_label = QLabel()
        self.icon_label.setPixmap(create_custom_icon("filter", ThemeColors.WHITE).pixmap(16, 16))
        self.icon_label.setFixedSize(16, 16)
        
        self.filter_label = QLabel(FilterMode.ALL)
        # Use inline style only for color/font that needs to ignore main QWidget style
        self.filter_label.setStyleSheet(f"color: {ThemeColors.WHITE}; font-weight: bold; font-size: 12px; border: none; background: transparent;")
        
        self.dropdown_icon = QLabel("▼")
        self.dropdown_icon.setStyleSheet(f"color: {ThemeColors.GOLD}; font-size: 10px; border: none; background: transparent;")
        
        btn_layout.addWidget(self.icon_label)
        btn_layout.addWidget(self.filter_label)
        btn_layout.addStretch() 
        btn_layout.addWidget(self.dropdown_icon)
        
        # REMOVED EMBEDDED CSS for main_button (Now in style.py)
        
        self.main_layout.addWidget(self.main_button)
        
        self.dropdown_container = QFrame()
        self.dropdown_container.setObjectName("FilterContainer") # Styled in style.py
        # REMOVED EMBEDDED CSS for dropdown_container (Now in style.py)
        self.dropdown_container.setMaximumHeight(0) 
        
        self.list_layout = QVBoxLayout(self.dropdown_container)
        self.list_layout.setContentsMargins(5, 5, 5, 5)
        self.list_layout.setSpacing(2)
        
        # Add Filter Options
        self.options = [FilterMode.ALL, FilterMode.NOT_STARTED, FilterMode.IN_PROGRESS, FilterMode.COMPLETED]
        for opt in self.options:
            btn = QPushButton(opt)
            # Option buttons are styled globally by QFrame#FilterContainer QPushButton
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(28) 
            # REMOVED EMBEDDED CSS for option buttons (Now in style.py)
            btn.clicked.connect(lambda checked, o=opt: self.select_filter(o))
            self.list_layout.addWidget(btn)

        self.main_layout.addWidget(self.dropdown_container)
        
        self.animation = QPropertyAnimation(self.dropdown_container, b"maximumHeight")
        self.animation.setDuration(150) # Faster duration for snappier feel
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad) # Smoother curve

    # ... (rest of FilterSelectorWidget methods remain the same)
    def toggle_menu(self):
        if self.is_expanded: self.collapse_menu()
        else: self.expand_menu()
            
    def expand_menu(self):
        self.dropdown_icon.setText("▲") 
        target_h = (len(self.options) * 30) + 10 
        self.animation.stop()
        self.animation.setStartValue(self.dropdown_container.height())
        self.animation.setEndValue(target_h)
        self.animation.start()
        self.is_expanded = True
        # Keep border radius logic for animation effect
        self.main_button.setStyleSheet(self.main_button.styleSheet().replace("border-radius: 12px;", "border-top-left-radius: 12px; border-top-right-radius: 12px; border-bottom-left-radius: 0; border-bottom-right-radius: 0;"))
    
    def collapse_menu(self):
        if not self.is_expanded: return
        self.dropdown_icon.setText("▼")
        self.animation.setStartValue(self.dropdown_container.height())
        self.animation.setEndValue(0)
        self.animation.start()
        self.is_expanded = False
        # Keep border radius logic for animation effect
        self.main_button.setStyleSheet(self.main_button.styleSheet().replace("border-top-left-radius: 12px; border-top-right-radius: 12px; border-bottom-left-radius: 0; border-bottom-right-radius: 0;", "border-radius: 12px;"))

    def select_filter(self, mode):
        self.current_filter = mode
        self.filter_label.setText(mode)
        self.filter_changed.emit(mode)
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
        self.main_button.setObjectName("ProfileMainBtn") # Styled in style.py
        self.main_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.main_button.clicked.connect(self.toggle_menu)
        self.main_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.main_button.setFixedHeight(40) 
        
        btn_layout = QHBoxLayout(self.main_button)
        btn_layout.setContentsMargins(15, 0, 15, 0)
        
        self.profile_name_label = QLabel("")
        # Use inline style only for color/font that needs to ignore main QWidget style
        self.profile_name_label.setStyleSheet(f"color: {ThemeColors.WHITE}; font-weight: bold; font-size: 14px; border: none; background: transparent;")
        
        self.dropdown_icon = QLabel("▼")
        self.dropdown_icon.setStyleSheet(f"color: {ThemeColors.GOLD}; font-size: 12px; border: none; background: transparent;")
        
        btn_layout.addWidget(self.profile_name_label)
        btn_layout.addStretch() 
        btn_layout.addWidget(self.dropdown_icon)
        
        # REMOVED EMBEDDED CSS for main_button (Now in style.py)
        
        self.main_layout.addWidget(self.main_button)
        
        self.dropdown_container = QFrame()
        self.dropdown_container.setObjectName("ProfileContainer") # Styled in style.py
        # REMOVED EMBEDDED CSS for dropdown_container (Now in style.py)
        self.dropdown_container.setMaximumHeight(0) 
        
        self.list_layout = QVBoxLayout(self.dropdown_container)
        self.list_layout.setContentsMargins(5, 5, 5, 5)
        self.list_layout.setSpacing(2)
        
        self.main_layout.addWidget(self.dropdown_container)
        
        self.animation = QPropertyAnimation(self.dropdown_container, b"maximumHeight")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        
    def update_state(self, profiles, current_profile):
        self.profile_name_label.setText(current_profile)
        while self.list_layout.count():
            child = self.list_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
        
        for p in profiles:
            if p == current_profile: continue 
            btn = QPushButton(p)
            # Option buttons are styled globally by QFrame#ProfileContainer QPushButton
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(30) 
            # REMOVED EMBEDDED CSS for option buttons (Now in style.py)
            btn.clicked.connect(lambda checked, name=p: self.select_profile(name))
            self.list_layout.addWidget(btn)
        self.dropdown_container.adjustSize()
        if self.is_expanded: self.expand_menu()
             
    # ... (rest of ProfileSelectorWidget methods remain the same)
    def toggle_menu(self):
        if self.is_expanded: self.collapse_menu()
        else: self.expand_menu()
            
    def expand_menu(self):
        self.dropdown_icon.setText("▲") 
        count = self.list_layout.count() 
        if count <= 0:
            self.collapse_menu(); return
        target_h = (count * 32) + 10 
        self.animation.stop()
        self.animation.setStartValue(self.dropdown_container.height())
        self.animation.setEndValue(target_h)
        self.animation.start()
        self.is_expanded = True
        # Keep border radius logic for animation effect
        self.main_button.setStyleSheet(self.main_button.styleSheet().replace("border-radius: 12px;", "border-top-left-radius: 12px; border-top-right-radius: 12px; border-bottom-left-radius: 0; border-bottom-right-radius: 0;"))
    
    def collapse_menu(self):
        if not self.is_expanded: return
        self.dropdown_icon.setText("▼")
        self.animation.setStartValue(self.dropdown_container.height())
        self.animation.setEndValue(0)
        self.animation.start()
        self.is_expanded = False
        # Keep border radius logic for animation effect
        self.main_button.setStyleSheet(self.main_button.styleSheet().replace("border-top-left-radius: 12px; border-top-right-radius: 12px; border-bottom-left-radius: 0; border-bottom-right-radius: 0;", "border-radius: 12px;"))

    def select_profile(self, name):
        self.profile_changed.emit(name)
        self.collapse_menu()
        
class QuestWidget(QFrame):
    status_changed = Signal(str, int)
    request_load = Signal(str)
    current_selected = None

    def __init__(self, name, data, parent=None):
        super().__init__(parent)
        self.original_index = 0 # For sorting
        
        # Data is now a dict {"status": int, "timestamp": str or None}
        self.status = data.get("status", QuestStatus.NOT_STARTED) if isinstance(data, dict) else QuestStatus.NOT_STARTED
        self.timestamp = data.get("timestamp") if isinstance(data, dict) else None # Store timestamp
        
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
        # Data is the full dict
        self.status = data.get("status", QuestStatus.NOT_STARTED)
        self.timestamp = data.get("timestamp")
        
        self._update_check_state()
        self._update_style()
        
        # When refreshing, hide the timestamp unless this widget is currently selected
        if QuestWidget.current_selected != self:
             self.timestamp_label.setVisible(False)
        # If it is the currently selected quest, update the label text and ensure visible if completed
        elif self.status == QuestStatus.COMPLETED:
             self._set_timestamp_label()
             self.timestamp_label.setVisible(True)
             
    def _update_check_state(self):
        self.checkbox.blockSignals(True)
        # 3-state logic for 3 status values
        if self.status == QuestStatus.COMPLETED: 
            self.checkbox.setCheckState(Qt.CheckState.Checked) 
        elif self.status == QuestStatus.IN_PROGRESS: 
            self.checkbox.setCheckState(Qt.CheckState.PartiallyChecked)
        else: 
            self.checkbox.setCheckState(Qt.CheckState.Unchecked)
            
        self.checkbox.blockSignals(False)

    def _on_check_change(self, state):
        # Determine the *actual* new status based on the current one for a cleaner cycle
        if self.status == QuestStatus.NOT_STARTED:
            new_status = QuestStatus.IN_PROGRESS
        elif self.status == QuestStatus.IN_PROGRESS:
            new_status = QuestStatus.COMPLETED
        else: # COMPLETED (2)
            new_status = QuestStatus.NOT_STARTED
        
        self.status = new_status
        self._update_style()
        self._update_check_state() # Ensure checkbox visual reflects the final new_status
        self.status_changed.emit(self.quest_button.text(), self.status)
        
        # If COMPLETED, set local timestamp and display it temporarily
        if self.status == QuestStatus.COMPLETED:
             self.timestamp = datetime.datetime.now().strftime(AppConfig.DATE_FORMAT)
             self._set_timestamp_label()
             self.timestamp_label.setVisible(True)
        else:
             self.timestamp = None
             self.timestamp_label.setVisible(False) 
             
    def _set_timestamp_label(self):
        """Helper to set the timestamp label content based on stored data."""
        if self.timestamp:
            # Display full month, day, year, and time format
            self.timestamp_label.setText(f"Completed: {self.timestamp}")
        else:
            # Fallback text if timestamp somehow missing but status is completed
            self.timestamp_label.setText("Completed") 

    def _on_click(self):
        self.request_load.emit(self.quest_button.text())
        
        # De-select old widget: Clear timestamp visibility for the previously selected item
        if QuestWidget.current_selected and QuestWidget.current_selected != self:
             old_widget = QuestWidget.current_selected
             old_widget.timestamp_label.setVisible(False)
             
        QuestWidget.current_selected = self
        
        # Display logic: Show the full timestamp when clicked ONLY IF completed
        self.timestamp_label.setVisible(self.status == QuestStatus.COMPLETED)
        if self.status == QuestStatus.COMPLETED:
            # Set the label using the stored timestamp (which includes the full format)
            self._set_timestamp_label()

    def _update_style(self):
        # Styling remains the same
        if self.status == QuestStatus.COMPLETED:
            self.quest_button.setStyleSheet(f"""
                QPushButton#QuestLabel {{
                    background-color: rgba(212, 175, 55, 0.15); color: #888; text-decoration: line-through;
                    border: 1px solid {ThemeColors.GOLD}; border-radius: 18px; text-align: left; padding: 8px 15px; max-width: 315px;
                }}
            """)
        elif self.status == QuestStatus.IN_PROGRESS:
            self.quest_button.setStyleSheet(f"""
                QPushButton#QuestLabel {{
                    background-color: rgba(76, 175, 80, 0.15); color: {ThemeColors.GREEN}; font-style: italic;
                    border: 1px solid {ThemeColors.GREEN}; border-radius: 18px; text-align: left; padding: 8px 15px; max-width: 315px;
                }}
            """)
        else:
            self.quest_button.setStyleSheet("")