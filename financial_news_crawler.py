"""
Financial News Crawler
Searches DuckDuckGo for top financial news on 10 random dates from the past 10 years.
Query format: "YYYY-MM-DD" "Wall Street"
Outputs: results.csv and results.json

Requires:  pip install ddgs
"""

import random
import csv
import json
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse
from ddgs import DDGS


# ── Config ──────────────────────────────────────────────────────────────────

TOP_N = 3
OUTPUT_CSV = "results.csv"
OUTPUT_JSON = "results.json"

# ── Dates à rechercher ── Mets tes dates ici (format YYYY-MM-DD) ─────────────

DATES = [
    "2017-07-11",
    "2021-10-07",
    "2021-10-05",
    "2022-09-05",
    "2018-04-16",
    "2022-07-05",
    "2022-04-19",
    "2021-10-12",
    "2021-03-18",
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def generate_random_dates(n: int = 10, years_back: int = 10) -> list[str]:
    """Return n sorted random dates within the last `years_back` years."""
    today = datetime.today()
    start = today - timedelta(days=years_back * 365)
    total_days = (today - start).days

    dates = set()
    while len(dates) < n:
        offset = random.randint(0, total_days)
        dates.add((start + timedelta(days=offset)).strftime("%Y-%m-%d"))

    return sorted(dates)


# Domaines non-news à exclure
EXCLUDED_DOMAINS = [
    "wikipedia.org",
    "reddit.com",
    "youtube.com",
    "twitter.com",
    "facebook.com",
    "quora.com",
    "amazon.com",
]


def is_news_url(url: str) -> bool:
    return not any(domain in url for domain in EXCLUDED_DOMAINS)


def ddg_search(date_str: str, top_n: int = TOP_N) -> list[dict]:
    """
    Search DuckDuckGo for: "YYYY-MM-DD" "Wall Street" financial news
    Fetches extra results to compensate for filtered-out non-news URLs.
    Returns up to top_n results with title, url, and snippet.
    """
    # Format alternatif : "2017-07-11" → "July 11, 2017"
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    date_verbose = dt.strftime("%B %d, %Y").replace(" 0", " ")  # "July 11, 2017"

    # Deux requêtes : d'abord format ISO, puis format écrit si pas assez de résultats
    queries = [
        f'"{date_str}" "Wall Street" financial news',
        f'"{date_verbose}" "Wall Street" financial news',
    ]

    results = []

    for query in queries:
        if len(results) >= top_n:
            break
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=top_n * 5):
                    url = r.get("href", "")
                    if not is_news_url(url):
                        continue
                    # Éviter les doublons
                    if any(x["url"] == url for x in results):
                        continue
                    results.append({
                        "date": date_str,
                        "rank": len(results) + 1,
                        "title": r.get("title", ""),
                        "url": url,
                        "snippet": r.get("body", ""),
                        "source": urlparse(url).netloc.replace("www.", ""),
                        "query": query,
                    })
                    if len(results) >= top_n:
                        break
        except Exception as e:
            print(f"  [WARN] Query failed ({query[:50]}...): {e}")

    return results


# ── Output ───────────────────────────────────────────────────────────────────

def save_csv(all_results: list[dict], path: str) -> None:
    fieldnames = ["date", "rank", "title", "url", "snippet", "source", "query"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_results)
    print(f"[CSV] Saved {len(all_results)} rows → {path}")


def save_json(all_results: list[dict], path: str) -> None:
    # Group by date for a readable structure
    grouped: dict[str, list] = {}
    for r in all_results:
        grouped.setdefault(r["date"], []).append(r)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(grouped, f, indent=2, ensure_ascii=False)
    print(f"[JSON] Saved {len(grouped)} dates → {path}")


# ── Main ─────────────────────────────────────────────────────────────────────

def ask_dates() -> list[str]:
    """Ask the user whether to use random dates or enter their own."""
    print("\nMode:")
    print("  [1] Random dates (auto-generated)")
    print("  [2] Enter my own dates")
    choice = input("\nChoose (1 or 2): ").strip()

    if choice == "2":
        print("\nEnter dates one per line in YYYY-MM-DD format.")
        print("Leave blank and press Enter when done.\n")
        dates = []
        while True:
            raw = input(f"  Date {len(dates)+1}: ").strip()
            if not raw:
                if dates:
                    break
                print("  Please enter at least one date.")
                continue
            # Validate format
            try:
                datetime.strptime(raw, "%Y-%m-%d")
                dates.append(raw)
            except ValueError:
                print(f"  Invalid format: '{raw}' — use YYYY-MM-DD")
        return sorted(dates)
    else:
        return generate_random_dates()


def main() -> None:
    print("=" * 60)
    print("  Financial News Crawler")
    print("=" * 60)

    dates = sorted(DATES)
    print(f"\nDates to search ({len(dates)}):")
    for d in dates:
        print(f"  {d}")

    all_results: list[dict] = []

    for i, date_str in enumerate(dates, 1):
        print(f"\n[{i}/{len(dates)}] Searching: {date_str} ...")
        results = ddg_search(date_str, TOP_N)

        if results:
            for r in results:
                print(f"  #{r['rank']} {r['title'][:80]}")
                print(f"       {r['url']}")
            all_results.extend(results)
        else:
            print("  No results found.")

        # Polite delay to avoid rate-limiting (2–4 seconds between requests)
        if i < len(dates):
            delay = random.uniform(2.0, 4.0)
            time.sleep(delay)

    print("\n" + "=" * 60)

    if all_results:
        save_csv(all_results, OUTPUT_CSV)
        save_json(all_results, OUTPUT_JSON)
    else:
        print("[WARN] No results collected. Nothing saved.")

    print("\nDone.")


if __name__ == "__main__":
    main()
