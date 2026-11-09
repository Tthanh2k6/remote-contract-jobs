# Codebase reference

## 1. Purpose

Python 3.10+ CLI and optional stdio MCP tools for public remote contract job feeds.
Version 0.1.0. Requirements are in SPEC.md; user documentation is in README.md.

## 2. Layout

`src/remote_contract_jobs/` contains models, sources, filters, network, search,
config, cli, mcp_server, and package entry points. `tests/fixtures/` contains supplied
API/RSS responses. The three test modules cover parsers, pure rules, and integration.
Root files provide metadata, examples, MIT license, changelog and MCP directory metadata.
`.github/workflows/ci.yml` installs the package and runs pytest on 3.10–3.12.

## 3. Data flow

CLI/MCP defaults + TOML → search_jobs → fetch_source → Fetcher.get → parser → Job
→ evaluate → dedupe → limit → public dictionaries → table/Markdown/JSON or MCP.
The fetcher only issues GET requests; no credentials or HTML page scraping.

## 4. Record schema

Job fields: source, title, company, url, apply_url, posted_at (UTC ISO or empty),
location_text, employment_type, tags, salary_text, snippet, score, reasons, flags.
Internal text holds the full description; `Job.to_dict()` excludes it.
Missing text/date/company values remain empty rather than fabricated.
Public search result: jobs[], source_errors[{source,error}], attribution;
optional rejected[] adds rejection_reasons per normalized record.

## 5. Modules and entry points

- models: `plain(value)`, `iso_date(value)`, `employment(value)`, `job(...)`, `Job.to_dict()`.
- sources: `parse_himalayas`, `parse_remotive`, `parse_remoteok`, `parse_wwr`,
  `parse_discourse(data, source)`, `parse_ashby(data, board)`, `hn_threads(data)`,
  `parse_hn(data, story_id, freelancer=False)`, `fetch_source(source, fetcher, query, boards)`.
- filters: `positive_match(pattern, text)`, `location_fit(location, text)`,
  `age_days(job, now)`, `evaluate(...) -> (Job, rejection_reasons)`, `dedupe(jobs)`.
- network: `Fetcher(cache_dir=None, no_cache=False, ttl=1800, session=None).get(url)`.
- search: `search_jobs(query, exclude, sources, max_age_days, include_fulltime,
  min_score, limit, *, boards, no_cache, show_rejected, fetcher, now)`.
- config: `load_config(path=None)` reads keywords, excludes, ashby_boards, max_age_days.
- cli: `main(argv=None, *, fetcher=None)`; `render(result, format)`.
- mcp_server: `search_jobs(...)`, `create_mcp_server(fastmcp_cls=None, config_path=None)`,
  `run_mcp_server(config_path=None)`; `list_sources` registered from sources.

## 6. Rule invariants

Blockers centralized in filters; positive matches recognize limited explicit negation.
Employment defaults to part-time/contract/freelance; unknown is rejected. Unknown
location/date are flagged. Full text, including content after the snippet, is filtered.
Score: base 20 + keywords (20 title / 12 tags / 5 text) + flexible 20 + location 20
+ freshness 0–15 − unclear location 15 − experience 20; clamp 0–100.
Deduplication selects highest-scoring records by company/title or normalized URL.

## 7. I/O and limits

GET timeout 20 seconds, minimum one second between requests to the same host,
process-wide lock, cache TTL 1800 seconds, atomic replacement. Cache errors are
nonfatal. Redirects are surfaced as source errors rather than making unthrottled requests.
Himalayas caps at five pages per browse/query; HN uses reported comment pagination.
Partial source results survive a later source error. MCP uses config defaults for
empty query/exclude and age 7 because the required tool signature has concrete defaults.

## 8. Tests and known gaps

`python -X utf8 -m pytest -q`; network connections blocked by autouse fixture.
Tests cover all sources, adapted HN freelancer comments, filtering, scoring, dedupe,
CLI formats/configuration, source errors, cache/rate limiting and fake MCP registration.
The supplied freelancer fixtures are mislabeled hiring-thread responses. Real freelancer
responses, live endpoints and external MCP clients are unverified. Fixtures are preserved.

## 9. Documentation changelog

- 2026-11-09: Initial package, source adapters, filters, CLI/MCP, offline tests and documentation.
