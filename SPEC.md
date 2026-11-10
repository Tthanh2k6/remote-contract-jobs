# remote-contract-jobs — spec (v0.1.0)

A small Python package with a CLI and an MCP server that pulls remote job posts from public APIs/feeds, keeps the ones that fit a part-time/contract developer outside the US, and drops posts that require things the user cannot do (video calls, camera interviews, ID document collection, US-only work authorization).

Owner: Trung Thanh Tran (GitHub Tthanh2k6). License MIT. Python 3.10+. Same layout and style as D:/Project/1-dang-ban/supabase-rls-check (src/ layout, pyproject, `MCPServer` import with FastMCP fallback, pytest, GitHub Actions CI). Read that repo for conventions before starting.

## Sources (public, no login, no scraping of HTML pages)
| id | endpoint | notes |
|---|---|---|
| himalayas | `https://himalayas.app/jobs/api?limit=..&cursor=..` and `https://himalayas.app/jobs/api/search?q=..` | fields include locationRestrictions, employmentType, pubDate, applicationLink |
| remotive | `https://remotive.com/api/remote-jobs?category=software-dev` (+ `search=`) | ToS: link back to the Remotive URL and name Remotive as source; do not republish to other job sites |
| remoteok | `https://remoteok.com/api` | first array element is a legal notice, skip it; ToS: link back and name "Remote OK" as source |
| wwr | `https://weworkremotely.com/categories/<cat>.rss` (programming categories) | RSS; region often in title/description |
| hn | HN Algolia: latest `whoishiring` stories (`search_by_date?tags=story,author_whoishiring`), pick newest "Who is hiring?" and "Freelancer? Seeking freelancer?" by title; then top-level comments of that story | only top-level comments (parent_id == story id); for the Freelancer thread keep only comments starting with "SEEKING FREELANCER" |
| n8n | `https://community.n8n.io/c/jobs/13.json` | Discourse topic list; topic URL `https://community.n8n.io/t/<slug>/<id>` |
| make | `https://community.make.com/c/hire-a-pro/hire-help/74.json` | same Discourse format |
| ashby | `https://api.ashbyhq.com/posting-api/job-board/<board>?includeCompensation=true` for a configurable list of board names (default: a short list in config, e.g. supabase) | public posting API |

Fixtures with real responses are already in `tests/fixtures/` (fetched 09/11/2026). Tests must use fixtures only — no network in tests.

Network etiquette: generic User-Agent `remote-contract-jobs/<version> (+https://github.com/Tthanh2k6/remote-contract-jobs)`, timeout 20 s, ≥1 s delay between requests to the same host, simple on-disk cache (default 30 min, `--no-cache`), one failing source must not stop the others (report it in a `source_errors` list).

## Normalized job record
`source, title, company, url (link back to the source page), apply_url (if given), posted_at (ISO UTC), location_text, employment_type (full-time|part-time|contract|freelance|unknown), tags[], salary_text, snippet (≤400 chars, plain text), score, reasons[], flags[]`.

## Filtering and scoring (pure functions, unit-tested)
- `max_age_days` (default 7).
- Keywords: include list (any match in title/tags/text) — default empty = all; exclude list.
- Employment type: default keep part-time, contract, freelance; `--include-fulltime` to keep full-time.
- Location fit, from location fields + text:
  - OK: worldwide, anywhere, global, remote (no country), APAC/Asia, Vietnam, UTC+7 ±3h.
  - REJECT: "US only", "must be located in the US/Canada/EU/UK", "authorized to work in the US", US time-zone requirement with full overlap, on-site/hybrid.
  - Unknown → keep with flag `location_unclear`.
- Hard blockers (drop, but list them in `rejected` with reason when `--show-rejected`): video interview / Loom / "record a video" / webcam / camera on / in-person; ID or document collection / notarized / background check with ID upload. Keep the patterns in one list in `filters.py` so they are easy to edit.
- Score 0–100: keyword hits in title > tags > text, contract/part-time bonus, location OK bonus, freshness bonus, penalties for `location_unclear` and for >3 years experience required ("5+ years", "senior", "staff", "lead").
- Dedupe by normalized (company, title) and by URL.

## CLI
`remote-contract-jobs search [--q supabase --q "react native"] [--exclude ...] [--sources himalayas,remotive,...] [--max-age-days 7] [--include-fulltime] [--min-score 40] [--limit 30] [--format table|json|md] [--show-rejected] [--no-cache]`
`remote-contract-jobs sources` — list sources with their terms note.
Markdown output: one line per job: score, title, company, source, age, location, link; then reasons/flags in small text. Always print the "source attribution" footer (Remotive, Remote OK names + links).

## MCP server (`remote-contract-jobs mcp`)
Tools: `search_jobs(query: list[str] = [], exclude: list[str] = [], sources: list[str] = [], max_age_days: int = 7, include_fulltime: bool = False, min_score: int = 40, limit: int = 20)` → JSON list + source_errors; `list_sources()`. Read-only. Install hint like supabase-rls-check when `mcp` extra missing.

## Config
Optional `~/.config/remote-contract-jobs/config.toml` (or `--config`): default keywords, excludes, ashby boards, max age. Ship `config.example.toml` with the owner's profile as example: keywords supabase, postgres, react native, expo, python, automation, scraping, n8n, apps script, mcp.

## Tests (pytest, fixtures only)
Per-source parser tests on the fixtures; filter tests for each blocker and location rule (positive + negative strings); scoring order; dedupe; HN top-level filtering; CLI smoke test with a fake fetcher; MCP tool returns JSON. Aim for ~40 tests.

## Repo files
README (what it does, why the filters exist, install with pipx from GitHub, CLI + MCP examples, source terms and attribution, limitations: heuristics can misjudge location; always read the post), CHANGELOG 0.1.0, LICENSE MIT, `.github/workflows/ci.yml` (pytest on 3.10–3.12), `glama.json` (`{"$schema": "https://glama.ai/mcp/schemas/server.json", "maintainers": ["Tthanh2k6"]}`), `.gitignore` (cache dir).

## Rules for the builder
- Do not run `git init`, commit or push; the owner will review first.
- No network calls in tests. If you need to check a live endpoint, say so in your report instead of guessing.
- Do not read any `.env` file. Do not put any personal email or phone in code.
- Report: files created, test count and result, anything unverified.
