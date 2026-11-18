import { describe, it, expect, vi, beforeEach } from "vitest";
import { api, API_BASE } from "../api";

// Mock global fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

beforeEach(() => {
  mockFetch.mockReset();
});

describe("API_BASE", () => {
  it("should point to localhost:8000", () => {
    expect(API_BASE).toBe("http://localhost:8000");
  });
});

describe("api.health", () => {
  it("should call GET /health", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: "ok", container_id: null, container_running: true }),
    });
    const result = await api.health();
    expect(mockFetch.mock.calls[0][0]).toBe(`${API_BASE}/health`);
    expect(result.status).toBe("ok");
  });
});

describe("api.tracing", () => {
  it("should call GET /tracing", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ enabled: false, status: "disabled" }),
    });
    const result = await api.tracing();
    expect(mockFetch.mock.calls[0][0]).toBe(`${API_BASE}/tracing`);
    expect(result.status).toBe("disabled");
  });
});

describe("api.createProject", () => {
  it("should POST to /projects with thread_id", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ project_id: "p1", root: "/ws/p1", status: "created" }),
    });
    const result = await api.createProject("p1", "t1");
    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE}/projects?thread_id=t1`,
      expect.objectContaining({ method: "POST" })
    );
    expect(result.project_id).toBe("p1");
  });
});

describe("api.listArtifacts", () => {
  it("should GET /projects/{id}/artifacts", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ project_id: "p1", artifacts: [] }),
    });
    const result = await api.listArtifacts("p1", "t1");
    expect(mockFetch.mock.calls[0][0]).toBe(
      `${API_BASE}/projects/p1/artifacts?thread_id=t1`
    );
    expect(result.artifacts).toEqual([]);
  });
});

describe("api.getArtifactContent", () => {
  it("should GET /projects/{id}/artifacts/{name}", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        project_id: "p1",
        name: "REQUIREMENTS.md",
        language: "markdown",
        content: "# Reqs",
        size: 10,
      }),
    });
    const result = await api.getArtifactContent("p1", "t1", "REQUIREMENTS.md");
    expect(mockFetch.mock.calls[0][0]).toBe(
      `${API_BASE}/projects/p1/artifacts/REQUIREMENTS.md?thread_id=t1`
    );
    expect(result.content).toBe("# Reqs");
  });
});

describe("api.uploadFiles", () => {
  it("should POST FormData to /upload/{project_id}", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        thread_id: "t1",
        project_id: "p1",
        files: [{ path: "/ws/f.txt", original_name: "f.txt" }],
      }),
    });
    const file = new File(["test"], "f.txt");
    const result = await api.uploadFiles("p1", "t1", [file]);
    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE}/upload/p1?thread_id=t1`,
      expect.objectContaining({ method: "POST" })
    );
    expect(result.files).toHaveLength(1);
  });
});

describe("api.listUploads", () => {
  it("should GET /upload/{project_id}", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ project_id: "p1", thread_id: "t1", files: [] }),
    });
    const result = await api.listUploads("p1", "t1");
    expect(mockFetch.mock.calls[0][0]).toBe(
      `${API_BASE}/upload/p1?thread_id=t1`
    );
  });
});

describe("api.getHistory", () => {
  it("should GET /history/{thread_id}", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ thread_id: "t1", messages: [] }),
    });
    const result = await api.getHistory("t1");
    expect(mockFetch.mock.calls[0][0]).toBe(`${API_BASE}/history/t1`);
  });
});

describe("api.deleteSession", () => {
  it("should DELETE /session/{thread_id}", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: "deleted", detail: "ok" }),
    });
    const result = await api.deleteSession("t1");
    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE}/session/t1`,
      expect.objectContaining({ method: "DELETE" })
    );
  });
});

describe("api.listCustomAgents", () => {
  it("should GET /agents/custom", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ agents: [] }),
    });
    const result = await api.listCustomAgents();
    expect(mockFetch.mock.calls[0][0]).toBe(`${API_BASE}/agents/custom`);
  });
});

describe("api.createCustomAgent", () => {
  it("should POST to /agents/custom", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: "a1", name: "helper", description: "Helper", system_prompt: "prompt", created_at: "now", updated_at: "now" }),
    });
    const result = await api.createCustomAgent({ name: "helper", description: "Helper", system_prompt: "prompt" });
    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE}/agents/custom`,
      expect.objectContaining({ method: "POST" })
    );
    expect(result.name).toBe("helper");
  });
});

describe("api.updateCustomAgent", () => {
  it("should PUT /agents/custom/{id}", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: "a1", name: "helper-v2", description: "Helper", system_prompt: "prompt", created_at: "now", updated_at: "now" }),
    });
    const result = await api.updateCustomAgent("a1", { name: "helper-v2" });
    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE}/agents/custom/a1`,
      expect.objectContaining({ method: "PUT" })
    );
    expect(result.name).toBe("helper-v2");
  });
});

describe("api.deleteCustomAgent", () => {
  it("should DELETE /agents/custom/{id}", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: "deleted", detail: "ok" }),
    });
    const result = await api.deleteCustomAgent("a1");
    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE}/agents/custom/a1`,
      expect.objectContaining({ method: "DELETE" })
    );
  });
});

describe("api.listProjectFiles", () => {
  it("should GET /projects/{id}/files", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ project_id: "p1", path: "", entries: [] }),
    });
    const result = await api.listProjectFiles("p1", "t1");
    expect(mockFetch.mock.calls[0][0]).toBe(
      `${API_BASE}/projects/p1/files?path=&thread_id=t1`
    );
  });
});

describe("api.downloadUrl", () => {
  it("should return a download URL", () => {
    const url = api.downloadUrl("p1", "t1", "REQUIREMENTS.md");
    expect(url).toContain("/projects/p1/download");
    expect(url).toContain("path=REQUIREMENTS.md");
    expect(url).toContain("thread_id=t1");
  });

  it("should include as=pdf when specified", () => {
    const url = api.downloadUrl("p1", "t1", "REQUIREMENTS.md", "pdf");
    expect(url).toContain("as=pdf");
  });
});

describe("api.listConversations", () => {
  it("should GET /conversations", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ conversations: [] }),
    });
    const result = await api.listConversations();
    expect(mockFetch.mock.calls[0][0]).toBe(`${API_BASE}/conversations`);
  });
});

describe("api.createConversation", () => {
  it("should POST /conversations", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: "c1", title: "Test", project_id: "p1", created_at: "now", updated_at: "now", message_count: 0 }),
    });
    const result = await api.createConversation({ id: "c1", title: "Test" });
    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE}/conversations`,
      expect.objectContaining({ method: "POST" })
    );
  });
});

describe("api.patchConversation", () => {
  it("should PATCH /conversations/{id}", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: "c1", title: "Updated", project_id: "p1", created_at: "now", updated_at: "now", message_count: 0 }),
    });
    const result = await api.patchConversation("c1", { title: "Updated" });
    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE}/conversations/c1`,
      expect.objectContaining({ method: "PATCH" })
    );
  });
});

describe("api.deleteConversationRow", () => {
  it("should DELETE /conversations/{id}", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: "deleted", detail: "ok" }),
    });
    const result = await api.deleteConversationRow("c1");
    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE}/conversations/c1`,
      expect.objectContaining({ method: "DELETE" })
    );
  });
});

describe("api.listMessages", () => {
  it("should GET /conversations/{id}/messages", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ conversation_id: "c1", messages: [] }),
    });
    const result = await api.listMessages("c1");
    expect(mockFetch.mock.calls[0][0]).toBe(
      `${API_BASE}/conversations/c1/messages`
    );
  });
});

describe("api.appendMessage", () => {
  it("should POST /conversations/{id}/messages", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: 1, conversation_id: "c1", role: "user", content: "hello", created_at: "now" }),
    });
    const result = await api.appendMessage("c1", { role: "user", content: "hello" });
    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE}/conversations/c1/messages`,
      expect.objectContaining({ method: "POST" })
    );
  });
});

describe("api.replaceMessages", () => {
  it("should PUT /conversations/{id}/messages", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: "replaced", detail: "ok" }),
    });
    const result = await api.replaceMessages("c1", [{ role: "user", content: "hello" }]);
    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE}/conversations/c1/messages`,
      expect.objectContaining({ method: "PUT" })
    );
  });
});

describe("API error handling", () => {
  it("should throw on non-ok response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      text: async () => "Not found",
    });
    await expect(api.health()).rejects.toThrow("404: Not found");
  });
});
