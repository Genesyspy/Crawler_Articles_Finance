"""
GDELT 2.0 Doc API — free, no API key required.
Best option for historical data going back years.
"""

import time
import requests
from typing import List

from .base import BaseSource, Article

GDELT_API = "https://api.gdeltproject.org/api/v2/doc/doc"

QUERY = (
    '("stock market" OR "federal reserve" OR "interest rate" OR inflation '
    'OR recession OR "wall street" OR earnings OR "trade war" OR "bond yield" '
    'OR "debt ceiling") sourcelang:english'
)


class GDELTSource(BaseSource):
    @property
    def name(self) -> str:
        return "gdelt"

    def fetch(self, date: str) -> List[Article]:
        start = date.replace("-", "") + "000000"
        end   = date.replace("-", "") + "235959"

        params = {
            "query":         QUERY,
            "mode":          "artlist",
            "maxrecords":    50,
            "format":        "json",
            "startdatetime": start,
            "enddatetime":   end,
        }

        for attempt in range(1, 4):
            try:
                resp = requests.get(GDELT_API, params=params, timeout=30)
                if resp.status_code == 429:
                    wait = 15 * attempt
                    print(f"[GDELT] Rate limited on {date}, waiting {wait}s... (attempt {attempt}/3)")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                break
            except Exception as e:
                print(f"[GDELT] Error fetching {date} (attempt {attempt}/3): {e}")
                if attempt < 3:
                    time.sleep(10)
        else:
            print(f"[GDELT] Failed to fetch {date} after 3 attempts.")
            return []

        time.sleep(3)

        articles = []
        for item in data.get("articles", []):
            articles.append(Article(
                title=item.get("title", "").strip(),
                description="",  # GDELT artlist does not return body/description
                url=item.get("url", ""),
                source_name=item.get("domain", ""),
                published_at=item.get("seendate", date),
            ))

        return articles
