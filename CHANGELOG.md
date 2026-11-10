# Changelog

## Unreleased

- Every search result now has `filtered_out` (`total` and `by_reason`, one count per post per reason), and table/Markdown output ends with a one-line summary, so a short result list shows why posts were dropped (in a live run on 10 Nov 2026: 873 dropped, mostly too old, full-time or location-restricted). MCP `search_jobs` returns the same field.

## 0.1.0 — 2026-11-09

- Public API/RSS adapters for Himalayas, Remotive, Remote OK, WWR, HN, n8n, Make, and Ashby.
- Remote contract filtering, explainable scoring, deduplication, cached and throttled requests.
- CLI table/JSON/Markdown output, TOML defaults, and optional read-only MCP tools.
- Offline fixture tests and Python 3.10–3.12 CI.

- Live-run fixes after review: Discourse tags returned as objects are flattened; Himalayas posts that list every time zone count as worldwide; structured location fields naming only countries/regions outside the accepted list are rejected; HN and Discourse posts with no stated employment type are kept and flagged instead of dropped; job-seeker posts in the HN hiring thread are skipped.
