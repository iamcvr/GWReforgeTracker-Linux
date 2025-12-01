# config.py
import os

class AppConfig:
    APP_TITLE = "Guild Wars Reforge Quest Tracker" 
    APP_VERSION = "1.0.1" # Bumped for UI update
    FONT_FAMILY = "Segoe UI" 
    
    # Files
    DB_FILE = "gw1_data.db"
    CACHE_FILE = "gw1_cache.db"
    USER_FILE = "gw1_user.json" 
    DEFAULT_PROFILE_NAME = "Default"
    SCHEMA_VERSION = 1 
    
    # Settings
    WINDOW_WIDTH = 1400
    WINDOW_HEIGHT = 900
    GAME_PROCESS_NAMES = ["Gw.exe", "Gw.tmp"]
    AUTO_CLOSE_CHECK_INTERVAL_MS = 10000
    
    # Networking
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    REQUEST_TIMEOUT = 15
    REQUEST_DELAY = 1.0 
    MAX_RETRIES = 3
    BACKOFF_FACTOR = 1 
    CACHE_EXPIRY_HOURS = 24
    MAX_CACHE_SIZE_MB = 50
    MAX_CACHE_ENTRIES = 100
    
    # Validation & UI
    MAX_QUEST_NAME_LEN = 128
    MAX_LOCATION_LEN = 64
    LAZY_LOAD_BATCH_SIZE = 20
    LAZY_LOAD_INTERVAL_MS = 20 
    SEARCH_DEBOUNCE_MS = 300
    DATE_FORMAT = "%m / %d / %Y %I:%M %p"

class ThemeColors:
    GOLD = "#D4AF37"
    GREEN = "#4CAF50"
    RED = "#FF6B6B"
    WHITE = "#ECECEC"
    GREY = "#A0A0A5"
    DARK_BG_GRADIENT_START = "#141414"
    DARK_BG_GRADIENT_END = "#1E1E24"
    PANEL_BG = "rgba(35, 35, 40, 0.9)"
    HOVER_WHITE = "rgba(255, 255, 255, 0.1)"

class QuestStatus:
    NOT_STARTED = 0
    IN_PROGRESS = 1
    # Reverted to standard completed status
    COMPLETED = 2
    
    # Removed: NORMAL_COMPLETED, HARD_COMPLETED

class FilterMode:
    ALL = "All Quests"
    NOT_STARTED = "Not Started"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed" # This will filter for COMPLETED (2)

SECTION_MARKER = "---" 

CAMPAIGN_URLS = {
    "Prophecies": "https://wiki.guildwars.com/wiki/List_of_Prophecies_quests",
    "Factions": "https://wiki.guildwars.com/wiki/List_of_Factions_quests",
    "Nightfall": "https://wiki.guildwars.com/wiki/List_of_Nightfall_quests",
    "Eye of the North": "https://wiki.guildwars.com/wiki/List_of_Eye_of_the_North_quests"
}

CAMPAIGN_ORDER = ["Prophecies", "Factions", "Nightfall", "Eye of the North", "Beyond", "LDoA"]

INITIAL_QUEST_DB = {
    "Prophecies": [f"{SECTION_MARKER} PRIMARY MISSIONS {SECTION_MARKER}", "Ascalon (Pre-Searing) Tutorials", "The Great Northern Wall"],
    "Factions": [f"{SECTION_MARKER} PRIMARY MISSIONS {SECTION_MARKER}", "Minister Cho's Estate"],
    "Nightfall": [f"{SECTION_MARKER} PRIMARY MISSIONS {SECTION_MARKER}", "Chahbek Village"],
    "Eye of the North": [f"{SECTION_MARKER} PRIMARY MISSIONS {SECTION_MARKER}", "Boreal Station"],
    "Beyond": [f"{SECTION_MARKER} WAR IN KRYTA {SECTION_MARKER}", "The War in Kryta"],
    "LDoA": [
        f"{SECTION_MARKER} LEVELING MILESTONES {SECTION_MARKER}",
        "Reach Level 10 (Charr at the Gate)",
        "Reach Level 13 (Farmer Hamnet Farm)",
        "Reach Level 16 (Vanguard Quest Scaling)",
        "Reach Level 20 (Legendary Defender)",
        f"{SECTION_MARKER} DAILY VANGUARD QUESTS {SECTION_MARKER}",
        "Vanguard Rescue: Farmer Hamnet",
        "Vanguard Annihilation: Undead",
        "Vanguard Rescue: Footman Tate",
        "The Blazefiend",
        "Vanguard Annihilation: Charr"
    ]
}