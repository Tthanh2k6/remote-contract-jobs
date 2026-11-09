# Changelog

## 0.1.0 — 2026-11-09

- Public API/RSS adapters for Himalayas, Remotive, Remote OK, WWR, HN, n8n, Make, and Ashby.
- Remote contract filtering, explainable scoring, deduplication, cached and throttled requests.
- CLI table/JSON/Markdown output, TOML defaults, and optional read-only MCP tools.
- Offline fixture tests and Python 3.10–3.12 CI.

- Live-run fixes after review: Discourse tags returned as objects are flattened; Himalayas posts that list every time zone count as worldwide; structured location fields naming only countries/regions outside the accepted list are rejected; HN and Discourse posts with no stated employment type are kept and flagged instead of dropped; job-seeker posts in the HN hiring thread are skipped.
