# database.py
import sqlite3
import json
import os
import logging
import datetime
import time
import shutil
import re
from config import AppConfig, SECTION_MARKER, INITIAL_QUEST_DB, QuestStatus

class DiskCache:
    def __init__(self, db_path, expiry_hours, max_size_mb, max_entries):
        self.db_path = db_path
        self.expiry_seconds = expiry_hours * 3600
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_entries = max_entries
        self._init_db_safe()

    def _init_db_safe(self):
        try:
            self._connect_and_create()
        except sqlite3.DatabaseError:
            logging.error(f"Cache DB corrupted: {self.db_path}. Recreating...")
            try:
                if self.conn: self.conn.close()
            except: pass
            if os.path.exists(self.db_path): os.remove(self.db_path)
            self._connect_and_create()

    def _connect_and_create(self):
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=60)
        self.conn.execute("PRAGMA journal_mode=WAL") 
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA auto_vacuum = INCREMENTAL")
        with self.conn:
            self.conn.execute("CREATE TABLE IF NOT EXISTS cache (url TEXT PRIMARY KEY, content TEXT, timestamp REAL)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_timestamp ON cache(timestamp)")

    def get(self, url):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT content, timestamp FROM cache WHERE url = ?", (url,))
            row = cursor.fetchone()
            if row:
                content, timestamp = row
                if time.time() - timestamp < self.expiry_seconds: return content
                else: self.delete(url)
        except sqlite3.Error: pass
        return None

    def set(self, url, content):
        try:
            with self.conn:
                self.conn.execute("INSERT OR REPLACE INTO cache (url, content, timestamp) VALUES (?, ?, ?)", (url, content, time.time()))
            self._prune()
        except sqlite3.Error: pass

    def delete(self, url):
        try:
            with self.conn:
                self.conn.execute("DELETE FROM cache WHERE url = ?", (url,))
        except sqlite3.Error: pass

    def _prune(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT count(*) FROM cache")
            count = cursor.fetchone()[0]
            if count > self.max_entries:
                with self.conn:
                    self.conn.execute("DELETE FROM cache WHERE url IN (SELECT url FROM cache ORDER BY timestamp ASC LIMIT ?)", (count - self.max_entries,))
            if os.path.exists(self.db_path) and os.path.getsize(self.db_path) > self.max_size_bytes:
                with self.conn:
                     self.conn.execute("DELETE FROM cache WHERE url IN (SELECT url FROM cache ORDER BY timestamp ASC LIMIT ?)", (self.max_entries // 4,))
        except sqlite3.Error: pass
            
    def maintenance(self):
        try:
            with self.conn: self.conn.execute("PRAGMA incremental_vacuum")
        except sqlite3.Error: pass
    
    def close(self):
        try: self.conn.close()
        except: pass

class DataManager:
    def __init__(self):
        self.db_path = AppConfig.DB_FILE
        self.json_user_file = AppConfig.USER_FILE
        self._backup_db()
        self._init_db_safe() 
        self.cache = DiskCache(AppConfig.CACHE_FILE, AppConfig.CACHE_EXPIRY_HOURS, AppConfig.MAX_CACHE_SIZE_MB, AppConfig.MAX_CACHE_ENTRIES)
        self.cache.maintenance()
        self.current_profile_name = self._get_setting("current_profile", AppConfig.DEFAULT_PROFILE_NAME)
        self.quest_db = self._load_quest_db()
        if not self.quest_db:
             self.quest_db = INITIAL_QUEST_DB
             self._save_quest_db(self.quest_db)
        self._migrate_from_json()
        if not self._profile_exists(self.current_profile_name):
             try:
                 with self.conn: self.conn.execute("INSERT INTO profiles (name) VALUES (?)", (self.current_profile_name,))
                 self.switch_profile(self.current_profile_name)
             except Exception: pass

    def _backup_db(self):
        if os.path.exists(self.db_path):
            try: 
                shutil.copy2(self.db_path, f"{self.db_path}.bak")
                logging.info(f"Database backup created at {self.db_path}.bak")
            except Exception as e:
                logging.warning(f"Failed to create database backup: {e}")

    def _init_db_safe(self):
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=60)
            self.conn.execute("PRAGMA foreign_keys = ON")
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA quick_check")
            self._run_migrations()
        except sqlite3.DatabaseError:
            self._recover_database()

    def _recover_database(self):
        try:
            if self.conn: self.conn.close()
        except: pass
        if os.path.exists(self.db_path):
            try: os.rename(self.db_path, f"{self.db_path}.corrupted_{int(time.time())}")
            except: pass
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=60)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._run_migrations()

    def _run_migrations(self):
        cursor = self.conn.execute("PRAGMA user_version")
        current_ver = cursor.fetchone()[0]
        with self.conn:
            if current_ver < 1:
                self.conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
                self.conn.execute("CREATE TABLE IF NOT EXISTS profiles (name TEXT PRIMARY KEY)")
                self.conn.execute("""CREATE TABLE IF NOT EXISTS quest_status (
                        profile TEXT, quest_name TEXT, status INTEGER, timestamp TEXT,
                        PRIMARY KEY (profile, quest_name),
                        FOREIGN KEY(profile) REFERENCES profiles(name) ON DELETE CASCADE
                    )""")
                self.conn.execute("CREATE TABLE IF NOT EXISTS game_data (key TEXT PRIMARY KEY, json_data TEXT)")
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_status_profile ON quest_status(profile)")
                self.conn.execute(f"PRAGMA user_version = 1")
            if current_ver < 2:
                cursor = self.conn.execute("PRAGMA table_info(quest_status)")
                if 'timestamp' not in [col[1] for col in cursor.fetchall()]:
                    self.conn.execute("ALTER TABLE quest_status ADD COLUMN timestamp TEXT")
                self.conn.execute(f"PRAGMA user_version = 2")

    def _migrate_from_json(self):
        if not os.path.exists(self.json_user_file): return
        try:
            with open(self.json_user_file, 'r', encoding='utf-8') as f: data = json.load(f)
            insert_data = []
            for q, info in data.items():
                s = info.get("status")
                if s in [QuestStatus.IN_PROGRESS, QuestStatus.COMPLETED]:
                     insert_data.append((self.current_profile_name, q, s, info.get("timestamp")))
            if insert_data:
                with self.conn:
                    self.conn.executemany("INSERT OR IGNORE INTO quest_status (profile, quest_name, status, timestamp) VALUES (?, ?, ?, ?)", insert_data)
            logging.info(f"Migrated {len(insert_data)} records from legacy JSON to SQLite.")
        except Exception as e: 
            logging.error(f"JSON Migration failed: {e}")

    # --- PUBLIC API ---
    def get_setting(self, key, default): return self._get_setting(key, default)
    def set_setting(self, key, value): self._set_setting(key, value)
    
    def _get_setting(self, key, default):
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cur.fetchone()
            return row[0] if row else default
        except: return default

    def _set_setting(self, key, value):
        with self.conn: self.conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))

    def _profile_exists(self, name):
        cur = self.conn.cursor()
        cur.execute("SELECT 1 FROM profiles WHERE name = ?", (name,))
        return cur.fetchone() is not None

    def _load_quest_db(self):
        cur = self.conn.cursor()
        cur.execute("SELECT json_data FROM game_data WHERE key = 'quest_db'")
        row = cur.fetchone()
        return json.loads(row[0]) if row else {}

    def _save_quest_db(self, data):
        with self.conn: self.conn.execute("INSERT OR REPLACE INTO game_data (key, json_data) VALUES (?, ?)", ('quest_db', json.dumps(data)))

    def get_theme(self): return self._get_setting("dark_mode", "False") == "True"
    def set_theme(self, is_dark): self._set_setting("dark_mode", str(is_dark))

    def get_profiles(self):
        cur = self.conn.cursor()
        cur.execute("SELECT name FROM profiles")
        return [row[0] for row in cur.fetchall()]
        
    def create_profile(self, name):
        name = name.strip()
        if not name or self._profile_exists(name) or len(name) > AppConfig.MAX_PROFILE_NAME_LEN: return False
        if not re.match(r'^[a-zA-Z0-9 _-]+$', name): return False
        try:
            with self.conn: self.conn.execute("INSERT INTO profiles (name) VALUES (?)", (name,))
            self.switch_profile(name)
            return True
        except: return False

    def delete_profile(self, name):
        if len(self.get_profiles()) <= 1: return False
        try:
            with self.conn: self.conn.execute("DELETE FROM profiles WHERE name = ?", (name,))
            remaining = self.get_profiles()
            if remaining: self.switch_profile(remaining[0])
            return True
        except: return False
        
    def switch_profile(self, profile_name):
        if self._profile_exists(profile_name):
            self.current_profile_name = profile_name
            self._set_setting("current_profile", profile_name)

    def get_current_quests(self):
        cur = self.conn.cursor()
        cur.execute("SELECT quest_name, status, timestamp FROM quest_status WHERE profile = ?", (self.current_profile_name,))
        return {row[0]: {"status": row[1], "timestamp": row[2]} for row in cur.fetchall()}

    def get_cached_content(self, url): return self.cache.get(url)
    
    def set_status(self, quest, status):
        with self.conn:
            if status == QuestStatus.COMPLETED:
                ts = datetime.datetime.now().strftime(AppConfig.DATE_FORMAT)
                self.conn.execute("INSERT OR REPLACE INTO quest_status (profile, quest_name, status, timestamp) VALUES (?, ?, ?, ?)", (self.current_profile_name, quest, status, ts))
            elif status == QuestStatus.IN_PROGRESS:
                 self.conn.execute("INSERT OR REPLACE INTO quest_status (profile, quest_name, status, timestamp) VALUES (?, ?, ?, NULL)", (self.current_profile_name, quest, status))
            else:
                self.conn.execute("DELETE FROM quest_status WHERE profile = ? AND quest_name = ?", (self.current_profile_name, quest))

    def reset_campaign(self, campaign):
        if campaign in self.quest_db:
            quests = [q for q in self.quest_db[campaign] if SECTION_MARKER not in q]
            with self.conn:
                self.conn.executemany("DELETE FROM quest_status WHERE profile = ? AND quest_name = ?", [(self.current_profile_name, q) for q in quests])
    
    def update_quest_db(self, new_db):
        self.quest_db = new_db
        self._save_quest_db(new_db)

    # --- API ALIASES ---
    def get_quests_for_campaign(self, campaign): return self.quest_db.get(campaign, [])
    def get_history(self): return self.get_completion_history()
    def import_profile(self, path): return self.import_profile_from_json(path)
    def export_profile(self, path): return self.export_profile_to_json(path)

    # --- NEW: ANALYTICS & EXPORT ---
    def get_completion_history(self):
        """Returns list of (quest_name, timestamp) sorted by most recent."""
        cur = self.conn.cursor()
        cur.execute("SELECT quest_name, timestamp FROM quest_status WHERE profile = ? AND status = ? AND timestamp IS NOT NULL ORDER BY timestamp DESC", 
                    (self.current_profile_name, QuestStatus.COMPLETED))
        return cur.fetchall()

    def export_profile_to_json(self, filepath):
        """Exports current profile data to JSON."""
        data = {
            "meta": {"version": AppConfig.APP_VERSION, "date": datetime.datetime.now().strftime(AppConfig.DATE_FORMAT)},
            "profile": self.current_profile_name,
            "quests": self.get_current_quests()
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def import_profile_from_json(self, filepath):
        """Imports data, merging with current profile."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        quests = data.get("quests", {})
        count = 0
        with self.conn:
            for q_name, q_data in quests.items():
                status = q_data.get("status")
                timestamp = q_data.get("timestamp")
                if status:
                    self.conn.execute("INSERT OR REPLACE INTO quest_status (profile, quest_name, status, timestamp) VALUES (?, ?, ?, ?)",
                                      (self.current_profile_name, q_name, status, timestamp))
                    count += 1
        return count