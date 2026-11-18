import { describe, it, expect } from "vitest";
import type {
  ChatMessage,
  ToolCallInfo,
  Conversation,
  ProjectInfo,
  TracingStatus,
  HealthStatus,
  UploadedFile,
  LocalUpload,
  TodoItemInfo,
  SubagentInfo,
  ReasoningEntry,
  ArtifactContent,
  CustomAgent,
  CustomAgentCreate,
  CustomAgentUpdate,
  ProjectFileListResponse,
  ConversationSummary,
  ConversationCreate,
  StoredMessage,
  MessageAppend,
} from "../types";

describe("Type definitions", () => {
  it("ChatMessage should be constructable", () => {
    const msg: ChatMessage = {
      id: "msg-1",
      role: "user",
      content: "Hello",
      timestamp: Date.now(),
    };
    expect(msg.id).toBe("msg-1");
    expect(msg.role).toBe("user");
  });

  it("ChatMessage should support optional fields", () => {
    const msg: ChatMessage = {
      id: "msg-2",
      role: "assistant",
      content: "Hi",
      timestamp: 1000,
      agentName: "Architecture",
      traceUrl: "https://smith.langchain.com/traces/abc",
      toolCalls: [],
      attachments: [{ name: "file.txt", path: "/workspace/file.txt" }],
    };
    expect(msg.agentName).toBe("Architecture");
    expect(msg.attachments).toHaveLength(1);
  });

  it("ToolCallInfo should be constructable", () => {
    const tc: ToolCallInfo = {
      toolId: "t1",
      toolName: "write_file",
      toolArgs: '{"file_path": "/test.md"}',
    };
    expect(tc.toolName).toBe("write_file");
  });

  it("Conversation should be constructable", () => {
    const conv: Conversation = {
      id: "c1",
      title: "Test Chat",
      createdAt: 1000,
      updatedAt: 1000,
      projectId: "p1",
      messageCount: 5,
    };
    expect(conv.title).toBe("Test Chat");
  });

  it("ProjectInfo should be constructable", () => {
    const info: ProjectInfo = {
      project_id: "p1",
      root: "/workspace/project_p1",
      status: "created",
    };
    expect(info.project_id).toBe("p1");
  });

  it("TracingStatus should be constructable", () => {
    const status: TracingStatus = {
      enabled: false,
      project: "",
      endpoint: "",
      status: "disabled",
      api_key_set: false,
    };
    expect(status.status).toBe("disabled");
  });

  it("HealthStatus should be constructable", () => {
    const health: HealthStatus = {
      status: "ok",
      container_id: null,
      container_running: true,
    };
    expect(health.status).toBe("ok");
  });

  it("UploadedFile should be constructable", () => {
    const file: UploadedFile = {
      path: "/workspace/uploads/test.txt",
      originalName: "test.txt",
    };
    expect(file.originalName).toBe("test.txt");
  });

  it("LocalUpload should support all three kinds", () => {
    const pending: LocalUpload = { kind: "pending", localId: "l1", name: "f.txt", size: 100 };
    expect(pending.kind).toBe("pending");

    const ready: LocalUpload = {
      kind: "ready",
      localId: "l1",
      path: "/workspace/f.txt",
      original_name: "f.txt",
      size: 100,
    };
    expect(ready.kind).toBe("ready");

    const error: LocalUpload = { kind: "error", localId: "l1", name: "f.txt", message: "Failed" };
    expect(error.kind).toBe("error");
  });

  it("TodoItemInfo should be constructable", () => {
    const todo: TodoItemInfo = { content: "Fix bug", status: "in_progress" };
    expect(todo.status).toBe("in_progress");
  });

  it("SubagentInfo should be constructable", () => {
    const sa: SubagentInfo = {
      name: "architecture",
      path: ["orchestrator", "architecture"],
      status: "completed",
      messages: [],
      toolCalls: [],
    };
    expect(sa.name).toBe("architecture");
  });

  it("ReasoningEntry should be constructable", () => {
    const entry: ReasoningEntry = {
      agent: "",
      content: "Step 1: Think...",
      source: "model",
      ts: Date.now(),
    };
    expect(entry.source).toBe("model");
  });

  it("ArtifactContent should be constructable", () => {
    const ac: ArtifactContent = {
      project_id: "p1",
      name: "REQUIREMENTS.md",
      language: "markdown",
      content: "# Requirements",
      size: 100,
    };
    expect(ac.language).toBe("markdown");
  });

  it("CustomAgent should be constructable", () => {
    const ca: CustomAgent = {
      id: "a1",
      name: "helper",
      description: "Helper agent",
      system_prompt: "Be helpful",
      tools: [],
      created_at: "now",
      updated_at: "now",
    };
    expect(ca.name).toBe("helper");
  });

  it("CustomAgentCreate should be constructable", () => {
    const cac: CustomAgentCreate = {
      name: "helper",
      description: "Helper",
      system_prompt: "Be helpful",
    };
    expect(cac.name).toBe("helper");
  });

  it("CustomAgentUpdate should be constructable", () => {
    const cau: CustomAgentUpdate = { name: "helper-v2" };
    expect(cau.name).toBe("helper-v2");
  });

  it("ProjectFileListResponse should be constructable", () => {
    const pflr: ProjectFileListResponse = {
      project_id: "p1",
      path: "",
      entries: [{ name: "file.txt", type: "file", size: 100, mtime: 1000 }],
    };
    expect(pflr.entries).toHaveLength(1);
  });

  it("ConversationSummary should be constructable", () => {
    const cs: ConversationSummary = {
      id: "c1",
      title: "Test",
      project_id: "p1",
      created_at: "now",
      updated_at: "now",
      message_count: 0,
    };
    expect(cs.id).toBe("c1");
  });

  it("ConversationCreate should be constructable", () => {
    const cc: ConversationCreate = { id: "c1", title: "Test" };
    expect(cc.title).toBe("Test");
  });

  it("StoredMessage should be constructable", () => {
    const sm: StoredMessage = {
      id: 1,
      conversation_id: "c1",
      role: "user",
      content: "hello",
      agent_name: null,
      trace_url: null,
      tool_calls: null,
      attachments: null,
      reasoning: null,
      created_at: "now",
    };
    expect(sm.role).toBe("user");
  });

  it("MessageAppend should be constructable", () => {
    const ma: MessageAppend = {
      role: "assistant",
      content: "hi",
      agent_name: "Architecture",
    };
    expect(ma.agent_name).toBe("Architecture");
  });
});
