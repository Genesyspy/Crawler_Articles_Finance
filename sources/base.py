from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List


@dataclass
class Article:
    title: str
    description: str
    url: str
    source_name: str
    published_at: str
    raw_position: int = 0
    captures: int = 0       # Wayback Machine archive capture count (proxy for importance)
    wayback_url: str = ""   # Direct link to a working archived snapshot on archive.org
    score: float = 0.0
    score_breakdown: dict = field(default_factory=dict)


class BaseSource(ABC):
    def __init__(self, api_keys: dict):
        self.api_keys = api_keys

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def fetch(self, date: str) -> List[Article]:
        """Fetch articles for a given date in YYYY-MM-DD format."""
        pass
