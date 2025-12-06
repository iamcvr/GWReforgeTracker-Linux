# ui/main_window.py
import os
import sys
import copy
import logging
import subprocess
from urllib.parse import quote
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFrame, 
                             QLabel, QPushButton, QLineEdit, QProgressBar, QStackedWidget, 
                             QGraphicsDropShadowEffect, QDialog, QFileDialog, QSizePolicy, QMenu)
from PySide6.QtCore import QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QAction
from database import DataManager
from scraper import DatabaseSyncer
from updater import UpdateChecker, UpdateDownloader
from config import AppConfig, ThemeColors, CAMPAIGN_ORDER
from .style import create_custom_icon, get_stylesheet
from .widgets import ProfileSelectorWidget, FilterSelectorWidget, CampaignSelectorWidget
from .dialogs import CustomDialog, HistoryDialog
from .tabs import CampaignTab
from .browser import CustomWebPage, RoundedWebEngineView

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
        
        self.update_checker = UpdateChecker()
        self.update_checker.result_ready.connect(self.handle_update_check_result)
        self.downloader = None 
        
        self.game_check_timer = QTimer()
        self.game_check_timer.timeout.connect(self.check_game_running)
        if auto_close: self.game_check_timer.start(AppConfig.AUTO_CLOSE_CHECK_INTERVAL_MS)

        self.search_debounce_timer = QTimer()
        self.search_debounce_timer.setSingleShot(True)
        self.search_debounce_timer.setInterval(AppConfig.SEARCH_DEBOUNCE_MS)
        self.search_debounce_timer.timeout.connect(self._filter_all_tabs)
        
        self.dark_mode = self.data.get_theme()
        
        self.last_requested_quest_name = ""
        self.last_failed_url = "" 
        self.selected_quest_widget = None 
        self.tab_map = {} 

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
        except: pass

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

        # --- HEADER ROW ---
        head_row = QHBoxLayout()
        head_row.addWidget(QLabel("Quest Journal", objectName="H1"))
        head_row.addStretch()
        
        search_btn = QPushButton(objectName="HeaderBtn")
        search_btn.setIcon(create_custom_icon("search", ThemeColors.WHITE))
        search_btn.setIconSize(QSize(20, 20))
        search_btn.setFixedSize(36, 36)
        search_btn.clicked.connect(self.search_wiki_direct)
        head_row.addWidget(search_btn)

        self.theme_button = QPushButton(objectName="HeaderBtn")
        self.theme_button.setFixedSize(36, 36)
        self.theme_button.clicked.connect(self.toggle_theme)
        head_row.addWidget(self.theme_button)
        
        # --- MENU BUTTON (3 DOTS) ---
        self.menu_btn = QPushButton(objectName="HeaderBtn")
        self.menu_btn.setIcon(create_custom_icon("menu", ThemeColors.WHITE))
        self.menu_btn.setIconSize(QSize(20, 20))
        self.menu_btn.setFixedSize(36, 36)
        self.menu_btn.setToolTip("Options")
        self.menu_btn.clicked.connect(self.show_main_menu)
        head_row.addWidget(self.menu_btn)
        
        l_layout.addLayout(head_row)
        
        # --- FILTER ROW ---
        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)
        filter_row.setAlignment(Qt.AlignmentFlag.AlignTop) 
        
        self.filter_selector = FilterSelectorWidget()
        self.filter_selector.filter_changed.connect(self.apply_filter_mode)
        filter_row.addWidget(self.filter_selector, 0, Qt.AlignmentFlag.AlignTop)
        
        self.search_input = QLineEdit()
        self.search_input.setObjectName("PillSearchInput") 
        self.search_input.setPlaceholderText("Search...")
        self.search_input.returnPressed.connect(self.search_wiki_direct)
        self.search_input.textChanged.connect(self.on_search_text_changed)
        self.search_input.setFixedHeight(36)
        filter_row.addWidget(self.search_input, 1, Qt.AlignmentFlag.AlignTop)
        l_layout.addLayout(filter_row)

        l_layout.addWidget(QLabel("Character Profile", objectName="SubText"))
        
        # --- PROFILE ROW ---
        prof_layout = QHBoxLayout()
        self.profile_selector = ProfileSelectorWidget()
        self.profile_selector.update_state(self.data.get_profiles(), self.data.current_profile_name)
        self.profile_selector.profile_changed.connect(self.change_profile)
        prof_layout.addWidget(self.profile_selector, 1) 
        
        tools_layout = QHBoxLayout()
        tools_layout.setSpacing(5)
        
        new_btn = QPushButton("+", objectName="ToolBtn")
        new_btn.setFixedSize(32, 32)
        new_btn.setToolTip("Create New Profile")
        new_btn.clicked.connect(self.create_new_profile)
        tools_layout.addWidget(new_btn)

        del_btn = QPushButton(objectName="ToolBtn")
        del_btn.setIcon(create_custom_icon("trash", ThemeColors.RED))
        del_btn.setFixedSize(32, 32)
        del_btn.setToolTip("Delete Current Profile")
        del_btn.clicked.connect(self.delete_current_profile)
        tools_layout.addWidget(del_btn)
        
        prof_layout.addLayout(tools_layout)
        l_layout.addLayout(prof_layout)
        
        # --- CAMPAIGN SELECTOR ---
        l_layout.addWidget(QLabel("Select Campaign", objectName="SubText"))
        self.campaign_selector = CampaignSelectorWidget()
        self.campaign_selector.campaign_changed.connect(self.switch_campaign_view)
        l_layout.addWidget(self.campaign_selector)
        
        self.campaign_stack = QStackedWidget()
        l_layout.addWidget(self.campaign_stack)

        # --- FOOTER ---
        footer = QVBoxLayout()
        footer.setSpacing(12) 
        self.sync_button = QPushButton("Sync Database", objectName="PrimaryBtn")
        self.sync_button.clicked.connect(self.start_sync)
        footer.addWidget(self.sync_button)
        
        prog_row = QHBoxLayout()
        prog_row.setSpacing(15)
        prog_row.addWidget(QLabel("Global Progress:", objectName="SubText"))
        
        self.global_progress_bar = QProgressBar()
        self.global_progress_bar.setObjectName("CampBar")
        self.global_progress_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.global_progress_bar.setFixedHeight(12) 
        self.global_progress_bar.setTextVisible(False)
        self.global_progress_bar.setStyleSheet(f"""
            QProgressBar {{ background: rgba(255,255,255,0.1); border: none; border-radius: 6px; }}
            QProgressBar::chunk {{ background-color: {ThemeColors.GOLD}; border-radius: 6px; }}
        """)
        prog_row.addWidget(self.global_progress_bar)
        
        self.global_count_label = QLabel("0 / 0", objectName="SubText")
        self.global_count_label.setStyleSheet(f"color: {ThemeColors.GOLD}; font-weight: bold; margin-left: 2px;")
        prog_row.addWidget(self.global_count_label)
        
        footer.addLayout(prog_row)
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

    def show_main_menu(self):
        menu = QMenu(self)
        
        act_history = QAction("Quest History", self)
        act_history.triggered.connect(self.show_history)
        menu.addAction(act_history)
        
        menu.addSeparator()
        
        act_import = QAction("Import Profile", self)
        act_import.triggered.connect(self.import_profile)
        menu.addAction(act_import)
        
        act_export = QAction("Export Profile", self)
        act_export.triggered.connect(self.export_profile)
        menu.addAction(act_export)
        
        menu.addSeparator()
 
        act_update = QAction("Check for Updates", self)
        act_update.triggered.connect(self.check_updates_manual)
        menu.addAction(act_update)
        
        menu.addSeparator()
        
        act_about = QAction("About && Legal", self)
        act_about.triggered.connect(self.show_about)
        menu.addAction(act_about)
        
        menu.exec(self.menu_btn.mapToGlobal(self.menu_btn.rect().bottomLeft()))

    def show_history(self):
        data = self.data.get_completion_history()
        HistoryDialog(data, self).exec()

    def export_profile(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Export Profile", f"{self.data.current_profile_name}.json", "JSON Files (*.json)")
        if filename:
            try:
                self.data.export_profile_to_json(filename)
                CustomDialog("Success", f"Profile exported to:\n{filename}", self, is_confirmation=False).exec()
            except Exception as e:
                CustomDialog("Error", f"Export failed: {e}", self, is_confirmation=False).exec()

    def import_profile(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Import Profile", "", "JSON Files (*.json)")
        if filename:
            try:
                count = self.data.import_profile_from_json(filename)
                self._build_tabs() 
                CustomDialog("Success", f"Imported {count} quest records.", self, is_confirmation=False).exec()
            except Exception as e:
                CustomDialog("Error", f"Import failed: {e}", self, is_confirmation=False).exec()

    def check_updates_manual(self):
        if self.update_checker.isRunning():
            self.update_checker.requestInterruption()
            self.update_checker.quit()
            self.update_checker.wait()
        
        self.update_checker.start()

    def handle_update_check_result(self, has_update, url, tag, error_msg):
        if error_msg: CustomDialog("Update Check Failed", f"Error: {error_msg}", self, is_confirmation=False).exec()
        elif has_update:
            msg = f"A new version ({tag}) is available!\n\nDownload now?"
            if CustomDialog("Update Available", msg, self, is_confirmation=True).exec() == QDialog.DialogCode.Accepted:
                self.start_download(url)
        else: CustomDialog("No Updates", "You are running the latest version.", self, is_confirmation=False).exec()

    def start_download(self, url):
        self.dl_dialog = CustomDialog("Downloading Update", "Please wait...", self, is_confirmation=False)
        self.dl_dialog.show()
        
        if self.downloader and self.downloader.isRunning():
            self.downloader.requestInterruption()
            self.downloader.quit()
            self.downloader.wait()
        self.downloader = UpdateDownloader(url)
        self.downloader.progress.connect(lambda p: self.dl_dialog.setWindowTitle(f"Downloading... {p}%"))
        self.downloader.finished.connect(self.on_download_finished)
        self.downloader.error.connect(self.on_download_error)
        self.downloader.start()

    def on_download_error(self, err_msg):
        if hasattr(self, 'dl_dialog'): self.dl_dialog.close()
        CustomDialog("Update Failed", f"Download error: {err_msg}", self, is_confirmation=False).exec()

    def on_download_finished(self, file_path):
        if hasattr(self, 'dl_dialog'): self.dl_dialog.close()
        try:
            current_exe = sys.executable
            if not getattr(sys, 'frozen', False):
                CustomDialog("Update Downloaded", f"Update saved to:\n{file_path}\n(Dev env: No restart)", self, is_confirmation=False).exec()
                return
            bat_path = os.path.join(os.path.dirname(current_exe), "updater.bat")
            with open(bat_path, "w") as bat:
                bat.write(f'@echo off\ntimeout /t 2 /nobreak >nul\ndel "{current_exe}"\nmove "{file_path}" "{current_exe}"\nstart "" "{current_exe}"\ndel "%~f0"\n')
            subprocess.Popen([bat_path], shell=True)
            sys.exit(0)
        except Exception as e:
            CustomDialog("Update Error", f"Failed to install: {e}", self, is_confirmation=False).exec()

    def apply_filter_mode(self, mode):
        for i in range(self.campaign_stack.count()):
            tab = self.campaign_stack.widget(i)
            if isinstance(tab, CampaignTab): tab.set_filter_mode(mode)

    def _build_tabs(self):
        for i in range(self.campaign_stack.count()):
            tab = self.campaign_stack.widget(i)
            if isinstance(tab, CampaignTab): tab.stop_loading()
        while self.campaign_stack.count(): self.campaign_stack.removeWidget(self.campaign_stack.widget(0))
        self.selected_quest_widget = None
        self.tab_map = {} 
        current_data = self.data.get_current_quests()
        available = []
        for camp in CAMPAIGN_ORDER:
            if camp in self.data.quest_db:
                available.append(camp)
                tab = CampaignTab(camp, self.data.quest_db[camp], current_data)
                tab.quest_status_changed.connect(self.handle_quest_update)
                tab.reset_requested.connect(self.handle_campaign_reset)
                tab.wiki_requested.connect(self.load_quest)
                self.campaign_stack.addWidget(tab)
                self.tab_map[camp] = tab
        if available: self.campaign_selector.update_options(available, available[0])
        self.update_global_progress()

    def switch_campaign_view(self, campaign_name):
        if campaign_name in self.tab_map:
            self.campaign_stack.setCurrentWidget(self.tab_map[campaign_name])
            available = [c for c in CAMPAIGN_ORDER if c in self.tab_map]
            self.campaign_selector.update_options(available, campaign_name)

    def handle_quest_update(self, name, status):
        self.data.set_status(name, status)
        self.update_global_progress()
        
    def handle_campaign_reset(self, campaign_name):
        self.data.reset_campaign(campaign_name)
        current_data = self.data.get_current_quests()
        if campaign_name in self.tab_map: self.tab_map[campaign_name].refresh_tab_state(current_data)
        self.update_global_progress()

    def create_new_profile(self):
        dlg = CustomDialog("New Profile", "Enter name:", self, is_confirmation=False, show_input=True)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name = dlg.get_input_text().strip()
            if self.data.create_profile(name):
                self.profile_selector.update_state(self.data.get_profiles(), self.data.current_profile_name) 
                self._build_tabs() 
            else: CustomDialog("Error", "Invalid name or already exists.", self, is_confirmation=False).exec()

    def delete_current_profile(self):
        current = self.data.current_profile_name
        if len(self.data.get_profiles()) <= 1:
            CustomDialog("Error", "Cannot delete last profile.", self, is_confirmation=False).exec(); return
        if CustomDialog("Delete Profile", f"Delete '{current}'?", self).exec() == QDialog.DialogCode.Accepted:
            if self.data.delete_profile(current):
                self.profile_selector.update_state(self.data.get_profiles(), self.data.current_profile_name) 
                self._build_tabs() 

    def change_profile(self, name):
        if not name or name == self.data.current_profile_name: return
        self.data.switch_profile(name)
        self.profile_selector.update_state(self.data.get_profiles(), self.data.current_profile_name) 
        current_data = self.data.get_current_quests()
        for i in range(self.campaign_stack.count()):
            tab = self.campaign_stack.widget(i)
            if isinstance(tab, CampaignTab): tab.refresh_tab_state(current_data)
        self.update_global_progress()

    def load_quest(self, quest_name, widget_ref=None):
        self.show_loading()
        self.last_requested_quest_name = quest_name 
        if widget_ref:
            if self.selected_quest_widget and self.selected_quest_widget != widget_ref:
                try: self.selected_quest_widget.set_highlighted(False)
                except: pass
            self.selected_quest_widget = widget_ref
            self.selected_quest_widget.set_highlighted(True)
        
        if quest_name in AppConfig.WIKI_OVERRIDES: url = f"https://wiki.guildwars.com/wiki/{AppConfig.WIKI_OVERRIDES[quest_name]}"
        elif "Reach Level" in quest_name: url = "https://wiki.guildwars.com/wiki/Legendary_Defender_of_Ascalon"
        else: url = f"https://wiki.guildwars.com/wiki/{quote(quest_name.replace(' ', '_'))}"

        cached = self.data.get_cached_content(url)
        if cached: self.web_view.setHtml(cached, QUrl(url))
        else: self.web_view.setUrl(QUrl(url))

    def show_loading(self): self.stack_widget.setCurrentIndex(2)
    
    def handle_load_finished(self, ok):
        global _LAST_FAILED_URL
        if ok:
            _LAST_FAILED_URL = ""
            self.finalize_page()
        else:
            failed_url = self.web_view.url().toString()
            if failed_url != _LAST_FAILED_URL:
                 logging.warning(f"Failed to load URL: {failed_url}. Showing custom error message.")
                 _LAST_FAILED_URL = failed_url
            encoded = quote(self.last_requested_quest_name)
            error_html = f"""<script>function searchWiki() {{ window.location.href = `https://wiki.guildwars.com/index.php?search=${{'{encoded}'}}`; }}</script><style>body {{ background: #1a1a1a; color: {ThemeColors.WHITE}; font-family: 'Segoe UI'; text-align: center; display: flex; flex-direction: column; justify-content: center; height: 90vh; }} .btn {{ background: #444; color: #fff; padding: 10px; cursor: pointer; }}</style><div><h2>WIKI UNAVAILABLE</h2><p>{self.last_requested_quest_name}</p><button class="btn" onclick="searchWiki()">Search Wiki</button></div>"""
            self.web_view.setHtml(error_html, QUrl("https://wiki.guildwars.com"))
            self.stack_widget.setCurrentIndex(1) 

    def search_wiki_direct(self):
        text = self.search_input.text()
        self.show_loading()
        self.last_requested_quest_name = text 
        if text: self.web_view.setUrl(QUrl(f"https://wiki.guildwars.com/index.php?search={quote(text)}"))
        else: self.web_view.setUrl(QUrl("https://wiki.guildwars.com/index.php?title=Special%3ASearch"))

    def on_search_text_changed(self, text): self.search_debounce_timer.start()

    def _filter_all_tabs(self):
        text = self.search_input.text().lower()
        found, first = False, None
        for i in range(self.campaign_stack.count()):
            tab = self.campaign_stack.widget(i)
            if isinstance(tab, CampaignTab):
                tab.filter_content(text)
                if any(s.isVisible() for s in tab.section_widgets):
                    found = True
                    if not first: first = tab.campaign_name
        if not found and first: self.switch_campaign_view(first)

    def update_global_progress(self):
        tc, tq = 0, 0
        for tab in self.tab_map.values():
            c, t = tab.get_progress_stats()
            tc += c; tq += t
        self.global_count_label.setText(f"{tc} / {tq}")
        self.global_progress_bar.setMaximum(tq if tq > 0 else 1)
        self.global_progress_bar.setValue(tc)

    def start_sync(self):
        if self.syncer.isRunning():
            self.syncer.requestInterruption(); self.sync_button.setText("Stopping..."); self.sync_button.setEnabled(False); return
        self.sync_button.setText("Cancel Sync"); self.sync_button.setEnabled(True)
        self.syncer.set_current_db(copy.deepcopy(self.data.quest_db))
        self.syncer.start()

    def _on_sync_finished(self, new_db, errors):
        self.sync_button.setText("Sync Database"); self.sync_button.setEnabled(True)
        if new_db:
            self.data.update_quest_db(new_db) 
            self._build_tabs()
            if errors: CustomDialog("Sync Warnings", "\n".join(errors), self, is_confirmation=False).exec()
            else: CustomDialog("Success", "Database Synced.", self, is_confirmation=False).exec()
    
    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.data.set_theme(self.dark_mode)
        self.update_theme_btn_style()
        self.web_view.reload()

    def update_theme_btn_style(self):
        icon, style = ("moon", "background-color: rgba(123, 104, 238, 0.2); color: #fff; border: 1px solid #7B68EE;") if self.dark_mode else ("sun", f"background-color: {ThemeColors.GOLD}; color: #000; border: 1px solid {ThemeColors.GOLD};")
        self.theme_button.setStyleSheet(style)
        self.theme_button.setIcon(create_custom_icon(icon, ThemeColors.WHITE if self.dark_mode else "#000"))
    
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
        if self.game_check_timer.isActive(): self.game_check_timer.stop()
        if self.syncer.isRunning(): self.syncer.requestInterruption(); self.syncer.wait()
        if self.update_checker.isRunning(): self.update_checker.requestInterruption(); self.update_checker.wait()
        if self.downloader and self.downloader.isRunning(): self.downloader.requestInterruption(); self.downloader.wait()
        try: self.web_view.page().profile().clearHttpCache()
        except: pass
        event.accept()