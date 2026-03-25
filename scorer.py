import math
import re
from difflib import SequenceMatcher
from typing import List

from sources.base import Article

# Weighted financial keywords — higher weight = more important signal
FINANCIAL_KEYWORDS: dict[str, float] = {
    # Tier 1 — critical market/macro events
    "federal reserve": 3.0, "fed rate": 3.0, "interest rate": 3.0,
    "rate hike": 3.0, "rate cut": 3.0, "fomc": 3.0,
    "inflation": 3.0, "recession": 3.0, "market crash": 3.0,
    "financial crisis": 3.0, "debt ceiling": 3.0, "default": 2.5,
    "stock market": 3.0, "dow jones": 3.0, "s&p 500": 3.0,
    "s&p500": 3.0, "nasdaq": 3.0, "gdp": 3.0,
    "unemployment": 3.0, "jobs report": 3.0, "nonfarm payroll": 3.0,
    "earnings report": 3.0, "quantitative easing": 3.0,
    # Tier 2 — important financial topics
    "treasury": 2.0, "bond yield": 2.0, "yield curve": 2.0,
    "trade war": 2.0, "tariff": 2.0, "deficit": 2.0,
    "stimulus": 2.0, "bailout": 2.0, "bankruptcy": 2.0,
    "hedge fund": 2.0, "wall street": 2.0, "ipo": 2.0,
    "merger": 2.0, "acquisition": 2.0, "sec": 2.0,
    "cpi": 2.0, "ppi": 2.0, "housing market": 2.0,
    "dollar": 2.0, "bank": 1.5, "fed": 2.5,
    # Tier 3 — general financial context
    "economy": 1.0, "economic": 1.0, "financial": 1.0,
    "fiscal": 1.0, "monetary": 1.0, "investor": 1.0,
    "market": 1.0, "shares": 1.0, "stock": 1.0,
    "equity": 1.0, "commodity": 1.0, "portfolio": 1.0,
}

US_KEYWORDS = [
    "united states", "u.s.", " us ", "america", "american",
    "washington", "wall street", "new york", "federal",
    "congress", "senate", "white house", "treasury",
]


def _keyword_score(article: Article) -> float:
    text = (article.title + " " + article.description).lower()
    total = sum(w for kw, w in FINANCIAL_KEYWORDS.items()
                if re.search(r'\b' + re.escape(kw) + r'\b', text))
    return min(total / 6.0, 1.0)


def _us_relevance_score(article: Article) -> float:
    text = (article.title + " " + article.description).lower()
    matches = sum(1 for kw in US_KEYWORDS if kw in text)
    return min(matches / 3.0, 1.0)


def _position_score(position: int, total: int) -> float:
    if total <= 1:
        return 1.0
    return 1.0 - (position / total)


def _title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _cross_domain_score(article: Article, all_articles: List[Article]) -> float:
    """
    Boost articles whose topic is covered by multiple DIFFERENT domains.
    Same story on 4 different sites = more important than 4 articles on 1 site.
    """
    similar_domains = set()
    for other in all_articles:
        if other is not article and _title_similarity(article.title, other.title) > 0.35:
            similar_domains.add(other.source_name.lower())
    return min(len(similar_domains) / 4.0, 1.0)


def _captures_score(article: Article, max_captures: int) -> float:
    """
    Normalize Wayback capture count to 0–1 on a log scale.
    More captures = article was widely referenced/shared at the time.
    Returns 0 if no capture data was fetched.
    """
    if max_captures <= 0 or article.captures <= 0:
        return 0.0
    return math.log1p(article.captures) / math.log1p(max_captures)


def score_articles(articles: List[Article]) -> List[Article]:
    """Score and sort articles by financial importance. Returns sorted list (best first)."""
    total        = len(articles)
    max_captures = max((a.captures for a in articles), default=0)
    has_captures = max_captures > 0

    for i, article in enumerate(articles):
        article.raw_position = i
        kw    = _keyword_score(article)
        pos   = _position_score(i, total)
        xdom  = _cross_domain_score(article, articles)
        us    = _us_relevance_score(article)
        cap   = _captures_score(article, max_captures)

        if has_captures:
            # With capture data: redistribute weight to include captures signal
            article.score = (
                0.30 * kw   +
                0.20 * pos  +
                0.15 * xdom +
                0.10 * us   +
                0.25 * cap   # Wayback captures — strongest external signal
            )
        else:
            # Without capture data: original weights (captures not fetched)
            article.score = (
                0.40 * kw   +
                0.30 * pos  +
                0.20 * xdom +
                0.10 * us
            )

        article.score_breakdown = {
            "financial_keywords": round(kw,   3),
            "position":           round(pos,  3),
            "cross_domain":       round(xdom, 3),
            "us_relevance":       round(us,   3),
            "wayback_captures":   round(cap,  3),
            "raw_captures":       article.captures,
        }

    return sorted(articles, key=lambda a: a.score, reverse=True)
