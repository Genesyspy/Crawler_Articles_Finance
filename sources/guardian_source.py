"""
The Guardian Open Platform API — free, no paid key required.
Covers business/finance/economics going back to the 1990s.
Articles are permanently accessible (no Wayback needed).

Free API key: https://open-platform.theguardian.com/access/
Use "test" as api-key for limited access without registration.
"""

import time
import requests
from typing import List

from .base import BaseSource, Article

GUARDIAN_API = "https://content.guardianapis.com/search"

QUERY = (
    '"federal reserve" OR "wall street" OR "S&P 500" OR "dow jones" OR nasdaq '
    'OR "US economy" OR "american economy" OR "US inflation" OR "US jobs" '
    'OR "US GDP" OR "US treasury" OR "US interest rate" OR "US stock" '
    'OR "US trade" OR "US recession" OR "white house economy" OR "congress economy"'
)


class GuardianSource(BaseSource):
    @property
    def name(self) -> str:
        return "guardian"

    def fetch(self, date: str) -> List[Article]:
        api_key = self.api_keys.get("guardian", "test")
        params = {
            "q":         QUERY,
            "section":   "business",
            "from-date": date,
            "to-date":   date,
            "page-size": 50,
            "order-by":  "relevance",
            "api-key":   api_key,
        }

        try:
            resp = requests.get(GUARDIAN_API, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[Guardian] Error fetching {date}: {e}")
            return []

        time.sleep(1)

        articles = []
        for item in data.get("response", {}).get("results", []):
            url = item.get("webUrl", "")
            articles.append(Article(
                title=item.get("webTitle", "").strip(),
                description="",
                url=url,
                source_name="The Guardian",
                published_at=item.get("webPublicationDate", date),
                wayback_url=url,  # Guardian URLs are permanently accessible
            ))

        return articles
