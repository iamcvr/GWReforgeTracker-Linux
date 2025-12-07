#!/usr/bin/env python3
"""
Linux-native Guild Wars Reforge Quest Tracker UI.

Uses:
  - Tkinter for the UI (stdlib, cross-platform)
  - DataManager (database.py) for profiles, quest statuses, history, export/import
  - WikiScraper (scraper.py) for syncing quests from the Guild Wars wiki
  - webbrowser to open the wiki in your default browser

This completely avoids PySide6 / Qt / QtWebEngine.
"""

import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import webbrowser
import logging

from config import (
    AppConfig,
    CAMPAIGN_ORDER,
    SECTION_MARKER,
    AppConfig,
    CAMPAIGN_ORDER,
    SECTION_MARKER,
    QuestStatus,
    ThemeColors,
)
from database import DataManager
from scraper import WikiScraper

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")




logging.basicConfig(level=logging.INFO)



class LinuxQuestTracker(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # self._setup_dark_theme() # Not needed with CTk

        self.title(f"{AppConfig.APP_TITLE} (Modern)")
        self.geometry("1400x900")

        # Core data / logic
        self.data = DataManager()
        self.scraper = WikiScraper()

        # State
        self.current_campaign = CAMPAIGN_ORDER[0]
        self.selected_quest = None
        self.visible_quests = []  # parallel to listbox rows
        self.quest_cards = {} # currently active {quest_name: (widget, icon, label, row)}
        self.loading_task = None
        self.visible_quests = []

        self.search_var = tk.StringVar()
        self.profile_var = tk.StringVar(value=self.data.current_profile_name)
        self.status_var = tk.StringVar(value="Ready")
        self.inprogress_search_var = tk.StringVar()
        self.completed_search_var = tk.StringVar()

        self.collapsed_sections = {}  # campaign_name -> set of header lines
        self.row_meta = []  # one entry per row in quest_list

        # Global status panels
        self.inprogress_search_var = tk.StringVar()
        self.completed_search_var = tk.StringVar()

        self.inprogress_list = None
        self.completed_list = None
        self.inprogress_frame = None
        self.completed_frame = None

        # Build UI
        # Build UI
        self._build_layout()
        self._load_profiles()
        self._render_campaign_buttons()
        self._switch_campaign(self.current_campaign)
        self._refresh_summary_lists()

    # ---------------- UI LAYOUT ----------------
    def _setup_dark_theme(self):
        # CTk handles theme, but we can set custom specific colors if needed here
        pass    

    def _build_layout(self):
        # Configure grid layout (1x2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=0) # Top bar
        self.grid_rowconfigure(1, weight=1) # Main area

        # --- Top Bar ---
        self.top_bar = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.top_bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=10)

        # Profile
        ctk.CTkLabel(self.top_bar, text="Profile:").pack(side="left", padx=(0, 10))
        self.profile_combo = ctk.CTkComboBox(
            self.top_bar,
            variable=self.profile_var,
            width=200,
            command=self._on_profile_changed,
            dropdown_hover_color=ThemeColors.DARK_LISTSEL,
            state="readonly"
        )
        self.profile_combo.pack(side="left", padx=5)

        ctk.CTkButton(self.top_bar, text="New", width=60, command=self._create_profile).pack(side="left", padx=5)
        ctk.CTkButton(self.top_bar, text="Delete", width=60, fg_color=ThemeColors.RED, hover_color="#cc0000", command=self._delete_profile).pack(side="left", padx=5)

        # Search
        ctk.CTkLabel(self.top_bar, text="Search:").pack(side="left", padx=(20, 10))
        search_entry = ctk.CTkEntry(self.top_bar, textvariable=self.search_var, width=200, placeholder_text="Search quests...")
        search_entry.pack(side="left", padx=5)

        search_entry.bind("<Control-a>", self._select_all_text)

        # Clear Search Button
        ctk.CTkButton(
            self.top_bar, text="✕", width=24, height=24, fg_color="transparent", 
            text_color=ThemeColors.GREY, hover_color=ThemeColors.DARK_LISTBG,
            command=lambda: self.search_var.set("")
        ).pack(side="left", padx=(0, 5))

        # Global Actions
        ctk.CTkButton(self.top_bar, text="History", width=80, command=self._show_history).pack(side="right", padx=5)
        ctk.CTkButton(self.top_bar, text="Sync DB", width=80, command=self._sync_database).pack(side="right", padx=5)
        ctk.CTkButton(self.top_bar, text="Import", width=80, command=self._import_profile).pack(side="right", padx=5)
        ctk.CTkButton(self.top_bar, text="Export", width=80, command=self._export_profile).pack(side="right", padx=5)

        # --- Main Area ---
        # Sidebar (Campaigns) - Left
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=1, column=0, sticky="nsew", padx=(0, 5), pady=0)
        
        ctk.CTkLabel(self.sidebar, text="CAMPAIGNS", font=("Segoe UI", 16, "bold"), text_color=ThemeColors.DARK_SUBTEXT).pack(pady=20, padx=20, anchor="w")
        
        self.campaign_buttons_frame = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.campaign_buttons_frame.pack(fill="both", expand=True)

        # Content - Center
        self.content = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent")
        self.content.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        # Tab View for Lists
        self.tabs = ctk.CTkTabview(self.content)
        self.tabs.grid(row=0, column=0, sticky="nsew")
        
        self.tabs.add("Campaign")
        self.tabs.add("In Progress")
        self.tabs.add("Completed")

        # Campaign Tab
        self.quest_scroll_frame = ctk.CTkScrollableFrame(self.tabs.tab("Campaign"), fg_color="transparent")
        self.quest_scroll_frame.pack(fill="both", expand=True)

        # In Progress Tab
        self.inprogress_scroll_frame = ctk.CTkScrollableFrame(self.tabs.tab("In Progress"), fg_color="transparent")
        self.inprogress_scroll_frame.pack(fill="both", expand=True)

        # Completed Tab
        self.completed_scroll_frame = ctk.CTkScrollableFrame(self.tabs.tab("Completed"), fg_color="transparent")
        self.completed_scroll_frame.pack(fill="both", expand=True)

        # Status Bar (Bottom)
        self.status_bar_label = ctk.CTkLabel(self, textvariable=self.status_var, height=30, anchor="w", fg_color=ThemeColors.DARK_PANEL)
        self.status_bar_label.grid(row=2, column=0, columnspan=2, sticky="ew")

        # Loading Progress Bar (Below status bar, initially hidden or empty)
        self.progress_bar = ctk.CTkProgressBar(
            self, height=4, corner_radius=0, 
            progress_color=ThemeColors.DARK_ACCENT, 
            fg_color=ThemeColors.DARK_PANEL
        )
        self.progress_bar.grid(row=3, column=0, columnspan=2, sticky="ew")
        self.progress_bar.set(0) # Start empty
        self.progress_bar.grid_remove() # Hide initially

        # Bind events
        self.search_var.trace_add("write", lambda *args: self._filter_quest_list()) 
        # We might want separate search vars for the tabs, but for now global search effects campaign list only? 

        # Scroll bindings for Linux
        self.bind_all("<Button-4>", self._on_mouse_wheel)
        self.bind_all("<Button-5>", self._on_mouse_wheel)

    def _select_all_text(self, event):
        # Select all text in the widget
        event.widget.select_range(0, 'end')
        event.widget.icursor('end')
        return 'break' # Prevent default binding

    def _on_mouse_wheel(self, event):
        # find which scrollable frame is under cursor or active
        # CTkScrollableFrame does not expose standardized yview easily for external events
        # BUT, standard CTk usually handles this. If user reports issue, 
        # we might need to verify where the mouse is.
        # Simple hack: Scroll currently visible tab's frame? 
        
        # We need to identifying which widget is hovered. 
        # A simple approach for now:
        current_tab = self.tabs.get()
        target = None
        if current_tab == "Campaign":
            target = self.quest_scroll_frame
        elif current_tab == "In Progress":
            target = self.inprogress_scroll_frame
        elif current_tab == "Completed":
            target = self.completed_scroll_frame
            
        if target:
             # scroll logic for CTkScrollableFrame
             # It uses a canvas internally.
             # event.num == 4 -> scroll up, 5 -> scroll down
             if event.num == 4:
                 target._parent_canvas.yview_scroll(-1, "units")
             elif event.num == 5:
                 target._parent_canvas.yview_scroll(1, "units")
        
    def _render_campaign_buttons(self):
        # Clear existing
        for widget in self.campaign_buttons_frame.winfo_children():
            widget.destroy()

        for camp in CAMPAIGN_ORDER:
            is_active = (camp == self.current_campaign)
            color = ThemeColors.DARK_ACCENT if is_active else "transparent"
            fg = ThemeColors.WHITE if is_active else ThemeColors.GREY
            
            btn = ctk.CTkButton(
                self.campaign_buttons_frame,
                text=camp,
                fg_color=color,
                text_color=fg,
                hover_color=ThemeColors.DARK_LISTSEL,
                anchor="w",
                height=40,
                command=lambda c=camp: self._switch_campaign(c)
            )
            btn.pack(fill="x", pady=2, padx=5)

    def _switch_campaign(self, campaign_name):
        self.current_campaign = campaign_name
        self.selected_quest = None
        self._set_status_text(f"Switched to campaign: {campaign_name}")
        self._render_campaign_buttons() # Update active state highlight
        self._rebuild_quest_list()

    # ---------------- PROFILES ----------------

    def _load_profiles(self):
        profiles = self.data.get_profiles()
        if not profiles:
            profiles = [self.data.current_profile_name]

        self.profile_combo.configure(values=profiles)

        if self.data.current_profile_name in profiles:
            self.profile_var.set(self.data.current_profile_name)
        else:
            self.profile_var.set(profiles[0])

    def _on_profile_changed(self, event=None):
        name = self.profile_var.get()
        if not name:
            return
        self.data.switch_profile(name)
        self._rebuild_quest_list()
        self._refresh_summary_lists()
        self._set_status_text(f"Switched to profile: {name}")

    def _import_profile(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if path:
            try:
                self.data.import_profile(path)
                self._load_profiles()
                messagebox.showinfo("Success", "Profile imported successfully.")
                self._rebuild_quest_list()
                self._refresh_summary_lists()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import: {e}")

    def _export_profile(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON", "*.json")]
        )
        if path:
            try:
                self.data.export_profile(path)
                messagebox.showinfo("Success", f"Profile exported to {path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {e}")

    def _create_profile(self):
        # Using native CTkInputDialog correctly
        dialog = ctk.CTkInputDialog(text="Enter profile name:", title="New Profile")
        name = dialog.get_input()
        if name:
            self.data.create_profile(name)
            self._load_profiles()
            self._on_profile_changed() # Trigger load

    def _delete_profile(self):
        if len(self.data.get_profiles()) <= 1:
            self._show_custom_dialog("Warning", "Cannot delete the last profile.", mode="info")
            return
        
        def on_confirm(confirmed):
            if confirmed:
                self.data.delete_profile(self.data.current_profile_name)
                self._load_profiles()
                self._on_profile_changed()

        self._show_custom_dialog(
            "Confirm Delete", 
            f"Delete profile '{self.data.current_profile_name}'?\nThis cannot be undone.", 
            on_confirm,
            mode="confirm"
        )

    # ---------------- CAMPAIGNS & QUESTS ----------------

    def _toggle_section(self, header_line: str):
        """Toggle collapsed/expanded state for a section header in the current campaign."""
        camp = self.current_campaign
        coll = self.collapsed_sections.setdefault(camp, set())
        if header_line in coll:
            coll.remove(header_line)
        else:
            coll.add(header_line)
        self._filter_quest_list()

    def _collapse_all_sections(self):
        """Collapse all section headers for the current campaign."""
        quests = self.data.quest_db.get(self.current_campaign, [])
        headers = {q for q in quests if SECTION_MARKER in q}
        if headers:
            self.collapsed_sections[self.current_campaign] = set(headers)
        else:
            self.collapsed_sections[self.current_campaign] = set()
        self._filter_quest_list()

    def _expand_all_sections(self):
        """Expand all section headers for the current campaign."""
        if self.current_campaign in self.collapsed_sections:
            self.collapsed_sections[self.current_campaign].clear()
        self._filter_quest_list()

    def _clear_scrollable(self, frame):
        for widget in frame.winfo_children():
            widget.destroy()

    def _get_or_create_quest_card(self, q_name, row_idx):
        """Create widget if not exists, otherwise return existing."""
        if q_name in self.quest_cards:
            return self.quest_cards[q_name]

        status_map = self.data.get_current_quests()
        info = status_map.get(
            q_name, {"status": QuestStatus.NOT_STARTED, "timestamp": None}
        )
        st = info.get("status", QuestStatus.NOT_STARTED)

        # Create Header
        if SECTION_MARKER in q_name:
             header_text = q_name.replace(SECTION_MARKER, "").strip() or "---"
             collapsed = self.collapsed_sections.get(self.current_campaign, set())
             is_coll = q_name in collapsed
             
             header_frame = ctk.CTkFrame(self.quest_scroll_frame, fg_color="transparent")
             # grid comes later
             
             icon = "▸" if is_coll else "▾"
             btn = ctk.CTkButton(
                header_frame,
                text=f"{icon} {header_text.upper()}",
                font=("Segoe UI", 12, "bold"),
                fg_color="transparent",
                text_color=ThemeColors.DARK_ACCENT,
                anchor="w",
                hover_color=ThemeColors.DARK_PANEL,
                command=lambda h=q_name: self._toggle_section(h)
             )
             btn.pack(fill="x")
             
             # tuple: (widget, None, btn, row)
             self.quest_cards[q_name] = (header_frame, None, btn, row_idx)
             return self.quest_cards[q_name]

        # Create Card
        # Restoring Rounded Corners for "Pretty UI"
        card = ctk.CTkFrame(self.quest_scroll_frame, fg_color=ThemeColors.DARK_PANEL, corner_radius=6)
        # grid comes later

        # Colors/Icons
        if st == QuestStatus.COMPLETED:
            icon_color = ThemeColors.GREEN
            icon_text = "✔"
        elif st == QuestStatus.IN_PROGRESS:
            icon_color = ThemeColors.GOLD
            icon_text = "▶"
        else:
            icon_color = ThemeColors.GREY
            icon_text = "○"

        # Status Icon
        icon_btn = ctk.CTkLabel(
            card, text=icon_text, text_color=icon_color, 
            font=("Segoe UI", 16), width=40
        )
        icon_btn.pack(side="left", padx=5)

        # Name Label
        name_lbl = ctk.CTkLabel(
            card, text=q_name, font=("Segoe UI", 13), 
            text_color=ThemeColors.DARK_TEXT, anchor="w"
        )
        name_lbl.pack(side="left", fill="x", expand=True)

        # Controls
        ctk.CTkButton(
            card, text="Wiki", width=50, height=24, font=("Segoe UI", 11),
            fg_color=ThemeColors.DARK_ACCENT, corner_radius=6,
            command=lambda q=q_name: self._open_specific_wiki(q)
        ).pack(side="right", padx=(5, 5), pady=5)

        ctk.CTkButton(
            card, text="✔", width=24, height=24, fg_color="transparent", 
            text_color=ThemeColors.GREEN, hover_color=ThemeColors.DARK_LISTBG, corner_radius=6,
            command=lambda q=q_name: self._update_quest_status(q, QuestStatus.COMPLETED)
        ).pack(side="right", padx=1)

        ctk.CTkButton(
            card, text="▶", width=24, height=24, fg_color="transparent", 
            text_color=ThemeColors.GOLD, hover_color=ThemeColors.DARK_LISTBG, corner_radius=6,
            command=lambda q=q_name: self._update_quest_status(q, QuestStatus.IN_PROGRESS)
        ).pack(side="right", padx=1)

        ctk.CTkButton(
            card, text="○", width=24, height=24, fg_color="transparent", 
            text_color=ThemeColors.GREY, hover_color=ThemeColors.DARK_LISTBG, corner_radius=6,
            command=lambda q=q_name: self._update_quest_status(q, QuestStatus.NOT_STARTED)
        ).pack(side="right", padx=1)

        # Save ref
        self.quest_cards[q_name] = (card, icon_btn, name_lbl, row_idx)
        return self.quest_cards[q_name]


    def _rebuild_quest_list(self):
        """Re-populates the quest list with incremental loader."""
        if self.loading_task:
            self.after_cancel(self.loading_task)
            self.loading_task = None

        camp = self.current_campaign
        quests = self.data.get_quests_for_campaign(camp)
        
        self._clear_scrollable(self.quest_scroll_frame)
        self.quest_cards.clear()
        self.quest_scroll_frame.grid_columnconfigure(0, weight=1)
        
        # Show progress bar
        self.progress_bar.grid(row=3, column=0, columnspan=2, sticky="ew")
        self.progress_bar.set(0)
        self._set_status_text(f"Loading {camp}...")
        
        # Start incremental load
        self._load_incremental(quests, 0)
        
        # If searching, filter immediately
        if self.search_var.get():
            self._filter_quest_list()

    def _load_incremental(self, all_quests, start_idx):
        """Load 20 quests at a time to keep UI responsive."""
        limit = start_idx + 20
        chunk = all_quests[start_idx:limit]
        
        # Update Progress
        total = len(all_quests)
        if total > 0:
            progress = start_idx / total
            self.progress_bar.set(progress)
            percent = int(progress * 100)
            self._set_status_text(f"Loading {self.current_campaign}... {percent}%")
        
        if not chunk:
            self.loading_task = None
            self.progress_bar.set(1)
            self.progress_bar.grid_remove() # Hide when done
            self._set_status_text(f"Loaded {self.current_campaign} ({total} quests)")
            return

        for i, q in enumerate(chunk):
            row = start_idx + i
            # Create widget
            widget, _, _, _ = self._get_or_create_quest_card(q, row)
            
            # Check basic filter logic locally to avoid flash
            search = self.search_var.get().lower().strip()
            
            show = True
            if search:
                if SECTION_MARKER in q: show = False # Hide headers in search
                elif search not in q.lower(): show = False
            
            if show:
                widget.grid(row=row, column=0, sticky="ew", pady=1 if SECTION_MARKER not in q else (10,2), padx=5 if SECTION_MARKER not in q else 0)

        # Schedule next
        if limit < len(all_quests):
             self.loading_task = self.after(10, lambda: self._load_incremental(all_quests, limit))
        else:
             self.loading_task = None
             self.progress_bar.set(1)
             self.after(500, self.progress_bar.grid_remove) # Fade out delay
             self._set_status_text(f"Loaded {self.current_campaign} ({len(all_quests)} quests)")
             # Final pass to ensure filter state is perfect
             self._filter_quest_list()

    def _filter_quest_list(self):
        """Toggle visibility of existing widgets based on search and collapse state."""
        search = self.search_var.get().lower().strip()
        collapsed = self.collapsed_sections.get(self.current_campaign, set())
        
        quests = self.data.get_quests_for_campaign(self.current_campaign)
        skipping = False
        
        for i, q in enumerate(quests):
            # Lazy creation if needed (e.g. searching before full load)
            widget = None
            btn_or_lbl = None
            
            # Check if exists
            if q in self.quest_cards:
                 widget, _, btn_or_lbl, row_idx = self.quest_cards[q]
            else:
                 # If we are searching, we match, but it's not loaded... force create?
                 # Yes, for instant search feel.
                 if search and search in q.lower():
                     widget, _, btn_or_lbl, row_idx = self._get_or_create_quest_card(q, i)
                 else:
                     # Not loaded yet, and doesn't match/not priority. Skip.
                     continue

            if widget is None: continue # Should not happen

            if SECTION_MARKER in q:
                is_coll = q in collapsed
                if search:
                     widget.grid_remove()
                     skipping = False
                else:
                     icon = "▸" if is_coll else "▾"
                     clean_text = q.replace(SECTION_MARKER, "").strip().upper()
                     if btn_or_lbl:
                         btn_or_lbl.configure(text=f"{icon} {clean_text}")

                     widget.grid(row=i, column=0, sticky="ew", pady=(10, 2))
                     skipping = is_coll
                continue
            
            # Quest Logic
            if search:
                if search in q.lower():
                    widget.grid(row=i, column=0, sticky="ew", pady=1, padx=2)
                else:
                    widget.grid_remove()
            else:
                if skipping:
                    widget.grid_remove()
                else:
                    widget.grid(row=i, column=0, sticky="ew", pady=1, padx=2)
    
    def _open_specific_wiki(self, quest_name):
        url = self.scraper.get_quest_url(quest_name)
        webbrowser.open(url)

    def _refresh_summary_lists(self):
        """Populate the global In Progress / Completed panels tabs."""
        status_map = self.data.get_current_quests()

        # Collect quests
        inprogress = []
        completed = []

        for campaign, quests in self.data.quest_db.items():
            for q in quests:
                if SECTION_MARKER in q:
                    continue
                info = status_map.get(q, {})
                st = info.get("status", QuestStatus.NOT_STARTED)
                if st == QuestStatus.IN_PROGRESS:
                    inprogress.append(q)
                elif st == QuestStatus.COMPLETED:
                    completed.append(q)

        inprogress.sort()
        completed.sort()

        # Apply panel-specific search filters
        in_s = self.inprogress_search_var.get().lower().strip()
        if in_s:
            inprogress = [q for q in inprogress if in_s in q.lower()]

        c_s = self.completed_search_var.get().lower().strip()
        if c_s:
            completed = [q for q in completed if c_s in q.lower()]

        # Render helper
        def render_simple_list(frame, quest_list, color, icon):
            self._clear_scrollable(frame)
            if not quest_list:
                ctk.CTkLabel(frame, text="No quests found.").pack(pady=20)
                return

            for q in quest_list:
                card = ctk.CTkFrame(frame, fg_color=ThemeColors.DARK_PANEL, corner_radius=6)
                card.pack(fill="x", pady=2, padx=5)
                
                # Icon
                ctk.CTkLabel(card, text=icon, text_color=color, font=("Segoe UI", 16), width=40).pack(side="left", padx=5)
                # Name
                ctk.CTkLabel(card, text=q, font=("Segoe UI", 13), text_color=ThemeColors.DARK_TEXT, anchor="w").pack(side="left", fill="x", expand=True)
                # Wiki Button
                ctk.CTkButton(
                    card, text="Wiki", width=50, height=24, font=("Segoe UI", 11), fg_color=ThemeColors.DARK_ACCENT,
                    command=lambda name=q: self._open_specific_wiki(name)
                ).pack(side="right", padx=10, pady=5)
                # Jump Button (Switch campaign)
                ctk.CTkButton(
                    card, text="Jump", width=50, height=24, font=("Segoe UI", 11), fg_color=ThemeColors.DARK_ENTRY,
                    command=lambda name=q: self._jump_to_quest(name)
                ).pack(side="right", padx=5, pady=5)

        render_simple_list(self.inprogress_scroll_frame, inprogress, ThemeColors.GOLD, "▶")
        render_simple_list(self.completed_scroll_frame, completed, ThemeColors.GREEN, "✔")

    def _jump_to_quest(self, quest_name: str):
        """Switch campaign, expand section if needed, and select quest in the main list."""
        # Find campaign + header that contains this quest
        target_campaign = None
        target_header = None

        for camp, quests in self.data.quest_db.items():
            header_line = None
            for q in quests:
                if SECTION_MARKER in q:
                    header_line = q
                elif q == quest_name:
                    target_campaign = camp
                    target_header = header_line
                    break
            if target_campaign is not None:
                break

        if target_campaign is None:
            return  # quest not found in DB for some reason

        # Switch campaign
        self._switch_campaign(target_campaign)
        self.tabs.set("Campaign")

        # Ensure the section is not collapsed
        if target_header is not None:
            coll = self.collapsed_sections.setdefault(target_campaign, set())
            if target_header in coll:
                coll.remove(target_header)

        # Refresh quest list for that campaign (already done by _switch_campaign)
        # We need to find the specific card and scroll to it.
        # This is more complex with CTkScrollableFrame. For now, just switching campaign and tab is sufficient.
        # Optionally, set search_var to highlight the quest.
        self.search_var.set(quest_name) # This will trigger _refresh_quest_list and filter to the quest.

    # ---------------- UI ACTIONS ----------------

    # Friendly status text handled in _update_quest_status


    # ---------------- WIKI & CAMPAIGN ACTIONS ----------------

    def _open_in_wiki(self):
        if not self.selected_quest:
            messagebox.showinfo("Wiki", "Please select a quest first.")
            return

        name = self.selected_quest

        # Basic slug: spaces -> underscores
        slug = name.replace(" ", "_")
        url = f"https://wiki.guildwars.com/wiki/{slug}"

        webbrowser.open(url)
        self._set_status_text(f"Opened wiki for: {name}")

    def _show_history(self):
        # Create a Modal Overlay for history
        overlay = ctk.CTkFrame(self, fg_color="#000000", corner_radius=0)
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        overlay.bind("<Button-1>", lambda e: "break")

        card = ctk.CTkFrame(overlay, fg_color=ThemeColors.DARK_PANEL, corner_radius=10, border_width=2, border_color=ThemeColors.DARK_ACCENT, width=600, height=500)
        card.place(relx=0.5, rely=0.5, anchor="center")
        
        # Header
        ctk.CTkLabel(card, text="Quest Completion History", font=("Segoe UI", 18, "bold"), text_color=ThemeColors.DARK_ACCENT).pack(pady=(20, 10))
        
        # Scrollable Text Area
        txt = ctk.CTkTextbox(card, width=540, height=350, font=("Segoe UI", 12))
        txt.pack(pady=10, padx=20)
        
        # Load Data
        history = self.data.get_history()
        
        txt.configure(state="normal")
        txt.delete("1.0", "end")
        
        if not history:
             txt.insert("end", "No completion history found.")
        else:
             for entry in history:
                # entry is (quest_name, timestamp)
                line = f"[{entry[1]}] {entry[0]}\n"
                txt.insert("end", line)
                
        txt.configure(state="disabled")

        # Close Button
        ctk.CTkButton(card, text="Close", fg_color=ThemeColors.DARK_ACCENT, width=100, command=overlay.destroy).pack(pady=20)


    def _reset_campaign(self):
        if not messagebox.askyesno(
            "Reset Campaign",
            f"Reset all quest states for {self.current_campaign} in profile '{self.data.current_profile_name}'?",
        ):
            return
        self.data.reset_campaign(self.current_campaign)
        self._rebuild_quest_list()
        self._refresh_summary_lists()
        self._set_status_text(f"Reset campaign: {self.current_campaign}")

    # ---------------- SYNC / EXPORT / HISTORY ----------------

    def _sync_database(self):
        def on_confirm(confirmed):
            if not confirmed: return
            self._run_sync_process()
            
        self._show_custom_dialog(
            "Sync Database", 
            "Syncing will contact the Guild Wars wiki and may take a moment.\n\nContinue?", 
            on_confirm,
            mode="confirm"
        )
            
    def _run_sync_process(self):
        self._set_status_text("Syncing quest database from wiki...")
        self.status_var.set("Sync in progress...")
        self.progress_bar.grid(row=3, column=0, columnspan=2, sticky="ew")
        self.progress_bar.start()
        self.update_idletasks()

        def worker():
            try:
                new_db, errors = self.scraper.run_sync(self.data.quest_db)
                if new_db:
                    self.data.update_quest_db(new_db)
                self.after(0, lambda: self._on_sync_finished(errors))
            except Exception as e:
                logging.exception("Sync failed")
                self.after(0, lambda: self._on_sync_finished([str(e)]))

        threading.Thread(target=worker, daemon=True).start()
    
    def _on_sync_finished(self, errors):
        self.progress_bar.stop()
        self.progress_bar.grid_remove()
        if errors:
            msg = "Sync completed with some errors:\n" + "\n".join(errors[:5])
            if len(errors) > 5:
                msg += f"\n... and {len(errors) - 5} more."
        if errors:
            msg = "Sync completed with some errors:\n" + "\n".join(errors[:5])
            if len(errors) > 5:
                msg += f"\n... and {len(errors) - 5} more."
            self._show_custom_dialog("Sync Warning", msg, mode="info")
        else:
            self._show_custom_dialog("Sync Finished", "Quest database updated successfully.", mode="info")
        
        # Invalidate Cache (No longer used)
        self._rebuild_quest_list()
        self._set_status_text("Sync finished.")

    def _update_quest_status(self, quest_name, status):
        """Update status and refresh UI."""
        self.data.set_status(quest_name, status)
        self._update_quest_status_ui(quest_name, status)
        self._set_status_text(f"Updated {quest_name}")
        
    def _update_quest_status_ui(self, quest_name, status):
        # 1. Update the Data Object
        # 2. Update the visual card if it exists
        if quest_name in self.quest_cards:
            _, icon_label, _, _ = self.quest_cards[quest_name]
            
            if status == QuestStatus.NOT_STARTED:
                icon_label.configure(text="○", text_color=ThemeColors.GREY)
            elif status == QuestStatus.IN_PROGRESS:
                icon_label.configure(text="▶", text_color=ThemeColors.GOLD)
            else:
                icon_label.configure(text="✔", text_color=ThemeColors.GREEN)

        # 3. Only refresh summary lists
        self._refresh_summary_lists()

    def _set_status_text(self, text):
        self.status_var.set(text)

    def _show_custom_dialog(self, title, message, callback=None, mode="confirm"):
        """Shows a modal overlay dialog within the main window."""
        # 1. Overlay (Dark background to block clicks)
        overlay = ctk.CTkFrame(self, fg_color="#000000", corner_radius=0)
        # We can try alpha if supported, but typically hex with transparency isn't full supported on all linux backends in TK.
        # Just use mostly opaque dark.
        # A trick for transparency in CTk is 'transparent' but that's fully transparent.
        # We will wrap the card in a frame that spans the whole window.
        
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # Capture clicks on overlay to prevent click-through (logic implicit by heavy widget on top)
        overlay.bind("<Button-1>", lambda e: "break")
        
        # 2. Card
        card = ctk.CTkFrame(overlay, fg_color=ThemeColors.DARK_PANEL, corner_radius=10, border_width=2, border_color=ThemeColors.DARK_ACCENT)
        card.place(relx=0.5, rely=0.5, anchor="center")
        
        # Content
        ctk.CTkLabel(card, text=title, font=("Segoe UI", 18, "bold"), text_color=ThemeColors.DARK_ACCENT).pack(pady=(20, 10), padx=40)
        ctk.CTkLabel(card, text=message, font=("Segoe UI", 14), text_color=ThemeColors.DARK_TEXT, wraplength=400).pack(pady=10, padx=20)
        
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        def close(result):
            overlay.destroy()
            if callback: 
                # If mode is confirm, callback expects boolean.
                # If mode is info, callback might be None or take no args?
                # Let's standardize: callback(result) 
                # But existing code for info passed None.
                if mode == "confirm":
                    callback(result)
                else:
                    if callback: callback()

        if mode == "confirm":
            ctk.CTkButton(btn_frame, text="Confirm", fg_color=ThemeColors.DARK_ACCENT, width=100, command=lambda: close(True)).pack(side="left", padx=10)
            ctk.CTkButton(btn_frame, text="Cancel", fg_color="transparent", border_width=1, border_color=ThemeColors.GREY, width=100, command=lambda: close(False)).pack(side="left", padx=10)
        else:
            ctk.CTkButton(btn_frame, text="OK", fg_color=ThemeColors.DARK_ACCENT, width=100, command=lambda: close(True)).pack(side="left", padx=10)



if __name__ == "__main__":
    app = LinuxQuestTracker()
    app.mainloop()
