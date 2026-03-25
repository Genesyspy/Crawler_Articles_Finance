"""
Yahoo Finance RSS via Wayback Machine — free, no API key required.
Yahoo Finance RSS was archived frequently on archive.org.
Very US-focused financial news.
"""

import time
import requests
import xml.etree.ElementTree as ET
from typing import List, Optional

from .base import BaseSource, Article

CDX_API      = "https://web.archive.org/cdx/search/cdx"
WAYBACK_BASE = "https://web.archive.org/web"
HEADERS      = {"User-Agent": "Mozilla/5.0 (compatible; FinancialNewsArchiveCrawler/1.0)"}

RSS_FEEDS = [
    "finance.yahoo.com/rss/topfinstories",
    "finance.yahoo.com/rss/headline?s=%5EGSPC",   # S&P 500
    "finance.yahoo.com/rss/headline?s=%5EDJI",    # Dow Jones
]


class YahooFinSource(BaseSource):
    @property
    def name(self) -> str:
        return "yahoofin"

    def _get_rss_snapshot(self, feed_url: str, date: str) -> Optional[str]:
        """Find an archived snapshot of the RSS feed on the exact given date."""
        date_compact = date.replace("-", "")
        params = {
            "url":    feed_url,
            "output": "json",
            "from":   date_compact + "000000",
            "to":     date_compact + "235959",
            "limit":  1,
            "fl":     "timestamp,original",
        }
        try:
            resp = requests.get(CDX_API, params=params, timeout=10, headers=HEADERS)
            data = resp.json()
            if len(data) >= 2:
                timestamp, original = data[1]
                return f"{WAYBACK_BASE}/{timestamp}/{original}"
        except Exception:
            pass
        return None

    def _parse_rss(self, snapshot_url: str, date: str) -> List[Article]:
        """Fetch and parse the archived RSS feed."""
        articles = []
        try:
            resp = requests.get(snapshot_url, timeout=20, headers=HEADERS)
            root = ET.fromstring(resp.content)

            for item in root.iter("item"):
                title = item.findtext("title", "").strip()
                url   = item.findtext("link", "").strip()
                desc  = item.findtext("description", "").strip()

                if not title or not url or len(title) < 15:
                    continue

                # Strip Wayback rewrite prefix if present
                if "/web/" in url and "archive.org" in url:
                    url = url.split("/web/")[1]
                    url = url.split("/", 1)[-1] if "/" in url else url
                    url = "http://" + url if not url.startswith("http") else url

                articles.append(Article(
                    title=title,
                    description=desc[:300] if desc else "",
                    url=url,
                    source_name="Yahoo Finance",
                    published_at=date,
                ))

                if len(articles) >= 20:
                    break

        except Exception as e:
            print(f"[YahooFin] Failed to parse RSS {snapshot_url}: {e}")

        return articles

    def fetch(self, date: str) -> List[Article]:
        all_articles: List[Article] = []
        seen_titles: set = set()

        for feed_url in RSS_FEEDS:
            print(f"[YahooFin] Looking up RSS: {feed_url} for {date}...")
            snapshot_url = self._get_rss_snapshot(feed_url, date)

            if snapshot_url:
                print(f"[YahooFin] Found snapshot: {snapshot_url}")
                articles = self._parse_rss(snapshot_url, date)
                for a in articles:
                    if a.title not in seen_titles:
                        seen_titles.add(a.title)
                        all_articles.append(a)
            else:
                print(f"[YahooFin] No snapshot for {feed_url} on {date}")

            time.sleep(0.5)

        print(f"[YahooFin] {len(all_articles)} unique articles found for {date}")
        return all_articles
