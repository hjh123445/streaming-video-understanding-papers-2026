# 2026 Streaming Video Understanding Papers

This repository tracks **2026 papers** related to streaming/online video understanding, and now includes **automatic direction-based classification**.

Last refreshed: **2026-03-28** (Asia/Shanghai)

## What is improved

- Expanded retrieval coverage from arXiv query set (broader than the initial seed list)
- Automatic deduplication (same paper from multiple queries)
- Automatic research-direction classification
- Auto-generated grouped report for easy browsing

## Current snapshot

- Total papers currently collected: **42**
- Primary direction counts:
  - Memory & KV-Cache: 20
  - Reasoning & Agents: 16
  - Efficiency & Compression: 3
  - Benchmarks & Evaluation: 1
  - General Streaming Video Understanding: 1
  - Video QA / Query: 1

## Main files

- Master list with direction labels:
  - `data/papers_2026_streaming_video_understanding.csv`
- Raw relevant results:
  - `data/papers_2026_streaming_video_understanding.auto.csv`
- Direction summary counts:
  - `data/papers_2026_streaming_video_understanding.categories.csv`
- Grouped markdown report:
  - `data/papers_2026_streaming_video_understanding.by_direction.md`

## Refresh command

```bash
python scripts/update_arxiv_2026.py
```

This command regenerates all files above.

## Classification logic (automatic)

Current rule-based categories include:

- Memory & KV-Cache
- Reasoning & Agents
- Efficiency & Compression
- Video QA / Query
- Benchmarks & Evaluation
- Sensors / Systems
- General Streaming Video Understanding (fallback)

Notes:
- Classification is keyword-based and may include edge cases.
- You can tighten or widen the rules in `scripts/update_arxiv_2026.py` depending on your preference for precision vs. recall.
