"""
Financial News Archive Crawler
================================
Usage:
    1. Edit config.json — set "sources", "dates", and "top_n".
    2. Run:  python main.py

Available sources:
    nytimes     — NY Times API (requires key), US-focused, historical
    guardian    — The Guardian API (requires key), good historical coverage
    gdelt       — free, no key, large historical index
    reuters     — Reuters RSS via Wayback Machine, free
    yahoofin    — Yahoo Finance RSS via Wayback Machine, free
    marketwatch — MarketWatch RSS via Wayback Machine, free
    wayback     — Scrapes archived homepages (Reuters, CNBC, Bloomberg, MarketWatch)
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List

import pandas as pd

from scorer import score_articles
from sources.base import Article
from wayback_enricher import enrich_with_captures
from sources.gdelt_source import GDELTSource
from sources.wayback_source import WaybackSource
from sources.guardian_source import GuardianSource
from sources.nytimes_source import NYTimesSource
from sources.marketwatch_source import MarketWatchSource
from sources.reuters_source import ReutersSource
from sources.yahoofin_source import YahooFinSource

CONFIG_FILE = "config.json"
OUTPUT_DIR  = "output"

SOURCES = {
    "gdelt":       GDELTSource,
    "wayback":     WaybackSource,
    "guardian":    GuardianSource,
    "nytimes":     NYTimesSource,
    "marketwatch": MarketWatchSource,
    "reuters":     ReutersSource,
    "yahoofin":    YahooFinSource,
}


def load_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        print(f"ERROR: {CONFIG_FILE} not found. Run from the news_crawler directory.")
        sys.exit(1)
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def article_to_dict(article: Article, rank: int, date: str) -> dict:
    return {
        "date":            date,
        "rank":            rank,
        "title":           article.title,
        "description":     article.description,
        "url":             article.url,
        "wayback_url":     article.wayback_url,
        "source":          article.source_name,
        "published_at":    article.published_at,
        "score":           round(article.score, 4),
        "score_breakdown": article.score_breakdown,
    }


def save_results(results: Dict[str, List[dict]], label: str) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"results_{label}_{timestamp}"

    json_path = os.path.join(OUTPUT_DIR, base_name + ".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nJSON  -> {json_path}")

    rows = []
    for date, articles in results.items():
        for art in articles:
            row = {k: v for k, v in art.items() if k != "score_breakdown"}
            breakdown = art.get("score_breakdown", {})
            row["score_keywords"]     = breakdown.get("financial_keywords", 0)
            row["score_position"]     = breakdown.get("position", 0)
            row["score_cross_domain"] = breakdown.get("cross_domain", 0)
            row["score_us"]           = breakdown.get("us_relevance", 0)
            row["score_captures"]     = breakdown.get("wayback_captures", 0)
            row["raw_captures"]       = breakdown.get("raw_captures", 0)
            rows.append(row)

    csv_path = os.path.join(OUTPUT_DIR, base_name + ".csv")
    pd.DataFrame(rows).to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"CSV   -> {csv_path}")


def fetch_date_multi(sources: list, date: str, top_n: int) -> List[dict]:
    """Query all sources for a date, merge, enrich, score and return top N."""
    print(f"\n{'='*55}")
    print(f"  Date : {date}")
    print(f"{'='*55}")

    all_articles: List[Article] = []
    seen_urls: set = set()

    for source_name, source in sources:
        try:
            articles = source.fetch(date)
        except Exception as e:
            print(f"  [{source_name}] Error: {e}")
            continue
        added = 0
        for a in articles:
            if a.url and a.url not in seen_urls:
                seen_urls.add(a.url)
                all_articles.append(a)
                added += 1
        print(f"  [{source_name}] +{added} articles  (total: {len(all_articles)})")

    if not all_articles:
        print(f"  No articles found for {date}.")
        return []

    print(f"\n  Enriching top 30 of {len(all_articles)} articles...")
    enrich_with_captures(all_articles, max_articles=30)
    accessible = [a for a in all_articles[:30] if a.wayback_url]
    print(f"  [Filter] {len(accessible)}/30 accessible")

    if not accessible:
        print(f"  No accessible articles for {date}.")
        return []

    scored  = score_articles(accessible)
    finance = [a for a in scored if
               a.score_breakdown.get("financial_keywords", 0) >= 0.25 and
               (a.source_name != "The Guardian" or a.score_breakdown.get("us_relevance", 0) > 0)]

    seen_keys: set = set()
    unique: list = []
    for a in finance:
        key = a.wayback_url or a.url
        if key not in seen_keys:
            seen_keys.add(key)
            unique.append(a)

    top = unique[:top_n]
    if not top:
        print(f"  No finance-relevant articles for {date}.")
        return []

    for i, a in enumerate(top):
        cap = a.score_breakdown.get("raw_captures", 0)
        cap_str = f"  |  {cap:,} captures" if cap else ""
        print(f"\n  #{i+1}  [{a.score:.3f}]  {a.title}")
        print(f"       Source : {a.source_name}{cap_str}")
        print(f"       URL    : {a.wayback_url or a.url}")

    return [article_to_dict(a, i + 1, date) for i, a in enumerate(top)]


def main() -> None:
    config   = load_config()
    dates    = config.get("dates", [])
    top_n    = config.get("top_n", 3)
    api_keys = config.get("api_keys", {})

    # Support both "sources" (list) and legacy "source" (single string)
    sources_cfg = config.get("sources") or [config.get("source", "guardian")]

    invalid = [s for s in sources_cfg if s not in SOURCES]
    if invalid:
        print(f"Unknown source(s): {invalid}. Choose from: {list(SOURCES.keys())}")
        sys.exit(1)

    if not dates:
        print("No dates in config.json.")
        sys.exit(1)

    sources = [(name, SOURCES[name](api_keys)) for name in sources_cfg]
    print(f"Sources actives : {[n for n, _ in sources]}")

    results: Dict[str, List[dict]] = {}
    for date in dates:
        results[date] = fetch_date_multi(sources, date, top_n)

    label   = "_".join(sources_cfg) if len(sources_cfg) <= 3 else "multi"
    save_results(results, label)

    success      = [d for d, arts in results.items() if arts]
    still_failed = [d for d, arts in results.items() if not arts]
    print(f"\n{'='*55}")
    print(f"  RÉSUMÉ : {len(success)}/{len(dates)} dates récupérées avec succès")
    if still_failed:
        print(f"  Dates sans résultat : {', '.join(still_failed)}")
    print(f"{'='*55}")
    print("\nDone.")


if __name__ == "__main__":
    main()
