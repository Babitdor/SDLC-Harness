import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import McpPanel from "../McpPanel";

const listMcpServers = vi.fn();
const createMcpServer = vi.fn();
const updateMcpServer = vi.fn();
const deleteMcpServer = vi.fn();
const testMcpServer = vi.fn();
const restoreMcpPresets = vi.fn();
const connectMcpOAuth = vi.fn();
const mcpOAuthStatus = vi.fn();
const cancelMcpOAuth = vi.fn();

vi.mock("../../lib/api", () => ({
  api: {
    connectMcpOAuth: (id: string) => connectMcpOAuth(id),
    mcpOAuthStatus: (id: string) => mcpOAuthStatus(id),
    cancelMcpOAuth: (id: string) => cancelMcpOAuth(id),
    listMcpServers: () => listMcpServers(),
    createMcpServer: (body: unknown) => createMcpServer(body),
    updateMcpServer: (id: string, body: unknown) => updateMcpServer(id, body),
    deleteMcpServer: (id: string) => deleteMcpServer(id),
    testMcpServer: (id: string) => testMcpServer(id),
    restoreMcpPresets: () => restoreMcpPresets(),
  },
}));

const SERVER = {
  id: "abc12345",
  name: "github",
  description: "Read the existing repo + workflows. Needs a PAT with repo scope.",
  credential_hint: "Authorization: Bearer <PAT>",
  transport: "http" as const,
  enabled: true,
  command: "",
  args: [],
  url: "https://api.githubcopilot.com/mcp/",
  agents: ["architecture", "devops"],
  env_keys: [],
  header_keys: ["Authorization"],
};

function respond(overrides: Partial<Record<string, unknown>> = {}) {
  listMcpServers.mockResolvedValue({
    servers: [SERVER],
    adapter_available: true,
    adapter_error: null,
    status: [
      {
        server_id: "abc12345",
        name: "github",
        ok: true,
        tools: ["search_repositories", "get_file_contents"],
        error: null,
        checked_at: 1,
        latency_ms: 42,
      },
    ],
    ...overrides,
  });
}

beforeEach(() => {
  vi.restoreAllMocks();
  vi.clearAllMocks();
  respond();
});

describe("McpPanel", () => {
  it("cancels a pending OAuth sign-in", async () => {
    const popup = { opener: window, location: { replace: vi.fn() }, close: vi.fn() };
    vi.spyOn(window, "open").mockReturnValue(popup as unknown as Window);
    connectMcpOAuth.mockResolvedValue({ authorization_url: "https://auth.test/authorize", pending: true, complete: false, error: null });
    mcpOAuthStatus.mockResolvedValue({ pending: true, complete: false, error: null });
    cancelMcpOAuth.mockResolvedValue({ cancelled: true });
    render(<McpPanel active={true} />);
    fireEvent.click(await screen.findByText("CONNECT"));
    fireEvent.click(await screen.findByText("CANCEL SIGN-IN"));
    await waitFor(() => expect(cancelMcpOAuth).toHaveBeenCalledWith(SERVER.id));
    await waitFor(() => expect(screen.queryByText("CANCEL SIGN-IN")).toBeNull());
  });

  it("rejects malformed credentials instead of silently dropping them", async () => {
    render(<McpPanel active={true} />);
    fireEvent.click(await screen.findByText("EDIT"));
    fireEvent.change(screen.getByLabelText("Credentials"), { target: { value: "Bearer missing-key" } });
    fireEvent.click(screen.getByText("SAVE"));
    expect(await screen.findByText(/Use KEY: value/)).toBeTruthy();
    expect(updateMcpServer).not.toHaveBeenCalled();
  });

  it("opens OAuth sign-in and refreshes after completion", async () => {
    const popup = { opener: window, location: { replace: vi.fn() }, close: vi.fn() };
    vi.spyOn(window, "open").mockReturnValue(popup as unknown as Window);
    connectMcpOAuth.mockResolvedValue({ authorization_url: "https://auth.test/authorize", pending: true, complete: false, error: null });
    mcpOAuthStatus.mockResolvedValue({ pending: false, complete: true, error: null });
    render(<McpPanel active={true} />);
    fireEvent.click(await screen.findByText("CONNECT"));
    await waitFor(() => expect(popup.location.replace).toHaveBeenCalledWith("https://auth.test/authorize"));
    expect(popup.opener).toBeNull();
    await waitFor(() => expect(mcpOAuthStatus).toHaveBeenCalledWith(SERVER.id), { timeout: 3000 });
    await waitFor(() => expect(listMcpServers.mock.calls.length).toBeGreaterThan(1));
  });

  it("explains blocked popups without starting a flow", async () => {
    vi.spyOn(window, "open").mockReturnValue(null);
    render(<McpPanel active={true} />);
    fireEvent.click(await screen.findByText("CONNECT"));
    expect(await screen.findByText(/Allow popups/)).toBeTruthy();
    expect(connectMcpOAuth).not.toHaveBeenCalled();
  });

  it("can clear OAuth credentials without exposing tokens", async () => {
    respond({ servers: [{ ...SERVER, header_keys: [], oauth_connected: true }] });
    updateMcpServer.mockResolvedValue({ ...SERVER, oauth_connected: false });
    render(<McpPanel active={true} />);
    expect(await screen.findByText("RECONNECT")).toBeTruthy();
    fireEvent.click(screen.getByText("EDIT"));
    expect(screen.getByText("OAuth ✓")).toBeTruthy();
    fireEvent.click(screen.getByText("CLEAR"));
    await waitFor(() => expect(updateMcpServer).toHaveBeenCalledWith(SERVER.id, { clear_credentials: true }));
  });

  it("renders the panel header", () => {
    render(<McpPanel active={true} />);
    expect(screen.getByText("MCP CONNECTIONS")).toBeTruthy();
  });

  it("does not fetch while inactive", () => {
    render(<McpPanel active={false} />);
    expect(listMcpServers).not.toHaveBeenCalled();
  });

  it("shows a stored server with its loaded tools and phase chips", async () => {
    render(<McpPanel active={true} />);

    expect(await screen.findByText("github")).toBeTruthy();
    expect(screen.getByText(/2 tools/)).toBeTruthy();
    // Assigned agents render with their roster names.
    expect(screen.getByText("Architecture")).toBeTruthy();
    expect(screen.getByText("DevOps")).toBeTruthy();
  });

  it("warns when the adapter package is missing", async () => {
    respond({ adapter_available: false, adapter_error: "No module named 'langchain_mcp_adapters'" });
    render(<McpPanel active={true} />);

    expect(await screen.findByText(/MCP ADAPTER MISSING/)).toBeTruthy();
  });

  it("opens the create form and saves a paste of URL plus headers", async () => {
    createMcpServer.mockResolvedValue({ ...SERVER, id: "newid" });
    render(<McpPanel active={true} />);

    fireEvent.click(await screen.findByText("+ ADD SERVER"));
    fireEvent.change(screen.getByLabelText("Server name"), { target: { value: "postman" } });
    fireEvent.change(screen.getByLabelText("Server URL"), {
      target: { value: "https://mcp.postman.com/mcp" },
    });
    fireEvent.change(screen.getByLabelText("Credentials"), {
      target: { value: "Authorization: Bearer tok" },
    });
    fireEvent.click(screen.getByText("SAVE"));

    await waitFor(() => expect(createMcpServer).toHaveBeenCalled());
    const body = createMcpServer.mock.calls[0][0];
    expect(body).toMatchObject({
      name: "postman",
      transport: "http",
      url: "https://mcp.postman.com/mcp",
      headers: { Authorization: "Bearer tok" },
      env: {},
    });
  });

  it("keeps stored credentials when the box is left empty on edit", async () => {
    updateMcpServer.mockResolvedValue(SERVER);
    render(<McpPanel active={true} />);

    fireEvent.click(await screen.findByText("EDIT"));
    fireEvent.change(screen.getByLabelText("Server name"), { target: { value: "github-renamed" } });
    fireEvent.click(screen.getByText("SAVE"));

    await waitFor(() => expect(updateMcpServer).toHaveBeenCalled());
    const [id, body] = updateMcpServer.mock.calls[0];
    expect(id).toBe("abc12345");
    expect(body).toMatchObject({ name: "github-renamed" });
    expect(body.headers).toBeUndefined();
  });

  it("surfaces a failed connection test", async () => {
    testMcpServer.mockResolvedValue({
      ok: false,
      tools: [],
      error: "RuntimeError: 401 unauthorized",
      latency_ms: 12,
    });
    render(<McpPanel active={true} />);

    fireEvent.click(await screen.findByText("TEST"));
    expect(await screen.findByText(/401 unauthorized/)).toBeTruthy();
  });
  it("renders the catalog description for a server", async () => {
    render(<McpPanel active={true} />);
    expect(await screen.findByText(/Needs a PAT with repo scope/)).toBeTruthy();
  });

  it("flags an unauthenticated http preset with AUTH", async () => {
    respond({
      servers: [
        {
          ...SERVER,
          enabled: false,
          header_keys: [],
          name: "atlassian",
          description: "Confluence + Jira. Needs an OAuth bearer token.",
        },
      ],
      status: [],
    });
    render(<McpPanel active={true} />);

    expect(await screen.findByText("atlassian")).toBeTruthy();
    expect(screen.getByText("AUTH")).toBeTruthy();
  });

  it("shows the credential hint and the saved keys when editing", async () => {
    render(<McpPanel active={true} />);

    fireEvent.click(await screen.findByText("EDIT"));
    const box = screen.getByLabelText("Credentials") as HTMLTextAreaElement;
    expect(box.getAttribute("placeholder")).toBe("Authorization: Bearer <PAT>");
    // Values are write-only; only the key name comes back from the API.
    expect(screen.getByText("Authorization ✓")).toBeTruthy();
  });

  it("sends a merge patch for the typed key only", async () => {
    updateMcpServer.mockResolvedValue(SERVER);
    render(<McpPanel active={true} />);

    fireEvent.click(await screen.findByText("EDIT"));
    fireEvent.change(screen.getByLabelText("Credentials"), {
      target: { value: "Authorization: Bearer gh_new" },
    });
    fireEvent.click(screen.getByText("SAVE"));

    await waitFor(() => expect(updateMcpServer).toHaveBeenCalled());
    const [, body] = updateMcpServer.mock.calls[0];
    expect(body.headers).toEqual({ Authorization: "Bearer gh_new" });
  });

  it("clears every stored credential on CLEAR", async () => {
    updateMcpServer.mockResolvedValue({ ...SERVER, header_keys: [] });
    render(<McpPanel active={true} />);

    fireEvent.click(await screen.findByText("EDIT"));
    fireEvent.click(screen.getByText("CLEAR"));

    await waitFor(() => expect(updateMcpServer).toHaveBeenCalled());
    expect(updateMcpServer).toHaveBeenCalledWith("abc12345", { clear_credentials: true });
  });

  it("restores the preset catalog on demand", async () => {
    restoreMcpPresets.mockResolvedValue([]);
    render(<McpPanel active={true} />);

    fireEvent.click(await screen.findByText("RESTORE CATALOG"));
    await waitFor(() => expect(restoreMcpPresets).toHaveBeenCalled());
  });
});
