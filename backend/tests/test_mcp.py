"""MCP configuration: store, credential masking, client cache, tool injection.

Deliberately does not spin up FastAPI/TestClient — the suite has no precedent
for it and these units are where the behaviour lives. Endpoint registration is
asserted directly against the app's route table.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from sdlc.services import mcp, mcp_settings


class FakeTool:
    """Stand-in for a LangChain tool: the cache only reads .name."""

    def __init__(self, name: str) -> None:
        self.name = name


@pytest.fixture()
def store(tmp_path, monkeypatch):
    """Isolate the JSON store in tmp_path; clear the module cache around each test."""
    path = tmp_path / "mcp_settings.json"
    monkeypatch.setattr(mcp_settings, "_STORE_PATH", path)
    mcp.clear()
    yield path
    mcp.clear()


def _http(name: str = "remote", **extra):
    return {"name": name, "transport": "http", "url": "https://example.test/mcp", **extra}


# ── Store ───────────────────────────────────────────────────────────────


def test_create_masks_credentials_and_filters_agents(store):
    server = mcp_settings.create_server(
        _http(headers={"Authorization": "Bearer secret"}, agents=["api", "nope"])
    )
    public = mcp_settings.public_server(server["id"])

    assert public["header_keys"] == ["Authorization"]
    assert "Bearer secret" not in json.dumps(public)
    assert public["agents"] == ["api"], "unknown agent keys are dropped"


def test_update_merges_credentials_per_key(store):
    """Editing one header must not silently drop the other stored credentials."""
    server = mcp_settings.create_server(_http(headers={"Authorization": "old", "X-Extra": "1"}))
    mcp_settings.update_server(server["id"], {"headers": {"Authorization": "new"}})

    stored = mcp_settings.get_server(server["id"])
    assert stored["headers"] == {"Authorization": "new", "X-Extra": "1"}


def test_update_can_clear_credentials(store):
    server = mcp_settings.create_server(_http(headers={"Authorization": "old"}))
    mcp_settings.update_server(server["id"], {"clear_credentials": True})

    assert mcp_settings.get_server(server["id"])["headers"] == {}
    assert mcp_settings.public_server(server["id"])["header_keys"] == []


def test_omitting_credentials_keeps_stored_values(store):
    server = mcp_settings.create_server(_http(headers={"Authorization": "keep"}))
    mcp_settings.update_server(server["id"], {"name": "renamed"})

    stored = mcp_settings.get_server(server["id"])
    assert stored["headers"] == {"Authorization": "keep"}
    assert stored["name"] == "renamed"


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"name": "x", "transport": "stdio"}, "command"),
        ({"name": "x", "transport": "http"}, "url"),
        ({"name": "x", "transport": "carrier-pigeon", "url": "u"}, "transport"),
        ({"name": "", "transport": "http", "url": "u"}, "name"),
    ],
)
def test_invalid_definitions_are_rejected(store, payload, message):
    with pytest.raises(ValueError, match=message):
        mcp_settings.create_server(payload)


def test_malformed_store_reads_as_empty(store):
    store.write_text("{not json", encoding="utf-8")
    assert mcp_settings.public_servers() == []


def test_delete_removes_record(store):
    server = mcp_settings.create_server(_http())
    assert mcp_settings.delete_server(server["id"]) is True
    assert mcp_settings.delete_server(server["id"]) is False
    assert mcp_settings.public_servers() == []


# ── Client cache ────────────────────────────────────────────────────────


def test_connection_shape_per_transport():
    stdio = mcp._connection(
        {"id": "a", "transport": "stdio", "command": "uvx", "args": ["mcp-server-fetch"], "env": {"K": "v"}}
    )
    assert stdio == {
        "transport": "stdio",
        "command": "uvx",
        "args": ["mcp-server-fetch"],
        "env": {"K": "v"},
    }

    http = mcp._connection({"id": "b", "transport": "http", "url": "https://x/mcp", "headers": {"H": "v"}})
    assert http == {"transport": "http", "url": "https://x/mcp", "headers": {"H": "v"}}


def test_refresh_distributes_tools_per_agent(store, monkeypatch):
    a = mcp_settings.create_server(_http("alpha", agents=["api", "devops"]))
    mcp_settings.create_server(_http("beta", agents=["planning"]))
    mcp_settings.create_server(_http("off", agents=["api"], enabled=False))

    loaded: list[str] = []

    async def fake_load(server):
        loaded.append(server["name"])
        return [FakeTool(f"{server['name']}_tool")]

    monkeypatch.setattr(mcp, "_load_tools", fake_load)
    status = asyncio.run(mcp.refresh())

    assert loaded == ["alpha", "beta"], "disabled servers are never contacted"
    assert [t.name for t in mcp.tools_for("api")] == ["alpha_tool"]
    assert [t.name for t in mcp.tools_for("devops")] == ["alpha_tool"]
    assert [t.name for t in mcp.tools_for("planning")] == ["beta_tool"]
    assert mcp.tools_for("architecture") == []
    assert status[a["id"]]["ok"] is True


def test_refresh_isolates_a_failing_server(store, monkeypatch):
    good = mcp_settings.create_server(_http("good", agents=["api"]))
    bad = mcp_settings.create_server(_http("bad", agents=["api"]))

    async def fake_load(server):
        if server["name"] == "bad":
            raise RuntimeError("401 unauthorized")
        return [FakeTool("ok_tool")]

    monkeypatch.setattr(mcp, "_load_tools", fake_load)
    status = asyncio.run(mcp.refresh())

    assert [t.name for t in mcp.tools_for("api")] == ["ok_tool"], "one failure must not drop the others"
    assert status[good["id"]]["ok"] is True
    assert status[bad["id"]]["ok"] is False
    assert "401 unauthorized" in status[bad["id"]]["error"]


def test_test_server_reports_success_and_failure(monkeypatch):
    async def boom(server):
        raise ConnectionError("connection refused")

    monkeypatch.setattr(mcp, "_load_tools", boom)
    result = asyncio.run(mcp.test_server({"id": "x", "transport": "http", "url": "u"}))
    assert result["ok"] is False
    assert "connection refused" in result["error"]

    async def ok(server):
        return [FakeTool("search"), FakeTool("read")]

    monkeypatch.setattr(mcp, "_load_tools", ok)
    result = asyncio.run(mcp.test_server({"id": "x", "transport": "http", "url": "u"}))
    assert result["ok"] is True
    assert result["tools"] == ["search", "read"]


# ── Error reporting ─────────────────────────────────────────────────────
# anyio wraps transport failures in ExceptionGroups; the panel must show the
# leaf, not "unhandled errors in a TaskGroup".


def test_describe_error_passes_through_plain_exceptions():
    assert mcp._describe_error(ValueError("bad url")) == "ValueError: bad url"


def test_describe_error_unwraps_nested_groups():
    inner = RuntimeError("connection reset")
    grouped = ExceptionGroup("unhandled errors in a TaskGroup", [inner])  # type: ignore[arg-type]

    described = mcp._describe_error(grouped)
    assert "connection reset" in described
    assert "RuntimeError" in described
    assert "from ExceptionGroup" in described


def test_describe_error_flags_missing_credentials():
    class HTTPStatusError(Exception):
        pass

    inner = HTTPStatusError("Client error '401 Unauthorized' for url 'https://mcp.atlassian.com/v2/mcp'")
    grouped = ExceptionGroup("unhandled errors in a TaskGroup", [inner])  # type: ignore[arg-type]

    described = mcp._describe_error(grouped)
    assert "401 Unauthorized" in described
    assert "add a credential" in described


def test_describe_error_survives_cause_cycles():
    first = RuntimeError("outer")
    second = RuntimeError("inner")
    first.__cause__ = second
    second.__context__ = first

    described = mcp._describe_error(first)
    assert "inner" in described, "must not loop forever and must report the cause"

# ── Injection into subagent specs ────────────────────────────────────────


def test_build_tools_merges_cached_mcp_tools(monkeypatch):
    from sdlc.services import subagents

    monkeypatch.setattr(mcp, "tools_for_all", lambda: {"api": [FakeTool("gh_search")]})
    tools = subagents._build_tools()

    assert "gh_search" in [t.name for t in tools["api"]]
    assert any(t.__class__.__name__ == "OpenAPIValidatorTool" for t in tools["api"]), (
        "MCP tools must extend, not replace, the built-in validators"
    )

# ── Preset catalog ──────────────────────────────────────────────────────


def test_seed_inserts_catalog_once(store):
    added = mcp_settings.seed_presets()
    names = {s["name"] for s in added}

    assert names == {p["name"] for p in mcp_settings.PRESETS}
    assert mcp_settings.seed_presets() == [], "a second boot must not re-seed"
    assert len(mcp_settings.public_servers()) == len(mcp_settings.PRESETS)


def test_every_preset_maps_to_known_agents(store):
    mcp_settings.seed_presets()
    for preset in mcp_settings.PRESETS:
        assert preset["agents"], f"{preset['name']} would never reach an agent"
        for agent in preset["agents"]:
            assert agent in mcp_settings.AGENT_KEYS


def test_auth_requiring_presets_ship_disabled(store):
    mcp_settings.seed_presets()
    by_name = {s["name"]: s for s in mcp_settings.public_servers()}

    # Zero-auth servers work out of the box; the rest must not paint a failed row.
    assert by_name["fetch"]["enabled"] is True
    assert by_name["context7"]["enabled"] is True
    for name in ("atlassian", "notion", "linear", "github", "postman", "mermaidchart", "terraform"):
        assert by_name[name]["enabled"] is False, name
        assert by_name[name]["description"], f"{name} must say what it needs"


def test_seed_preserves_user_edits_and_restores_only_missing(store):
    mcp_settings.seed_presets()
    edited = next(s for s in mcp_settings.public_servers() if s["name"] == "fetch")
    mcp_settings.update_server(edited["id"], {"description": "my own note"})
    removed = next(s for s in mcp_settings.public_servers() if s["name"] == "notion")
    mcp_settings.delete_server(removed["id"])

    restored = mcp_settings.seed_presets(force=True)
    assert [s["name"] for s in restored] == ["notion"], "only the deleted entry returns"

    after = {s["name"]: s for s in mcp_settings.public_servers()}
    assert after["fetch"]["description"] == "my own note", "user edits win over the catalog"
    assert len(after) == len(mcp_settings.PRESETS)


def test_existing_store_without_flag_is_treated_as_unseeded(store):
    """Stores written before the flag existed still get the catalog once."""
    store.write_text(json.dumps({"servers": []}), encoding="utf-8")

    added = mcp_settings.seed_presets()
    assert len(added) == len(mcp_settings.PRESETS)



def test_build_tools_survives_mcp_failure(monkeypatch):
    from sdlc.services import subagents

    def explode():
        raise RuntimeError("cache poisoned")

    monkeypatch.setattr(mcp, "tools_for_all", explode)
    tools = subagents._build_tools()  # must not raise

    assert "diagram" in tools and tools["diagram"], "validators still load when MCP breaks"


# ── Endpoint registration ───────────────────────────────────────────────


def test_mcp_endpoints_are_registered():
    from sdlc.api.app import app

    paths = {route.path for route in app.routes if "mcp" in getattr(route, "path", "")}
    assert paths == {
        "/mcp/servers",
        "/mcp/servers/presets",
        "/mcp/servers/{server_id}",
        "/mcp/servers/{server_id}/test",
        "/mcp/servers/{server_id}/oauth",
        "/mcp/servers/{server_id}/oauth/cancel",
        "/mcp/oauth/callback",
    }
