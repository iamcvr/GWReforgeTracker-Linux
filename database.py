# database.py
import sqlite3
import json
import os
import logging
import datetime
import time
import shutil
from config import AppConfig, SECTION_MARKER, INITIAL_QUEST_DB, QuestStatus

class DiskCache:
# ... (DiskCache class remains the same)
# ... (all DiskCache methods remain the same)
    def __init__(self, db_path, expiry_hours, max_size_mb, max_entries):
        self.db_path = db_path
        self.expiry_seconds = expiry_hours * 3600
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_entries = max_entries
        self._init_db()

    def _init_db(self):
        try:
            # Use max timeout for busy operations
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=60) 
            with self.conn:
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS cache (
                        url TEXT PRIMARY KEY,
                        content TEXT,
                        timestamp REAL
                    )
                """)
                # PERFORMANCE: Add index on timestamp for faster pruning
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_timestamp ON cache(timestamp)")
        except Exception as e:
            # This is a critical error, likely permission or file corruption
            logging.error(f"Cache Init Error: {e}", exc_info=True) 

    def get(self, url):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT content, timestamp FROM cache WHERE url = ?", (url,))
            row = cursor.fetchone()
            if row:
                content, timestamp = row
                if time.time() - timestamp < self.expiry_seconds:
                    return content
                else:
                    self.delete(url)
        except sqlite3.Error as e: 
            logging.warning(f"DiskCache GET error for {url}: {e}")
        return None

    def set(self, url, content):
        try:
            with self.conn:
                self.conn.execute("INSERT OR REPLACE INTO cache (url, content, timestamp) VALUES (?, ?, ?)", 
                                  (url, content, time.time()))
            self._prune()
        except sqlite3.Error as e: 
            logging.warning(f"DiskCache SET error for {url}: {e}")

    def delete(self, url):
        try:
            with self.conn:
                self.conn.execute("DELETE FROM cache WHERE url = ?", (url,))
        except sqlite3.Error as e: 
            logging.warning(f"DiskCache DELETE error for {url}: {e}")

    def _prune(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT count(*) FROM cache")
            count = cursor.fetchone()[0]
            
            needs_vacuum = False
            
            if count > self.max_entries:
                logging.info(f"Pruning cache by count: {count} > {self.max_entries}")
                with self.conn:
                    # Efficiently delete oldest entries using the index
                    self.conn.execute("""
                        DELETE FROM cache WHERE url IN (
                            SELECT url FROM cache ORDER BY timestamp ASC LIMIT ?
                        )
                    """, (count - self.max_entries,))
                    needs_vacuum = True
            
            if os.path.exists(self.db_path) and os.path.getsize(self.db_path) > self.max_size_bytes:
                logging.info(f"Pruning cache by size: {os.path.getsize(self.db_path)/1024/1024:.2f}MB > {self.max_size_bytes/1024/1024:.2f}MB")
                with self.conn:
                     self.conn.execute("""
                        DELETE FROM cache WHERE url IN (
                            SELECT url FROM cache ORDER BY timestamp ASC LIMIT ?
                        )
                    """, (self.max_entries // 2,))
                     needs_vacuum = True
                
            # Reclaim disk space after large deletes
            if needs_vacuum:
                with self.conn:
                    self.conn.execute("VACUUM")
                    
        except sqlite3.Error as e: 
            logging.error(f"DiskCache PRUNE error: {e}")
    
    def close(self):
        try: self.conn.close()
        except sqlite3.Error as e: 
            logging.error(f"DiskCache CLOSE error: {e}")

class DataManager:
    def __init__(self):
        self.db_path = AppConfig.DB_FILE
        self.json_user_file = AppConfig.USER_FILE
        
        self._backup_db()
        self._init_db()
        
        self.cache = DiskCache(
            AppConfig.CACHE_FILE, 
            AppConfig.CACHE_EXPIRY_HOURS, 
            AppConfig.MAX_CACHE_SIZE_MB,
            AppConfig.MAX_CACHE_ENTRIES
        )
        
        # --- Initialization Order Change ---
        self.current_profile_name = self._get_setting("current_profile", AppConfig.DEFAULT_PROFILE_NAME)
        
        # 1. Load/Initialize quest_db FIRST
        self.quest_db = self._load_quest_db()
        if not self.quest_db:
             self.quest_db = INITIAL_QUEST_DB
             self._save_quest_db(self.quest_db)
        
        # 2. Perform migration (which relies on self.current_profile_name being set)
        self._migrate_from_json()

        # 3. Ensure profile exists (which calls switch_profile/ensure_tracked)
        if not self._profile_exists(self.current_profile_name):
             self.create_profile(self.current_profile_name) 
        
        # 4. Final integrity check (can now access self.quest_db safely)
        self._ensure_all_quests_tracked() 
        # ----------------------------------------------------------------------------------


    def _backup_db(self):
        if os.path.exists(self.db_path):
            try:
                backup_path = f"{self.db_path}.bak"
                shutil.copy2(self.db_path, backup_path)
                logging.info(f"Database backup created at {backup_path}")
            except Exception as e:
                logging.error(f"Failed to create database backup: {e}")

    def _init_db(self):
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=60)
            with self.conn:
                self.conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
                self.conn.execute("CREATE TABLE IF NOT EXISTS profiles (name TEXT PRIMARY KEY)")
                
                # Check if 'timestamp' column exists
                cursor = self.conn.execute("PRAGMA table_info(quest_status)")
                columns = [col[1] for col in cursor.fetchall()]
                
                # If table exists but timestamp is missing, add it (simple migration)
                if 'quest_status' in columns and 'timestamp' not in columns:
                     self.conn.execute("ALTER TABLE quest_status ADD COLUMN timestamp TEXT")
                     logging.info("Migrated quest_status table: Added timestamp column.")

                # Ensure table structure, including timestamp, for new or clean databases
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS quest_status (
                        profile TEXT,
                        quest_name TEXT,
                        status INTEGER,
                        timestamp TEXT,
                        PRIMARY KEY (profile, quest_name),
                        FOREIGN KEY(profile) REFERENCES profiles(name) ON DELETE CASCADE
                    )
                """)
                self.conn.execute("CREATE TABLE IF NOT EXISTS game_data (key TEXT PRIMARY KEY, json_data TEXT)")
                
                # PERFORMANCE: Add indexes for frequent lookups
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_status_profile ON quest_status(profile)")
                
                self.conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", 
                                ("db_version", str(AppConfig.SCHEMA_VERSION)))
        except sqlite3.Error as e:
            logging.critical(f"CRITICAL: Failed to initialize main database: {e}", exc_info=True)


    def _migrate_from_json(self):
        if not os.path.exists(self.json_user_file):
            return

        try:
            logging.info("Checking for legacy JSON data to merge...")
            with open(self.json_user_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # --- CRITICAL MIGRATION LOGIC ADDED ---
            profile_name = self.current_profile_name
            insert_data = []

            for quest_name, quest_info in data.items():
                status = quest_info.get("status")
                timestamp = quest_info.get("timestamp")
                
                # Only migrate statuses 1 and 2 (as 0 is represented by absence in the new DB model)
                if status == QuestStatus.IN_PROGRESS or status == QuestStatus.COMPLETED:
                     insert_data.append((profile_name, quest_name, status, timestamp))
            
            if insert_data:
                with self.conn:
                    self.conn.executemany("""
                        INSERT OR IGNORE INTO quest_status (profile, quest_name, status, timestamp) 
                        VALUES (?, ?, ?, ?)
                    """, insert_data)
                logging.info(f"Successfully migrated {len(insert_data)} quest entries from legacy JSON.")
            # -------------------------------------

            # MODIFIED: Stop deleting the file as requested
            logging.warning("Legacy JSON file found. Data merged, but file WILL NOT be removed as requested.")
            # os.remove(self.json_user_file) 
            
        except Exception as e:
            logging.error(f"Migration failed: {e}", exc_info=True)

    def _ensure_all_quests_tracked(self):
        """Checks the current profile's status data against the full quest_db 
        and logs any newly found quests. Called once after initialization and profile switch."""
        
        current_status = self.get_current_quests() # Fetches tracked quests (status 1 or 2)
        all_quests = set()
        
        for quest_list in self.quest_db.values():
            for item in quest_list:
                if SECTION_MARKER not in item:
                    all_quests.add(item)
                    
        missing_quests = all_quests - set(current_status.keys())
        
        if missing_quests:
            logging.info(f"Detected {len(missing_quests)} new/untracked quests in current quest database.")
            
            
    def _get_setting(self, key, default):
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else default

    def _set_setting(self, key, value):
        with self.conn:
            self.conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))

    def _profile_exists(self, name):
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM profiles WHERE name = ?", (name,))
        return cursor.fetchone() is not None

    def _load_quest_db(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT json_data FROM game_data WHERE key = 'quest_db'")
        row = cursor.fetchone()
        return json.loads(row[0]) if row else {}

    def _save_quest_db(self, data):
        with self.conn:
            self.conn.execute("INSERT OR REPLACE INTO game_data (key, json_data) VALUES (?, ?)", 
                              ('quest_db', json.dumps(data)))

    def get_theme(self):
        val = self._get_setting("dark_mode", "False")
        return val == "True"

    def set_theme(self, is_dark):
        self._set_setting("dark_mode", str(is_dark))

    def get_profiles(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM profiles")
        return [row[0] for row in cursor.fetchall()]
        
    def create_profile(self, name):
        if not name or self._profile_exists(name):
            return False
        try:
            with self.conn:
                self.conn.execute("INSERT INTO profiles (name) VALUES (?)", (name,))
            self.switch_profile(name)
            return True
        except sqlite3.Error as e:
            logging.error(f"Failed to create profile '{name}': {e}")
            return False

    def delete_profile(self, name):
        profiles = self.get_profiles()
        if len(profiles) <= 1: return False
        try:
            with self.conn:
                self.conn.execute("DELETE FROM profiles WHERE name = ?", (name,))
            remaining = self.get_profiles()
            if remaining:
                self.switch_profile(remaining[0])
            return True
        except sqlite3.Error as e:
            logging.error(f"Failed to delete profile '{name}': {e}")
            return False
        
    def switch_profile(self, profile_name):
        if self._profile_exists(profile_name):
            self.current_profile_name = profile_name
            self._set_setting("current_profile", profile_name)
            self._ensure_all_quests_tracked() # Check for new quests on profile switch

    def get_current_quests(self):
        # UPDATED: Select status AND timestamp
        cursor = self.conn.cursor()
        cursor.execute("SELECT quest_name, status, timestamp FROM quest_status WHERE profile = ?", (self.current_profile_name,))
        rows = cursor.fetchall()
        # Returning a dict: {quest_name: {"status": status_int, "timestamp": timestamp_text}}
        return {row[0]: {"status": row[1], "timestamp": row[2]} for row in rows}

    def get_status_data(self, quest):
        # UPDATED: Select status AND timestamp
        cursor = self.conn.cursor()
        cursor.execute("SELECT status, timestamp FROM quest_status WHERE profile = ? AND quest_name = ?", 
                       (self.current_profile_name, quest))
        row = cursor.fetchone()
        # Returning dict {"status": row[0], "timestamp": row[1]} if row else None
        return {"status": row[0], "timestamp": row[1]} if row else None

    def get_cached_content(self, url):
        return self.cache.get(url)
    
    def set_status(self, quest, status):
        try:
            with self.conn:
                if status == QuestStatus.COMPLETED:
                    # Store current time when completed
                    current_time = datetime.datetime.now().strftime(AppConfig.DATE_FORMAT)
                    self.conn.execute("""
                        INSERT OR REPLACE INTO quest_status (profile, quest_name, status, timestamp) 
                        VALUES (?, ?, ?, ?)
                    """, (self.current_profile_name, quest, status, current_time))
                elif status == QuestStatus.IN_PROGRESS:
                     # Store as in-progress, clear timestamp
                     self.conn.execute("""
                        INSERT OR REPLACE INTO quest_status (profile, quest_name, status, timestamp) 
                        VALUES (?, ?, ?, NULL)
                    """, (self.current_profile_name, quest, status))
                else:
                    # Status is NOT_STARTED (0) - DELETE the entry
                    self.conn.execute("DELETE FROM quest_status WHERE profile = ? AND quest_name = ?", 
                                      (self.current_profile_name, quest))
        except sqlite3.Error as e:
            logging.error(f"Failed to set status for '{quest}' to {status}: {e}")

    def reset_campaign(self, campaign):
        if campaign in self.quest_db:
            quests_to_reset = [q for q in self.quest_db[campaign] if SECTION_MARKER not in q]
            try:
                with self.conn:
                    for q in quests_to_reset:
                         self.conn.execute("DELETE FROM quest_status WHERE profile = ? AND quest_name = ?", 
                                          (self.current_profile_name, q))
            except sqlite3.Error as e:
                logging.error(f"Failed to reset campaign '{campaign}': {e}")
    
    def update_quest_db(self, new_db):
        """Updates the master quest list and calls for status integrity check."""
        self.quest_db = new_db
        self._save_quest_db(new_db)
        # We call this mainly to log the presence of new quests.
        self._ensure_all_quests_tracked()