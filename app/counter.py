# counter.py

from typing import Dict, Set, List, Tuple
from pydantic import BaseModel
import sqlite3
import os
import re
from datetime import datetime

class VoteConfig(BaseModel):
    mode: str  # "normal" or "series"
    vote_mode: bool

class VoteCounter:
    def __init__(self, db_path: str = "shows.db"):
        self.config = self.load_config()
        self.user_votes: Dict[str, Set[str]] = {}  # user -> voted IDs
        self.votes: Dict[str, int] = {}  # vote key -> count
        self.db_path = os.path.join("assets", db_path)
        self.valid_titles = self._load_valid_titles()
        self.started_at: datetime | None = None

    def _load_valid_titles(self) -> Set[str]:
        path = os.path.abspath(self.db_path)
        if not os.path.exists(path):
            print(f"Database not found at {path}")
            return set()

        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        cursor.execute("SELECT title_romaji, title_english, synonyms FROM anime")

        titles = set()
        for row in cursor.fetchall():
            for value in row[:2]:
                if value:
                    titles.add(value.strip().lower())
            if row[2]:
                titles.update(s.strip().lower() for s in row[2].split(",") if s.strip())

        conn.close()
        return titles

    def start_counting(self):
        self.user_votes.clear()
        self.votes.clear()
        self.started_at = datetime.utcnow()

    def end_counting(self) -> List[Tuple[str, int]]:
        return self._get_sorted_votes()

    def set_config(self):
        with open(CONFIG_FILE, 'w') as f:
            f.write(self.config.json(indent=2))

    def get_config(self) -> VoteConfig:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return VoteConfig.parse_raw(f.read())
        return VoteConfig(mode="normal", vote_mode=False)

    def get_state(self) -> Tuple[List[Tuple[str, int]], datetime | None]:
        return self._get_sorted_votes(), self.started_at

    def notify_update(self):
        # Placeholder for event firing or callback mechanism
        pass

    def vote(self, user: str, message: str):
        vote_key = message.strip().lower()
        if self.config.mode == "series" and vote_key not in self.valid_titles:
            return

        if self.config.vote_mode:
            if user not in self.user_votes:
                self.user_votes[user] = set()
            if vote_key in self.user_votes[user]:
                return
            self.user_votes[user].add(vote_key)

        self.votes[vote_key] = self.votes.get(vote_key, 0) + 1
        self.notify_update()


