# MCP provider authentication

Open the **MCP** tab and assign each server to the specialists that need its tools.

- **OAuth:** click **CONNECT**, sign in and approve access in the popup. Successful connection enables the server and reloads the specialists' tools for the next message. **RECONNECT** starts a fresh sign-in. Use **CANCEL SIGN-IN** to abandon an attempt. Sign-in expires after five minutes; a failed, cancelled or declined attempt preserves previous credentials.
- **API keys / bearer tokens:** click **EDIT**, enter `Authorization: Bearer <token>` or the provider's required header, enable the server and save. Saved values stay hidden. Updating a header replaces it regardless of capitalization; other headers remain saved.
- **Local stdio servers:** use **EDIT** to set the executable, arguments and environment credentials as `KEY: value` lines. OAuth applies to HTTP servers.
- **Disconnect:** open **EDIT** and click **CLEAR**. This removes all headers, environment credentials and OAuth tokens. Changing the server URL or transport also invalidates OAuth tokens. This removes local authorization; revoke the app at the provider to revoke the grant itself.

Use **TEST** to check connectivity and see the tools exposed by a server. A failed server does not prevent other servers or agents from running.

## Callback and persistence

The default callback is `http://localhost:8000/mcp/oauth/callback`. Set `MCP_OAUTH_CALLBACK_URL` in `backend/.env` when the browser reaches the backend at a different address. Use HTTPS for a remote deployment, and allow the exact callback URI at the provider. Do not use the frontend port for this callback.

The OAuth flow uses the MCP SDK for protected-resource discovery, authorization-server discovery, dynamic client registration, state validation and PKCE. Providers must support dynamic registration of public clients. Providers that require a pre-registered client ID/secret need their bearer-token or API-key flow instead; the harness does not configure those OAuth clients.

Tokens, registered client information, expiry and discovery metadata persist in `mcp_settings.json` beside `CHECKPOINT_DB_PATH`. Refresh works during tool discovery and tool calls, including after a backend restart. Token values never appear in API responses. This uses the existing file-based credential store: protect its directory and backups as secrets; it is not encrypted at rest.

Keep the existing single API worker configuration. Pending browser sign-ins are in memory and must be restarted after a backend restart. Completed connections survive restarts. The MCP SDK minor version is constrained because persistence extends its internal OAuth hooks; run `backend/tests/test_mcp_oauth.py` when upgrading it.

This authenticates MCP provider connections. The harness's existing API access controls are unchanged; it does not add application user sign-in.
