"""Command-line entry point; JSON stdout remains machine-readable."""
import argparse
from datetime import datetime, timezone
import html
import json
import sys

from .config import load_config
from .search import search_jobs
from .sources import ATTRIBUTION, SOURCES, list_sources


def age_label(posted_at):
    if not posted_at:
        return "unknown age"
    days = max(0, (datetime.now(timezone.utc) - datetime.fromisoformat(posted_at.replace("Z", "+00:00"))).days)
    return f"{days}d"


def render(result, format):
    if format == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    lines = []
    if format == "table":
        lines.append("SCORE | TITLE | COMPANY | SOURCE | AGE | LOCATION | LINK")
    def safe(value):
        value = html.escape(str(value), quote=False)
        for char in ("\\", "*", "_", "[", "]", "|", "`"):
            value = value.replace(char, "\\" + char)
        return value
    for job in result["jobs"]:
        source = SOURCES[job["source"]][0]
        cells = [job["score"], job["title"], job["company"] or "Unknown company", source,
                 age_label(job["posted_at"]), job["location_text"] or "Unknown location"]
        details = "; ".join(job["reasons"] + job["flags"])
        if format == "md":
            link = job["url"].replace("<", "%3C").replace(">", "%3E").replace(" ", "%20")
            lines.append("- " + " | ".join(safe(c) for c in cells) + f" | [View post](<{link}>)")
            lines.append("  <small>" + html.escape(details) + "</small>")
        else:
            lines.append(" | ".join(map(str, cells)) + " | " + job["url"])
            lines.append("  " + details)
    if not result["jobs"]:
        lines.append("No matching jobs.")
    for rejected in result.get("rejected", []):
        lines.append("Rejected: " + (safe(rejected["title"]) if format == "md" else rejected["title"]) + " — " + ", ".join(rejected["rejection_reasons"]))
    for error in result["source_errors"]:
        message = f"Source error ({error['source']}): {error['error']}"
        lines.append(safe(message) if format == "md" else message)
    lines.extend(["", "Source attribution: [Remotive](https://remotive.com), [Remote OK](https://remoteok.com)." if format == "md" else ATTRIBUTION])
    return "\n".join(lines)


def main(argv=None, *, fetcher=None):
    parser = argparse.ArgumentParser(prog="remote-contract-jobs")
    parser.add_argument("--config", help="TOML configuration path")
    commands = parser.add_subparsers(dest="command", required=True)
    search = commands.add_parser("search", help="Search public job feeds")
    search.add_argument("--config", default=argparse.SUPPRESS)
    search.add_argument("--q", action="append")
    search.add_argument("--exclude", action="append")
    search.add_argument("--sources", help="Comma-separated source IDs")
    search.add_argument("--max-age-days", type=int)
    search.add_argument("--include-fulltime", action="store_true")
    search.add_argument("--min-score", type=int, default=40)
    search.add_argument("--limit", type=int, default=30)
    search.add_argument("--format", choices=("table", "json", "md"), default="table")
    search.add_argument("--show-rejected", action="store_true")
    search.add_argument("--no-cache", action="store_true")
    commands.add_parser("sources", help="List sources and terms notes")
    mcp = commands.add_parser("mcp", help="Run the optional stdio MCP server")
    mcp.add_argument("--config", default=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        if args.command == "sources":
            for source in list_sources():
                print(f"{source['id']}: {source['name']} — {source['url']}\n  {source['terms']}")
            print(ATTRIBUTION)
        elif args.command == "mcp":
            from .mcp_server import run_mcp_server
            run_mcp_server(args.config)
        else:
            config = load_config(args.config)
            result = search_jobs(query=args.q if args.q is not None else config.get("keywords", []),
                exclude=args.exclude if args.exclude is not None else config.get("excludes", []),
                sources=[s.strip() for s in args.sources.split(",")] if args.sources else [],
                max_age_days=args.max_age_days if args.max_age_days is not None else config.get("max_age_days", 7),
                include_fulltime=args.include_fulltime, min_score=args.min_score, limit=args.limit,
                boards=config.get("ashby_boards", ["supabase"]), no_cache=args.no_cache,
                show_rejected=args.show_rejected, fetcher=fetcher)
            print(render(result, args.format))
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return 0
