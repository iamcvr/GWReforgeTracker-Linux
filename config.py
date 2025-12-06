# config.py
import os

class AppConfig:
    APP_TITLE = "Guild Wars Reforge Quest Tracker" 
    APP_VERSION = "1.0.2" 
    FONT_FAMILY = "Segoe UI" 
    
    GITHUB_REPO = "Mr-Akito/GWReforgeTracker"
    GITHUB_API_LATEST = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    
    DB_FILE = "gw1_data.db"
    CACHE_FILE = "gw1_cache.db"
    USER_FILE = "gw1_user.json" 
    DEFAULT_PROFILE_NAME = "Default"
    
    SCHEMA_VERSION = 2
    
    WINDOW_WIDTH = 1400
    WINDOW_HEIGHT = 900
    GAME_PROCESS_NAMES = ["Gw.exe", "Gw.tmp"]
    AUTO_CLOSE_CHECK_INTERVAL_MS = 10000
    
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    REQUEST_TIMEOUT = 15
    REQUEST_DELAY = 1.0 
    MAX_RETRIES = 3
    BACKOFF_FACTOR = 1 
    CACHE_EXPIRY_HOURS = 24
    MAX_CACHE_SIZE_MB = 50
    MAX_CACHE_ENTRIES = 100
    
    MAX_QUEST_NAME_LEN = 128
    MAX_LOCATION_LEN = 64
    MAX_PROFILE_NAME_LEN = 24
    LAZY_LOAD_BATCH_SIZE = 20
    LAZY_LOAD_INTERVAL_MS = 20 
    SEARCH_DEBOUNCE_MS = 300
    DATE_FORMAT = "%m / %d / %Y %I:%M %p"

    WIKI_OVERRIDES = {
        "Isle of the Dead": "Isle_of_the_Dead_(quest)",
        "The Great Escape": "The_Great_Escape_(Factions_quest)",
        "Augury Rock": "Augury_Rock_(mission)",
        "Dragon's Lair": "The_Dragon%27s_Lair_(mission)",
        "Adventure with an Ally": "Adventure_with_an_Ally",
        "The Healing Spring": "The_Healing_Spring",
        "The Hunter's Horn": "The_Hunter%27s_Horn",
    }

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
    COMPLETED = 2

class FilterMode:
    ALL = "All Quests"
    ACTIVE_ONLY = "Hide Completed"
    NOT_STARTED = "Not Started"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"

SECTION_MARKER = "---" 

CAMPAIGN_URLS = {
    "Prophecies": "https://wiki.guildwars.com/wiki/List_of_Prophecies_quests",
    "Factions": "https://wiki.guildwars.com/wiki/List_of_Factions_quests",
    "Nightfall": "https://wiki.guildwars.com/wiki/List_of_Nightfall_quests",
    "Eye of the North": "https://wiki.guildwars.com/wiki/List_of_Eye_of_the_North_quests"
}

CAMPAIGN_ORDER = [
    "Prophecies", 
    "Factions", 
    "Nightfall", 
    "Eye of the North", 
    "Beyond", 
    "Legendary Defender of Ascalon"
]

INITIAL_QUEST_DB = {
    "Prophecies": [
        f"{SECTION_MARKER} TUTORIAL - LAKESIDE COUNTY {SECTION_MARKER}",
        "Adventure with an Ally",
        "The Hunter's Horn",
        "Charr at the Gate",
        f"{SECTION_MARKER} TUTORIAL - ASCALON CITY {SECTION_MARKER}",
        "A Test of Marksmanship",
        "War Preparations",
        f"{SECTION_MARKER} PRIMARY MISSIONS {SECTION_MARKER}", 
        "The Great Northern Wall"
    ],
    "Factions": [f"{SECTION_MARKER} PRIMARY MISSIONS {SECTION_MARKER}", "Minister Cho's Estate"],
    "Nightfall": [f"{SECTION_MARKER} PRIMARY MISSIONS {SECTION_MARKER}", "Chahbek Village"],
    "Eye of the North": [f"{SECTION_MARKER} PRIMARY MISSIONS {SECTION_MARKER}", "Boreal Station"],
    "Beyond": [f"{SECTION_MARKER} WAR IN KRYTA {SECTION_MARKER}", "The War in Kryta"],
    "Legendary Defender of Ascalon": [
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