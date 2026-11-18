"""OAuth handoff and persistence, with the real SDK over an in-process HTTP provider."""

import asyncio
import json
import time
from urllib.parse import parse_qs

import httpx
import pytest

from sdlc.services import mcp, mcp_oauth, mcp_settings


@pytest.fixture
def server(tmp_path, monkeypatch):
    monkeypatch.setattr(mcp_settings, "_STORE_PATH", tmp_path / "mcp.json")
    mcp_oauth._flows.clear()
    mcp_oauth._providers.clear()
    return mcp_settings.create_server(
        {
            "name": "test",
            "transport": "http",
            "url": "https://resource.test/mcp",
            "enabled": False,
        }
    )


def test_oauth_sdk_handoff_refresh_restart_and_replay(server, monkeypatch):
    requests = []

    def handler(request):
        requests.append(request)
        # MermaidChart rejects SDK-created discovery requests without this header.
        assert request.headers.get("User-Agent"), (
            "OAuth requests must retain HTTP client defaults"
        )
        path = request.url.path
        if path == "/mcp":
            if request.headers.get("Authorization") in (
                "Bearer access",
                "Bearer refreshed",
            ):
                return httpx.Response(200, json={"ok": True})
            return httpx.Response(
                401,
                headers={
                    "WWW-Authenticate": 'Bearer resource_metadata="https://resource.test/.well-known/oauth-protected-resource"'
                },
            )
        if "oauth-protected-resource" in path:
            return httpx.Response(
                200,
                json={
                    "resource": server["url"],
                    "authorization_servers": ["https://auth.test"],
                },
            )
        if "oauth-authorization-server" in path:
            return httpx.Response(
                200,
                json={
                    "issuer": "https://auth.test",
                    "authorization_endpoint": "https://auth.test/authorize",
                    "token_endpoint": "https://auth.test/token",
                    "registration_endpoint": "https://auth.test/register",
                    "response_types_supported": ["code"],
                    "code_challenge_methods_supported": ["S256"],
                    "grant_types_supported": ["authorization_code", "refresh_token"],
                },
            )
        if path == "/register":
            return httpx.Response(
                201, json={**json.loads(request.content), "client_id": "client"}
            )
        if path == "/token":
            data = parse_qs(request.content.decode())
            if data["grant_type"] == ["authorization_code"]:
                assert data["code"] == ["code"]
                assert len(data["code_verifier"][0]) >= 43
                return httpx.Response(
                    200,
                    json={
                        "access_token": "access",
                        "refresh_token": "refresh",
                        "expires_in": 60,
                        "token_type": "Bearer",
                    },
                )
            assert request.url.host == "auth.test", (
                "refresh must use the discovered issuer after restart"
            )
            assert data["refresh_token"] == ["refresh"]
            assert data["resource"] == [server["url"]]
            return httpx.Response(
                200,
                json={
                    "access_token": "refreshed",
                    "expires_in": 60,
                    "token_type": "Bearer",
                },
            )
        return httpx.Response(404)

    def http_client(**kwargs):
        return httpx.AsyncClient(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(mcp, "create_mcp_http_client", http_client)

    async def load(stored, *, auth=None, timeout=None):
        async with mcp._http_client(auth=auth or mcp_oauth.provider(stored)) as client:
            response = await client.get(stored["url"])
            response.raise_for_status()
        return []

    reloaded = []

    async def reload(reason):
        reloaded.append(reason)

    monkeypatch.setattr(mcp, "_load_tools", load)

    async def scenario():
        url = await mcp_oauth.start(server, reload)
        state = parse_qs(httpx.URL(url).query.decode())["state"][0]
        assert "code_challenge_method=S256" in url
        with pytest.raises(ValueError, match="state"):
            await mcp_oauth.finish("wrong", "code", None)
        assert await mcp_oauth.finish(state, "code", None)
        with pytest.raises(ValueError, match="state"):
            await mcp_oauth.finish(state, "code", None)
        assert reloaded
        stored = mcp_settings.get_server(server["id"])
        assert stored["enabled"]
        public = mcp_settings.public_server(server["id"])
        assert public["oauth_connected"]
        assert "refresh_token" not in json.dumps(public)
        assert "client_info" not in json.dumps(public)
        # Simulate a process restart with an expired token.
        mcp_oauth.Storage(stored).write(expires_at=time.time() - 1)
        mcp_oauth._providers.clear()
        await load(mcp_settings.get_server(server["id"]))
        assert requests[-1].headers["Authorization"] == "Bearer refreshed"
        assert (
            mcp_settings.get_server(server["id"])["oauth"]["tokens"]["refresh_token"]
            == "refresh"
        )

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "patch",
    [
        {"clear_credentials": True},
        {"url": "https://other.test/mcp"},
        {"headers": {"authorization": "Bearer PAT"}},
    ],
)
def test_disconnect_invalidates_storage_and_retained_provider(server, patch):
    mcp_settings.save_oauth(
        server["id"], {"generation": "old", "tokens": {"access_token": "secret"}}
    )
    stored = mcp_settings.get_server(server["id"])
    storage = mcp_oauth.Storage(stored)
    provider = mcp_oauth.provider(stored)
    mcp_settings.update_server(server["id"], patch)
    assert not mcp_settings.public_server(server["id"])["oauth_connected"]
    with pytest.raises(ValueError, match="changed"):
        storage.write(tokens={"access_token": "resurrected"})

    async def retained():
        async with httpx.AsyncClient(
            auth=provider,
            transport=httpx.MockTransport(
                lambda req: pytest.fail("must not send old tokens")
            ),
        ) as client:
            with pytest.raises(ValueError, match="changed"):
                await client.get(server["url"])

    asyncio.run(retained())


def test_header_rotation_is_case_insensitive(server):
    mcp_settings.update_server(
        server["id"], {"headers": {"Authorization": "old", "X-Key": "keep"}}
    )
    mcp_settings.update_server(server["id"], {"headers": {"authorization": "new"}})
    assert mcp_settings.get_server(server["id"])["headers"] == {
        "authorization": "new",
        "X-Key": "keep",
    }


def test_oauth_connection_uses_sdk_auth_instead_of_manual_bearer(server):
    mcp_settings.update_server(
        server["id"], {"headers": {"Authorization": "Bearer old", "X-Key": "keep"}}
    )
    mcp_settings.save_oauth(server["id"], {"generation": "oauth"})
    connection = mcp._connection(mcp_settings.get_server(server["id"]))
    assert isinstance(connection["auth"], mcp_oauth.Provider)
    assert connection["headers"] == {"X-Key": "keep"}


@pytest.mark.parametrize("user_agent", [None, "explicit-client/1.0"])
def test_oauth_subrequests_have_user_agent_without_copying_credentials(
    monkeypatch, user_agent
):
    class Auth(httpx.Auth):
        async def async_auth_flow(self, request):
            headers = {"User-Agent": user_agent} if user_agent else {}
            yield httpx.Request("GET", "https://issuer.test/discovery", headers=headers)
            yield request

    def handler(request):
        assert request.headers.get("User-Agent")
        if request.url.host == "issuer.test":
            assert "Authorization" not in request.headers
            if user_agent:
                assert request.headers["User-Agent"] == user_agent
        return httpx.Response(200)

    monkeypatch.setattr(
        mcp,
        "create_mcp_http_client",
        lambda **kwargs: httpx.AsyncClient(
            transport=httpx.MockTransport(handler), **kwargs
        ),
    )

    async def scenario():
        async with mcp._http_client(
            headers={"Authorization": "Bearer private"}, auth=Auth()
        ) as client:
            response = await client.get("https://resource.test/mcp")
            assert response.status_code == 200

    asyncio.run(scenario())


def test_cancel_preserves_existing_connection_and_rejects_callback(server, monkeypatch):
    prior = {"generation": "prior", "tokens": {"access_token": "existing"}}
    mcp_settings.save_oauth(server["id"], prior)
    server = mcp_settings.get_server(server["id"])

    async def load(stored, *, auth, timeout):
        await auth.context.redirect_handler(
            "https://auth.test/authorize?state=cancelled"
        )
        await auth.context.callback_handler()

    async def reload(reason):
        pytest.fail("cancelled sign-in must not reload tools")

    monkeypatch.setattr(mcp, "_load_tools", load)

    async def scenario():
        await mcp_oauth.start(server, reload)
        await mcp_oauth.cancel(server["id"])
        assert not mcp_oauth.status(server["id"])["pending"]
        assert mcp_settings.get_server(server["id"])["oauth"] == prior
        with pytest.raises(ValueError, match="state"):
            await mcp_oauth.finish("cancelled", "late", None)

    asyncio.run(scenario())


def test_denial_and_timeout_do_not_enable_server(server, monkeypatch):
    async def load(stored, *, auth, timeout):
        await auth.context.redirect_handler("https://auth.test/authorize?state=denied")
        await auth.context.callback_handler()

    async def reload(reason):
        pytest.fail("denied flows must not reload tools")

    monkeypatch.setattr(mcp, "_load_tools", load)

    async def scenario():
        await mcp_oauth.start(server, reload)
        with pytest.raises(ValueError, match="already pending"):
            await mcp_oauth.start(server, reload)
        assert not await mcp_oauth.finish("denied", None, "access_denied")
        assert mcp_oauth.status(server["id"])["error"]
        assert not mcp_settings.get_server(server["id"])["enabled"]
        monkeypatch.setattr(mcp_oauth, "FLOW_TIMEOUT", 0.01)
        await mcp_oauth.start(server, reload)
        await asyncio.sleep(0.03)
        assert not mcp_oauth.status(server["id"])["pending"]
        assert mcp_oauth.status(server["id"])["error"]

    asyncio.run(scenario())
