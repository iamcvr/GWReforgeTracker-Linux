# scraper.py
import requests
import logging
import copy
import time
import unicodedata
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from PySide6.QtCore import QThread, Signal
from config import AppConfig, INITIAL_QUEST_DB, CAMPAIGN_URLS, SECTION_MARKER
from database import DiskCache 

class WikiScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': AppConfig.USER_AGENT})
        retry_strategy = Retry(total=AppConfig.MAX_RETRIES, backoff_factor=AppConfig.BACKOFF_FACTOR, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        
        self.cache = DiskCache(AppConfig.CACHE_FILE, AppConfig.CACHE_EXPIRY_HOURS, AppConfig.MAX_CACHE_SIZE_MB, AppConfig.MAX_CACHE_ENTRIES)
        
        # UPDATED: Added "logs", "logs:", and other system terms to ignore list
        self.ignore_exact = {
            "quest", "name", "location", "type", "given by", "level", "reward", "experience", "gold",
            "core", "logic", "mechanics", "user interface", "controls", "game mechanics", "terminology",
            "professions", "attributes", "skills", "builds", "edit", 
            "logs", "logs:", "history", "recent changes", "random page", "help", "donate", 
            "what links here", "related changes", "special pages", "printable version", "permanent link"
        }

    def _sanitize_text(self, text, max_len):
        if not text: return None
        text = unicodedata.normalize('NFKC', text)
        text = "".join(ch for ch in text if ch.isprintable())
        text = text.strip()
        if len(text) > max_len: return text[:max_len] + "..."
        return text

    def run_sync(self, existing_db, progress_callback=None, interrupt_check=None):
        new_db = copy.deepcopy(INITIAL_QUEST_DB)
        total_campaigns = len(CAMPAIGN_URLS)
        current_count = 0
        error_log = []
        
        VALID_TABLE_HEADERS = {"quest", "location", "given by", "type", "level"}
        
        for campaign, url in CAMPAIGN_URLS.items():
            if interrupt_check and interrupt_check(): 
                self.cache.close()
                return None, None
            
            if current_count > 0: time.sleep(AppConfig.REQUEST_DELAY)
            
            if progress_callback:
                progress_callback(int((current_count / total_campaigns) * 100), f"Scanning {campaign}...")

            fresh_campaign_list = copy.deepcopy(INITIAL_QUEST_DB.get(campaign, []))
            side_quests_map = {} 
            seen_quests = set()
            
            try:
                content = self.cache.get(url)
                if not content:
                    response = self.session.get(url, timeout=AppConfig.REQUEST_TIMEOUT)
                    if response.status_code == 200:
                        content = response.text
                        self.cache.set(url, content) 
                    else: raise Exception(f"HTTP {response.status_code}")
                
                soup = BeautifulSoup(content, 'html.parser')
                content_root = soup.find('div', {'id': 'mw-content-text'})
                if not content_root: content_root = soup
                
                tables = content_root.find_all('table')
                
                for table in tables:
                    if interrupt_check and interrupt_check(): 
                        self.cache.close(); return None, None
                        
                    # Filter: Ignore navigation boxes and catlinks
                    classes = table.get('class', [])
                    if 'navbox' in classes or 'catlinks' in classes or 'mw-footer' in classes:
                        continue

                    headers = [th.get_text().strip() for th in table.find_all('th')]
                    headers_lower = [h.lower() for h in headers]
                    
                    if not any(valid in h for h in headers_lower for valid in VALID_TABLE_HEADERS):
                        continue

                    location_column_index = -1
                    for i, h in enumerate(headers_lower):
                        if "location" in h or "given at" in h:
                            location_column_index = i; break
                    
                    rows = table.find_all('tr')
                    for row in rows:
                        if interrupt_check and interrupt_check(): 
                            self.cache.close(); return None, None
                        if row.find('th'): continue 
                        
                        cols = row.find_all('td')
                        if not cols: continue
                        
                        anchor = cols[0].find('a')
                        if not anchor: continue
                        
                        quest_name = self._sanitize_text(anchor.get_text(), AppConfig.MAX_QUEST_NAME_LEN)
                        
                        # --- UPDATED FILTERING LOGIC ---
                        if not quest_name or len(quest_name) < 2: continue
                        
                        # Normalize for checking (remove trailing colons like "Logs:")
                        check_name = quest_name.lower().strip().rstrip(':')
                        
                        if check_name in self.ignore_exact: continue
                        if "Category:" in quest_name or "Help:" in quest_name: continue

                        location = "Uncategorized"
                        if location_column_index != -1 and len(cols) > location_column_index:
                            raw = self._sanitize_text(cols[location_column_index].get_text(), AppConfig.MAX_LOCATION_LEN)
                            if raw: location = raw
                        
                        if location not in side_quests_map: side_quests_map[location] = []
                        if quest_name not in side_quests_map[location] and quest_name not in seen_quests:
                            side_quests_map[location].append(quest_name)
                            seen_quests.add(quest_name)
                
                primary_missions_set = set(item for item in fresh_campaign_list if SECTION_MARKER not in item)
                final_side_quests = []
                sorted_locations = sorted(side_quests_map.keys())
                
                if "Uncategorized" in sorted_locations:
                    sorted_locations.remove("Uncategorized")
                    sorted_locations.append("Uncategorized")
                    
                for loc in sorted_locations:
                    unique_quests = [q for q in sorted(side_quests_map[loc]) if q not in primary_missions_set]
                    if unique_quests:
                        final_side_quests.append(f"{SECTION_MARKER} {loc.upper()} {SECTION_MARKER}")
                        final_side_quests.extend(unique_quests)

                if final_side_quests: fresh_campaign_list.extend(final_side_quests)
                new_db[campaign] = fresh_campaign_list

            except Exception as e:
                logging.error(f"Failed to scrape {campaign}: {e}")
                error_log.append(f"{campaign}: {str(e)}")
                if campaign in existing_db: new_db[campaign] = existing_db[campaign]
            
            current_count += 1
        
        self.cache.close()
        return new_db, error_log

class DatabaseSyncer(QThread):
    progress_updated = Signal(int, str)
    sync_finished = Signal(dict, list)

    def __init__(self):
        super().__init__()
        self.current_db = {}

    def set_current_db(self, db):
        self.current_db = db

    def run(self):
        scraper = WikiScraper()
        try:
            result, errors = scraper.run_sync(
                self.current_db, 
                lambda p, m: self.progress_updated.emit(p, m), 
                lambda: self.isInterruptionRequested()
            )
            if result is not None: 
                self.sync_finished.emit(result, errors)
                
        except Exception as e:
            logging.critical(f"Critical error in DatabaseSyncer thread: {e}", exc_info=True)
            self.sync_finished.emit({}, [f"Critical Sync Error: {str(e)}"])