# ui/tabs.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QProgressBar, QScrollArea, QPushButton, QFrame, QDialog, QSizePolicy)
from PySide6.QtCore import QTimer, Signal, Qt, QPropertyAnimation, QEasingCurve
from config import AppConfig, ThemeColors, QuestStatus, SECTION_MARKER, FilterMode
from .widgets import QuestWidget
from .dialogs import CustomDialog

class CollapsibleSection(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.is_expanded = True
        self.quests = []
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 10)
        self.layout.setSpacing(0)

        # --- Header Button ---
        self.toggle_btn = QPushButton()
        self.toggle_btn.setObjectName("SectionHeader")
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.setFixedHeight(40)
        self.toggle_btn.setStyleSheet(f"""
            QPushButton#SectionHeader {{
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                text-align: left;
                padding-left: 10px;
            }}
            QPushButton#SectionHeader:hover {{
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid {ThemeColors.GOLD};
            }}
        """)
        self.toggle_btn.clicked.connect(self.toggle)

        btn_layout = QHBoxLayout(self.toggle_btn)
        btn_layout.setContentsMargins(10, 0, 15, 0)
        
        self.arrow_label = QLabel("▼")
        self.arrow_label.setStyleSheet(f"color: {ThemeColors.GOLD}; font-size: 10px; font-weight: bold;")
        btn_layout.addWidget(self.arrow_label)
        
        title_clean = title.replace(SECTION_MARKER, "").strip()
        self.title_label = QLabel(title_clean)
        self.title_label.setStyleSheet(f"color: {ThemeColors.WHITE}; font-weight: bold; font-size: 13px; text-transform: uppercase; letter-spacing: 1px;")
        btn_layout.addWidget(self.title_label)
        
        btn_layout.addStretch()
        
        self.stats_label = QLabel("0/0")
        self.stats_label.setStyleSheet(f"color: {ThemeColors.GREY}; font-size: 12px;")
        btn_layout.addWidget(self.stats_label)
        
        self.layout.addWidget(self.toggle_btn)

        # --- Wrapper (QScrollArea) ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background: transparent;")
        
        # --- Inner Content ---
        self.content_area = QWidget()
        self.content_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.content_area.setStyleSheet("background: transparent;")
        
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(10, 5, 5, 5)
        self.content_layout.setSpacing(6)
        
        self.scroll_area.setWidget(self.content_area)
        self.layout.addWidget(self.scroll_area)
        
        # --- Animation ---
        self.animation = QPropertyAnimation(self.scroll_area, b"maximumHeight")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.finished.connect(self.on_animation_finished)
        
    def add_quest_widget(self, widget):
        self.content_layout.addWidget(widget)
        self.quests.append(widget)
        self.update_stats()
        if self.is_expanded:
             self.refresh_geometry()

    def refresh_geometry(self):
        """Forces the wrapper to be exactly the height of the content, eliminating internal scrollbars."""
        self.content_area.adjustSize()
        h = self.content_area.sizeHint().height()
        self.scroll_area.setMinimumHeight(h)
        self.scroll_area.setMaximumHeight(h)

    def update_stats(self):
        total = 0
        completed = 0
        visible_count = 0
        
        for q in self.quests:
            total += 1
            if q.status == QuestStatus.COMPLETED:
                completed += 1
            if q.isVisible():
                visible_count += 1
        
        color = ThemeColors.GREEN if (total > 0 and completed == total) else ThemeColors.GREY
        self.stats_label.setStyleSheet(f"color: {color}; font-size: 12px;")
        self.stats_label.setText(f"{completed}/{total}")
        
        return visible_count > 0

    def toggle(self):
        if self.is_expanded: self.collapse()
        else: self.expand()

    def collapse(self):
        if not self.is_expanded: return
        
        current_h = self.scroll_area.height()
        self.scroll_area.setMinimumHeight(0) 
        self.scroll_area.setMaximumHeight(current_h) 
        
        self.animation.setStartValue(current_h)
        self.animation.setEndValue(0)
        self.animation.start()
        
        self.arrow_label.setText("▶")
        self.is_expanded = False

    def expand(self):
        if self.is_expanded: return
        
        self.content_area.adjustSize()
        target_h = self.content_area.sizeHint().height()
        
        self.scroll_area.setMinimumHeight(0)
        self.scroll_area.setMaximumHeight(0) 
        
        self.animation.setStartValue(0)
        self.animation.setEndValue(target_h)
        self.animation.start()
        
        self.arrow_label.setText("▼")
        self.is_expanded = True
    
    def on_animation_finished(self):
        if self.is_expanded:
            self.refresh_geometry()

    def set_expanded(self, expand):
        if expand:
            self.arrow_label.setText("▼")
            self.is_expanded = True
            QTimer.singleShot(0, self.refresh_geometry)
        else:
            self.scroll_area.setMinimumHeight(0)
            self.scroll_area.setMaximumHeight(0)
            self.arrow_label.setText("▶")
            self.is_expanded = False

class CampaignTab(QWidget):
    quest_status_changed = Signal(str, int)
    reset_requested = Signal(str)
    wiki_requested = Signal(str, object) 

    def __init__(self, campaign_name, quest_list, quest_status_data):
        super().__init__()
        self.campaign_name = campaign_name
        self.quest_widgets = [] 
        self.current_status_data = quest_status_data 
        
        self._cached_total = 0
        self._cached_done = 0
        
        self.section_widgets = [] 
        self.current_section_widget = None
        
        self.current_filter_text = ""
        self.current_filter_mode = FilterMode.ALL
        
        self.pending_quests = list(quest_list) if isinstance(quest_list, list) else []
        self.batch_timer = QTimer(self)
        self.batch_timer.setInterval(AppConfig.LAZY_LOAD_INTERVAL_MS)
        self.batch_timer.timeout.connect(self._process_batch)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 0)
        
        # --- Top Progress Bar ---
        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(15)
        progress_layout.addWidget(QLabel("Campaign Progress:", objectName="SubText"))
        
        self.campaign_progress_bar = QProgressBar()
        self.campaign_progress_bar.setObjectName("CampBar")
        self.campaign_progress_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.campaign_progress_bar.setFixedHeight(12) 
        self.campaign_progress_bar.setTextVisible(False)
        self.campaign_progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: rgba(255,255,255,0.1);
                border: none;
                border-radius: 6px; 
            }}
            QProgressBar::chunk {{
                background-color: {ThemeColors.GOLD};
                border-radius: 6px;
            }}
        """)
        progress_layout.addWidget(self.campaign_progress_bar)
        
        self.percent_label = QLabel("0%", objectName="SubText")
        self.percent_label.setStyleSheet(f"color: {ThemeColors.GOLD}; font-weight: bold;")
        progress_layout.addWidget(self.percent_label)
        
        layout.addLayout(progress_layout)
        layout.addSpacing(15)

        # --- Scroll Area ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff) 
        scroll_area.setStyleSheet("background: transparent;")
        scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.content_layout.setSpacing(10) 
        self.content_layout.setContentsMargins(2, 0, 25, 10) 

        scroll_area.setWidget(self.content_widget)
        layout.addWidget(scroll_area)
        
        reset_button = QPushButton(f"Reset {campaign_name}", objectName="DangerBtn")
        reset_button.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_button.clicked.connect(self.reset_clicked)
        layout.addWidget(reset_button)
        
        self.batch_timer.start()

    def stop_loading(self):
        if self.batch_timer.isActive():
            self.batch_timer.stop()

    def _process_batch(self):
        if not self.pending_quests:
            self.batch_timer.stop()
            self.update_progress() 
            self._initial_collapse_logic()
            return

        self.content_widget.setUpdatesEnabled(False)
        
        count = 0
        while self.pending_quests and count < AppConfig.LAZY_LOAD_BATCH_SIZE:
            item = self.pending_quests.pop(0)
            
            if SECTION_MARKER in item:
                section = CollapsibleSection(item, self.content_widget)
                self.content_layout.addWidget(section)
                self.section_widgets.append(section)
                self.current_section_widget = section
            else:
                qw = self._create_quest_widget(item)
                
                self._cached_total += 1
                if qw.status == QuestStatus.COMPLETED:
                    self._cached_done += 1
                    
                if self.current_section_widget:
                    self.current_section_widget.add_quest_widget(qw)
                else:
                    self.content_layout.addWidget(qw)
                
                self.quest_widgets.append(qw)
                
            count += 1
            
        self.content_widget.setUpdatesEnabled(True)
            
        if self.pending_quests:
            self.update_progress()
        else:
            self.apply_filters()

    def _create_quest_widget(self, name):
        status_data = self._parse_status(name)
        quest_widget = QuestWidget(name, status_data)
        quest_widget.status_changed.connect(self._on_quest_changed)
        quest_widget.request_load.connect(self.wiki_requested.emit)
        return quest_widget

    def _initial_collapse_logic(self):
        for i, section in enumerate(self.section_widgets):
            has_active = False
            for q in section.quests:
                if q.status == QuestStatus.IN_PROGRESS:
                    has_active = True
                    break
            
            if i == 0 or has_active:
                section.set_expanded(True)
            else:
                section.set_expanded(False)

    def _parse_status(self, quest_name):
        val = self.current_status_data.get(quest_name)
        if val is None or not isinstance(val, dict):
             return {"status": QuestStatus.NOT_STARTED, "timestamp": None}
        return val

    def get_progress_stats(self):
        pending_count = 0
        pending_done = 0
        
        for item in self.pending_quests:
            if SECTION_MARKER in item: continue
            pending_count += 1
            status_data = self._parse_status(item)
            if status_data["status"] == QuestStatus.COMPLETED:
                pending_done += 1
        
        return (self._cached_done + pending_done), (self._cached_total + pending_count)

    def refresh_tab_state(self, current_data):
        self.current_status_data = current_data
        
        self.content_widget.setUpdatesEnabled(False)
        
        self._cached_total = 0
        self._cached_done = 0
        
        for quest_widget in self.quest_widgets:
            quest_name = quest_widget.quest_button.text()
            status_data = self._parse_status(quest_name)
            quest_widget.refresh_data(status_data)
            
            self._cached_total += 1
            if status_data.get("status") == QuestStatus.COMPLETED:
                self._cached_done += 1
        
        self.content_widget.setUpdatesEnabled(True)
        
        self.update_progress()
        self.apply_filters()
        
    def _on_quest_changed(self, name, status):
        self._cached_done = 0
        self._cached_total = 0
        for qw in self.quest_widgets:
            self._cached_total += 1
            if qw.status == QuestStatus.COMPLETED:
                self._cached_done += 1
        
        self.quest_status_changed.emit(name, status)
        self.update_progress()
        if self.current_filter_mode != FilterMode.ALL:
            self.apply_filters()

    def set_filter_mode(self, mode):
        self.current_filter_mode = mode
        self.apply_filters()

    def filter_content(self, text):
        self.current_filter_text = text.lower()
        self.apply_filters()

    def apply_filters(self):
        self.content_widget.setUpdatesEnabled(False)
        mode = self.current_filter_mode
        search = self.current_filter_text
        
        for section in self.section_widgets:
            section_has_visible = False
            
            for qw in section.quests:
                text_match = True
                if search:
                    text_match = search in qw.quest_button.text().lower()
                
                status_match = True
                if mode == FilterMode.ACTIVE_ONLY:
                     status_match = (qw.status != QuestStatus.COMPLETED)
                elif mode == FilterMode.NOT_STARTED:
                    status_match = (qw.status == QuestStatus.NOT_STARTED)
                elif mode == FilterMode.IN_PROGRESS:
                    status_match = (qw.status == QuestStatus.IN_PROGRESS)
                elif mode == FilterMode.COMPLETED:
                    status_match = (qw.status == QuestStatus.COMPLETED)
                
                is_visible = text_match and status_match
                qw.setVisible(is_visible)
                if is_visible:
                    section_has_visible = True
            
            section.setVisible(section_has_visible)
            if section_has_visible:
                section.update_stats()
                if search and not section.is_expanded:
                    section.expand()
                elif section.is_expanded:
                    section.refresh_geometry()

        self.content_widget.setUpdatesEnabled(True)

    def reset_clicked(self):
        dlg = CustomDialog("Confirm Reset", f"Are you sure you want to reset all progress for {self.campaign_name}?", self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.reset_requested.emit(self.campaign_name)

    def update_progress(self):
        done, total = self.get_progress_stats()
        if total > 0:
            percent = int((done/total)*100)
            self.percent_label.setText(f"{percent}%")
            self.campaign_progress_bar.setMaximum(total)
            self.campaign_progress_bar.setValue(done)
            
        for section in self.section_widgets:
            section.update_stats()