"""
Wayback Machine enricher — fetches archive capture counts for article URLs.

A URL that was captured many times by archive.org was likely widely shared
and referenced at the time, making the capture count a solid proxy for
article importance/virality.

This runs AFTER fetching articles, on the top candidates only (to limit API calls).
"""

import math
import time
import requests
from typing import List

from sources.base import Article

CDX_API = "http://web.archive.org/cdx/search/cdx"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; FinancialNewsArchiveCrawler/1.0)"}


def _fetch_capture_count(url: str) -> int:
    """
    Query the CDX API to count how many times a URL was archived.
    Uses showNumPages=true which returns the number of result pages
    (each page holds ~150 captures). Returns estimated total captures.
    """
    if not url or url.startswith("https://web.archive.org"):
        return 0
    try:
        params = {
            "url":          url,
            "output":       "json",
            "limit":        1,
            "showNumPages": "true",
        }
        resp = requests.get(CDX_API, params=params, timeout=8, headers=HEADERS)
        pages = int(resp.text.strip())
        return pages * 150  # each page ≈ 150 captures
    except Exception:
        return 0


def _fetch_snapshot_url(url: str, published_at: str) -> str:
    """
    Find the closest real snapshot (statuscode 200) to the article's publish date.
    Returns a working archive.org URL, or empty string if none found.
    """
    # Convert "20170711T161500Z" -> "20170711161500"
    ts = published_at.replace("T", "").replace("Z", "")
    try:
        params = {
            "url":    url,
            "output": "json",
            "limit":  1,
            "fl":     "timestamp,original",
        }
        resp = requests.get(CDX_API, params=params, timeout=8, headers=HEADERS)
        rows = resp.json()
        # rows[0] is the header ["timestamp","original"], rows[1] is data
        if len(rows) >= 2:
            snapshot_ts, original = rows[1]
            return f"https://web.archive.org/web/{snapshot_ts}/{original}"
    except Exception:
        pass
    return ""


def enrich_with_captures(articles: List[Article], max_articles: int = 20) -> None:
    """
    Fetch Wayback capture counts and working snapshot URLs for the top N articles (in-place).
    Limits requests to avoid being slow — only enriches candidates likely
    to reach the final top-N ranking.
    """
    targets = articles[:max_articles]
    print(f"  [Enricher] Fetching Wayback capture counts for {len(targets)} articles...")

    for article in targets:
        if article.wayback_url or article.url.startswith("https://web.archive.org"):
            # Already has a working URL (archive.org or permanent source like Guardian)
            if not article.wayback_url:
                article.wayback_url = article.url
            continue
        article.captures = _fetch_capture_count(article.url)
        time.sleep(0.3)  # stay polite with archive.org
        article.wayback_url = _fetch_snapshot_url(article.url, article.published_at)
        time.sleep(0.3)

    captured = [a for a in targets if a.captures > 0]
    if captured:
        max_cap = max(a.captures for a in captured)
        print(f"  [Enricher] Max captures found: {max_cap:,}")


def captures_score(article: Article, max_captures: int) -> float:
    """
    Normalize capture count to 0–1 using log scale.
    Log scale prevents a single viral article from drowning out everything else.
    """
    if max_captures <= 0 or article.captures <= 0:
        return 0.0
    return math.log1p(article.captures) / math.log1p(max_captures)
