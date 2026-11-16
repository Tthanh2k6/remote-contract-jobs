# remote-contract-jobs

<!-- mcp-name: io.github.Tthanh2k6/remote-contract-jobs -->

[![Remote Contract Jobs MCP on mcprush](https://mcprush.com/badge/remote-contract-jobs-mcp/score.svg)](https://mcprush.com/to/remote-contract-jobs-mcp?ref=badge)

A Python command-line tool and optional MCP server that collects remote part-time, contract and freelance developer posts from nine public APIs and RSS feeds. It drops posts restricted to a country or time zone you are not in, and posts that require video calls, a webcam, in-person meetings or ID document uploads. I wrote it for my own search from Vietnam (UTC+7), where those blockers rule out most listings.

It sends only GET requests to public feeds, filters and scores posts on your machine, and links back to the originals. It does not apply to jobs or contact employers. Python 3.10+, MIT.

```sh
pipx install remote-contract-jobs     # or: uvx remote-contract-jobs search --help
remote-contract-jobs search --max-age-days 7 --limit 5 --format md
```

Output of that search on 16 Nov 2026 (first three of five results; each result also lists its score reasons, and links are shortened here):

```text
- 65 | Audio Transcription Adjudicator | Welocalize | We Work Remotely | 4d | Asia Only | [View post](...)
- 65 | Business System Analyst | ProArch | We Work Remotely | 4d | Asia Only | [View post](...)
- 65 | [HIRING] Founding n8n Builders for US Small-Business Client Work \| Freelance, Remote | Unknown company | n8n Community | 4d | Unknown location | [View post](...)
Filtered out 779 posts (too_old 574, employment_type_full-time 520, location_restricted 464, employment_type_unknown 79, in_person 73, below_min_score 8). A post can fail several checks; use --show-rejected for details.
```

The last line shows what the filters did on that run: 779 posts dropped, mostly for age, full-time employment and location. The filters are heuristics, so read each post before you apply (see Limitations).

## Install

```sh
pipx install remote-contract-jobs
pipx install 'remote-contract-jobs[mcp]'    # with the MCP server
```

From a checkout:

```sh
python -m pip install -e '.[dev]'
python -m pytest -q
```

On Windows, use `python -X utf8` for commands that print Unicode.

## CLI

```sh
remote-contract-jobs sources
remote-contract-jobs search --q supabase --q "react native"
remote-contract-jobs search --q python --exclude sales --sources himalayas,remotive,hn
remote-contract-jobs search --max-age-days 14 --include-fulltime --min-score 40 --limit 30 --format md
remote-contract-jobs search --format json --show-rejected --no-cache
remote-contract-jobs --config ./config.example.toml search
```

Defaults: all nine sources, no keywords, no excludes, seven days, no full-time, minimum score 40, at most 30 results. Repeating `--q` matches posts containing any of the keywords (case-insensitive substring match on title, tags and the full available text). Posts with an unknown employment type are excluded. Full-time posts are included only with `--include-fulltime`. When the structured fields lack a type, it is inferred from the title and the first 300 characters of text.

Table and Markdown output show score, title, company, source, age, location, link, reasons and flags. JSON output is one object with `jobs`, `source_errors`, `filtered_out` and `attribution`; `--show-rejected` adds `rejected` records with `rejection_reasons`. `filtered_out` holds the number of dropped posts and a count per reason (a post that fails several checks counts once under each).

One failed source does not stop the others, even when an earlier page of that source succeeded. Invalid options or configuration exit with code 2. A completed search exits with 0, including one with source errors, so check `source_errors`.

## Configuration

Copy `config.example.toml` to `~/.config/remote-contract-jobs/config.toml`, or pass `--config PATH` before the subcommand or after `search`/`mcp`.

```toml
keywords = ["supabase", "postgres", "react native", "expo", "python", "automation", "scraping", "n8n", "apps script", "mcp"]
excludes = []
ashby_boards = ["supabase", "PostHog", "Mastra", "inngest", "linear", "railway"]
lever_boards = ["fly"]
max_age_days = 7
```

The example profile is optional: the built-in keyword and exclude lists are empty. Keywords and excludes given on the command line replace the configured lists. Unknown TOML keys and invalid values are errors. The built-in Ashby boards are `supabase`, `PostHog`, `Mastra`, `inngest`, `linear` and `railway`; the built-in Lever board is `fly`. No credentials or environment files are needed.

## MCP

```sh
remote-contract-jobs mcp
remote-contract-jobs mcp --config ./config.example.toml
```

Client configuration (the executable must be on the client's PATH):

```json
{
  "mcpServers": {
    "remote-contract-jobs": {
      "command": "remote-contract-jobs",
      "args": ["mcp"]
    }
  }
}
```

Tools:

- `search_jobs(query=[], exclude=[], sources=[], max_age_days=7, include_fulltime=false, min_score=40, limit=20)` returns `jobs`, `source_errors`, `filtered_out` and `attribution` as JSON-compatible data.
- `list_sources()` returns source ids, display names, URLs and terms notes.

The tools only read public feeds. Their one file write is the response cache. An empty `query` or `exclude` list, and the default age of 7, fall back to the configured defaults. An empty config file requests the built-in defaults regardless of your profile. The server uses stdio and keeps diagnostics off protocol stdout. If the MCP dependencies are missing, it prints an installation hint. Both the `MCPServer` and the older `FastMCP` import layouts are supported.

## Filtering and ranking

Hard blockers live in `src/remote_contract_jobs/filters.py`: video interviews and calls, Loom, recorded videos, webcam, camera on, in-person, ID or document uploads, notarization, and background checks with ID upload. Simple explicit negations such as "no video interview" are recognized.

Location rules accept worldwide, anywhere, global, APAC, Asia, Vietnam, remote with no country restriction, and UTC/GMT offsets from +4 through +10. They reject US-only posts, explicit US, Canada, EU or UK residence requirements, US work authorization, full US time-zone overlap, and on-site or hybrid requirements. An explicit location field takes precedence over generic remote wording. Other unclear locations are kept with the flag `location_unclear`. Undated posts are kept with `date_unclear`, since their age is unknown. The full available text is checked, not only the 400-character snippet.

The score is clamped to 0 to 100. It starts at 20. Each keyword adds 20 if it is in the title, otherwise 12 if it is in the tags, otherwise 5 if it is in the text. Flexible employment adds 20 and a suitable location adds 20. Freshness adds up to 15, declining linearly over the age window. An unclear location subtracts 15. More than three years of required experience, or a senior, staff or lead title, subtracts 20. Results are sorted by score, then deduplicated by normalized company and title and by URL (tracking parameters and fragments ignored). The highest-scoring record is kept.

## Sources, terms and attribution

| ID | Source | Access and terms notes |
| --- | --- | --- |
| himalayas | [Himalayas](https://himalayas.app) | Public jobs and search API; source links kept. |
| remotive | [Remotive](https://remotive.com) | Attribution and original links required. Do not republish to other job sites or gate posts behind signups. The fixture notice recommends at most four fetches a day. |
| remoteok | [Remote OK](https://remoteok.com) | Attribution and source links required; no logo use without permission. The legal notice entry is skipped when parsing. |
| wwr | [We Work Remotely](https://weworkremotely.com) | Back-end, front-end and full-stack programming RSS feeds. |
| hn | [Hacker News](https://news.ycombinator.com) | Algolia API; newest matching hiring and freelancer threads; top-level comments only. Freelancer posts must start with SEEKING FREELANCER. |
| n8n | [n8n Community](https://community.n8n.io/c/jobs/13) | Public Discourse topic list; original topic links. |
| make | [Make Community](https://community.make.com/c/hire-a-pro/hire-help/74) | Public Discourse topic list; original topic links. |
| ashby | [Ashby](https://jobs.ashbyhq.com) | Configured public employer boards (see Configuration), with compensation when available. |
| lever | [Lever](https://jobs.lever.co) | Configured public employer postings (`fly` by default); original employer links kept. |

The client sends the user agent `remote-contract-jobs/<version> (+https://github.com/Tthanh2k6/remote-contract-jobs)`, uses a 20-second timeout, and waits at least one second between requests to the same host within a process. Responses are cached atomically for 30 minutes in `~/.cache/remote-contract-jobs/`, and `--no-cache` skips both reading and writing the cache. Avoid frequent polling, especially of Remotive; the 30-minute cache is not a polling interval. Separate CLI processes do not share a rate limiter.

## Limitations and verification

The heuristics can misjudge location, negation, experience and employment type. They do not prove you are eligible, and they cannot detect a requirement that the feed leaves out. Read the post before you apply. Discourse list excerpts are sometimes missing; those records carry `description_incomplete`, and pinned category guides are skipped. We Work Remotely country fields take precedence over broad region labels. No HTML pages are scraped.

Search is bounded. Himalayas fetches up to five browse pages, or five pages per keyword. Discourse sources read the current category list. The other sources use whatever window their public feed returns. HN reads all comment pages of the selected threads. Source records can be stale or removed, and APIs can change, so the results are not an exhaustive job index.

Tests make no network connections. They use the response fixtures in `tests/fixtures/`, plus adapted copies for edge cases (95 tests on 16 Nov 2026). Despite their names, `hn_freelancer_thread.json` and `hn_freelancer_comments.json` hold an October 2025 "Who is hiring?" thread, not a freelancer thread. The freelancer-prefix behavior is tested with adapted records, and I have not checked it against a real freelancer-thread response. CI runs Python 3.10, 3.11 and 3.12. The offline suite checks MCP tool registration and JSON results with a fake server; testing against a real MCP client needs the `mcp` package installed.

Source attribution: [Remotive](https://remotive.com), [Remote OK](https://remoteok.com).
