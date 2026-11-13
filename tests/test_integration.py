import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from remote_contract_jobs import cli, config, mcp_server, network
from remote_contract_jobs.search import search_jobs

NOW = datetime(2026, 11, 9, tzinfo=timezone.utc)


class FixtureFetcher:
    def __init__(self, fixture_data):
        self.fixture_data = fixture_data
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        if "remotive.com" in url:
            return json.dumps(self.fixture_data("remotive.json"))
        if "remoteok.com" in url:
            raise OSError("fixture source failure")
        if "himalayas.app" in url:
            data = self.fixture_data("himalayas_search.json")
            data["nextCursor"] = None
            data["totalCount"] = 20
            return json.dumps(data)
        raise AssertionError("Unexpected fixture URL: " + url)


def test_search_source_isolation(fixture_data):
    result = search_jobs(sources=["remoteok", "himalayas"], max_age_days=100,
                         min_score=0, include_fulltime=True, show_rejected=True,
                         fetcher=FixtureFetcher(fixture_data), now=NOW)
    assert result["jobs"]
    assert result["source_errors"] == [{"source": "remoteok", "error": "fixture source failure"}]
    assert result["rejected"] and result["rejected"][0]["rejection_reasons"]
    assert "Remotive" in result["attribution"] and "Remote OK" in result["attribution"]


@pytest.mark.parametrize("format", ["table", "json", "md"])
def test_cli_smoke(fixture_data, tmp_path, capsys, format):
    path = tmp_path / "config.toml"
    path.write_text('keywords = ["python"]\nmax_age_days = 500\n', encoding="utf-8")
    assert cli.main(["search", "--config", str(path), "--sources", "himalayas,remoteok",
                     "--include-fulltime", "--min-score", "0", "--format", format,
                     "--show-rejected", "--no-cache"], fetcher=FixtureFetcher(fixture_data)) == 0
    output = capsys.readouterr().out
    assert "Remotive" in output and "Remote OK" in output
    if format == "json":
        data = json.loads(output)
        assert data["source_errors"] and "rejected" in data
    else:
        assert "Source error" in output and "Source attribution" in output


def test_cli_invalid_and_sources(capsys, tmp_path):
    assert cli.main(["sources"]) == 0
    assert "do not republish" in capsys.readouterr().out
    assert cli.main(["search", "--sources", "bad"]) == 2
    assert "Unknown sources" in capsys.readouterr().err


def test_config_validation_and_override(fixture_data, tmp_path, monkeypatch):
    path = tmp_path / "config.toml"
    monkeypatch.setattr(config, "DEFAULT_PATH", path)
    assert config.load_config() == {}
    path.write_text('keywords = "python"', encoding="utf-8")
    with pytest.raises(ValueError):
        config.load_config(path)
    path.write_text('keywords = ["rust"]\nmax_age_days = 14', encoding="utf-8")
    assert config.load_config()["max_age_days"] == 14
    received = {}
    def fake(**kwargs):
        received.update(kwargs)
        return {"jobs": [], "source_errors": []}
    monkeypatch.setattr(cli, "search_jobs", fake)
    cli.main(["--config", str(path), "search", "--q", "python", "--max-age-days", "0"])
    assert received["query"] == ["python"] and received["max_age_days"] == 0
    cli.main(["--config", str(path), "search", "--q", "supabase, react native", "--q", "expo"])
    assert received["query"] == ["supabase", "react native", "expo"]


def test_mcp_tools_return_json(fixture_data, monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DEFAULT_PATH", tmp_path / "missing.toml")
    def offline(**kwargs):
        return search_jobs(**kwargs, fetcher=FixtureFetcher(fixture_data), now=NOW)
    monkeypatch.setattr(mcp_server, "_search_jobs", offline)
    result = mcp_server.search_jobs(sources=["himalayas"], max_age_days=100, min_score=0, include_fulltime=True)
    assert json.loads(json.dumps(result))["jobs"]
    class FakeServer:
        def __init__(self, name):
            self.tools = {}
        def add_tool(self, fn, name=None):
            self.tools[name or fn.__name__] = fn
    server = mcp_server.create_mcp_server(FakeServer)
    assert set(server.tools) == {"search_jobs", "list_sources"}
    assert len(server.tools["list_sources"]()) == 8
    assert server.tools["search_jobs"](sources=["remoteok"])["source_errors"]


def test_mcp_real_sdk_lists_named_tools_with_descriptions():
    pytest.importorskip("mcp")
    server = mcp_server.create_mcp_server()
    # The tool manager lists synchronously; asyncio.run would open a socketpair
    # on Windows, which the no-network fixture forbids.
    tools = server._tool_manager.list_tools()
    assert sorted(t.name for t in tools) == ["list_sources", "search_jobs"]
    assert all(t.description for t in tools)


def test_mcp_missing_extra(monkeypatch):
    import builtins
    original = builtins.__import__
    def no_mcp(name, *args, **kwargs):
        if name.startswith("mcp."):
            raise ImportError("test missing extra")
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", no_mcp)
    with pytest.raises(RuntimeError, match=r"remote-contract-jobs\[mcp\]"):
        mcp_server.create_mcp_server()


def test_transport_cache_throttle_timeout(fixture_data, monkeypatch, tmp_path):
    calls, sleeps = [], []
    data = json.dumps(fixture_data("remotive.json"))
    class Response:
        status_code = 200
        text = data
        def raise_for_status(self):
            pass
    class Session:
        def get(self, url, **kwargs):
            calls.append((url, kwargs))
            return Response()
    monkeypatch.setattr(network, "_LAST_REQUEST", {})
    monkeypatch.setattr(network.time, "monotonic", lambda: 100.0)
    monkeypatch.setattr(network.time, "sleep", sleeps.append)
    fetcher = network.Fetcher(tmp_path, session=Session())
    url = "https://remotive.com/api/remote-jobs?category=software-dev"
    assert fetcher.get(url) == data
    assert fetcher.get(url) == data
    assert len(calls) == 1
    cache = next(tmp_path.iterdir())
    os.utime(cache, (0, 0))
    assert fetcher.get(url) == data
    assert len(calls) == 2 and sleeps == [1.0]
    assert calls[0][1]["timeout"] == 20
    assert calls[0][1]["headers"]["User-Agent"].startswith("remote-contract-jobs/")
    cache_before = cache.read_bytes()
    fetcher.no_cache = True
    fetcher.get(url)
    assert len(calls) == 3 and cache.read_bytes() == cache_before


def test_search_invalid_parameters():
    for kwargs in ({"max_age_days": -1}, {"min_score": 101}, {"limit": -1}, {"query": "python"}):
        with pytest.raises(ValueError):
            search_jobs(**kwargs)


def test_filtered_out_summary_counts_each_post_once_per_reason(fixture_data, capsys):
    result = search_jobs(sources=["himalayas"], max_age_days=100, min_score=0,
                         show_rejected=True, fetcher=FixtureFetcher(fixture_data), now=NOW)
    summary = result["filtered_out"]
    assert summary["total"] == len(result["rejected"]) > 0
    for reason, count in summary["by_reason"].items():
        assert ":" not in reason
        assert count == sum(1 for r in result["rejected"]
                            if reason in {x.split(":", 1)[0] for x in r["rejection_reasons"]})
    hidden = search_jobs(sources=["himalayas"], max_age_days=100, min_score=0,
                         fetcher=FixtureFetcher(fixture_data), now=NOW)
    assert "rejected" not in hidden and hidden["filtered_out"] == summary
    assert f"Filtered out {summary['total']} posts" in cli.render(hidden, "table")
