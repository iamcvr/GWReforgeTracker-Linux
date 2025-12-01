# ui/main_window.py
import os
import copy
import logging
from urllib.parse import quote
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFrame, QLabel, QPushButton, QLineEdit, QTabWidget, QProgressBar, QStackedWidget, QGraphicsDropShadowEffect, QDialog, QMenu, QSizePolicy
from PySide6.QtCore import QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QAction
from database import DataManager
from scraper import DatabaseSyncer
from config import AppConfig, ThemeColors, CAMPAIGN_ORDER
from .style import create_custom_icon, get_stylesheet
from .widgets import ProfileSelectorWidget, FilterSelectorWidget
from .dialogs import CustomDialog
from .tabs import CampaignTab
from .browser import CustomWebPage, RoundedWebEngineView

# NEW: Global state to suppress redundant logging
_LAST_FAILED_URL = ""

class GuildWarsTracker(QMainWindow):
    def __init__(self, profile_name=None, auto_close=False):
        super().__init__()
        self.setWindowTitle(AppConfig.APP_TITLE) 
        self.resize(AppConfig.WINDOW_WIDTH, AppConfig.WINDOW_HEIGHT)
        
        self.data = DataManager()
        self.syncer = DatabaseSyncer()
        self.syncer.sync_finished.connect(self._on_sync_finished)
        self.syncer.progress_updated.connect(lambda p, m: self.sync_button.setText(f"{m} ({p}%)"))
        
        self.game_check_timer = QTimer()
        self.game_check_timer.timeout.connect(self.check_game_running)
        if auto_close: self.game_check_timer.start(AppConfig.AUTO_CLOSE_CHECK_INTERVAL_MS)

        self.search_debounce_timer = QTimer()
        self.search_debounce_timer.setSingleShot(True)
        self.search_debounce_timer.setInterval(AppConfig.SEARCH_DEBOUNCE_MS)
        self.search_debounce_timer.timeout.connect(self._filter_all_tabs)
        
        self.dark_mode = self.data.get_theme()
        
        # Store the last requested quest name for error handling
        self.last_requested_quest_name = "" 

        self._setup_ui()
        self._build_tabs()
        self.setStyleSheet(get_stylesheet())
        self.update_theme_btn_style()

        if profile_name and profile_name in self.data.get_profiles():
            self.change_profile(profile_name)

    def check_game_running(self):
        try:
            tasks = os.popen('tasklist').read()
            running = False
            for process in AppConfig.GAME_PROCESS_NAMES:
                if process in tasks:
                    running = True; break
            if not running: 
                logging.info("Game process not found. Closing application.")
                self.close()
        except Exception as e: 
            logging.error(f"Error checking game process: {e}")

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(25) 

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
        
        search_btn = QPushButton(objectName="HeaderBtn")
        search_btn.setIcon(create_custom_icon("search", ThemeColors.WHITE))
        search_btn.setIconSize(QSize(20, 20))
        search_btn.setFixedSize(36, 36)
        search_btn.setToolTip("Search Wiki")
        search_btn.clicked.connect(self.search_wiki_direct)
        head_row.addWidget(search_btn)

        self.theme_button = QPushButton(objectName="HeaderBtn")
        self.theme_button.setIconSize(QSize(20, 20))
        self.theme_button.setFixedSize(36, 36)
        self.theme_button.setToolTip("Toggle Wiki Theme")
        self.theme_button.clicked.connect(self.toggle_theme)
        head_row.addWidget(self.theme_button)
        
        info_btn = QPushButton(objectName="HeaderBtn")
        info_btn.setIcon(create_custom_icon("info", ThemeColors.WHITE))
        info_btn.setIconSize(QSize(20, 20))
        info_btn.setFixedSize(36, 36)
        info_btn.setToolTip("About & Legal")
        info_btn.clicked.connect(self.show_about)
        head_row.addWidget(info_btn)
        l_layout.addLayout(head_row)
        
        # --- NEW FILTER/SORT ROW ---
        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)
        # CRITICAL: This layout itself must align items to the top
        filter_row.setAlignment(Qt.AlignmentFlag.AlignTop) 
        
        # New Animated Filter Selector
        self.filter_selector = FilterSelectorWidget()
        self.filter_selector.filter_changed.connect(self.apply_filter_mode)
        # Explicitly set alignment for the widget within the layout
        filter_row.addWidget(self.filter_selector, 0, Qt.AlignmentFlag.AlignTop)
        
        self.search_input = QLineEdit()
        self.search_input.setObjectName("PillSearchInput") # Styled in style.py
        self.search_input.setPlaceholderText("Search...")
        self.search_input.returnPressed.connect(self.search_wiki_direct)
        self.search_input.textChanged.connect(self.on_search_text_changed)
        
        # STYLE FIX: Border radius 18px makes it a perfect pill shape (half of 36px height)
        self.search_input.setFixedHeight(36)
        # REMOVED EMBEDDED CSS: Now uses PillSearchInput objectName
        
        # Explicitly set alignment for the search input as well
        filter_row.addWidget(self.search_input, 1, Qt.AlignmentFlag.AlignTop)
        
        l_layout.addLayout(filter_row)
        # ---------------------------

        l_layout.addWidget(QLabel("Character Profile", objectName="SubText"))
        
        prof_layout = QHBoxLayout()
        self.profile_selector = ProfileSelectorWidget()
        self.profile_selector.update_state(self.data.get_profiles(), self.data.current_profile_name)
        self.profile_selector.profile_changed.connect(self.change_profile)
        prof_layout.addWidget(self.profile_selector, 1) 
        
        tools_layout = QHBoxLayout()
        tools_layout.setSpacing(5)
        new_btn = QPushButton("+", objectName="ToolBtn")
        new_btn.setFixedSize(40, 40)
        new_btn.setToolTip("Create New Profile")
        new_btn.clicked.connect(self.create_new_profile)
        tools_layout.addWidget(new_btn)
        del_btn = QPushButton(objectName="ToolBtn")
        del_btn.setIcon(create_custom_icon("trash", ThemeColors.RED))
        del_btn.setFixedSize(40, 40)
        del_btn.setToolTip("Delete Current Profile")
        del_btn.clicked.connect(self.delete_current_profile)
        tools_layout.addWidget(del_btn)
        prof_layout.addLayout(tools_layout)
        prof_layout.setAlignment(tools_layout, Qt.AlignmentFlag.AlignTop)
        l_layout.addLayout(prof_layout)
        
        self.tabs_widget = QTabWidget()
        l_layout.addWidget(self.tabs_widget)

        footer = QVBoxLayout()
        prog_row = QHBoxLayout()
        prog_row.addWidget(QLabel("Global Progress", objectName="SubText"))
        prog_row.addStretch()
        self.global_count_label = QLabel("0 / 0", objectName="SubText")
        self.global_count_label.setStyleSheet(f"color: {ThemeColors.GOLD}; font-weight: bold;")
        prog_row.addWidget(self.global_count_label)
        footer.addLayout(prog_row)
        
        self.global_progress_bar = QProgressBar()
        self.global_progress_bar.setFixedHeight(18) 
        self.global_progress_bar.setTextVisible(True)
        footer.addWidget(self.global_progress_bar)
        
        self.sync_button = QPushButton("Sync Database", objectName="PrimaryBtn")
        self.sync_button.clicked.connect(self.start_sync)
        footer.addWidget(self.sync_button)
        l_layout.addLayout(footer)

        right_panel = QFrame(objectName="CardPanel")
        r_shadow = QGraphicsDropShadowEffect()
        r_shadow.setBlurRadius(30); r_shadow.setColor(QColor(0,0,0,120)); r_shadow.setOffset(0, 10)
        right_panel.setGraphicsEffect(r_shadow)
        r_layout = QVBoxLayout(right_panel)
        r_layout.setContentsMargins(0,0,0,0)
        
        self.stack_widget = QStackedWidget()
        welcome = QWidget()
        w_layout = QVBoxLayout(welcome)
        w_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        w_title = QLabel("WELCOME TO\nTHE QUEST JOURNAL", objectName="H1")
        w_title.setStyleSheet(f"font-size: 36px; color: {ThemeColors.GOLD};")
        w_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        w_layout.addWidget(w_title)
        w_layout.addWidget(QLabel("Select a quest to view details", objectName="SubText"), alignment=Qt.AlignmentFlag.AlignCenter)
        self.stack_widget.addWidget(welcome)
        
        self.web_view = RoundedWebEngineView()
        self.web_view.setPage(CustomWebPage(self.web_view)) 
        self.web_view.loadStarted.connect(self.show_loading)
        # Connect loadFinished to a new slot that checks for success/failure
        self.web_view.loadFinished.connect(self.handle_load_finished) 
        self.stack_widget.addWidget(self.web_view)

        self.loading_screen = QWidget()
        l_layout = QVBoxLayout(self.loading_screen)
        l_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_bar = QProgressBar()
        self.loading_bar.setFixedWidth(300)
        self.loading_bar.setRange(0, 0)
        self.loading_bar.setStyleSheet(f"QProgressBar {{ background: #222; border-radius: 10px; height: 10px; }} QProgressBar::chunk {{ background: {ThemeColors.GOLD}; border-radius: 10px; }}")
        l_layout.addWidget(QLabel("DECRYPTING...", objectName="H2"))
        l_layout.addWidget(self.loading_bar)
        self.stack_widget.addWidget(self.loading_screen)
        
        r_layout.addWidget(self.stack_widget)
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, 1) 

    def apply_filter_mode(self, mode):
        # Applies to all tabs
        for i in range(self.tabs_widget.count()):
            tab = self.tabs_widget.widget(i)
            if isinstance(tab, CampaignTab):
                tab.set_filter_mode(mode)

    def _build_tabs(self):
        for i in range(self.tabs_widget.count()):
            tab = self.tabs_widget.widget(i)
            if isinstance(tab, CampaignTab): tab.stop_loading()

        self.tabs_widget.clear()
        self.tab_map = {} 
        current_data = self.data.get_current_quests()
        
        for camp in CAMPAIGN_ORDER:
            if camp in self.data.quest_db:
                tab = CampaignTab(camp, self.data.quest_db[camp], current_data)
                tab.quest_status_changed.connect(self.handle_quest_update)
                tab.reset_requested.connect(self.handle_campaign_reset)
                tab.wiki_requested.connect(self.load_quest)
                self.tabs_widget.addTab(tab, camp)
                self.tab_map[camp] = tab
        self.update_global_progress()

    def handle_quest_update(self, name, status):
        self.data.set_status(name, status)
        self.update_global_progress()
        
    def handle_campaign_reset(self, campaign_name):
        self.data.reset_campaign(campaign_name)
        current_data = self.data.get_current_quests()
        if campaign_name in self.tab_map:
            self.tab_map[campaign_name].refresh_tab_state(current_data)
        self.update_global_progress()

    def create_new_profile(self):
        dlg = CustomDialog("New Profile", "Enter a name for the new character profile:", self, is_confirmation=False, show_input=True)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name = dlg.get_input_text().strip()
            if name:
                if self.data.create_profile(name):
                    self.profile_selector.update_state(self.data.get_profiles(), self.data.current_profile_name) 
                    self._build_tabs() 
                else:
                    CustomDialog("Error", "Profile already exists or invalid name.", self, is_confirmation=False).exec()

    def delete_current_profile(self):
        current = self.data.current_profile_name
        if len(self.data.get_profiles()) <= 1:
            CustomDialog("Error", "Cannot delete the last profile.", self, is_confirmation=False).exec()
            return
        dlg = CustomDialog("Delete Profile", f"Are you sure you want to delete '{current}'?\nThis cannot be undone.", self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            if self.data.delete_profile(current):
                self.profile_selector.update_state(self.data.get_profiles(), self.data.current_profile_name) 
                self._build_tabs() 

    def change_profile(self, name):
        if not name or name == self.data.current_profile_name: return
        self.data.switch_profile(name)
        self.profile_selector.update_state(self.data.get_profiles(), self.data.current_profile_name) 
        current_data = self.data.get_current_quests()
        
        if self.tabs_widget.count() > 0:
            for i in range(self.tabs_widget.count()):
                tab = self.tabs_widget.widget(i)
                if isinstance(tab, CampaignTab):
                    tab.refresh_tab_state(current_data)
            self.update_global_progress()
        else:
            self._build_tabs()

    def load_quest(self, quest_name):
        self.show_loading()
        self.last_requested_quest_name = quest_name # Store quest name
        
        if "Reach Level" in quest_name: 
            url = "https://wiki.guildwars.com/wiki/Legendary_Defender_of_Ascalon"
        else:
            encoded = quote(quest_name.replace(" ", "_"))
            url = f"https://wiki.guildwars.com/wiki/{encoded}"

        # --- CACHE LOGIC ---
        cached_html = self.data.get_cached_content(url)
        
        if cached_html:
            self.web_view.setHtml(cached_html, QUrl(url))
        else:
            self.web_view.setUrl(QUrl(url))

    def show_loading(self):
        self.stack_widget.setCurrentIndex(2)
    
    def handle_load_finished(self, ok):
        global _LAST_FAILED_URL
        
        if ok:
            _LAST_FAILED_URL = "" # Clear failed status on success
            self.finalize_page()
        else:
            failed_url = self.web_view.url().toString()
            
            # Suppress repetitive logging if the URL is the same
            if failed_url != _LAST_FAILED_URL:
                 logging.warning(f"Failed to load URL: {failed_url}. Showing custom error message.")
                 _LAST_FAILED_URL = failed_url
            
            # Encode the quest name for use in a JavaScript search function
            encoded_quest = quote(self.last_requested_quest_name)
            
            error_html = f"""
                <script>
                    function searchWiki() {{
                        // Use the last requested quest name to perform a new search
                        const questName = "{encoded_quest}"; 
                        const searchUrl = `https://wiki.guildwars.com/index.php?search=${{questName}}`;
                        // Redirect the web view itself
                        window.location.href = searchUrl;
                    }}
                </script>
                <style>
                    body {{ background-color: #1a1a1a; color: {ThemeColors.WHITE}; font-family: '{AppConfig.FONT_FAMILY}'; text-align: center; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 90vh; margin: 0; }}
                    .card {{ background-color: #252525; border: 1px solid #444; border-radius: 16px; padding: 30px; max-width: 400px; }}
                    .header {{ color: {ThemeColors.RED}; font-size: 24px; font-weight: bold; margin-bottom: 10px; }}
                    .message {{ color: {ThemeColors.GREY}; font-size: 14px; margin-bottom: 20px; }}
                    .btn {{ 
                        background-color: rgba(212, 175, 55, 0.15); 
                        color: {ThemeColors.GOLD}; 
                        border: 1px solid {ThemeColors.GOLD}; 
                        border-radius: 8px; 
                        padding: 10px 15px; 
                        text-decoration: none; 
                        font-weight: 600;
                        cursor: pointer;
                        display: inline-block;
                        transition: background-color 0.1s;
                    }}
                    .btn:hover {{ background-color: rgba(212, 175, 55, 0.25); }}
                </style>
                <div class="card">
                    <div class="header">WIKI PAGE UNAVAILABLE</div>
                    <div class="message">
                        We couldn't load the wiki page for this quest or there is no specific entry.
                        <br><br>
                        Quest Name: {self.last_requested_quest_name}
                    </div>
                    <button class="btn" onclick="searchWiki()">Check Wiki Search</button>
                </div>
            """
            
            # Set the error HTML and remain on the view stack position 1 (web view)
            self.web_view.setHtml(error_html, QUrl("https://wiki.guildwars.com"))
            self.stack_widget.setCurrentIndex(1) 
            

    def search_wiki_direct(self):
        text = self.search_input.text()
        self.show_loading()
        # Store for potential error handling if this search fails
        self.last_requested_quest_name = text 
        
        if text:
            encoded = quote(text)
            url = f"https://wiki.guildwars.com/index.php?search={encoded}"
            self.web_view.setUrl(QUrl(url))
        else:
            self.web_view.setUrl(QUrl("https://wiki.guildwars.com/index.php?title=Special%3ASearch"))

    def on_search_text_changed(self, text):
        self.search_debounce_timer.start()

    def _filter_all_tabs(self):
        text = self.search_input.text().lower()
        has_match = False
        first_idx = -1
        
        for i in range(self.tabs_widget.count()):
            tab = self.tabs_widget.widget(i)
            if isinstance(tab, CampaignTab):
                tab.filter_content(text)
                visible_items = False
                for section in tab.sections:
                    if section['header'].isVisible():
                        visible_items = True; break
                
                if i == self.tabs_widget.currentIndex() and visible_items: has_match = True
                if first_idx == -1 and visible_items: first_idx = i

        if not has_match and first_idx != -1:
            self.tabs_widget.setCurrentIndex(first_idx)

    def update_global_progress(self):
        total_q = 0; total_c = 0
        for tab in self.tab_map.values():
            c, t = tab.get_progress_stats()
            total_c += c; total_q += t
        
        self.global_count_label.setText(f"{total_c} / {total_q}")
        if total_q > 0:
            self.global_progress_bar.setMaximum(total_q)
            self.global_progress_bar.setValue(total_c)
        else:
            self.global_progress_bar.setMaximum(1)
            self.global_progress_bar.setValue(0)

    def start_sync(self):
        if self.syncer.isRunning():
            logging.info("Sync already running.")
            return

        self.sync_button.setText("Syncing...")
        self.sync_button.setEnabled(False)
        snapshot = copy.deepcopy(self.data.quest_db) 
        self.syncer.set_current_db(snapshot)
        self.syncer.start()

    def _on_sync_finished(self, new_db, errors):
        self.sync_button.setText("Sync Database")
        self.sync_button.setEnabled(True)
        if new_db:
            # Critical: Update the master quest database AND ensure status integrity
            self.data.update_quest_db(new_db) 
            self._build_tabs()
            
            if errors:
                msg = "Sync completed with warnings (local data preserved):\n\n" + "\n".join(errors)
                logging.warning(f"Sync finished with errors: {errors}")
                CustomDialog("Sync Warnings", msg, self, is_confirmation=False).exec()
            else:
                logging.info("Database Synced successfully.")
                CustomDialog("Success", "Database Synced.", self, is_confirmation=False).exec()
    
    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.data.set_theme(self.dark_mode)
        self.update_theme_btn_style()
        self.web_view.reload()

    def update_theme_btn_style(self):
        if self.dark_mode:
             icon_name = "moon"
             self.theme_button.setStyleSheet("background-color: rgba(123, 104, 238, 0.2); color: #fff; border: 1px solid #7B68EE;")
        else:
             icon_name = "sun"
             self.theme_button.setStyleSheet(f"background-color: {ThemeColors.GOLD}; color: #000; border: 1px solid {ThemeColors.GOLD};")
        self.theme_button.setIcon(create_custom_icon(icon_name, ThemeColors.WHITE if self.dark_mode else "#000"))
    
    def show_about(self):
        disclaimer = (
            f"<h3 style='color: {ThemeColors.GOLD};'>{AppConfig.APP_TITLE} v{AppConfig.APP_VERSION}</h3>"
            "<p>Fan-made Guild Wars Quest Tracker.</p>"
            "<p><b>Created by Akito</b><br>"
            "<hr>"
            "<p><b>LEGAL DISCLAIMER:</b></p>"
            "<p style='font-size: 11px;'>"
            "&bull; This tool is <b>not</b> affiliated with, endorsed, sponsored, or approved by ArenaNet, LLC or NCSoft Corporation.<br>"
            "&bull; 'Guild Wars', 'ArenaNet', 'NCSoft', and all associated logos and designs are trademarks or registered trademarks of NCSoft Corporation.<br>"
            "&bull; All game content is property of their respective owners and the <a href='https://wiki.guildwars.com'>Guild Wars Wiki</a> community (GNU FDL 1.2)."
            "</p>"
        )
        CustomDialog("About & Legal", disclaimer, self, is_confirmation=False).exec()

    def finalize_page(self):
        common_css = """
        * { box-sizing: border-box; }
        body, .mw-body, #content, .mw-parser-output { font-family: 'Segoe UI', sans-serif !important; line-height: 1.6 !important; }
        #mw-navigation, #mw-page-base, #mw-head-base, #footer, #mw-panel, #p-personal, #p-logo, #p-navigation, #p-search, #p-tb, #p-lang, #side, #left-navigation, #right-navigation, .mw-editsection, #siteNotice, #column-one, #footer { display: none !important; }
        html { scroll-behavior: smooth; }
        #globalWrapper, .mw-body { width: 100% !important; padding: 0 !important; margin: 0 !important; background: transparent !important; }
        #content { margin: 0 !important; padding: 15px 20px !important; border: none !important; background: transparent !important; width: 100% !important; }
        body, html { overflow-x: hidden !important; width: 100% !important; margin: 0 !important; }
        table, .wikitable { max-width: 100% !important; width: auto !important; display: block !important; overflow-x: auto !important; box-sizing: border-box !important; }
        img { border-radius: 4px; max-width: 100% !important; height: auto !important; }
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: rgba(0,0,0,0.1); }
        ::-webkit-scrollbar-thumb { background: #888; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #555; }
        """
        if not self.dark_mode:
            css = common_css
        else:
            css = common_css + f"""
            body, html, #globalWrapper, .mw-body, #content {{ background-color: #1a1a1a !important; color: #e0e0e0 !important; }}
            .mw-parser-output {{ color: #e0e0e0 !important; }}
            h1, h2, h3, h4, h5, h6, p, li, dt, dd, span, div, td, th {{ color: #e0e0e0 !important; background-color: transparent !important; word-wrap: break-word !important; }}
            .infobox, .navbox, .toc, .wikitable, .thumb {{ background-color: #252525 !important; border-color: #444 !important; color: #e0e0e0 !important; }}
            div[style*="background"], span[style*="background"] {{ background-color: transparent !important; color: inherit !important; }}
            input[type="search"], input[type="text"], input, select, textarea, .oo-ui-textInputWidget .oo-ui-inputWidget-input, .oo-ui-dropdownWidget-handle, .oo-ui-buttonElement-button, #searchInput {{ background-color: #ffffff !important; color: #000000 !important; border: 1px solid #ccc !important; }}
            .oo-ui-labelElement-label {{ color: #000000 !important; }}
            .oo-ui-iconElement-icon {{ filter: none !important; }}
            a {{ color: #ce93d8 !important; text-decoration: none; }}
            a:hover {{ color: #fff !important; text-decoration: underline; }}
            a.new {{ color: {ThemeColors.RED} !important; }}
            table, .wikitable {{ background-color: #252525 !important; color: #ddd !important; border: 1px solid #444 !important; }}
            th {{ background-color: #333 !important; color: {ThemeColors.GOLD} !important; padding: 8px !important; }}
            td {{ border-color: #444 !important; padding: 6px !important; }}
            .mwe-popups {{ background-color: #ffffff !important; border: 1px solid #a2a9b1 !important; box-shadow: 0 30px 90px -20px rgba(0,0,0,0.3) !important; color: #222222 !important; }}
            .mwe-popups div, .mwe-popups p, .mwe-popups span, .mwe-popups h1, .mwe-popups h2, .mwe-popups-extract {{ color: #222222 !important; background-color: transparent !important; }}
            .mwe-popups a, .mwe-popups a:visited {{ color: #0645ad !important; text-decoration: none !important; }}
            .mwe-popups::after {{ border-top-color: #ffffff !important; }}
            .mwe-popups::before {{ border-top-color: #a2a9b1 !important; }}
            .mwe-popups-settings-icon {{ opacity: 0.6 !important; }}
            ::-webkit-scrollbar-track {{ background: #1a1a1a; }}
            ::-webkit-scrollbar-thumb {{ background: #444; }}
            ::-webkit-scrollbar-thumb:hover {{ background: {ThemeColors.GOLD}; }}
            """
        
        js = f"""
        if (document.head) {{
            var s = document.createElement('style'); s.innerHTML = `{css}`; document.head.appendChild(s);
            var observer = new MutationObserver(function(mutations) {{
                var searchInput = document.querySelector('.oo-ui-inputWidget-input');
                if (searchInput) {{ searchInput.style.backgroundColor = '#ffffff'; searchInput.style.color = '#000000'; }}
            }});\
            observer.observe(document.body, {{ childList: true, subtree: true }});
            var content = document.getElementById('mw-content-text');
            if(content && !document.querySelector('form') && !document.querySelector('input') && (content.innerText.trim().length < 50 || content.innerText.includes("There is currently no text in this page"))) {{
                 content.innerHTML = "<div style='display:flex;justify-content:center;align-items:center;height:80vh;color:#888;'><h2>No Wiki Content Available</h2></div>";
            }}
        }}
        """
        self.web_view.page().runJavaScript(js)
        QTimer.singleShot(150, lambda: self.stack_widget.setCurrentIndex(1))

    def closeEvent(self, event):
        if self.game_check_timer.isActive():
            self.game_check_timer.stop()
        if self.syncer.isRunning():
            self.syncer.requestInterruption()
            self.syncer.quit()
            self.syncer.wait() 
        try:
            # PERFORMANCE: Clear memory cache on close to prevent bloat
            self.web_view.page().profile().clearHttpCache()
        except Exception as e:
            logging.error(f"Failed to clear WebEngine cache on close: {e}")
        event.accept()