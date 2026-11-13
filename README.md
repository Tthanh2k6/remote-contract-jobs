# remote-contract-jobs

<!-- mcp-name: io.github.Tthanh2k6/remote-contract-jobs -->

[![Remote Contract Jobs MCP on mcprush](https://mcprush.com/badge/remote-contract-jobs-mcp/score.svg)](https://mcprush.com/to/remote-contract-jobs-mcp?ref=badge)

A small Python CLI and optional MCP server for finding remote part-time, contract,
and freelance work from public APIs and RSS feeds. Built for a developer in Vietnam
(UTC+7) who needs opportunities outside US-only hiring restrictions and cannot
participate in video/camera interviews, in-person meetings, or ID document collection.

The package fetches public data with GET requests, filters and ranks posts locally,
and links back to the originals. It does not apply to jobs or contact employers.
Python 3.10+; MIT; maintained by Trung Thanh Tran ([Tthanh2k6](https://github.com/Tthanh2k6)).

## Install

```sh
pipx install remote-contract-jobs        # or: uvx remote-contract-jobs search --help
# Include the optional MCP server:
pipx install 'remote-contract-jobs[mcp]'
```

For a local checkout:

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

Defaults: all nine sources, any keyword, no excludes, seven days, no full-time,
minimum score 40, maximum 30 results. Repeating `--q` uses **any** match; matching is
case-insensitive substring matching across title, tags and full available text.
Unknown employment types are excluded. Full-time is added only with `--include-fulltime`.
Types absent from structured fields are inferred from the title and first 300 text characters.

Table and Markdown output include score, title, company, source name, age, location,
source link, reasons and flags. JSON returns an object containing `jobs`,
`source_errors`, and `attribution`; `--show-rejected` adds `rejected` records with
`rejection_reasons`. `filtered_out` is always present: the number of dropped posts and a
count per reason (a post failing several checks counts once under each). JSON attribution stays inside the object so stdout remains valid JSON.
One failed source does not stop the others, including when an earlier page succeeded.
Invalid options/configuration return exit code 2; completed searches, including partial
results with source errors, return 0. Always inspect `source_errors`.

## Configuration

Copy `config.example.toml` to `~/.config/remote-contract-jobs/config.toml`, or use
`--config PATH` before the subcommand or after `search`/`mcp`.

```toml
keywords = ["supabase", "postgres", "react native", "expo", "python", "automation", "scraping", "n8n", "apps script", "mcp"]
excludes = []
ashby_boards = ["supabase", "PostHog", "Mastra", "inngest", "linear", "railway"]
lever_boards = ["fly"]
max_age_days = 7
```

The example profile is optional: built-in keywords and excludes are empty. CLI
keyword/exclude lists replace their configured lists when supplied. Unknown TOML
keys and invalid values are errors. Ashby and Lever board names are configurable
(built-in defaults cover `supabase`, `PostHog`, `Mastra`, `inngest`, `linear`,
`railway` on Ashby and `fly` on Lever); no credentials or environment files are required.

## MCP

```sh
remote-contract-jobs mcp
remote-contract-jobs mcp --config ./config.example.toml
```

Example MCP client configuration (the executable must be on the client's PATH):

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

- `search_jobs(query=[], exclude=[], sources=[], max_age_days=7, include_fulltime=false, min_score=40, limit=20)` returns JSON-compatible `jobs`, `source_errors`, and `attribution`.
- `list_sources()` returns source IDs, display names, URLs and terms notes.

Tools only read public feeds; the local response cache is their only file write.
Empty MCP query/exclude lists and the default age of 7 use configured defaults.
Use an empty config file to request built-in defaults independently of your profile.
The server uses stdio and keeps diagnostics off protocol stdout. Missing MCP
dependencies produce an installation hint. Both `MCPServer` and the older `FastMCP`
import layout are supported.

## Filtering and ranking

Hard blockers are centralized in `src/remote_contract_jobs/filters.py`:
video interviews/calls, Loom, recorded videos, webcam, camera on, in-person,
ID/document uploads or collection, notarization, and background checks with ID upload.
Simple explicit negations such as “no video interview” are recognized.

Location rules accept worldwide/anywhere/global, APAC/Asia/Vietnam, remote without
a country restriction, and UTC/GMT offsets from +4 through +10. They reject US-only,
explicit US/Canada/EU/UK residence requirements, US work authorization, full US
time-zone overlap, and on-site/hybrid requirements. Explicit location fields take
precedence over generic remote prose. Other unclear locations are retained with
`location_unclear`. Undated posts are retained with `date_unclear` because age cannot
be established. Full available text is checked even beyond the 400-character snippet.

Score is clamped to 0–100: base 20; each keyword gets 20 in title, otherwise 12 in
tags, otherwise 5 in text; flexible employment adds 20; suitable location adds 20;
freshness adds up to 15, declining linearly over the age window. Unclear location
subtracts 15; more than three years' experience or a senior/staff/lead title subtracts
20. Results sort by score, then deduplicate using normalized company/title and URLs
(ignoring tracking parameters and fragments). The highest-scoring record is retained.

## Sources, terms and attribution

| ID | Source | Access and terms notes |
| --- | --- | --- |
| himalayas | [Himalayas](https://himalayas.app) | Public jobs/search API; source links retained. |
| remotive | [Remotive](https://remotive.com) | Attribution and original links required. Do not republish to other job sites or gate posts behind signups. Fixture notice recommends at most four fetches daily. |
| remoteok | [Remote OK](https://remoteok.com) | Attribution and source links required; no logo use without permission. Legal notice skipped when parsing. |
| wwr | [We Work Remotely](https://weworkremotely.com) | Back-end, front-end and full-stack programming RSS feeds. |
| hn | [Hacker News](https://news.ycombinator.com) | Algolia; newest matching hiring and freelancer threads; top-level comments only. Freelancer posts must start with SEEKING FREELANCER. |
| n8n | [n8n Community](https://community.n8n.io/c/jobs/13) | Public Discourse topic list; original topic links. |
| make | [Make Community](https://community.make.com/c/hire-a-pro/hire-help/74) | Public Discourse topic list; original topic links. |
| ashby | [Ashby](https://jobs.ashbyhq.com) | Public configured employer boards (`supabase`, `PostHog`, `Mastra`, `inngest`, `linear`, `railway`), including compensation when available. |
| lever | [Lever](https://jobs.lever.co) | Public configured employer postings (`fly`), preserving original employer job links. |

The client sends `remote-contract-jobs/<version> (+https://github.com/Tthanh2k6/remote-contract-jobs)`,
uses a 20-second timeout, and spaces requests to each host by at least one second
within a process. Responses are cached atomically for 30 minutes in
`~/.cache/remote-contract-jobs/`. `--no-cache` bypasses both cache reads and writes.
Avoid frequent polling, especially Remotive; a 30-minute cache is not a recommendation
to poll every 30 minutes. Concurrent independent CLI processes do not share a rate limiter.

## Limitations and verification

Heuristics can misjudge location, negation, experience and employment type. They do
not prove eligibility, guarantee accessibility, or detect requirements absent from the
feed. Always read the post before applying. Discourse list excerpts can be missing;
those records have `description_incomplete`, and pinned category guides are skipped.
WWR country fields take precedence over broad region labels. No HTML pages are scraped.

Search is bounded: Himalayas fetches up to five browse pages or five pages per keyword;
Discourse reads the current category list; other sources use their public feed windows.
HN paginates all returned comment pages for the selected threads. Source records can
be stale or removed, and APIs can change. Search is not an exhaustive job index.

Tests prohibit network connections and use the supplied response fixtures plus
controlled adaptations for edge cases. Despite their filenames, `hn_freelancer_thread.json`
and `hn_freelancer_comments.json` contain an October 2025 **Who is hiring?** thread,
not a freelancer thread. Freelancer-prefix behavior is tested using adapted records;
an actual freelancer-thread response and live endpoints have not been verified.
CI tests Python 3.10, 3.11 and 3.12. Optional SDK/client interoperability needs an MCP
installation; the offline suite verifies registration and JSON results with a fake server.

Source attribution: [Remotive](https://remotive.com), [Remote OK](https://remoteok.com).
