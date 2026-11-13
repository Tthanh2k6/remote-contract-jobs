"""Optional read-only stdio tools backed by public GET requests."""
from .config import load_config
from .search import search_jobs as _search_jobs
from .sources import DEFAULT_ASHBY_BOARDS, DEFAULT_LEVER_BOARDS, list_sources

MCP_INSTALL_HINT = ('Optional dependency "mcp" is not installed. '
                    'Install it with: pip install "remote-contract-jobs[mcp]"')


def search_jobs(query: list[str] = [], exclude: list[str] = [], sources: list[str] = [],
                max_age_days: int = 7, include_fulltime: bool = False,
                min_score: int = 40, limit: int = 20) -> dict:
    """Return normalized jobs, source_errors and source attribution as JSON data."""
    config = load_config()
    return _search_jobs(query=query or config.get("keywords", []), exclude=exclude or config.get("excludes", []),
        sources=sources, max_age_days=config.get("max_age_days", 7) if max_age_days == 7 else max_age_days,
        include_fulltime=include_fulltime, min_score=min_score, limit=limit,
        boards=config.get("ashby_boards", DEFAULT_ASHBY_BOARDS),
        lever_boards=config.get("lever_boards", DEFAULT_LEVER_BOARDS))


def create_mcp_server(fastmcp_cls=None, config_path=None):
    if fastmcp_cls is None:
        try:
            from mcp.server.mcpserver import MCPServer as fastmcp_cls
        except ImportError:
            try:
                from mcp.server.fastmcp import FastMCP as fastmcp_cls
            except ImportError as exc:
                raise RuntimeError(MCP_INSTALL_HINT) from exc
    config = load_config(config_path)
    server = fastmcp_cls("remote-contract-jobs")

    def configured_search_jobs(query: list[str] = [], exclude: list[str] = [], sources: list[str] = [],
            max_age_days: int = 7, include_fulltime: bool = False, min_score: int = 40, limit: int = 20) -> dict:
        """Search public feeds. Empty keyword/exclude lists and age 7 use config defaults."""
        return _search_jobs(query=query or config.get("keywords", []), exclude=exclude or config.get("excludes", []),
            sources=sources, max_age_days=config.get("max_age_days", 7) if max_age_days == 7 else max_age_days,
            include_fulltime=include_fulltime, min_score=min_score, limit=limit,
            boards=config.get("ashby_boards", DEFAULT_ASHBY_BOARDS),
            lever_boards=config.get("lever_boards", DEFAULT_LEVER_BOARDS))

    # add_tool(fn) rather than tool()(fn): static scanners such as MCP Trust
    # Checker (mcprush) only read the add_tool / @tool registration shapes.
    server.add_tool(configured_search_jobs, name="search_jobs")
    server.add_tool(list_sources)
    return server


def run_mcp_server(config_path=None):
    create_mcp_server(config_path=config_path).run(transport="stdio")
