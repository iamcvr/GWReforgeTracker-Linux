import sys
import logging
import copy
import requests
import json
import os
import datetime
from urllib.parse import quote
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- PYSIDE6 IMPORTS ---
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QTabWidget, QFrame, QPushButton, 
                             QSplitter, QStackedWidget, QMessageBox, QProgressBar, QCheckBox, 
                             QScrollArea, QGraphicsDropShadowEffect, QSizePolicy)
from PySide6.QtCore import Qt, QUrl, QThread, Signal, QSize, QRect, QTimer
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtGui import QColor, QPainter, QRegion, QPainterPath, QIcon, QPixmap, QPen

# ==========================================
#  CONFIG
# ==========================================
APP_TITLE = "Guild Wars Reforge Quest Tracker" 
APP_VERSION = "1.0.0 Release" 
FONT_FAMILY = "Segoe UI" 

FILES = { "DB": "gw1_db.json", "USER": "gw1_user.json", "SETTINGS": "gw1_settings.json" }

REQUEST_HEADERS = { 
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36' 
}

CAMPAIGN_URLS = {
    "Prophecies": "https://wiki.guildwars.com/wiki/List_of_Prophecies_quests",
    "Factions": "https://wiki.guildwars.com/wiki/List_of_Factions_quests",
    "Nightfall": "https://wiki.guildwars.com/wiki/List_of_Nightfall_quests",
    "Eye of the North": "https://wiki.guildwars.com/wiki/List_of_Eye_of_the_North_quests"
}

CAMPAIGN_ORDER = ["Prophecies", "Factions", "Nightfall", "Eye of the North", "Beyond"]
SECTION_MARKER = "---" 

INITIAL_QUEST_DB = {
    "Prophecies": [f"{SECTION_MARKER} PRIMARY MISSIONS {SECTION_MARKER}", "Ascalon (Pre-Searing) Tutorials", "The Great Northern Wall"],
    "Factions": [f"{SECTION_MARKER} PRIMARY MISSIONS {SECTION_MARKER}", "Minister Cho's Estate"],
    "Nightfall": [f"{SECTION_MARKER} PRIMARY MISSIONS {SECTION_MARKER}", "Chahbek Village"],
    "Eye of the North": [f"{SECTION_MARKER} PRIMARY MISSIONS {SECTION_MARKER}", "Boreal Station"],
    "Beyond": [f"{SECTION_MARKER} WAR IN KRYTA {SECTION_MARKER}", "The War in Kryta"]
}

# ==========================================
#  STYLESHEET
# ==========================================

def get_stylesheet():
    accent_gold = "#D4AF37"
    accent_green = "#4CAF50" # Green for In-Progress
    accent_red = "#FF6B6B"
    text_white = "#ECECEC"
    text_grey = "#A0A0A5"
    
    return f"""
    QMainWindow {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #141414, stop:1 #1E1E24);
    }}
    
    QWidget {{ font-family: "{FONT_FAMILY}"; font-size: 14px; color: {text_white}; }}

    /* --- PANELS --- */
    QFrame#CardPanel {{
        background-color: rgba(35, 35, 40, 0.9);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 24px;
    }}
    QFrame#Transparent {{ background: transparent; border: none; }}

    /* --- SCROLLBARS --- */
    QScrollBar:vertical {{ border: none; background: transparent; width: 6px; margin: 0px; }}
    QScrollBar::handle:vertical {{ background: rgba(255,255,255,0.2); min-height: 20px; border-radius: 3px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}

    /* --- BUTTONS --- */
    QPushButton {{
        background-color: rgba(255, 255, 255, 0.05);
        color: {text_white};
        border-radius: 20px;
        padding: 8px 16px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }}
    
    /* SYNC BUTTON */
    QPushButton#PrimaryBtn {{
        background-color: {accent_gold};
        color: #111; border: none;
    }}
    QPushButton#PrimaryBtn:hover {{ background-color: #F4CF57; }}
    
    /* HEADER BUTTONS (CIRCULAR) */
    QPushButton#HeaderBtn {{
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 18px; /* Perfect Circle for 36px size */
        border: 1px solid rgba(255, 255, 255, 0.1);
    }}
    QPushButton#HeaderBtn:hover {{
        background-color: rgba(255, 255, 255, 0.15);
        border: 1px solid {accent_gold};
    }}
    
    /* RESET BUTTON */
    QPushButton#DangerBtn {{ 
        background-color: rgba(255, 107, 107, 0.1); 
        color: {accent_red}; 
        border: 1px solid {accent_red}; 
        border-radius: 20px;
    }}
    QPushButton#DangerBtn:hover {{ background-color: rgba(255, 107, 107, 0.2); color: #FF8888; }}

    /* --- CHECKBOXES (TRI-STATE) --- */
    QCheckBox {{ spacing: 15px; background: transparent; }}
    QCheckBox::indicator {{ 
        width: 18px; height: 18px; 
        border: 2px solid #666; 
        border-radius: 6px; 
        background-color: #222; 
    }}
    QCheckBox::indicator:hover {{ border-color: {text_white}; }}
    
    /* COMPLETED STATE */
    QCheckBox::indicator:checked {{ 
        background-color: {accent_gold}; 
        border-color: {accent_gold}; 
    }}
    
    /* IN-PROGRESS STATE (Indeterminate) */
    QCheckBox::indicator:indeterminate {{
        background-color: {accent_green};
        border-color: {accent_green};
    }}

    /* --- INPUTS --- */
    QLineEdit {{
        background-color: rgba(0, 0, 0, 0.3);
        border-radius: 20px;
        padding: 10px 15px;
        color: {text_white};
        border: 1px solid rgba(255, 255, 255, 0.1);
    }}
    QLineEdit:focus {{ border: 1px solid {accent_gold}; }}

    /* --- QUEST PILLS (STRICT WIDTH) --- */
    QPushButton#QuestLabel {{
        background-color: rgba(255, 255, 255, 0.03);
        border-radius: 18px;
        padding: 8px 15px;
        text-align: left;
        border: 1px solid transparent;
        max-width: 315px;
    }}
    QPushButton#QuestLabel:hover {{
        background-color: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }}

    /* --- TIMESTAMP LABEL --- */
    QLabel#TimeLabel {{
        color: {text_grey};
        font-size: 11px;
        font-style: italic;
        margin-left: 5px;
    }}

    /* --- TABS --- */
    QTabWidget::pane {{ border: none; background: transparent; }}
    QTabBar::tab {{ background: transparent; color: {text_grey}; padding: 8px 12px; font-weight: bold; border-bottom: 2px solid transparent; }}
    QTabBar::tab:selected {{ color: {accent_gold}; border-bottom: 2px solid {accent_gold}; }}
    QTabBar::scroller {{ width: 0px; }}

    /* --- HEADERS --- */
    QLabel#H1 {{ font-size: 24px; font-weight: bold; color: {text_white}; }}
    QLabel#H2 {{ font-size: 13px; font-weight: bold; color: {accent_gold}; margin-top: 15px; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1px; }}
    QLabel#SubText {{ font-size: 12px; color: {text_grey}; }}
    
    QProgressBar {{
        background: rgba(0,0,0,0.4);
        border-radius: 8px;
        text-align: center;
        color: #fff;
        font-weight: bold;
        font-size: 11px;
        border: none;
    }}
    QProgressBar::chunk {{ background-color: {accent_gold}; border-radius: 8px; }}
    
    QSplitter::handle {{ background: transparent; }}
    """

# ==========================================
#  BACKEND LOGIC
# ==========================================

class DataManager:
    def __init__(self):
        self.db_file = FILES["DB"]
        self.user_file = FILES["USER"]
        self.db = self._load(self.db_file, INITIAL_QUEST_DB)
        self.user = self._load(self.user_file, {})

    def _load(self, filepath, default):
        if not os.path.exists(filepath): return default
        try:
            with open(filepath, 'r', encoding='utf-8') as f: return json.load(f)
        except: return default

    def _save(self, filepath, data):
        try:
            with open(filepath, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4)
        except: pass

    def save_all(self):
        self._save(self.db_file, self.db)
        self._save(self.user_file, self.user)
    
    def get_status_data(self, quest):
        val = self.user.get(quest, None)
        if val is None: return None
        if isinstance(val, bool): return { "status": 2 if val else 0, "timestamp": "" }
        if isinstance(val, int): return { "status": val, "timestamp": "" }
        if isinstance(val, dict): return val
        return None
    
    def set_status(self, quest, status):
        if status > 0:
            data = {
                "status": status,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M") 
            }
            self.user[quest] = data
        elif quest in self.user: 
            del self.user[quest]
        self._save(self.user_file, self.user)

    def reset_campaign(self, campaign):
        if campaign in self.db:
            for q in self.db[campaign]:
                q_key = q if isinstance(q, str) else q.get("title")
                if q_key in self.user: del self.user[q_key]
            self._save(self.user_file, self.user)

    def set_bulk(self, quests, status):
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        for q in quests:
            if status: 
                self.user[q] = { "status": 2, "timestamp": ts } 
            elif q in self.user: 
                del self.user[q]
        self._save(self.user_file, self.user)

class DatabaseSyncer(QThread):
    progress = Signal(int, str)
    finished = Signal(dict)

    def run(self):
        session = requests.Session()
        new_db = copy.deepcopy(INITIAL_QUEST_DB)
        total = len(CAMPAIGN_URLS)
        count = 0
        
        IGNORE_EXACT = {"Quest", "Name", "Location", "Type", "Given by", "Level", "Reward", "Experience", "Gold"}

        for campaign, url in CAMPAIGN_URLS.items():
            if self.isInterruptionRequested(): return
            self.progress.emit(int((count/total)*100), f"Scanning {campaign}...")
            try:
                r = session.get(url, headers=REQUEST_HEADERS, timeout=15)
                soup = BeautifulSoup(r.content, 'html.parser')
                
                content_root = soup.find('div', {'id': 'mw-content-text'})
                if not content_root: content_root = soup
                
                tables = content_root.find_all('table')
                found_quests = set()
                
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows:
                        if row.find('th'): continue
                        cols = row.find_all('td')
                        if not cols: continue
                        
                        target_col = cols[0]
                        anchor = target_col.find('a')
                        if not anchor: continue
                        
                        href = anchor.get('href', '')
                        if not href.startswith('/wiki/'): continue
                        if any(x in href for x in ["File:", "Category:", "Special:", "Template:", "Talk:"]):
                            continue
                            
                        text = anchor.get_text().strip()
                        if len(text) < 2: continue
                        if text in IGNORE_EXACT: continue 
                        
                        found_quests.add(text)
                
                existing = [q for q in new_db[campaign] if SECTION_MARKER in q or q in INITIAL_QUEST_DB[campaign]]
                others = sorted([q for q in found_quests if q not in existing and SECTION_MARKER not in q])
                
                if others:
                    new_db[campaign] = existing + [f"{SECTION_MARKER} SIDE QUESTS {SECTION_MARKER}"] + others
            except Exception: pass
            count += 1
        self.finished.emit(new_db)

# ==========================================
#  UI COMPONENTS
# ==========================================

class CustomWebPage(QWebEnginePage):
    """ Suppresses console warnings like 'mediawiki.ui is deprecated' """
    def javaScriptConsoleMessage(self, level, msg, line, source):
        if "mediawiki.ui" in msg or "deprecated" in msg:
            return
        super().javaScriptConsoleMessage(level, msg, line, source)

class RoundedWebEngineView(QWebEngineView):
    def resizeEvent(self, event):
        path = QPainterPath()
        rect = QRect(0, 0, self.width(), self.height())
        path.addRoundedRect(rect, 24, 24)
        region = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)
        super().resizeEvent(event)

class QuestWidget(QFrame):
    status_changed = Signal(str, int)
    request_load = Signal(str)
    
    current_selected = None

    def __init__(self, name, data):
        super().__init__()
        # FIX: Robustly get status from data dict or set default
        if data and isinstance(data, dict):
            self.status = data.get("status", 0)
            self.timestamp = data.get("timestamp", "")
        else:
            self.status = 0
            self.timestamp = ""
        
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
        
        self.btn_label = QPushButton(name)
        self.btn_label.setObjectName("QuestLabel")
        self.btn_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_label.clicked.connect(self._on_click) 
        self.btn_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        text_layout.addWidget(self.btn_label)
        
        self.lbl_time = QLabel("")
        self.lbl_time.setObjectName("TimeLabel")
        self.lbl_time.setVisible(False)
        # Initialize label text if already complete
        if self.status == 2 and self.timestamp:
             self.lbl_time.setText(f"Completed: {self.timestamp}")

        text_layout.addWidget(self.lbl_time)
        
        layout.addWidget(self.checkbox)
        layout.addLayout(text_layout)
        layout.addStretch() 

        self._update_style()

    def _update_check_state(self):
        self.checkbox.blockSignals(True)
        if self.status == 2: self.checkbox.setCheckState(Qt.CheckState.Checked)
        elif self.status == 1: self.checkbox.setCheckState(Qt.CheckState.PartiallyChecked)
        else: self.checkbox.setCheckState(Qt.CheckState.Unchecked)
        self.checkbox.blockSignals(False)

    def _on_check_change(self, state):
        new_status = 0
        if state == Qt.CheckState.PartiallyChecked.value: new_status = 1
        elif state == Qt.CheckState.Checked.value: new_status = 2
        elif state == Qt.CheckState.Unchecked.value: new_status = 0
        
        self.status = new_status
        self._update_style()
        self.status_changed.emit(self.btn_label.text(), self.status)
        
        if self.status == 2:
             self.timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
             self.lbl_time.setText(f"Completed: {self.timestamp}")
        else:
             self.lbl_time.setVisible(False) 

    def _on_click(self):
        self.request_load.emit(self.btn_label.text())
        
        if QuestWidget.current_selected and QuestWidget.current_selected != self:
            QuestWidget.current_selected.lbl_time.setVisible(False)
        
        QuestWidget.current_selected = self
        
        if self.status == 2:
            self.lbl_time.setText(f"Completed: {self.timestamp}")
            self.lbl_time.setVisible(True)
        else:
            self.lbl_time.setVisible(False)

    def _update_style(self):
        if self.status == 2: # Complete
            self.btn_label.setStyleSheet("""
                QPushButton#QuestLabel {
                    background-color: rgba(212, 175, 55, 0.15); 
                    color: #888; 
                    text-decoration: line-through;
                    border: 1px solid #D4AF37;
                    border-radius: 18px;
                    text-align: left;
                    padding: 8px 15px;
                    max-width: 315px;
                }
            """)
        elif self.status == 1: # In Progress
            self.btn_label.setStyleSheet("""
                QPushButton#QuestLabel {
                    background-color: rgba(76, 175, 80, 0.15); 
                    color: #4CAF50; /* Green Text */
                    font-style: italic;
                    border: 1px solid #4CAF50;
                    border-radius: 18px;
                    text-align: left;
                    padding: 8px 15px;
                    max-width: 315px;
                }
            """)
        else: # Not Started
            self.btn_label.setStyleSheet("") 

class CampaignTab(QWidget):
    def __init__(self, campaign_name, quest_data, data_manager, parent_window):
        super().__init__()
        self.data_manager = data_manager
        self.parent_window = parent_window
        self.quest_widgets = [] 
        self.campaign_name = campaign_name
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 5, 0)
        
        h_layout = QHBoxLayout()
        self.lbl_percent = QLabel("0%", objectName="H1")
        self.lbl_percent.setStyleSheet("color: #D4AF37; font-size: 28px;") 
        h_layout.addWidget(self.lbl_percent)
        h_layout.addWidget(QLabel(f"{campaign_name.upper()}", objectName="SubText"), alignment=Qt.AlignmentFlag.AlignBottom)
        h_layout.addStretch()
        layout.addLayout(h_layout)

        self.camp_prog_bar = QProgressBar()
        self.camp_prog_bar.setFixedHeight(6)
        self.camp_prog_bar.setTextVisible(False)
        layout.addWidget(self.camp_prog_bar)
        layout.addSpacing(15)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff) 
        scroll.setStyleSheet("background: transparent;")
        
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self.vbox = QVBoxLayout(content)
        self.vbox.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.vbox.setSpacing(6)
        
        self.vbox.setContentsMargins(2, 0, 25, 0) 

        if isinstance(quest_data, list):
            for item in quest_data:
                if SECTION_MARKER in item:
                    self.vbox.addWidget(QLabel(item.replace(SECTION_MARKER, "").strip(), objectName="H2"))
                else:
                    self._add_quest(item)

        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        btn_reset = QPushButton(f"Reset {campaign_name}", objectName="DangerBtn")
        btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reset.clicked.connect(self.reset_clicked)
        layout.addWidget(btn_reset)
        
        self.update_progress()

    def _add_quest(self, name):
        data = self.data_manager.get_status_data(name)
        qw = QuestWidget(name, data)
        qw.status_changed.connect(self._on_quest_changed)
        qw.request_load.connect(self.parent_window.load_quest)
        self.vbox.addWidget(qw)
        self.quest_widgets.append(qw)

    def _on_quest_changed(self, name, status):
        self.data_manager.set_status(name, status)
        self.update_progress()
        self.parent_window.update_global_progress()

    def filter_content(self, text):
        text = text.lower()
        for qw in self.quest_widgets:
            qw.setVisible(text in qw.btn_label.text().lower())

    def reset_clicked(self):
        if QMessageBox.question(self, "Confirm Reset", f"Reset {self.campaign_name}?") == QMessageBox.StandardButton.Yes:
            self.data_manager.reset_campaign(self.campaign_name)
            for qw in self.quest_widgets:
                qw.status = 0
                qw._update_check_state()
                qw._update_style()
                qw.lbl_time.setVisible(False)
            self.update_progress()
            self.parent_window.update_global_progress()

    def update_progress(self):
        valid = self.quest_widgets
        total = len(valid)
        if total == 0: return
        done = sum(1 for qw in valid if qw.status == 2)
        percent = int((done/total)*100)
        self.lbl_percent.setText(f"{percent}%")
        self.camp_prog_bar.setMaximum(total)
        self.camp_prog_bar.setValue(done)

# ==========================================
#  MAIN WINDOW
# ==========================================

class GuildWarsTracker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE) 
        self.resize(1400, 900)
        
        self._author = "Akito" 
        
        self.data = DataManager()
        self.syncer = DatabaseSyncer()
        self.syncer.finished.connect(self._on_sync_finished)
        self.syncer.progress.connect(lambda p, m: self.btn_sync.setText(f"{m} ({p}%)"))
        
        self._setup_ui()
        self._build_tabs()
        self.setStyleSheet(get_stylesheet())

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(25) 

        left_panel = QFrame(objectName="CardPanel")
        left_panel.setFixedWidth(420)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30); shadow.setColor(QColor(0,0,0,120)); shadow.setOffset(0, 10)
        left_panel.setGraphicsEffect(shadow)

        l_layout = QVBoxLayout(left_panel)
        l_layout.setContentsMargins(25, 30, 25, 30)
        l_layout.setSpacing(15)

        head_row = QHBoxLayout()
        head_row.addWidget(QLabel("Quest Journal", objectName="H1"))
        head_row.addStretch()
        
        # --- CUSTOM ICONS ---
        btn_search = QPushButton(objectName="HeaderBtn")
        btn_search.setIcon(self.create_custom_icon("search", "#ECECEC"))
        btn_search.setIconSize(QSize(20, 20))
        btn_search.setFixedSize(36, 36)
        btn_search.setToolTip("Search Wiki")
        btn_search.clicked.connect(self.search_wiki_direct)
        head_row.addWidget(btn_search)
        
        btn_info = QPushButton(objectName="HeaderBtn")
        btn_info.setIcon(self.create_custom_icon("info", "#ECECEC"))
        btn_info.setIconSize(QSize(20, 20))
        btn_info.setFixedSize(36, 36)
        btn_info.setToolTip("About & Legal")
        btn_info.clicked.connect(self.show_about)
        head_row.addWidget(btn_info)
        
        l_layout.addLayout(head_row)
        
        self.search_inp = QLineEdit()
        self.search_inp.setPlaceholderText("Search missions...")
        self.search_inp.returnPressed.connect(self.search_wiki_direct)
        # Search all tabs simultaneously
        self.search_inp.textChanged.connect(self._filter_all_tabs)
        l_layout.addWidget(self.search_inp)

        self.tabs = QTabWidget()
        l_layout.addWidget(self.tabs)

        footer = QVBoxLayout()
        prog_info_row = QHBoxLayout()
        prog_info_row.addWidget(QLabel("Global Progress", objectName="SubText"))
        prog_info_row.addStretch()
        self.lbl_global_count = QLabel("0 / 0", objectName="SubText")
        self.lbl_global_count.setStyleSheet("color: #D4AF37; font-weight: bold;")
        prog_info_row.addWidget(self.lbl_global_count)
        footer.addLayout(prog_info_row)
        
        self.global_prog_bar = QProgressBar()
        self.global_prog_bar.setFixedHeight(18) 
        self.global_prog_bar.setTextVisible(True)
        footer.addWidget(self.global_prog_bar)
        
        self.btn_sync = QPushButton("Sync Database", objectName="PrimaryBtn")
        self.btn_sync.clicked.connect(self.start_sync)
        footer.addWidget(self.btn_sync)
        l_layout.addLayout(footer)

        right_container = QFrame(objectName="CardPanel")
        shadow_r = QGraphicsDropShadowEffect()
        shadow_r.setBlurRadius(30); shadow_r.setColor(QColor(0,0,0,120)); shadow_r.setOffset(0, 10)
        right_container.setGraphicsEffect(shadow_r)
        
        r_layout = QVBoxLayout(right_container)
        r_layout.setContentsMargins(0,0,0,0)
        
        self.stack = QStackedWidget()
        
        welcome = QWidget()
        w_layout = QVBoxLayout(welcome)
        w_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        welcome_title = QLabel("WELCOME TO\nTHE QUEST JOURNAL", objectName="H1")
        welcome_title.setStyleSheet("font-size: 36px; color: #D4AF37;")
        welcome_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        w_layout.addWidget(welcome_title)
        w_layout.addWidget(QLabel("Select a quest to view details", objectName="SubText"), alignment=Qt.AlignmentFlag.AlignCenter)
        self.stack.addWidget(welcome)
        
        self.web = RoundedWebEngineView()
        self.web.setPage(CustomWebPage(self.web)) 
        self.web.loadStarted.connect(self.show_loading)
        self.web.loadFinished.connect(self.finalize_page)
        self.stack.addWidget(self.web)

        self.loading_screen = QWidget()
        l_layout = QVBoxLayout(self.loading_screen)
        l_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_bar = QProgressBar()
        self.loading_bar.setFixedWidth(300)
        self.loading_bar.setRange(0, 0)
        self.loading_bar.setStyleSheet("""
            QProgressBar { background: #222; border-radius: 10px; height: 10px; }
            QProgressBar::chunk { background: #D4AF37; border-radius: 10px; }
        """)
        l_layout.addWidget(QLabel("DECRYPTING...", objectName="H2"))
        l_layout.addWidget(self.loading_bar)
        self.stack.addWidget(self.loading_screen)
        
        r_layout.addWidget(self.stack)

        layout.addWidget(left_panel)
        layout.addWidget(right_container, 1) 

    def create_custom_icon(self, shape, color_hex):
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        pen = QPen(QColor(color_hex))
        pen.setWidth(4)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        
        if shape == "search":
            painter.drawEllipse(12, 12, 28, 28)
            painter.drawLine(36, 36, 52, 52)
        elif shape == "info":
            font = painter.font()
            font.setBold(True)
            font.setPixelSize(36)
            font.setFamily("Segoe UI")
            painter.setFont(font)
            painter.drawText(QRect(0, 0, 64, 64), Qt.AlignCenter, "i")
            
        painter.end()
        return QIcon(pixmap)

    def _build_tabs(self):
        self.tabs.clear()
        self.tab_map = {} 
        for camp in CAMPAIGN_ORDER:
            if camp in self.data.db:
                tab = CampaignTab(camp, self.data.db[camp], self.data, self)
                self.tabs.addTab(tab, camp)
                self.tab_map[camp] = tab
        self.update_global_progress()

    def load_quest(self, quest_name):
        self.show_loading()
        encoded = quote(quest_name.replace(" ", "_"))
        url = f"https://wiki.guildwars.com/wiki/{encoded}"
        self.web.setUrl(QUrl(url))

    def show_loading(self):
        self.stack.setCurrentIndex(2)

    def search_wiki_direct(self):
        text = self.search_inp.text()
        self.show_loading()
        if text:
            encoded = quote(text)
            url = f"https://wiki.guildwars.com/index.php?search={encoded}"
            self.web.setUrl(QUrl(url))
        else:
            self.web.setUrl(QUrl("https://wiki.guildwars.com/index.php?title=Special%3ASearch"))

    def show_about(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("About & Legal")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(f"""
            <h3 style='color: #D4AF37;'>{APP_TITLE} v{APP_VERSION}</h3>
            <p>This application is a free, open-source, fan-made tool designed to assist players in tracking their Guild Wars quest progress.</p>
            <p><b>Created by Akito</b><br>
            <hr>
            <p><b>LEGAL DISCLAIMER:</b></p>
            <p style='font-size: 11px;'>
            &bull; This tool is <b>not</b> affiliated with, endorsed, sponsored, or approved by ArenaNet, LLC or NCSoft Corporation.<br>
            &bull; "Guild Wars", "ArenaNet", "NCSoft", and all associated logos and designs are trademarks or registered trademarks of NCSoft Corporation.<br>
            &bull; All game content is property of their respective owners and the <a href='https://wiki.guildwars.com'>Guild Wars Wiki</a> community (GNU FDL 1.2).
            </p>
        """)
        msg.exec()

    def finalize_page(self):
        css = """
        * { box-sizing: border-box; }
        #mw-navigation, #mw-page-base, #mw-head-base, #footer, #mw-panel, 
        #p-personal, #p-logo, #p-navigation, #p-search, #p-tb, #p-lang,
        #side, #left-navigation, #right-navigation, .mw-editsection, #siteNotice,
        #column-one, #footer { display: none !important; }

        .mw-body, #content, #column-content, #globalWrapper { 
            border: none !important; 
            margin: 0 !important; 
            padding-left: 5px !important; 
            padding-right: 5px !important;
            margin-left: 0 !important;
            background: transparent !important;
            width: 100% !important;
        }
        #bodyContent { padding-left: 5px !important; width: 100% !important; }
        body { background-color: #fff !important; overflow-x: hidden; }
        """
        js = f"var s = document.createElement('style'); s.innerHTML = `{css}`; document.head.appendChild(s);"
        self.web.page().runJavaScript(js)
        QTimer.singleShot(150, lambda: self.stack.setCurrentIndex(1))

    # --- UPDATED: SEARCH ACROSS ALL TABS ---
    def _filter_all_tabs(self, text):
        text = text.lower()
        has_match_current = False
        first_match_tab_index = -1
        
        # 1. Filter ALL tabs
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, CampaignTab):
                match_count = 0
                for qw in tab.quest_widgets:
                    visible = text in qw.btn_label.text().lower()
                    qw.setVisible(visible)
                    if visible: match_count += 1
                
                # Check if current tab has matches
                if i == self.tabs.currentIndex() and match_count > 0:
                    has_match_current = True
                
                # Record first tab with matches
                if first_match_tab_index == -1 and match_count > 0:
                    first_match_tab_index = i

        # 2. Auto-switch tab if current has no results but another does
        if not has_match_current and first_match_tab_index != -1:
            self.tabs.setCurrentIndex(first_match_tab_index)

    def _filter_tabs(self, text):
        self._filter_all_tabs(text)

    def update_global_progress(self):
        total_q = 0; total_d = 0
        for tab in self.tab_map.values():
            for qw in tab.quest_widgets:
                total_q += 1
                if qw.status == 2: total_d += 1 # Count only fully completed
        
        self.lbl_global_count.setText(f"{total_d} / {total_q}")
        if total_q > 0:
            self.global_prog_bar.setMaximum(total_q)
            self.global_prog_bar.setValue(total_d)

    def start_sync(self):
        self.btn_sync.setText("Syncing...")
        self.btn_sync.setEnabled(False)
        self.syncer.start()

    def _on_sync_finished(self, new_db):
        self.btn_sync.setText("Sync Database")
        self.btn_sync.setEnabled(True)
        if new_db:
            self.data.db = new_db
            self.data.save_all()
            self._build_tabs()
            QMessageBox.information(self, "Success", "Database Synced.")

    def closeEvent(self, event):
        self.data.save_all()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    w = GuildWarsTracker()
    w.show()
    sys.exit(app.exec())