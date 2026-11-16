# Security policy

## Supported versions

The latest release on PyPI gets fixes. Older releases do not.

## Reporting a vulnerability

Report it privately through GitHub: https://github.com/Tthanh2k6/remote-contract-jobs/security/advisories/new

Do not open a public issue for a security problem.

Include the version, the command or MCP tool call, your OS and Python version, and steps that reproduce it.

This is a one-person project. Reports are handled on a best-effort basis, with no promised response time.

## In scope

- The tool sending any request other than a `GET` to a public feed, or sending credentials.
- A way to make it write a file outside the cache directory (`~/.cache/remote-contract-jobs/`), or to read a file outside the config path you gave it.
- Unsafe handling of feed content: a crafted post that runs code, or that corrupts the cache.
- An MCP tool doing more than reading public feeds and writing the response cache.

## Out of scope

- Wrong location, experience or employment-type judgments. Open a normal bug report for those.
- Stale or removed posts, and changes to a source's API.
- Anything listed under "Limitations and verification" in the README.
