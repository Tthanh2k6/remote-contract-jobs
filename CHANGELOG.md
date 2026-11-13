# Changelog

## Unreleased

- Add `lever` public postings adapter (`parse_lever`, epoch-millisecond `iso_date` handling, `lever_boards` config key) and default boards for Ashby (`supabase`, `PostHog`, `Mastra`, `inngest`, `linear`, `railway`) and Lever (`fly`).
- Tighten location filtering to reject `EMEA`/`AMER`/`NAMER`/`LATAM`-only, `Prague`, `Boston`, and regional `Remote (...)` / `Remote - ...` variants while keeping shared accepted lists. Now nine sources, 95 tests.

## 0.1.2 — 2026-11-13

- MCP tools are registered with `add_tool()` instead of `tool()(fn)`, so static scanners and MCP catalogues (for example MCP Trust Checker on mcprush) can list them; behaviour is unchanged. `list_sources` now has a description, and a test checks both tool names and descriptions against the real `mcp` SDK.
- Every search result now has `filtered_out` (`total` and `by_reason`, one count per post per reason), and table/Markdown output ends with a one-line summary, so a short result list shows why posts were dropped (in a live run on 10 Nov 2026: 873 dropped, mostly too old, full-time or location-restricted). MCP `search_jobs` returns the same field.

## 0.1.0 — 2026-11-09

- Public API/RSS adapters for Himalayas, Remotive, Remote OK, WWR, HN, n8n, Make, and Ashby.
- Remote contract filtering, explainable scoring, deduplication, cached and throttled requests.
- CLI table/JSON/Markdown output, TOML defaults, and optional read-only MCP tools.
- Offline fixture tests and Python 3.10–3.12 CI.

- Live-run fixes after review: Discourse tags returned as objects are flattened; Himalayas posts that list every time zone count as worldwide; structured location fields naming only countries/regions outside the accepted list are rejected; HN and Discourse posts with no stated employment type are kept and flagged instead of dropped; job-seeker posts in the HN hiring thread are skipped.
