"""
New York Times Article Search API — free API key required.
Get a free key at: https://developer.nytimes.com/

Covers US financial/business news with historical data since 1851.
Returns abstracts (descriptions) for better keyword scoring.
Articles are permanently accessible — no Wayback needed.
"""

import time
import requests
from typing import List

from .base import BaseSource, Article

NYT_API = "https://api.nytimes.com/svc/search/v2/articlesearch.json"

QUERY = '"federal reserve" OR "stock market" OR "wall street" OR inflation OR recession'


class NYTimesSource(BaseSource):
    @property
    def name(self) -> str:
        return "nytimes"

    def fetch(self, date: str) -> List[Article]:
        api_key = self.api_keys.get("nytimes", "")
        if not api_key:
            print("[NYTimes] API key not configured in config.json")
            return []

        date_compact = date.replace("-", "")
        params = {
            "q":          QUERY,
            "begin_date": date_compact,
            "end_date":   date_compact,
            "sort":       "relevance",
            "api-key":    api_key,
        }

        for attempt in range(1, 4):
            try:
                resp = requests.get(NYT_API, params=params, timeout=15)
                if resp.status_code == 429:
                    wait = 15 * attempt
                    print(f"[NYTimes] Rate limited, waiting {wait}s... (attempt {attempt}/3)")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                break
            except Exception as e:
                print(f"[NYTimes] Error fetching {date}: {e}")
                return []
        else:
            return []

        time.sleep(12)  # NYT free tier: 5 requests/minute = 1 per 12s

        docs = (data.get("response") or {}).get("docs") or []
        print(f"[NYTimes] {len(docs)} articles found for {date}")
        if not docs:
            print(f"[NYTimes] API response: {data.get('fault') or data.get('message') or data.get('status') or 'empty'}")

        articles = []
        for item in docs:
            url = item.get("web_url", "")
            articles.append(Article(
                title=item.get("headline", {}).get("main", "").strip(),
                description=item.get("abstract", ""),
                url=url,
                source_name="New York Times",
                published_at=item.get("pub_date", date),
                wayback_url=url,  # NYT URLs are permanently accessible
            ))

        return articles
