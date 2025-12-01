# ui/tabs.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QProgressBar, QScrollArea, QPushButton, QFrame, QDialog)
from PySide6.QtCore import QTimer, Signal, Qt
from config import AppConfig, ThemeColors, QuestStatus, SECTION_MARKER, FilterMode
from .widgets import QuestWidget
from .dialogs import CustomDialog

class CampaignTab(QWidget):
    quest_status_changed = Signal(str, int)
    reset_requested = Signal(str)
    wiki_requested = Signal(str)

    def __init__(self, campaign_name, quest_list, quest_status_data):
        super().__init__()
        self.campaign_name = campaign_name
        self.quest_widgets = [] 
        self.current_status_data = quest_status_data 
        self.sections = []
        
        # State
        self.current_filter_text = ""
        self.current_filter_mode = FilterMode.ALL
        
        self.pending_quests = list(quest_list) if isinstance(quest_list, list) else []
        self.batch_timer = QTimer(self)
        self.batch_timer.setInterval(AppConfig.LAZY_LOAD_INTERVAL_MS)
        self.batch_timer.timeout.connect(self._process_batch)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 5, 0)
        
        header_layout = QHBoxLayout()
        self.percent_label = QLabel("0%", objectName="H1")
        self.percent_label.setStyleSheet(f"color: {ThemeColors.GOLD}; font-size: 28px;") 
        header_layout.addWidget(self.percent_label)
        header_layout.addWidget(QLabel(f"{campaign_name.upper()}", objectName="SubText"), alignment=Qt.AlignmentFlag.AlignBottom)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        self.campaign_progress_bar = QProgressBar()
        self.campaign_progress_bar.setObjectName("CampBar")
        self.campaign_progress_bar.setFixedHeight(6)
        self.campaign_progress_bar.setTextVisible(False)
        layout.addWidget(self.campaign_progress_bar)
        layout.addSpacing(15)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff) 
        scroll_area.setStyleSheet("background: transparent;")
        
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.content_layout.setSpacing(6)
        self.content_layout.setContentsMargins(2, 0, 25, 0) 

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
            return

        self.content_widget.setUpdatesEnabled(False)
        
        count = 0
        while self.pending_quests and count < AppConfig.LAZY_LOAD_BATCH_SIZE:
            item = self.pending_quests.pop(0)
            if SECTION_MARKER in item:
                header_lbl = QLabel(item.replace(SECTION_MARKER, "").strip(), objectName="H2")
                header_lbl.setParent(self.content_widget)
                self.content_layout.addWidget(header_lbl)
                self.sections.append({"header": header_lbl, "quests": []})
            else:
                qw = self._add_quest(item)
                if self.sections:
                    self.sections[-1]["quests"].append(qw)
            count += 1
            
        self.content_widget.setUpdatesEnabled(True)
            
        if self.pending_quests:
            self.update_progress()
        else:
            # Re-apply filters once fully loaded to ensure consistent state
            self.apply_filters()

    def _parse_status(self, quest_name):
        # Returns the full data dict: {"status": int, "timestamp": str/None}
        val = self.current_status_data.get(quest_name)
        
        if val is None or not isinstance(val, dict):
             # Default structure for not tracked quests
             return {"status": QuestStatus.NOT_STARTED, "timestamp": None}
            
        return val

    def get_progress_stats(self):
        completed = 0
        total = 0
        # Check all currently loaded widgets
        for qw in self.quest_widgets:
            total += 1
            if qw.status == QuestStatus.COMPLETED: 
                completed += 1
                
        # Check all pending quests
        for item in self.pending_quests:
            if SECTION_MARKER in item: continue
            total += 1
            # Get status from the data dict
            status_data = self._parse_status(item)
            if status_data["status"] == QuestStatus.COMPLETED: 
                completed += 1
        return completed, total

    def refresh_tab_state(self, current_data):
        self.current_status_data = current_data
        for quest_widget in self.quest_widgets:
            quest_name = quest_widget.quest_button.text()
            # Pass the full status data dict
            status_data = self._parse_status(quest_name)
            quest_widget.refresh_data(status_data)
            
        self.update_progress()
        self.apply_filters() # Re-check visibility as status changed
        
    def _add_quest(self, name):
        # Pass the full status data dict
        status_data = self._parse_status(name)
            
        quest_widget = QuestWidget(name, status_data, parent=self.content_widget)
        quest_widget.original_index = len(self.quest_widgets)
        
        quest_widget.status_changed.connect(self._on_quest_changed)
        quest_widget.request_load.connect(self.wiki_requested.emit)
        
        self.content_layout.addWidget(quest_widget)
        self.quest_widgets.append(quest_widget)
        return quest_widget

    def _on_quest_changed(self, name, status):
        # The widget emits the name and new status (int)
        self.quest_status_changed.emit(name, status)
        self.update_progress()
        
        # The widget's internal state already changed; need to re-fetch/re-filter 
        if self.current_filter_mode != FilterMode.ALL:
            self.apply_filters()

    def set_filter_mode(self, mode):
        self.current_filter_mode = mode
        self.apply_filters()

    def filter_content(self, text):
        self.current_filter_text = text.lower()
        self.apply_filters()

    def apply_filters(self):
        """
        Consolidated logic to handle visibility based on:
        1. Search Text
        2. Filter Mode (All, Not Started, In-Progress, Completed)
        """
        self.content_widget.setUpdatesEnabled(False)
        
        mode = self.current_filter_mode
        search = self.current_filter_text
        
        for section in self.sections:
            section_has_visible = False
            for qw in section['quests']:
                # 1. Check Search Match
                text_match = True
                if search:
                    text_match = search in qw.quest_button.text().lower()
                
                # 2. Check Status Match
                status_match = True
                if mode == FilterMode.NOT_STARTED:
                    status_match = (qw.status == QuestStatus.NOT_STARTED)
                elif mode == FilterMode.IN_PROGRESS:
                    status_match = (qw.status == QuestStatus.IN_PROGRESS)
                elif mode == FilterMode.COMPLETED:
                    status_match = (qw.status == QuestStatus.COMPLETED)
                
                # Final Visibility
                is_visible = text_match and status_match
                qw.setVisible(is_visible)
                
                if is_visible:
                    section_has_visible = True
            
            # Show/Hide Section Header
            if section['header']:
                section['header'].setVisible(section_has_visible)
                
        self.content_widget.setUpdatesEnabled(True)

    def reset_clicked(self):
        dlg = CustomDialog("Confirm Reset", f"Are you sure you want to reset all progress for {self.campaign_name}?", self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.reset_requested.emit(self.campaign_name)

    def update_progress(self):
        done, total = self.get_progress_stats()
        if total == 0: return
        percent = int((done/total)*100)
        self.percent_label.setText(f"{percent}%")
        self.campaign_progress_bar.setMaximum(total)
        self.campaign_progress_bar.setValue(done)