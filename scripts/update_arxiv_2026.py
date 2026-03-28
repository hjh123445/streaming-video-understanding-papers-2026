#!/usr/bin/env python3
"""Update a 2026 streaming video understanding paper list from arXiv.

This script performs keyword-based search via the arXiv API and writes a CSV.
"""

from __future__ import annotations

import csv
import datetime as dt
import html
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ARXIV_API = "http://export.arxiv.org/api/query"
OUT_FILE = Path("data/papers_2026_streaming_video_understanding.auto.csv")

SEARCH_TERMS = [
    'all:"streaming video understanding"',
    'all:"video stream understanding"',
    'all:"online video understanding"',
    'all:"streaming video reasoning"',
    'all:"long video understanding" AND all:"streaming"',
]

RELEVANCE_HINTS = {
    "streaming",
    "online",
    "video understanding",
    "video stream",
    "long video",
    "video reasoning",
}


def fetch_entries(query: str, max_results: int = 100) -> list[dict[str, str]]:
    params = {
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    url = f"{ARXIV_API}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = resp.read()

    root = ET.fromstring(data)
    ns = {"atom": "http://www.w3.org/2005/Atom"}

    rows: list[dict[str, str]] = []
    for entry in root.findall("atom:entry", ns):
        title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
        summary = (entry.findtext("atom:summary", default="", namespaces=ns) or "").strip()
        published = (entry.findtext("atom:published", default="", namespaces=ns) or "").strip()
        link = (entry.findtext("atom:id", default="", namespaces=ns) or "").strip()

        rows.append(
            {
                "title": html.unescape(" ".join(title.split())),
                "summary": html.unescape(" ".join(summary.split())),
                "published": published,
                "url": link,
            }
        )
    return rows


def looks_relevant(title: str, summary: str) -> bool:
    blob = f"{title} {summary}".lower()
    return any(h in blob for h in RELEVANCE_HINTS)


def main() -> None:
    all_rows: dict[str, dict[str, str]] = {}

    for q in SEARCH_TERMS:
        for row in fetch_entries(q):
            date = row["published"][:10]
            if not date.startswith("2026-"):
                continue
            if not looks_relevant(row["title"], row["summary"]):
                continue
            all_rows[row["url"]] = row

    sorted_rows = sorted(all_rows.values(), key=lambda r: r["published"], reverse=True)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "title", "source", "url"])
        for r in sorted_rows:
            writer.writerow([r["published"][:10], r["title"], "arXiv", r["url"]])

    print(f"Wrote {len(sorted_rows)} rows to {OUT_FILE}")
    print(f"Generated at: {dt.datetime.now().isoformat(timespec='seconds')}")


if __name__ == "__main__":
    main()
