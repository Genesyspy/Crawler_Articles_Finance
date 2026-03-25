"""
Wayback Machine (archive.org) — free, no API key required.
Uses the CDX API to find archived snapshots of major financial news sites,
then scrapes the headlines from those archived pages.
Best for historical data with no API cost.
"""

import time
import requests
from bs4 import BeautifulSoup
from typing import List, Optional

from .base import BaseSource, Article

CDX_API      = "https://web.archive.org/cdx/search/cdx"
WAYBACK_BASE = "https://web.archive.org/web"

# Financial news sites to target
FINANCIAL_SITES = [
    ("reuters.com/business", "Reuters"),
    ("cnbc.com/finance",     "CNBC"),
    ("marketwatch.com",      "MarketWatch"),
    ("bloomberg.com/markets","Bloomberg"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; FinancialNewsArchiveCrawler/1.0)"
}


class WaybackSource(BaseSource):
    @property
    def name(self) -> str:
        return "wayback"

    def _get_snapshot_url(self, site: str, date: str) -> Optional[str]:
        """Find the closest archived snapshot of a site for the given date."""
        date_compact = date.replace("-", "")
        params = {
            "url":    site,
            "output": "json",
            "from":   date_compact + "000000",
            "to":     date_compact + "235959",
            "limit":  1,
            "fl":     "timestamp,original",
        }
        try:
            resp = requests.get(CDX_API, params=params, timeout=15, headers=HEADERS)
            data = resp.json()
            # First row is the header ["timestamp", "original"]
            if len(data) > 1:
                timestamp, original = data[1]
                return f"{WAYBACK_BASE}/{timestamp}/{original}"
        except Exception as e:
            print(f"[Wayback] CDX lookup failed for {site}: {e}")
        return None

    def _parse_headlines(
        self, snapshot_url: str, source_name: str, date: str
    ) -> List[Article]:
        """Fetch the archived page and extract headline articles."""
        articles = []
        try:
            resp = requests.get(snapshot_url, timeout=20, headers=HEADERS)
            soup = BeautifulSoup(resp.text, "lxml")

            seen = set()
            # Cast a wide net over common headline tags
            for tag in soup.find_all(["h1", "h2", "h3"]):
                title = tag.get_text(strip=True)
                if not title or len(title) < 25 or title in seen:
                    continue
                seen.add(title)

                # Try to find the associated link
                link = tag.find("a") or tag.find_parent("a")
                url  = link.get("href", snapshot_url) if link else snapshot_url

                # Skip homepage URLs (no specific article path)
                bare = url.split("web.archive.org/web/")[-1]  # strip wayback prefix
                bare = bare.split("/", 1)[-1] if "/" in bare else ""  # strip domain
                if not bare or bare in ("/", ""):
                    continue

                articles.append(Article(
                    title=title,
                    description="",
                    url=url,
                    source_name=source_name,
                    published_at=date,
                ))

                if len(articles) >= 10:
                    break

        except Exception as e:
            print(f"[Wayback] Failed to parse {snapshot_url}: {e}")

        return articles

    def fetch(self, date: str) -> List[Article]:
        all_articles: List[Article] = []

        for site, label in FINANCIAL_SITES:
            print(f"[Wayback] Looking up {label} ({site}) for {date}...")
            snapshot_url = self._get_snapshot_url(site, date)

            if snapshot_url:
                print(f"[Wayback] Found snapshot: {snapshot_url}")
                articles = self._parse_headlines(snapshot_url, label, date)
                all_articles.extend(articles)
            else:
                print(f"[Wayback] No snapshot found for {site} on {date}")

            time.sleep(0.5)  # be respectful to archive.org

        return all_articles
