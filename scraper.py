"""
scraper.py (Linux-friendly, no PySide6)

This is a pure-Python port of the original scraper:
- Uses requests + BeautifulSoup
- Uses DiskCache to avoid hammering the wiki
- Uses CAMPAIGN_URLS from config to find the right pages
- Filters out non-quest rows and wiki chrome
"""

import copy
import logging
import time
import unicodedata

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import AppConfig, INITIAL_QUEST_DB, CAMPAIGN_URLS, SECTION_MARKER
from database import DiskCache


class WikiScraper:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": AppConfig.USER_AGENT})

        retry_strategy = Retry(
            total=AppConfig.MAX_RETRIES,
            backoff_factor=AppConfig.BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        self.cache = DiskCache(
            AppConfig.CACHE_FILE,
            AppConfig.CACHE_EXPIRY_HOURS,
            AppConfig.MAX_CACHE_SIZE_MB,
            AppConfig.MAX_CACHE_ENTRIES,
        )

        # Extra words/labels to ignore when scraping
        self.ignore_exact = {
            "quest",
            "name",
            "location",
            "type",
            "given by",
            "level",
            "reward",
            "experience",
            "gold",
            "core",
            "logic",
            "mechanics",
            "user interface",
            "controls",
            "game mechanics",
            "terminology",
            "professions",
            "attributes",
            "skills",
            "builds",
            "edit",
            "logs",
            "logs:",
            "history",
            "recent changes",
            "random page",
            "help",
            "donate",
            "what links here",
            "related changes",
            "special pages",
            "printable version",
            "permanent link",
        }

    def _sanitize_text(self, text: str | None, max_len: int) -> str | None:
        if not text:
            return None

        # Normalise unicode and strip non-printables
        text = unicodedata.normalize("NFKC", text)
        text = "".join(ch for ch in text if ch.isprintable())
        text = text.strip()

        if len(text) > max_len:
            return text[:max_len] + "..."

        return text

    def run_sync(
        self,
        existing_db: dict,
        progress_callback=None,
        interrupt_check=None,
    ):
        """
        Scrape all campaigns defined in CAMPAIGN_URLS and return:

            (new_db, error_log)

        - new_db is shaped like INITIAL_QUEST_DB
        - error_log is a list of human-readable error strings
        """
        new_db = copy.deepcopy(INITIAL_QUEST_DB)
        total_campaigns = len(CAMPAIGN_URLS)
        current_count = 0
        error_log: list[str] = []

        VALID_TABLE_HEADERS = {"quest", "location", "given by", "type", "level"}

        for campaign, url in CAMPAIGN_URLS.items():
            if interrupt_check and interrupt_check():
                self.cache.close()
                return None, None

            if current_count > 0:
                time.sleep(AppConfig.REQUEST_DELAY)

            if progress_callback:
                progress_callback(
                    int((current_count / total_campaigns) * 100),
                    f"Scanning {campaign}...",
                )

            # Start from the built-in quest list for this campaign
            fresh_campaign_list = copy.deepcopy(
                INITIAL_QUEST_DB.get(campaign, [])
            )
            side_quests_map: dict[str, list[str]] = {}
            seen_quests: set[str] = set()

            try:
                # Cached HTML if available
                content = self.cache.get(url)
                if not content:
                    response = self.session.get(
                        url, timeout=AppConfig.REQUEST_TIMEOUT
                    )
                    if response.status_code == 200:
                        content = response.text
                        self.cache.set(url, content)
                    else:
                        raise Exception(f"HTTP {response.status_code}")

                soup = BeautifulSoup(content, "html.parser")

                # Main wiki text area
                content_root = soup.find("div", {"id": "mw-content-text"})
                if not content_root:
                    content_root = soup

                tables = content_root.find_all("table")

                for table in tables:
                    if interrupt_check and interrupt_check():
                        self.cache.close()
                        return None, None

                    # Ignore navboxes / footer / category junk
                    classes = table.get("class", [])
                    if (
                        "navbox" in classes
                        or "catlinks" in classes
                        or "mw-footer" in classes
                    ):
                        continue

                    headers = [th.get_text().strip() for th in table.find_all("th")]
                    headers_lower = [h.lower() for h in headers]

                    # Ensure this table looks like a quest list
                    if not any(
                        valid in h for h in headers_lower for valid in VALID_TABLE_HEADERS
                    ):
                        continue

                    # Try to find a "location" column index if present
                    location_column_index = -1
                    for i, h in enumerate(headers_lower):
                        if "location" in h or "given at" in h:
                            location_column_index = i
                            break

                    rows = table.find_all("tr")
                    for row in rows:
                        if interrupt_check and interrupt_check():
                            self.cache.close()
                            return None, None

                        # Skip header rows
                        if row.find("th"):
                            continue

                        cols = row.find_all("td")
                        if not cols:
                            continue

                        anchor = cols[0].find("a")
                        if not anchor:
                            continue

                        quest_name = self._sanitize_text(
                            anchor.get_text(), AppConfig.MAX_QUEST_NAME_LEN
                        )

                        # Updated filtering from original scraper
                        if not quest_name or len(quest_name) < 2:
                            continue

                        # Strip trailing colon and compare against ignore list
                        check_name = quest_name.lower().strip().rstrip(":")
                        if check_name in self.ignore_exact:
                            continue

                        if "Category:" in quest_name or "Help:" in quest_name:
                            continue

                        # Location / grouping label
                        location = "Uncategorized"
                        if (
                            location_column_index != -1
                            and len(cols) > location_column_index
                        ):
                            raw = self._sanitize_text(
                                cols[location_column_index].get_text(),
                                AppConfig.MAX_LOCATION_LEN,
                            )
                            if raw:
                                location = raw

                        if location not in side_quests_map:
                            side_quests_map[location] = []

                        if (
                            quest_name not in side_quests_map[location]
                            and quest_name not in seen_quests
                        ):
                            side_quests_map[location].append(quest_name)
                            seen_quests.add(quest_name)

                # Don't duplicate campaign mainline missions
                primary_missions_set = set(
                    item
                    for item in fresh_campaign_list
                    if SECTION_MARKER not in item
                )

                final_side_quests: list[str] = []

                # Sort locations, keep "Uncategorized" at the end
                sorted_locations = sorted(side_quests_map.keys())
                if "Uncategorized" in sorted_locations:
                    sorted_locations.remove("Uncategorized")
                    sorted_locations.append("Uncategorized")

                for loc in sorted_locations:
                    unique_quests = [
                        q
                        for q in sorted(side_quests_map[loc])
                        if q not in primary_missions_set
                    ]
                    if not unique_quests:
                        continue

                    # Section header line
                    final_side_quests.append(
                        f"{SECTION_MARKER} {loc.upper()} {SECTION_MARKER}"
                    )
                    final_side_quests.extend(unique_quests)

                if final_side_quests:
                    fresh_campaign_list.extend(final_side_quests)

                new_db[campaign] = fresh_campaign_list

            except Exception as e:
                logging.error(f"Failed to scrape {campaign}: {e}")
                error_log.append(f"{campaign}: {str(e)}")

                # Fall back to existing DB for this campaign
                if campaign in existing_db:
                    new_db[campaign] = existing_db[campaign]

            current_count += 1

        self.cache.close()
        return new_db, error_log
