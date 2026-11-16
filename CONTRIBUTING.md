# Contributing

remote-contract-jobs is a one-person project. Issues and pull requests are welcome, and replies are best effort.

It is a read-only search tool. It fetches public data with GET requests, filters and ranks posts locally, and links back to the originals. It does not apply to jobs or contact employers.

## Setup

You need Python 3.10 or newer.

```bash
git clone https://github.com/Tthanh2k6/remote-contract-jobs.git
cd remote-contract-jobs
python -m pip install -e ".[dev]"
python -m pytest -q
```

Add the `mcp` extra (`".[dev,mcp]"`) if you work on `src/remote_contract_jobs/mcp_server.py`. On Windows, use `python -X utf8` for commands that print Unicode.

The tests run offline and use response fixtures. Do not add a test that needs a live network.

## Style

- Add a test with every behavior change or bug fix.
- Add no new dependency without opening a discussion first.
- Hard blockers (video calls, webcam, in-person, ID collection) live in `src/remote_contract_jobs/filters.py`. Put new ones there, with a test for the match and for a negation such as "no video interview".

## Adding a source

A source must be a public feed or API, read with GET requests, and its terms must allow reading and showing posts with a link back. Do not scrape HTML pages, log in, or get around a rate limit. Open an issue first and link the terms page.

If it is accepted:

1. Add a parser and the fetch logic in `src/remote_contract_jobs/sources.py`, and an entry in `SOURCES` with a terms note.
2. Save a real response as a fixture under `tests/` and cover the parser in `tests/test_sources.py`.
3. Keep the existing client behavior: the identifying user agent, the 20-second timeout, at least one second between requests to a host, and the 30-minute cache.
4. Add a row to the sources table in the README, with its attribution requirements.

## Pull requests

Fill in the pull request template. Keep one change per pull request.

## Security

Do not report security problems in public issues. See [SECURITY.md](SECURITY.md).
