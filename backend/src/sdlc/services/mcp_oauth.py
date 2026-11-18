"""Browser handoff for the MCP SDK's discovery, PKCE and token refresh flow.

Pending flows live in the single API worker, just like chat approval futures.
Only the SDK sees token values; the browser receives an authorization URL.
"""

from __future__ import annotations

import asyncio
import secrets
import time
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlsplit

from mcp.client.auth import OAuthClientProvider
from mcp.shared.auth import (
    OAuthClientInformationFull,
    OAuthClientMetadata,
    OAuthMetadata,
    OAuthToken,
    ProtectedResourceMetadata,
)

from sdlc.core import config
from sdlc.services import mcp_settings

FLOW_TIMEOUT = 300


class Storage:
    def __init__(self, server: dict[str, Any]):
        self.server_id = server["id"]
        self.generation = server["oauth"]["generation"]

    def read(self) -> dict[str, Any]:
        server = mcp_settings.get_server(self.server_id)
        oauth = server.get("oauth", {}) if server else {}
        if oauth.get("generation") != self.generation:
            raise ValueError("OAuth connection changed; connect again")
        return oauth

    def write(self, **fields: Any) -> None:
        mcp_settings.save_oauth(
            self.server_id, {**self.read(), **fields}, generation=self.generation
        )

    async def get_tokens(self) -> OAuthToken | None:
        data = self.read().get("tokens")
        return OAuthToken.model_validate(data) if data else None

    async def set_tokens(self, tokens: OAuthToken) -> None:
        self.write(
            tokens=tokens.model_dump(mode="json"),
            expires_at=(
                time.time() + tokens.expires_in
                if tokens.expires_in is not None
                else None
            ),
        )

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        data = self.read().get("client_info")
        return OAuthClientInformationFull.model_validate(data) if data else None

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        self.write(client_info=client_info.model_dump(mode="json"))


class Provider(OAuthClientProvider):
    async def _initialize(self) -> None:
        await super()._initialize()
        # The SDK restores tokens but not their expiry; preserve it across restarts.
        self.context.token_expiry_time = self.context.storage.read().get("expires_at")
        metadata = self.context.storage.read().get("metadata")
        if metadata:
            self.context.oauth_metadata = OAuthMetadata.model_validate(metadata)
        resource = self.context.storage.read().get("resource_metadata")
        if resource:
            self.context.protected_resource_metadata = (
                ProtectedResourceMetadata.model_validate(resource)
            )

    async def _handle_token_response(self, response) -> None:
        await super()._handle_token_response(response)
        resource = self.context.protected_resource_metadata
        metadata = self.context.oauth_metadata
        self.context.storage.write(
            metadata=metadata.model_dump(mode="json") if metadata else None,
            resource_metadata=resource.model_dump(mode="json") if resource else None,
        )

    async def _handle_refresh_response(self, response) -> bool:
        previous = (
            self.context.current_tokens.refresh_token
            if self.context.current_tokens
            else None
        )
        ok = await super()._handle_refresh_response(response)
        if ok and not self.context.current_tokens.refresh_token and previous:
            # OAuth permits providers to omit an unchanged refresh token.
            self.context.current_tokens.refresh_token = previous
            await self.context.storage.set_tokens(self.context.current_tokens)
        return ok

    def _add_auth_header(self, request) -> None:
        self.context.storage.read()  # Reject retained tools after disconnect/URL changes.
        super()._add_auth_header(request)

    async def _refresh_token(self):
        self.context.storage.read()
        return await super()._refresh_token()


@dataclass
class Flow:
    ready: asyncio.Future
    callback: asyncio.Future
    task: asyncio.Task | None = None
    state: str | None = None
    error: str | None = None
    complete: bool = False


_flows: dict[str, Flow] = {}
_providers: dict[str, tuple[str, Provider]] = {}


def provider(server: dict[str, Any], flow: Flow | None = None) -> Provider:
    oauth = server["oauth"]
    generation = oauth["generation"]
    cached = _providers.get(server["id"])
    if flow is None and cached and cached[0] == generation:
        return cached[1]

    async def redirect(url: str) -> None:
        if flow is None:
            raise ValueError("OAuth sign-in required; click CONNECT in MCP settings")
        parsed = urlsplit(url)
        if parsed.scheme != "https" and not (
            parsed.scheme == "http"
            and parsed.hostname in ("localhost", "127.0.0.1", "::1")
        ):
            raise ValueError("OAuth authorization URL must use HTTPS")
        flow.state = parse_qs(parsed.query).get("state", [None])[0]
        if not flow.state:
            raise ValueError("OAuth provider did not supply state")
        if not flow.ready.done():
            flow.ready.set_result(url)

    async def callback() -> tuple[str, str | None]:
        if flow is None:
            raise ValueError("OAuth sign-in required; click CONNECT in MCP settings")
        return await flow.callback

    auth = Provider(
        server_url=server["url"],
        client_metadata=OAuthClientMetadata(
            redirect_uris=[config.MCP_OAUTH_CALLBACK_URL],
            client_name="DevForge MCP",
            token_endpoint_auth_method="none",
        ),
        storage=Storage(server),
        redirect_handler=redirect,
        callback_handler=callback,
    )
    # Interactive handlers must never be reused by background loads.
    if flow is None:
        _providers[server["id"]] = (generation, auth)
    return auth


async def start(server: dict[str, Any], reload_tools) -> str | None:
    if server["transport"] != "http":
        raise ValueError("OAuth is only available for HTTP servers")
    previous = _flows.get(server["id"])
    if previous and previous.task and not previous.task.done():
        raise ValueError("OAuth sign-in is already pending for this server")
    prior_oauth = dict(server.get("oauth") or {})
    generation = uuid.uuid4().hex
    mcp_settings.save_oauth(server["id"], {"generation": generation})
    server = mcp_settings.get_server(server["id"])
    loop = asyncio.get_running_loop()
    flow = Flow(loop.create_future(), loop.create_future())
    _flows[server["id"]] = flow

    async def run() -> None:
        from sdlc.services import mcp

        try:
            async with asyncio.timeout(FLOW_TIMEOUT):
                auth = provider(server, flow)
                await mcp._load_tools(server, auth=auth, timeout=FLOW_TIMEOUT)
                if not auth.context.storage.read().get("tokens"):
                    flow.error = "Server did not request OAuth. Use TEST or EDIT to configure an API key."
                    raise ValueError(flow.error)
            mcp_settings.update_server(server["id"], {"enabled": True})
            flow.complete = True
            await reload_tools("MCP OAuth connected")
        except TimeoutError:
            flow.error = "OAuth sign-in timed out. Click CONNECT to try again."
        except asyncio.CancelledError:
            flow.error = "OAuth sign-in cancelled."
        except Exception:
            # Provider errors can contain tokens/codes; never return them to the UI.
            if flow.error is None:
                flow.error = "OAuth connection failed. Try again; check that the provider supports dynamic client registration."
        finally:
            if not flow.complete:
                try:
                    mcp_settings.save_oauth(
                        server["id"], prior_oauth, generation=generation
                    )
                except ValueError:
                    pass  # A concurrent edit/disconnect owns the new credentials.
            if not flow.ready.done():
                flow.ready.set_result(None)

    flow.task = asyncio.create_task(run())
    try:
        return await asyncio.wait_for(asyncio.shield(flow.ready), timeout=25)
    except TimeoutError:
        flow.task.cancel()
        await asyncio.gather(flow.task, return_exceptions=True)
        flow.error = "OAuth discovery timed out; try again"
        raise ValueError(flow.error) from None


def status(server_id: str) -> dict[str, Any]:
    flow = _flows.get(server_id)
    return {
        "pending": bool(flow and flow.task and not flow.task.done()),
        "complete": bool(flow and flow.complete),
        "error": flow.error if flow else None,
    }


async def cancel(server_id: str) -> None:
    flow = _flows.get(server_id)
    if flow and flow.task and not flow.task.done() and not flow.complete:
        flow.task.cancel()
        await asyncio.gather(flow.task, return_exceptions=True)


async def finish(state: str, code: str | None, error: str | None) -> bool:
    for flow in _flows.values():
        if not flow.state or not secrets.compare_digest(
            flow.state.encode(), state.encode()
        ):
            continue
        if flow.callback.done() or not flow.task or flow.task.done():
            break
        flow.state = None  # Consume before any await: callback replay must fail.
        if error or not code:
            flow.error = "OAuth authorization was declined. Click CONNECT to try again."
            flow.callback.set_exception(ValueError("OAuth authorization denied"))
        else:
            flow.callback.set_result((code, state))
        await flow.task
        return flow.complete
    raise ValueError("Invalid or expired OAuth state; connect again")
