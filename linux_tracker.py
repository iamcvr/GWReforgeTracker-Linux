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


class LinuxQuestTracker(tk.Tk):
    def __init__(self):
        super().__init__()

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

        # Build UI
        self._build_layout()
        self._load_profiles()
        self._select_initial_campaign()
        self._refresh_quest_list()

    # ---------------- UI LAYOUT ----------------

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
        self.campaign_list = tk.Listbox(left, height=10, exportselection=False)
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

        self.selected_label = ttk.Label(right, text="Selected: (none)", wraplength=200, justify="left")
        self.selected_label.pack(fill=tk.X, pady=(10, 0))

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

    def _on_campaign_selected(self, event=None):
        sel = self.campaign_list.curselection()
        if not sel:
            return
        idx = sel[0]
        self.current_campaign = CAMPAIGN_ORDER[idx]
        self.selected_quest = None
        self.selected_label.config(text="Selected: (none)")
        self._refresh_quest_list()
        self._set_status_text(f"Switched to campaign: {self.current_campaign}")

    def _refresh_quest_list(self):
        quests = self.data.quest_db.get(self.current_campaign, [])
        status_map = self.data.get_current_quests()
        search = self.search_var.get().lower().strip()

        self.quest_list.delete(0, tk.END)
        self.visible_quests = []

        # -------- No search: original behaviour --------
        if not search:
            for q in quests:
                # Section headers
                if SECTION_MARKER in q:
                    header_text = q.replace(SECTION_MARKER, "").strip()
                    if not header_text:
                        header_text = "---"
                    display = f"=== {header_text} ==="
                    self.quest_list.insert(tk.END, display)
                    self.visible_quests.append(None)
                    continue

                # Real quest entries
                info = status_map.get(q, {"status": QuestStatus.NOT_STARTED, "timestamp": None})
                status = info.get("status", QuestStatus.NOT_STARTED)

                if status == QuestStatus.NOT_STARTED:
                    prefix = "[ ]"
                elif status == QuestStatus.IN_PROGRESS:
                    prefix = "[~]"
                else:
                    prefix = "[X]"

                display = f"{prefix} {q}"
                self.quest_list.insert(tk.END, display)
                self.visible_quests.append(q)
            return

        # -------- Search active: only show relevant sections --------

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
                display = f"=== {header_text} ==="
                self.quest_list.insert(tk.END, display)
                self.visible_quests.append(None)

            # Render only matching quests
            for q in filtered_qs:
                info = status_map.get(q, {"status": QuestStatus.NOT_STARTED, "timestamp": None})
                status = info.get("status", QuestStatus.NOT_STARTED)

                if status == QuestStatus.NOT_STARTED:
                    prefix = "[ ]"
                elif status == QuestStatus.IN_PROGRESS:
                    prefix = "[~]"
                else:
                    prefix = "[X]"

                display = f"{prefix} {q}"
                self.quest_list.insert(tk.END, display)
                self.visible_quests.append(q)


    def _on_quest_selected(self, event=None):
        sel = self.quest_list.curselection()
        if not sel:
            self.selected_quest = None
            self.selected_label.config(text="Selected: (none)")
            return
        idx = sel[0]
        quest = self.visible_quests[idx]
        if quest is None:
            # Section header clicked
            self.selected_quest = None
            self.selected_label.config(text="Selected: (none)")
            return
        self.selected_quest = quest
        self.selected_label.config(text=f"Selected: {quest}")

    def _set_status(self, status):
        if not self.selected_quest:
            messagebox.showinfo("Quest Status", "Please select a quest first.")
            return
        self.data.set_status(self.selected_quest, status)
        self._refresh_quest_list()

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
