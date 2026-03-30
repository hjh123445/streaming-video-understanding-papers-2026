#!/usr/bin/env python3
"""Update 2026 streaming video understanding papers from arXiv.

Outputs:
- data/papers_2026_streaming_video_understanding.auto.csv (raw relevant rows)
- data/papers_2026_streaming_video_understanding.csv (classified master list)
- data/papers_2026_streaming_video_understanding.categories.csv (category counts)
- data/papers_2026_streaming_video_understanding.by_direction.md (readable grouped report)
"""

from __future__ import annotations

import csv
import datetime as dt
import html
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.error import HTTPError, URLError

ARXIV_API = "https://export.arxiv.org/api/query"
REQUEST_HEADERS = {
    "User-Agent": "streaming-video-understanding-papers-2026/1.0 (maintainer: 2736340051@qq.com)"
}
MAX_RETRIES = 5
BASE_SLEEP_SECONDS = 2.0
MIN_VALID_ROWS = 20
OUT_RAW = Path("data/papers_2026_streaming_video_understanding.auto.csv")
OUT_MASTER = Path("data/papers_2026_streaming_video_understanding.csv")
OUT_CATEGORIES = Path("data/papers_2026_streaming_video_understanding.categories.csv")
OUT_REPORT = Path("data/papers_2026_streaming_video_understanding.by_direction.md")

SEARCH_TERMS = [
    'all:"streaming video understanding"',
    'all:"video stream understanding"',
    'all:"online video understanding"',
    'all:"streaming video reasoning"',
    'all:"streaming video question answering"',
    'all:"long video understanding" AND all:"streaming"',
    'all:"streaming" AND all:"VideoLLM"',
    'all:"streaming" AND all:"multimodal" AND all:"video"',
]

RELEVANCE_HINTS = {
    "streaming",
    "online",
    "video understanding",
    "video stream",
    "long video",
    "video reasoning",
    "videollm",
    "video question answering",
}

CATEGORY_RULES = [
    (
        "Memory & KV-Cache",
        ("memory", "kv", "cache", "memor", "hierarchical memory", "eventmem"),
    ),
    (
        "Reasoning & Agents",
        ("reason", "thinking", "agent", "proactive", "tool use", "search"),
    ),
    (
        "Efficiency & Compression",
        ("token", "pruning", "compression", "efficient", "scaling", "optimization"),
    ),
    (
        "Video QA / Query",
        ("question answering", "qa", "query", "answer"),
    ),
    (
        "Benchmarks & Evaluation",
        ("benchmark", "evaluation", "eval", "protocol", "technical report"),
    ),
    (
        "Sensors / Systems",
        ("always-on", "sensing", "triggering", "sensor"),
    ),
]


def normalize_arxiv_url(url: str) -> str:
    url = url.replace("http://", "https://")
    if "arxiv.org/abs/" not in url:
        return url
    tail = url.split("/abs/", 1)[1]
    base_id = tail.split("v", 1)[0]
    return f"https://arxiv.org/abs/{base_id}"


def fetch_entries(query: str, max_results: int = 100) -> list[dict[str, str]]:
    params = {
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    url = f"{ARXIV_API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=REQUEST_HEADERS)
    data = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
            break
        except HTTPError as e:
            is_retryable = e.code in (429, 500, 502, 503, 504)
            if not is_retryable or attempt == MAX_RETRIES:
                raise
            retry_after = e.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                sleep_s = float(retry_after)
            else:
                sleep_s = BASE_SLEEP_SECONDS * (2 ** (attempt - 1))
            print(
                f"[warn] query failed with HTTP {e.code}; retrying in {sleep_s:.1f}s "
                f"({attempt}/{MAX_RETRIES})"
            )
            time.sleep(sleep_s)
        except URLError as e:
            if attempt == MAX_RETRIES:
                raise
            sleep_s = BASE_SLEEP_SECONDS * (2 ** (attempt - 1))
            print(f"[warn] transient network error ({e}); retrying in {sleep_s:.1f}s")
            time.sleep(sleep_s)

    if data is None:
        return []

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
                "url": normalize_arxiv_url(link),
            }
        )
    return rows


def looks_relevant(title: str, summary: str) -> bool:
    blob = f"{title} {summary}".lower()
    return any(h in blob for h in RELEVANCE_HINTS)


def classify_paper(title: str, summary: str) -> tuple[str, str]:
    blob = f"{title} {summary}".lower()
    hits: list[str] = []
    for name, keywords in CATEGORY_RULES:
        if any(k in blob for k in keywords):
            hits.append(name)
    if not hits:
        hits.append("General Streaming Video Understanding")
    primary = hits[0]
    return primary, " | ".join(hits)


def to_brief(summary: str, max_len: int = 120) -> str:
    plain = " ".join(summary.split())
    first_sentence = re.split(r"(?<=[.!?])\s+", plain, maxsplit=1)[0]
    if len(first_sentence) <= max_len:
        return first_sentence
    return first_sentence[: max_len - 3].rstrip() + "..."


def escape_md_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


def write_outputs(rows: list[dict[str, str]]) -> None:
    OUT_RAW.parent.mkdir(parents=True, exist_ok=True)

    with OUT_RAW.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "title", "source", "url", "brief"])
        for r in rows:
            writer.writerow([r["published"][:10], r["title"], "arXiv", r["url"], to_brief(r["summary"])])

    enriched: list[dict[str, str]] = []
    for r in rows:
        primary, categories = classify_paper(r["title"], r["summary"])
        enriched.append(
            {
                "date": r["published"][:10],
                "title": r["title"],
                "source": "arXiv",
                "url": r["url"],
                "primary_direction": primary,
                "all_directions": categories,
                "brief": to_brief(r["summary"]),
            }
        )

    with OUT_MASTER.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "date",
                "title",
                "source",
                "url",
                "primary_direction",
                "all_directions",
                "brief",
            ],
        )
        writer.writeheader()
        writer.writerows(enriched)

    category_counts: dict[str, int] = {}
    for r in enriched:
        category_counts[r["primary_direction"]] = category_counts.get(r["primary_direction"], 0) + 1

    with OUT_CATEGORIES.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["direction", "count"])
        for direction, count in sorted(category_counts.items(), key=lambda x: (-x[1], x[0])):
            writer.writerow([direction, count])

    grouped: dict[str, list[dict[str, str]]] = {}
    for r in enriched:
        grouped.setdefault(r["primary_direction"], []).append(r)

    lines = [
        "# 2026 Streaming Video Understanding Papers by Direction",
        "",
        f"Generated at: {dt.datetime.now().isoformat(timespec='seconds')}",
        "",
        f"Total papers: {len(enriched)}",
        "",
        "## Category Summary",
        "",
        "| Direction | Count |",
        "|---|---:|",
    ]
    for direction, count in sorted(category_counts.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"| {direction} | {count} |")

    for direction, _ in sorted(category_counts.items(), key=lambda x: (-x[1], x[0])):
        lines.extend(["", f"## {direction}", ""])
        lines.extend(
            [
                "| Date | Paper | Link | Brief |",
                "|---|---|---|---|",
            ]
        )
        for r in sorted(grouped[direction], key=lambda x: x["date"], reverse=True):
            title = escape_md_cell(r["title"])
            brief = escape_md_cell(r["brief"])
            link = f"[arXiv]({r['url']})"
            lines.append(f"| {r['date']} | {title} | {link} | {brief} |")

    OUT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    all_rows: dict[str, dict[str, str]] = {}

    for q in SEARCH_TERMS:
        try:
            rows = fetch_entries(q)
        except Exception as e:  # Keep scheduled job alive even if one query is rate-limited.
            print(f"[warn] skipped query due to error: {q} -> {e}")
            continue

        for row in rows:
            date = row["published"][:10]
            if not date.startswith("2026-"):
                continue
            if not looks_relevant(row["title"], row["summary"]):
                continue
            all_rows[row["url"]] = row
        time.sleep(2.0)

    sorted_rows = sorted(all_rows.values(), key=lambda r: r["published"], reverse=True)
    if len(sorted_rows) < MIN_VALID_ROWS:
        print(
            f"[warn] only collected {len(sorted_rows)} rows (<{MIN_VALID_ROWS}); "
            "skip writing output to avoid replacing data with partial results."
        )
        return
    write_outputs(sorted_rows)

    print(f"Wrote {len(sorted_rows)} rows to {OUT_MASTER}")
    print(f"Generated at: {dt.datetime.now().isoformat(timespec='seconds')}")


if __name__ == "__main__":
    main()
