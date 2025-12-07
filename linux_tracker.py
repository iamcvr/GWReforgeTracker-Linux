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
import webbrowser
import logging

from config import (
    AppConfig,
    CAMPAIGN_ORDER,
    SECTION_MARKER,
    QuestStatus,
)
from database import DataManager
from scraper import WikiScraper


logging.basicConfig(level=logging.INFO)

DARK_BG = "#1e1e1e"
DARK_PANEL = "#252526"
DARK_ACCENT = "#007acc"
DARK_TEXT = "#ffffff"
DARK_SUBTEXT = "#cccccc"
DARK_ENTRY = "#3c3c3c"
DARK_LISTBG = "#1e1e1e"
DARK_LISTSEL = "#094771"

class LinuxQuestTracker(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self._setup_dark_theme()

        self.title(f"{AppConfig.APP_TITLE} (Linux)")
        self.geometry("1200x800")

        # Core data / logic
        self.data = DataManager()
        self.scraper = WikiScraper()

        # State
        self.current_campaign = CAMPAIGN_ORDER[0]
        self.selected_quest = None
        self.visible_quests = []  # parallel to listbox rows
        self.search_var = tk.StringVar()
        self.profile_var = tk.StringVar(value=self.data.current_profile_name)

        self.collapsed_sections = {}  # campaign_name -> set of header lines
        self.row_meta = []  # one entry per row in quest_list

        # Build UI
        self._build_layout()
        self._load_profiles()
        self._select_initial_campaign()
        self._refresh_quest_list()

    # ---------------- UI LAYOUT ----------------
    def _setup_dark_theme(self):
        style = ttk.Style(self)

        # Use a theme that respects our color overrides
        try:
            style.theme_use("clam")
        except tk.TclError:
            # Fall back to current theme if clam is missing
            pass

        # General backgrounds
        self.configure(bg=DARK_BG)
        style.configure("TFrame", background=DARK_BG)
        style.configure("TLabel", background=DARK_BG, foreground=DARK_TEXT)
        style.configure("TButton", background=DARK_PANEL, foreground=DARK_TEXT)
        style.configure(
            "TCombobox",
            fieldbackground=DARK_ENTRY,
            foreground=DARK_TEXT,
            background=DARK_PANEL,
        )
        style.map(
            "TCombobox",
            fieldbackground=[
                ("readonly", DARK_ENTRY),
                ("!readonly", DARK_ENTRY),
                ("active", DARK_ENTRY),
                ("focus", DARK_ENTRY),
            ],
            foreground=[
                ("readonly", DARK_TEXT),
                ("!readonly", DARK_TEXT),
                ("active", DARK_TEXT),
                ("focus", DARK_TEXT),
            ],
        )
        # --- Combobox Arrow Styling ---
        # Force arrow background + hover color
        style.element_create(
            "CustomCombobox.downarrow", "from", "clam"
        )

        style.layout(
            "TCombobox",
            [
                ("Combobox.border", {
                    "sticky": "nswe",
                    "children": [
                        ("Combobox.padding", {
                            "sticky": "nswe",
                            "children": [
                                ("CustomCombobox.downarrow", {
                                    "side": "right",
                                    "sticky": "ns"
                                }),
                                ("Combobox.textarea", {
                                    "sticky": "nswe"
                                })
                            ]
                        })
                    ]
                })
            ]
        )
        # Arrow should always be white
        style.configure(
            "TCombobox",
            arrowsize=12,
            arrowcolor=DARK_TEXT,  # white
        )

        # Normal state → arrow box black
        # Hover (active) → arrow box blue
        style.map(
            "TCombobox",
            arrowcolor=[
                ("!disabled", DARK_TEXT),
                ("active", DARK_TEXT),
                ("focus", DARK_TEXT),
            ],
            fieldbackground=[
                ("readonly", DARK_ENTRY),
                ("!readonly", DARK_ENTRY),
                ("active", DARK_ENTRY),
                ("focus", DARK_ENTRY),
            ],
            background=[
                ("active", DARK_ACCENT),   # hover blue
                ("!active", DARK_ENTRY),   # idle black
            ]
        )

        style.map("TButton", background=[("active", DARK_ACCENT)])
        

        # Entry / Combobox
        style.configure(
            "TEntry",
            fieldbackground=DARK_ENTRY,
            foreground=DARK_TEXT,
        )
        style.configure(
            "TCombobox",
            fieldbackground=DARK_ENTRY,
            foreground=DARK_TEXT,
            background=DARK_PANEL,
        )

        # Treeview (history window)
        style.configure(
            "Treeview",
            background=DARK_PANEL,
            fieldbackground=DARK_PANEL,
            foreground=DARK_TEXT,
        )
        style.configure(
            "Treeview.Heading",
            background=DARK_PANEL,
            foreground=DARK_TEXT,
        )    

    def _build_layout(self):
        # Top bar (profiles + search + actions)
        top = ttk.Frame(self)
        top.pack(side=tk.TOP, fill=tk.X, padx=8, pady=8)

        # Profile selector
        ttk.Label(top, text="Profile:").pack(side=tk.LEFT)
        self.profile_combo = ttk.Combobox(
            top,
            textvariable=self.profile_var,
            state="readonly",
            width=24,
        )
        self.profile_combo.pack(side=tk.LEFT, padx=(4, 4))
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_changed)

        ttk.Button(top, text="New", command=self._create_profile).pack(side=tk.LEFT)
        ttk.Button(top, text="Delete", command=self._delete_profile).pack(side=tk.LEFT, padx=(2, 10))

        # Search box
        ttk.Label(top, text="Search:").pack(side=tk.LEFT)
        search_entry = ttk.Entry(top, textvariable=self.search_var, width=40)
        search_entry.pack(side=tk.LEFT, padx=(4, 4))
        self.search_var.trace_add("write", lambda *args: self._refresh_quest_list())

        ttk.Button(top, text="Sync DB", command=self._sync_database).pack(side=tk.LEFT, padx=(10, 2))

        ttk.Button(top, text="Export", command=self._export_profile).pack(side=tk.LEFT, padx=(2, 2))
        ttk.Button(top, text="Import", command=self._import_profile).pack(side=tk.LEFT, padx=(2, 2))

        ttk.Button(top, text="History", command=self._show_history).pack(side=tk.LEFT, padx=(10, 2))

        # Status bar
        self.status_var = tk.StringVar(value="Ready.")
        status_bar = ttk.Label(self, textvariable=self.status_var, anchor="w", relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Main area: left = campaigns, center = quest list, right = actions
        main = ttk.Frame(self)
        main.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        # Campaign list
        left = ttk.Frame(main)
        left.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Label(left, text="Campaigns", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 4))
        max_campaign_len = max(len(name) for name in CAMPAIGN_ORDER)
        self.campaign_list = tk.Listbox(
            left,
            height=10,
            width=max_campaign_len,
            exportselection=False,
            bg=DARK_LISTBG,
            fg=DARK_TEXT,
            selectbackground=DARK_LISTSEL,
            selectforeground=DARK_TEXT,
            highlightthickness=0,
            borderwidth=0,
            activestyle="none",
        )

        self.campaign_list.pack(fill=tk.Y, expand=False)
        for camp in CAMPAIGN_ORDER:
            self.campaign_list.insert(tk.END, camp)
        self.campaign_list.bind("<<ListboxSelect>>", self._on_campaign_selected)

        # Quest list
        center = ttk.Frame(main)
        center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 10))

        ttk.Label(center, text="Quests", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 4))

        self.quest_list = tk.Listbox(
            center,
            selectmode=tk.SINGLE,
            exportselection=False,
            bg=DARK_LISTBG,
            fg=DARK_TEXT,
            selectbackground=DARK_LISTSEL,
            selectforeground=DARK_TEXT,
            highlightthickness=0,
            borderwidth=0,
            activestyle="none",
        )

        self.quest_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.quest_list.bind("<<ListboxSelect>>", self._on_quest_selected)

        quest_scroll = ttk.Scrollbar(center, orient=tk.VERTICAL, command=self.quest_list.yview)
        quest_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.quest_list.configure(yscrollcommand=quest_scroll.set)

        # Right actions pane
        right = ttk.Frame(main)
        right.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Label(right, text="Actions", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 4))

        ttk.Button(right, text="Mark Not Started", command=lambda: self._set_status(QuestStatus.NOT_STARTED)).pack(
            fill=tk.X, pady=(0, 4)
        )
        ttk.Button(right, text="Mark In Progress", command=lambda: self._set_status(QuestStatus.IN_PROGRESS)).pack(
            fill=tk.X, pady=(0, 4)
        )
        ttk.Button(right, text="Mark Completed", command=lambda: self._set_status(QuestStatus.COMPLETED)).pack(
            fill=tk.X, pady=(0, 10)
        )

        ttk.Button(right, text="Open in Wiki", command=self._open_in_wiki).pack(fill=tk.X, pady=(0, 4))
        ttk.Button(right, text="Reset Campaign", command=self._reset_campaign).pack(fill=tk.X, pady=(10, 4))
        
        #ttk.Label(right, text="Sections:").pack(anchor="w", pady=(15, 2))
        ttk.Label(right, text="Section Control", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(15, 2))
        btn_expand_all = ttk.Button(
            right,
            text="Expand All",
            command=self._expand_all_sections,
        )
        btn_expand_all.pack(fill="x", pady=1)

        btn_collapse_all = ttk.Button(
            right,
            text="Collapse All",
            command=self._collapse_all_sections,
        )
        btn_collapse_all.pack(fill="x", pady=1)

    # ---------------- PROFILES ----------------

    def _load_profiles(self):
        profiles = self.data.get_profiles()
        if not profiles:
            profiles = [self.data.current_profile_name]

        self.profile_combo["values"] = profiles

        if self.data.current_profile_name in profiles:
            self.profile_var.set(self.data.current_profile_name)
        else:
            self.profile_var.set(profiles[0])

    def _on_profile_changed(self, event=None):
        name = self.profile_var.get()
        if not name:
            return
        self.data.switch_profile(name)
        self._refresh_quest_list()
        self._set_status_text(f"Switched to profile: {name}")

    def _create_profile(self):
        def do_create():
            name = entry.get().strip()
            if not name:
                messagebox.showwarning("Profile", "Profile name cannot be empty.")
                return
            if self.data.create_profile(name):
                self._load_profiles()
                self.profile_var.set(name)
                dialog.destroy()
                self._refresh_quest_list()
                self._set_status_text(f"Created profile: {name}")
            else:
                messagebox.showerror("Profile", "Could not create profile. Name may be invalid or already exists.")

        dialog = tk.Toplevel(self)
        dialog.title("New Profile")
        ttk.Label(dialog, text="Profile name:").pack(padx=10, pady=(10, 4))
        entry = ttk.Entry(dialog)
        entry.pack(padx=10, pady=(0, 10))
        entry.focus()
        ttk.Button(dialog, text="Create", command=do_create).pack(padx=10, pady=(0, 10))

    def _delete_profile(self):
        name = self.profile_var.get()
        if not name:
            return
        if not messagebox.askyesno("Delete Profile", f"Delete profile '{name}'? This cannot be undone."):
            return
        if not self.data.delete_profile(name):
            messagebox.showerror("Profile", "Cannot delete the last remaining profile.")
            return
        self._load_profiles()
        self._refresh_quest_list()
        self._set_status_text(f"Deleted profile: {name}")

    # ---------------- CAMPAIGNS & QUESTS ----------------

    def _select_initial_campaign(self):
        try:
            idx = CAMPAIGN_ORDER.index(self.current_campaign)
        except ValueError:
            idx = 0
        self.campaign_list.selection_clear(0, tk.END)
        self.campaign_list.selection_set(idx)
        self.campaign_list.see(idx)

    def _toggle_section(self, header_line: str):
        """Toggle collapsed/expanded state for a section header in the current campaign."""
        camp = self.current_campaign
        coll = self.collapsed_sections.setdefault(camp, set())
        if header_line in coll:
            coll.remove(header_line)
        else:
            coll.add(header_line)
        self._refresh_quest_list()

    def _collapse_all_sections(self):
        """Collapse all section headers for the current campaign."""
        quests = self.data.quest_db.get(self.current_campaign, [])
        headers = {q for q in quests if SECTION_MARKER in q}
        if headers:
            self.collapsed_sections[self.current_campaign] = set(headers)
        else:
            self.collapsed_sections[self.current_campaign] = set()
        self._refresh_quest_list()

    def _expand_all_sections(self):
        """Expand all section headers for the current campaign."""
        if self.current_campaign in self.collapsed_sections:
            self.collapsed_sections[self.current_campaign].clear()
        self._refresh_quest_list()

    def _on_campaign_selected(self, event=None):
        sel = self.campaign_list.curselection()
        if not sel:
            return
        idx = sel[0]
        self.current_campaign = CAMPAIGN_ORDER[idx]
        self.selected_quest = None
        self._refresh_quest_list()
        self._set_status_text(f"Switched to campaign: {self.current_campaign}")

    def _refresh_quest_list(self):
        quests = self.data.quest_db.get(self.current_campaign, [])
        status_map = self.data.get_current_quests()
        search = self.search_var.get().lower().strip()

        self.quest_list.delete(0, tk.END)
        self.visible_quests = []
        self.row_meta = []

        collapsed = self.collapsed_sections.get(self.current_campaign, set())

        # -------- No search: respect collapsed sections --------
        if not search:
            skipping = False  # whether we are currently inside a collapsed section

            for q in quests:
                # Section headers
                if SECTION_MARKER in q:
                    header_line = q
                    header_text = q.replace(SECTION_MARKER, "").strip()
                    if not header_text:
                        header_text = "---"

                    is_collapsed = header_line in collapsed
                    icon = "▸" if is_collapsed else "▾"
                    display = f"{icon} {header_text.upper()}"
                    self.quest_list.insert(tk.END, display)
                    self.visible_quests.append(None)
                    self.row_meta.append({"type": "header", "header": header_line})

                    # Determine if this section should be collapsed
                    skipping = is_collapsed
                    continue

                # Real quest entries
                if skipping:
                    # We are inside a collapsed section, skip showing these quests
                    continue

                info = status_map.get(q, {"status": QuestStatus.NOT_STARTED, "timestamp": None})
                status = info.get("status", QuestStatus.NOT_STARTED)

                if status == QuestStatus.NOT_STARTED:
                    prefix = "[ ]"
                elif status == QuestStatus.IN_PROGRESS:
                    prefix = "[~]"
                else:
                    prefix = "[✔]"

                display = f"\u00A0\u00A0\u00A0\u00A0\u00A0{prefix} {q}"
                self.quest_list.insert(tk.END, display)
                self.visible_quests.append(q)
                self.row_meta.append({"type": "quest", "name": q})

            return

        # -------- Search active: ignore collapsed state, only show relevant sections --------

        # First, group quests by section header
        sections: list[tuple[str | None, list[str]]] = []
        current_header: str | None = None
        current_quests: list[str] = []

        for q in quests:
            if SECTION_MARKER in q:
                # flush previous group
                if current_header is not None or current_quests:
                    sections.append((current_header, current_quests))
                current_header = q
                current_quests = []
            else:
                current_quests.append(q)

        # flush last group
        if current_header is not None or current_quests:
            sections.append((current_header, current_quests))

        # Now render only sections with at least one matching quest
        for header, qs in sections:
            # filter quests within this section
            filtered_qs = [q for q in qs if search in q.lower()]
            if not filtered_qs:
                continue  # skip section entirely

            # Render header if it exists
            if header is not None:
                header_text = header.replace(SECTION_MARKER, "").strip()
                if not header_text:
                    header_text = "---"
                # In search mode we always treat sections as expanded
                icon = "▾"
                display = f"{icon} {header_text.upper()}"
                self.quest_list.insert(tk.END, display)
                self.visible_quests.append(None)
                self.row_meta.append({"type": "header", "header": header})

            # Render only matching quests
            for q in filtered_qs:
                info = status_map.get(q, {"status": QuestStatus.NOT_STARTED, "timestamp": None})
                status = info.get("status", QuestStatus.NOT_STARTED)

                if status == QuestStatus.NOT_STARTED:
                    prefix = "[ ]"
                elif status == QuestStatus.IN_PROGRESS:
                    prefix = "[~]"
                else:
                    prefix = "[✔]"

                display = f"\u00A0\u00A0\u00A0\u00A0\u00A0{prefix} {q}"
                self.quest_list.insert(tk.END, display)
                self.visible_quests.append(q)
                self.row_meta.append({"type": "quest", "name": q})

    def _on_quest_selected(self, event=None):
        sel = self.quest_list.curselection()
        if not sel:
            self.selected_quest = None
            return

        idx = sel[0]

        # If we somehow got out of sync, guard against index error
        if idx >= len(self.row_meta):
            self.selected_quest = None
            return

        meta = self.row_meta[idx]

        # Clicking a header toggles collapse/expand (only when not searching)
        if meta["type"] == "header":
            # Don't let header clicks do anything while searching;
            # search results ignore collapsed state anyway.
            if self.search_var.get().strip():
                return

            header_line = meta["header"]
            self.selected_quest = None
            self._toggle_section(header_line)
            return

        # Normal quest row
        quest = meta["name"]
        self.selected_quest = quest
        
    def _set_status(self, status: int):
        """Set the status of the currently selected quest and refresh the view."""
        if not self.selected_quest:
            messagebox.showinfo("Status", "Please select a quest first.")
            return

        # Update DB
        self.data.set_status(self.selected_quest, status)

        # Refresh UI
        self._refresh_quest_list()

        # Friendly status text
        if status == QuestStatus.NOT_STARTED:
            label = "Not Started"
        elif status == QuestStatus.IN_PROGRESS:
            label = "In Progress"
        else:
            label = "Completed"

        self._set_status_text(f"Marked '{self.selected_quest}' as {label}.")

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


    def _reset_campaign(self):
        if not messagebox.askyesno(
            "Reset Campaign",
            f"Reset all quest states for {self.current_campaign} in profile '{self.data.current_profile_name}'?",
        ):
            return
        self.data.reset_campaign(self.current_campaign)
        self._refresh_quest_list()
        self._set_status_text(f"Reset campaign: {self.current_campaign}")

    # ---------------- SYNC / EXPORT / HISTORY ----------------

    def _sync_database(self):
        if not messagebox.askyesno(
            "Sync Database",
            "Syncing will contact the Guild Wars wiki and may take a bit.\n\nContinue?",
        ):
            return

        self._set_status_text("Syncing quest database from wiki...")
        self.status_var.set("Sync in progress...")
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
        if errors:
            msg = "Sync completed with errors:\n\n" + "\n".join(errors)
            messagebox.showwarning("Sync Finished", msg)
        else:
            messagebox.showinfo("Sync Finished", "Quest database updated successfully.")
        self._refresh_quest_list()
        self._set_status_text("Sync finished.")

    def _export_profile(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Export profile",
        )
        if not path:
            return
        try:
            self.data.export_profile_to_json(path)
            messagebox.showinfo("Export", f"Profile exported to:\n{path}")
            self._set_status_text(f"Exported profile to {path}")
        except Exception as e:
            logging.exception("Export failed")
            messagebox.showerror("Export Failed", str(e))

    def _import_profile(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Import profile",
        )
        if not path:
            return
        try:
            count = self.data.import_profile_from_json(path)
            messagebox.showinfo("Import", f"Imported {count} quests from:\n{path}")
            self._refresh_quest_list()
            self._set_status_text(f"Imported {count} quests.")
        except Exception as e:
            logging.exception("Import failed")
            messagebox.showerror("Import Failed", str(e))

    def _show_history(self):
        history = self.data.get_completion_history()
        if not history:
            messagebox.showinfo("Quest History", "No completed quests yet.")
            return

        dialog = tk.Toplevel(self)
        dialog.title("Quest History")
        dialog.geometry("600x400")
        dialog.configure(bg=DARK_BG)

        tree = ttk.Treeview(dialog, columns=("quest", "time"), show="headings")
        tree.heading("quest", text="Quest")
        tree.heading("time", text="Completed At")
        tree.column("quest", width=320)
        tree.column("time", width=240)
        tree.pack(fill=tk.BOTH, expand=True)

        for quest_name, ts in history:
            tree.insert("", tk.END, values=(quest_name, ts))

    # ---------------- UTILS ----------------

    def _set_status_text(self, text):
        self.status_var.set(text)


if __name__ == "__main__":
    app = LinuxQuestTracker()
    app.mainloop()
