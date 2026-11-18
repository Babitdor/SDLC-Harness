"use client";

import { startTransition, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  type ImperativePanelHandle,
  Panel,
  PanelGroup,
  PanelResizeHandle,
} from "react-resizable-panels";
import { settleRunningToolCalls, toolIdsIn } from "../lib/toolActivity";
import ChatMessage from "../components/ChatMessage";
import ChatInput from "../components/ChatInput";
import TypingIndicator from "../components/TypingIndicator";
import ChatSidebar, { type SidebarTab } from "../components/ChatSidebar";
import InspectorPanel from "../components/InspectorPanel";
import ArtifactCanvas from "../components/ArtifactCanvas";
import SkillCanvas from "../components/SkillCanvas";
import SubagentCard from "../components/SubagentCard";
import TodoList from "../components/TodoList";
import AppNav from "../components/AppNav";
import AuthGate from "../components/AuthGate";
import ArtifactsMenu from "../components/ArtifactsMenu";
import { useSSE } from "../hooks/useSSE";
import { useHealthCheck } from "../hooks/useHealthCheck";
import { api } from "../lib/api";
import type { ArtifactInfo } from "../lib/agents";
import type {
  ChatMessage as ChatMessageType,
  Conversation,
  LocalUpload,
  ArtifactContent,
  SubagentInfo,
  ToolCallInfo,
  TodoItemInfo,
} from "../lib/types";
import type { TodoItem } from "../components/TodoList";

// ── Helpers ────────────────────────────────────────────────────────────

function nextId() {
  // Collision-free across page reloads and conversation switches. A
  // module-level counter restarted at 0 on refresh and clashed with
  // message IDs hydrated from localStorage (e.g. two `msg-2`).
  return `msg-${crypto.randomUUID()}`;
}

const STORAGE_KEY_CONVERSATIONS = "sdlc_conversations";
const STORAGE_KEY_MESSAGES_PREFIX = "sdlc_messages_";
const STORAGE_KEY_ACTIVE_ID = "sdlc_active_conversation";
const STORAGE_KEY_SIDEBAR_COLLAPSED = "sdlc_sidebar_collapsed";

function loadConversations(): Conversation[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY_CONVERSATIONS);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveConversations(convs: Conversation[]) {
  try {
    localStorage.setItem(STORAGE_KEY_CONVERSATIONS, JSON.stringify(convs));
  } catch { /* quota exceeded, ignore */ }
}

function loadMessages(threadId: string): ChatMessageType[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY_MESSAGES_PREFIX + threadId);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveMessages(threadId: string, msgs: ChatMessageType[]) {
  try {
    localStorage.setItem(
      STORAGE_KEY_MESSAGES_PREFIX + threadId,
      JSON.stringify(msgs)
    );
  } catch { /* ignore */ }
}

function removeMessages(threadId: string) {
  try {
    localStorage.removeItem(STORAGE_KEY_MESSAGES_PREFIX + threadId);
  } catch { /* ignore */ }
}

function autoTitle(text: string): string {
  // Take first few words of the first user message as title
  const words = text.trim().split(/\s+/).slice(0, 6);
  const title = words.join(" ");
  return title.length > 40 ? title.slice(0, 40) + "\u2026" : title;
}

/**
 * Apply a tool_result SSE event to the matching ToolCallInfo.
 *
 * First tries an exact id match. If that fails (some gateways reassign
 * tool_call_ids between streaming chunks) we fall back to the earliest
 * still-running tool with the same name and no result yet.
 */
function applyToolResult(
  toolCalls: ToolCallInfo[],
  toolId: string,
  toolName: string,
  content: string,
): ToolCallInfo[] {
  const trimmedId = toolId.trim();
  const exactIndex = trimmedId
    ? toolCalls.findIndex((tc) => tc.toolId === trimmedId)
    : -1;

  if (exactIndex !== -1) {
    return toolCalls.map((tc, i) =>
      i === exactIndex
        ? { ...tc, result: (tc.result || "") + content, isRunning: false }
        : tc,
    );
  }

  // Fallback for id mismatches: earliest still-running tool of the same
  // name without a result yet.
  for (let i = 0; i < toolCalls.length; i++) {
    const tc = toolCalls[i];
    if (tc.toolName === toolName && tc.isRunning && !tc.result) {
      if (typeof window !== "undefined") {
        // eslint-disable-next-line no-console
        console.warn(
          `[applyToolResult] fallback matched ${toolName} (requested id=${toolId}, found id=${tc.toolId})`,
        );
      }
      return toolCalls.map((tc2, j) =>
        j === i
          ? { ...tc2, result: (tc2.result || "") + content, isRunning: false }
          : tc2,
      );
    }
  }

  if (typeof window !== "undefined") {
    // eslint-disable-next-line no-console
    console.warn(
      `[applyToolResult] no match for ${toolName} (id=${toolId}); active tool calls:`,
      toolCalls,
    );
  }
  return toolCalls;
}

// \u2500\u2500 Persistence boundary helpers \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
// The chat tree renders ChatMessageType / Conversation. The backend talks
// in ConversationSummary / StoredMessage / MessageAppend with wire-shape
// role names. Translate at the edge so the render tree stays unchanged.

const STORAGE_KEY_MIGRATED = "sdlc_localstorage_migrated";

function toRenderRole(role: string): ChatMessageType["role"] {
  if (role === "human" || role === "user") return "user";
  if (role === "ai" || role === "assistant") return "assistant";
  return "system";
}

function toWireRole(role: ChatMessageType["role"]): string {
  if (role === "user") return "human";
  if (role === "assistant") return "ai";
  return "system";
}

function storedToMessage(m: import("../lib/types").StoredMessage): ChatMessageType {
  return {
    id: `msg-db-${m.id}`,
    role: toRenderRole(m.role),
    content: m.content || "",
    agentName: m.agent_name ?? undefined,
    traceUrl: m.trace_url ?? undefined,
    timestamp: m.created_at ? Date.parse(m.created_at) : Date.now(),
    toolCalls: m.tool_calls ?? undefined,
    attachments: m.attachments ?? undefined,
    reasoning: m.reasoning ?? undefined,
  };
}

// Eagerly provision a chat's Docker sandbox + project workspace so it exists
// the moment a fresh/untitled thread appears — rather than lazily on the first
// message. Reuses POST /projects (which calls _get_or_create_session, creating
// the container, then inits the workspace) so it also warms first-message
// latency. Fire-and-forget: failure is non-fatal — sending a message
// re-provisions the same container by deterministic name.
function ensureSandbox(threadId: string, projectId = "default") {
  api.createProject(projectId, threadId).catch((e) =>
    console.warn(`ensureSandbox(${threadId}) failed:`, e),
  );
}

function summaryToConversation(s: import("../lib/types").ConversationSummary): Conversation {
  return {
    id: s.id,
    title: s.title,
    createdAt: Date.parse(s.created_at),
    updatedAt: Date.parse(s.updated_at),
    projectId: s.project_id,
    messageCount: s.message_count,
  };
}

function messageToWire(m: ChatMessageType): import("../lib/types").MessageAppend {
  return {
    role: toWireRole(m.role),
    content: m.content,
    agent_name: m.agentName ?? null,
    trace_url: m.traceUrl ?? null,
    tool_calls: m.toolCalls ?? null,
    attachments: m.attachments ?? null,
    reasoning: m.reasoning ?? null,
  };
}

const SUBAGENT_TYPE_RE = /"subagent_type"\s*:\s*"([^"]+)"/;

interface ProcessedHistory {
  mainMessages: ChatMessageType[];
  subagents: Map<string, SubagentInfo>;
  todos: TodoItem[];
}

/**
 * Should we re-attach to a possibly-live backend run for this thread?
 *
 * Both entry points — first mount and switchConversation — answer this, and
 * they used to answer it differently (mount inferred from the message tail,
 * switch consulted the in-flight set). The disagreement is what let the
 * stuck-"WORKING" bug hide: only one of the two paths cleaned up after
 * itself.
 *
 * `inFlight` is in-memory, so it is empty after a refresh and cannot be the
 * whole test. The message tail is the durable signal: the backend persists
 * the assistant turn when a run ends, so a tail that is NOT an assistant
 * message means the run either never finished or never started. Resuming
 * when nothing is live is cheap — the endpoint replies with a single `done`.
 */
/**
 * Everything that belongs to ONE chat thread.
 *
 * This used to be three top-level useStates shared by whichever thread was
 * on screen. That single fact produced most of the streaming bugs in this
 * file: a background run's events had nowhere of their own to land, so they
 * wrote into the visible thread's state and had to be fenced off by
 * `stillOnThread()` checks at every handler — checks that ran when an event
 * arrived but not when the batched update actually flushed, so they leaked
 * anyway. Switching threads also had to blank the transcript and refetch,
 * because there was nothing to switch *to*.
 *
 * Keyed per thread, a run writes to its own slot whether or not it is
 * visible, switching is a map lookup, and cross-thread contamination stops
 * being possible rather than being guarded against.
 */
interface ThreadState {
  messages: ChatMessageType[];
  subagents: Map<string, SubagentInfo>;
  todos: TodoItem[];
}

const EMPTY_THREAD: ThreadState = Object.freeze({
  messages: [],
  subagents: new Map<string, SubagentInfo>(),
  todos: [],
}) as ThreadState;

/** Apply `fn` to one thread's slot, leaving every other thread untouched. */
function updateThread(
  threads: Map<string, ThreadState>,
  id: string,
  fn: (t: ThreadState) => ThreadState,
): Map<string, ThreadState> {
  const cur = threads.get(id) ?? { messages: [], subagents: new Map(), todos: [] };
  const next = fn(cur);
  if (next === cur) return threads; // no-op updates must not re-render
  const out = new Map(threads);
  out.set(id, next);
  return out;
}

export function shouldResume(
  messages: ChatMessageType[],
  threadId: string,
  inFlight: Set<string>,
): boolean {
  if (inFlight.has(threadId)) return true;
  if (messages.length === 0) return false;
  return messages[messages.length - 1].role !== "assistant";
}

function processMessageHistory(allMessages: ChatMessageType[]): ProcessedHistory {
  const mainMessages = allMessages.filter((m) => !m.agentName);
  const subagents = new Map<string, SubagentInfo>();
  let todos: TodoItem[] = [];

  // Find the index of the last user message to locate the latest turn's boundaries.
  let lastUserIdx = -1;
  for (let i = mainMessages.length - 1; i >= 0; i--) {
    if (mainMessages[i].role === "user") {
      lastUserIdx = i;
      break;
    }
  }

  // Get the timestamp of the last user message to filter subagent messages belonging to the latest turn.
  const lastUserTimestamp = lastUserIdx >= 0 ? mainMessages[lastUserIdx].timestamp : 0;

  // Process all messages in history
  for (const m of allMessages) {
    if (m.agentName) {
      // Reconstruct subagents only if they belong to the latest turn (after last user message timestamp)
      if (m.timestamp >= lastUserTimestamp) {
        const sName = m.agentName;
        if (!subagents.has(sName)) {
          subagents.set(sName, {
            name: sName,
            path: [sName],
            status: "completed", // assume completed for loaded historical runs
            messages: [],
            toolCalls: [],
            todos: [],
          });
        }
        const sInfo = subagents.get(sName)!;
        if (m.role === "assistant") {
          sInfo.messages.push({
            role: "assistant",
            content: m.content,
            reasoning: m.reasoning,
          });
        }
        if (m.toolCalls) {
          for (const tc of m.toolCalls) {
            if (tc.toolName === "write_todos") {
              try {
                const parsed = JSON.parse(tc.toolArgs || "{}");
                if (parsed.todos) {
                  sInfo.todos = parsed.todos as TodoItemInfo[];
                }
              } catch {}
            }
            sInfo.toolCalls.push(tc);
          }
        }
      }
    } else {
      // Main message
      // Inspect tool calls of the latest turn for "task" spawning or "write_todos"
      if (m.timestamp >= lastUserTimestamp && m.toolCalls) {
        for (const tc of m.toolCalls) {
          if (tc.toolName === "task") {
            let sType = "";
            let taskDesc = "";
            try {
              const parsed = JSON.parse(tc.toolArgs || "{}");
              sType = parsed.subagent_type || "";
              taskDesc = parsed.task || "";
            } catch {
              const match = tc.toolArgs?.match(SUBAGENT_TYPE_RE);
              if (match) sType = match[1];
              const taskMatch = tc.toolArgs?.match(/"task"\s*:\s*"([^"]+)"/);
              if (taskMatch) taskDesc = taskMatch[1];
            }
            if (sType) {
              if (!subagents.has(sType)) {
                subagents.set(sType, {
                  name: sType,
                  path: [sType],
                  status: "completed",
                  messages: [],
                  toolCalls: [],
                  todos: [],
                });
              }
              const sInfo = subagents.get(sType)!;
              sInfo.task = taskDesc;
            }
          } else if (tc.toolName === "write_todos") {
            try {
              const parsed = JSON.parse(tc.toolArgs || "{}");
              if (parsed.todos) {
                todos = parsed.todos as TodoItem[];
              }
            } catch {}
          }
        }
      }
    }
  }

  return { mainMessages, subagents, todos };
}

/**
 * One-time pass: upload any conversations + messages still in localStorage
 * to the backend so the cutover doesn't lose history. Idempotent \u2014 the
 * STORAGE_KEY_MIGRATED flag is set on success so subsequent loads skip
 * the work entirely.
 *
 * Failures are logged but non-fatal \u2014 the user can still chat against an
 * empty backend; only their old history is lost. We never delete the
 * localStorage entries here (only the flag flips), so a future code path
 * can re-migrate if needed.
 */
async function migrateLocalStorageOnce(): Promise<void> {
  if (typeof window === "undefined") return;
  if (localStorage.getItem(STORAGE_KEY_MIGRATED) === "1") return;

  const localConvs = loadConversations();
  if (localConvs.length === 0) {
    localStorage.setItem(STORAGE_KEY_MIGRATED, "1");
    return;
  }

  // Existing rows on the server \u2014 skip them to avoid duplicate-id 409s.
  let existingIds = new Set<string>();
  try {
    const remote = await api.listConversations();
    existingIds = new Set(remote.conversations.map((c) => c.id));
  } catch (e) {
    console.warn("migrateLocalStorageOnce: could not list remote conversations", e);
    return; // try again next load
  }

  for (const conv of localConvs) {
    if (existingIds.has(conv.id)) continue;
    try {
      await api.createConversation({
        id: conv.id,
        title: conv.title,
        project_id: conv.projectId,
      });
      const msgs = loadMessages(conv.id);
      if (msgs.length > 0) {
        await api.replaceMessages(conv.id, msgs.map(messageToWire));
      }
    } catch (e) {
      console.warn(`migrateLocalStorageOnce: skipping ${conv.id}:`, e);
    }
  }

  localStorage.setItem(STORAGE_KEY_MIGRATED, "1");
}

function HarnessApp() {
  // ── Conversation state ─────────────────────────────────────────────
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [threads, setThreads] = useState<Map<string, ThreadState>>(new Map());
  // Tool-call ids already present in a thread's *hydrated* transcript (loaded
  // from Postgres, or settled by a previous run). A resumed run re-emits the
  // interrupted work with fresh message ids but stable tool-call ids, so this
  // is the only identity that survives a restart.
  //
  // A ref, not state: the stream callbacks run outside React's render cycle
  // and must answer "does this thread already hold this call?" at the moment
  // the event arrives, which a closure over `threads` cannot do.
  const hydratedToolIdsRef = useRef<Map<string, Set<string>>>(new Map());
  // Single-project app — backend calls take a project_id but the UI
  // never surfaces multiple projects. Auto-init happens on first
  // /artifacts call (see refreshArtifacts effect below).
  const projectId = "default";
  const [uploadedFiles, setUploadedFiles] = useState<LocalUpload[]>([]);
  const [artifacts, setArtifacts] = useState<ArtifactInfo[]>([]);
  const [selectedArtifact, setSelectedArtifact] = useState<string | null>(null);
  const [selectedSkill, setSelectedSkill] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  // Desktop-only: rail mode. Mobile uses `sidebarOpen` for slide-in.
  // Start with the SSR-safe default and hydrate from localStorage AFTER
  // mount — reading storage inside useState's initializer causes a
  // server/client divergence and Next 15 errors out on hydration.
  // `hydrated` gates the persist effect so the very first effect tick
  // (which would write back the default `false`) can't clobber the
  // stored preference before we've read it.
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [hydratedSidebar, setHydratedSidebar] = useState(false);
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY_SIDEBAR_COLLAPSED);
    if (stored === "1") setSidebarCollapsed(true);
    setHydratedSidebar(true);
  }, []);
  useEffect(() => {
    if (!hydratedSidebar) return;
    localStorage.setItem(
      STORAGE_KEY_SIDEBAR_COLLAPSED,
      sidebarCollapsed ? "1" : "0"
    );
  }, [sidebarCollapsed, hydratedSidebar]);

  // ── Resizable panels — desktop only ────────────────────────────────
  //
  // The desktop layout uses react-resizable-panels for sidebar / artifact
  // canvas / inspector / main split. On mobile (< lg) the original flex
  // layout is used — ChatSidebar's fixed-position slide-in handles itself.
  //
  // `isDesktop` starts false so SSR renders the mobile branch (safe
  // fallback). The effect promotes to desktop on mount when matchMedia
  // says so, and listens for viewport changes.
  const [isDesktop, setIsDesktop] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 1024px)");
    setIsDesktop(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsDesktop(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  // When the sidebar is collapsed on desktop, the rail (56px) renders
  // OUTSIDE the PanelGroup as a fixed-width column — no resize handle,
  // no draggable Panel. When expanded, the sidebar lives inside the
  // PanelGroup as a resizable Panel. So the collapse toggle is just a
  // state flip; the layout structure handles the size change.
  const sidebarPanelRef = useRef<ImperativePanelHandle | null>(null);
  const toggleSidebarCollapsed = useCallback(() => {
    setSidebarCollapsed((prev) => !prev);
  }, []);

  const [inspectorOpen, setInspectorOpen] = useState(false);
  // Sidebar section. Lives here because the tab buttons moved into AppNav;
  // the sidebar itself only renders the body for the selected section.
  const [activeTab, setActiveTab] = useState<SidebarTab>("threads");
  const [compacting, setCompacting] = useState(false);

  // ── SSE streaming ──────────────────────────────────────────────────
  const { streamingThreads, isStreaming, send, subscribe, abort, forgetThreadSeq } =
    useSSE();

  // ── Views onto the active thread ─────────────────────────────────
  // Every existing read site keeps working unchanged; only writes had to
  // learn which thread they belong to.
  const active: ThreadState = (activeId && threads.get(activeId)) || EMPTY_THREAD;
  const messages = active.messages;
  const subagents = active.subagents;
  // Derived once per subagent change instead of inline at the call site.
  // `Array.from(subagents.values())` in JSX allocated a fresh array on every
  // render, so `memo(SimpleActivityFeed)` never matched and the whole feed
  // re-rendered on every streamed token.
  const subagentList = useMemo(
    () => Array.from(subagents.values()),
    [subagents],
  );
  const todos = active.todos;

  // Writers. Each takes the thread it belongs to, so a background run
  // updates its own slot instead of whatever happens to be on screen.
  const setThreadMessages = useCallback(
    (id: string, fn: (prev: ChatMessageType[]) => ChatMessageType[]) => {
      setThreads((prev) =>
        updateThread(prev, id, (t) => {
          const next = fn(t.messages);
          return next === t.messages ? t : { ...t, messages: next };
        }),
      );
    },
    [],
  );


  /**
   * Replace a thread's slot with state loaded from postgres.
   *
   * Refuses when that thread has an open stream. The assistant turn is only
   * persisted when a run ENDS, so a hydrate landing mid-run replaces live
   * streamed output with an older snapshot that does not contain it yet —
   * the reply vanishes mid-flight and nothing further arrives, because the
   * slot the stream was writing into has been swapped underneath it. It
   * reappears on the next switch or reload, once postgres has caught up,
   * which is what makes the symptom look like a rendering fault rather than
   * a lost write.
   *
   * Storage is only authoritative for a thread that is NOT mid-run.
   */
  const hydrateThreadFromStore = useCallback(
    (
      id: string,
      next: { messages: ChatMessageType[]; subagents: Map<string, SubagentInfo>; todos: TodoItem[] },
    ) => {
      if (isStreaming(id)) return false;
      setThreads((prev) => updateThread(prev, id, (t) => ({ ...t, ...next })));
      // Re-seed the replay guard from the freshly loaded transcript: this is
      // the state a resumed run would duplicate, and it has just been rebuilt
      // from Postgres rather than appended to.
      hydratedToolIdsRef.current.set(id, toolIdsIn(next.messages));
      return true;
    },
    [isStreaming],
  );

  const setThreadTodos = useCallback(
    (id: string, next: TodoItem[]) => {
      setThreads((prev) =>
        updateThread(prev, id, (t) => ({ ...t, todos: next })),
      );
    },
    [],
  );

  // Threads with an agent still running on the backend. Switching to
  // another thread closes the local SSE listener via `abort()` but the
  // backend keeps running (and persists the reply on completion); this
  // set drives the sidebar WORKING chip and the auto-refresh poll on
  // re-entry. Marked on send, cleared on `done`/`error`, and cleared by
  // the polling loop once a fresh assistant message lands.
  const [inFlight, setInFlight] = useState<Set<string>>(new Set());
  // Latest inFlight snapshot, read by callbacks (switchConversation's
  // poll decision) without needing the set itself in their deps array —
  // otherwise every send/clear would invalidate every callback.
  const inFlightRef = useRef<Set<string>>(inFlight);
  useEffect(() => {
    inFlightRef.current = inFlight;
  }, [inFlight]);
  // Mirror of activeId — read by async resume callbacks to short-circuit
  // if the user switched threads again mid-stream. Without this guard,
  // tokens streamed from a previous thread's runner would land in the
  // newly-visible thread's UI state.
  const activeIdRef = useRef<string | null>(null);
  useEffect(() => {
    activeIdRef.current = activeId;
  }, [activeId]);
  // (v1 had a pollHandleRef + setInterval/setTimeout polling loop here
  //  for re-entry. v3 replaces that with the SSE /chat/resume stream —
  //  abort() in switchConversation tears down the previous subscriber.)

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // ── Health check ───────────────────────────────────────────────────
  const health = useHealthCheck();

  // "Is the thread I'm looking at busy?" — the composer, the typing indicator
  // and the empty state all mean the ACTIVE thread, not "any thread anywhere".
  const streaming = activeId ? streamingThreads.has(activeId) : false;
  // Latest `streaming` snapshot, read by the async-completion resume retry
  // so it never aborts a live user turn (subscribe() abort()s the current
  // stream on entry).
  const streamingRef = useRef(streaming);
  useEffect(() => {
    streamingRef.current = streaming;
  }, [streaming]);

  // ── Thinking / reasoning ───────────────────────────────────────────
  // `reasoning` feeds the Chat|Thinking tab: native model reasoning (when a
  // capable model emits it) plus client-derived "planning" narration — the
  // assistant text an agent writes *before* it calls a tool. planningBufRef
  // accumulates that pre-tool text per agent; it's flushed on the next tool
  // call for that agent.


  // ── rAF-batched streaming updates, keyed per thread ───────────────
  // SSE chunks arrive faster than React can render — each token's setState
  // used to trigger a full reconciliation, saturating the main thread. We
  // queue functional updaters and flush them in one setState per frame.
  // Order is preserved because the updaters compose left-to-right.
  //
  // Keyed by thread: a background run's ops accumulate under its own id, so
  // a flush that lands after the user switched away updates that run's slot
  // rather than whatever is on screen. This is what makes the old
  // `stillOnThread()` fencing unnecessary — those checks ran when an event
  // arrived, not when its batch flushed, so they never actually held.
  const pendingMsgOpsRef = useRef<Map<string, Array<(prev: ChatMessageType[]) => ChatMessageType[]>>>(new Map());
  const pendingSubOpsRef = useRef<Map<string, Array<(prev: Map<string, SubagentInfo>) => Map<string, SubagentInfo>>>>(new Map());
  const flushRafRef = useRef<number | null>(null);

  const flushPending = useCallback(() => {
    flushRafRef.current = null;
    const msgOps = pendingMsgOpsRef.current;
    const subOps = pendingSubOpsRef.current;
    if (msgOps.size === 0 && subOps.size === 0) return;
    pendingMsgOpsRef.current = new Map();
    pendingSubOpsRef.current = new Map();
    // startTransition keeps the streaming reconciliation low-priority so
    // user input (scroll, click, typing) preempts it.
    startTransition(() => {
      setThreads((prev) => {
        let next = prev;
        for (const [id, ops] of msgOps) {
          next = updateThread(next, id, (t) => {
            const msgs = ops.reduce((acc, op) => op(acc), t.messages);
            return msgs === t.messages ? t : { ...t, messages: msgs };
          });
        }
        for (const [id, ops] of subOps) {
          next = updateThread(next, id, (t) => {
            const subs = ops.reduce((acc, op) => op(acc), t.subagents);
            return subs === t.subagents ? t : { ...t, subagents: subs };
          });
        }
        return next;
      });
    });
  }, []);

  /**
   * Drop queued-but-unflushed updates for one thread (or all of them).
   *
   * `abort()` stops the SSE reader but does not empty the queue, so ops
   * enqueued moments earlier still flush afterwards. With per-thread
   * queues those ops can no longer reach the wrong thread — but a stopped
   * or replaced run should still not paint one more frame, so its own
   * pending work is dropped here.
   */
  const resetPendingStreamOps = useCallback((id?: string) => {
    if (id === undefined) {
      pendingMsgOpsRef.current = new Map();
      pendingSubOpsRef.current = new Map();
    } else {
      pendingMsgOpsRef.current.delete(id);
      pendingSubOpsRef.current.delete(id);
    }
    if (
      pendingMsgOpsRef.current.size === 0 &&
      pendingSubOpsRef.current.size === 0 &&
      flushRafRef.current !== null
    ) {
      window.cancelAnimationFrame(flushRafRef.current);
      flushRafRef.current = null;
    }
  }, []);

  const queueMsgOp = useCallback(
    (id: string, op: (prev: ChatMessageType[]) => ChatMessageType[]) => {
      const q = pendingMsgOpsRef.current.get(id);
      if (q) q.push(op);
      else pendingMsgOpsRef.current.set(id, [op]);
      if (flushRafRef.current === null) {
        flushRafRef.current = window.requestAnimationFrame(flushPending);
      }
    },
    [flushPending]
  );

  const queueSubOp = useCallback(
    (id: string, op: (prev: Map<string, SubagentInfo>) => Map<string, SubagentInfo>) => {
      const q = pendingSubOpsRef.current.get(id);
      if (q) q.push(op);
      else pendingSubOpsRef.current.set(id, [op]);
      if (flushRafRef.current === null) {
        flushRafRef.current = window.requestAnimationFrame(flushPending);
      }
    },
    [flushPending]
  );

  // ── Activity / todos / reasoning helpers (shared by send + resume) ──
  // A todo list: orchestrator (agent==="") → the global TodoList; otherwise
  // it's that subagent's own checklist, stored on its SubagentInfo.
  const recordTodos = useCallback(
    (id: string, agent: string, items: TodoItem[]) => {
      if (!agent) {
        setThreadTodos(id, items);
        return;
      }
      queueSubOp(id, (prev) => {
        const next = new Map(prev);
        const existing = next.get(agent);
        if (existing) next.set(agent, { ...existing, todos: items });
        return next;
      });
    },
    [queueSubOp]
  );

  // Planning buffer removed — planning text is already in message content.
  // Model reasoning is stored directly on the message's `reasoning` field
  // by the onReasoning handler below.

  // Cancel a scheduled flush on unmount so the rAF doesn't fire against a
  // dead component. Pending ops are dropped intentionally — the next
  // tokens after navigation belong to a different lifecycle.
  useEffect(() => {
    return () => {
      if (flushRafRef.current !== null) {
        window.cancelAnimationFrame(flushRafRef.current);
        flushRafRef.current = null;
      }
    };
  }, []);

  // ── Shared SSE callback factory ──────────────────────────────────
  // The single implementation of event routing (token → message,
  // tool_call → subagent card, …) for BOTH stream consumers: the initial
  // POST /chat/stream from send(), and the GET /chat/resume re-attach used
  // by the startup effect and switchConversation.
  //
  // These were two independent copies of the same twelve handlers. They
  // drifted, and every streaming bug fixed so far existed twice: the resume
  // copy carried thread guards the send copy lacked, and the send copy
  // completed subagents on `done` while the resume copy left them reading
  // "started" forever. Divergence was the default, because nothing forced
  // the two to agree.
  //
  // The genuine differences are parameters, not reasons to fork:
  //   mentionedAgent  only send knows which agent the user @mentioned
  //   surfaceErrors   send shows a stream error in the transcript; a resume
  //                   error is usually a benign re-attach hiccup and would
  //                   be noise
  //
  // These handlers no longer check whether `id` is the thread on screen.
  // They used to, because message state was shared and a background run's
  // events would otherwise land on the visible thread. State is now keyed
  // per thread, so an event writes to its own slot whether or not anyone is
  // looking at it — which is also the point: a run stays live while you read
  // another thread. The old guards were unsound anyway; they ran when an
  // event arrived, not when its batched update flushed.
  // `traceUrl` is handled unconditionally — resume never receives one, so
  // the branch simply doesn't fire there.
  const makeStreamCallbacks = useCallback(
    ({
      id,
      mentionedAgent,
      surfaceErrors = false,
    }: {
      id: string;
      mentionedAgent?: string;
      surfaceErrors?: boolean;
    }) => ({
      onToken: (token: string, agent?: string) => {
        if (agent) {
          queueSubOp(id, (prev) => {
            const next = new Map(prev);
            const existing = next.get(agent);
            if (existing) {
              const msgs = [...existing.messages];
              const lastMsg = msgs[msgs.length - 1];
              if (lastMsg && lastMsg.role === "assistant") {
                msgs[msgs.length - 1] = { ...lastMsg, content: lastMsg.content + token };
              } else {
                msgs.push({ role: "assistant", content: token });
              }
              next.set(agent, { ...existing, messages: msgs });
            }
            return next;
          });
        } else {
          queueMsgOp(id, (prev) => {
            const last = prev[prev.length - 1];
            if (last && last.role === "assistant" && !last.traceUrl) {
              return [...prev.slice(0, -1), { ...last, content: last.content + token }];
            }
            return [...prev, { id: nextId(), role: "assistant" as const, content: token, agentName: mentionedAgent, timestamp: Date.now() }];
          });
        }
      },
      onToolCall: ({ toolName, toolArgs, toolId, agent }: { toolName: string; toolArgs: string; toolId: string; agent?: string }) => {
        // Already in the transcript this thread was hydrated with — a replay
        // of interrupted work, not a new call. A resumed run re-emits the
        // whole prior tool sequence with fresh message ids, so without this
        // the user sees every tool call twice.
        if (toolId && hydratedToolIdsRef.current.get(id)?.has(toolId)) return;
        const tc: ToolCallInfo = { toolId, toolName, toolArgs, isRunning: true };
        if (agent) {
          queueSubOp(id, (prev) => {
            const next = new Map(prev);
            const existing = next.get(agent);
            if (existing) next.set(agent, { ...existing, toolCalls: [...existing.toolCalls, tc] });
            return next;
          });
        } else {
          queueMsgOp(id, (prev) => {
            const last = prev[prev.length - 1];
            if (last && last.role === "assistant" && !last.traceUrl) {
              const updated = [...prev];
              updated[prev.length - 1] = { ...last, toolCalls: [...(last.toolCalls || []), tc] };
              return updated;
            }
            return [
              ...prev,
              {
                id: nextId(),
                role: "assistant" as const,
                content: "",
                toolCalls: [tc],
                agentName: mentionedAgent,
                timestamp: Date.now(),
              },
            ];
          });
        }
      },
      onToolArgs: ({ toolId, content, agent }: { toolName: string; toolId: string; content: string; agent?: string }) => {
        // Argument deltas for a replayed call — see onToolCall.
        if (toolId && hydratedToolIdsRef.current.get(id)?.has(toolId)) return;
        const updateArgs = (tcs: ToolCallInfo[]) =>
          tcs.map((tc) => {
            if (tc.toolId === toolId) {
              const current = tc.toolArgs || "";
              let delta = content;
              if (content.startsWith(current)) {
                delta = content.substring(current.length);
              }
              return { ...tc, toolArgs: current + delta, isRunning: true };
            }
            return tc;
          });
        if (agent) {
          queueSubOp(id, (prev) => {
            const next = new Map(prev);
            const existing = next.get(agent);
            if (existing) next.set(agent, { ...existing, toolCalls: updateArgs(existing.toolCalls) });
            return next;
          });
        } else {
          queueMsgOp(id, (prev) => {
            const last = prev[prev.length - 1];
            if (last && last.role === "assistant" && last.toolCalls) {
              const updated = [...prev];
              updated[prev.length - 1] = { ...last, toolCalls: updateArgs(last.toolCalls) };
              return updated;
            }
            return prev;
          });
        }
      },
      onToolResult: ({ toolName, toolId, content, agent }: { toolName: string; toolId: string; content: string; agent?: string }) => {
        // Result for a replayed call — see onToolCall. Without this the guard
        // would be half-applied: the call suppressed, its result appended to
        // whichever live call happened to share the name.
        if (toolId && hydratedToolIdsRef.current.get(id)?.has(toolId)) return;
        if (agent) {
          queueSubOp(id, (prev) => {
            const next = new Map(prev);
            const existing = next.get(agent);
            if (existing) {
              next.set(agent, {
                ...existing,
                toolCalls: applyToolResult(existing.toolCalls, toolId, toolName, content),
              });
            }
            return next;
          });
        } else {
          queueMsgOp(id, (prev) => {
            const last = prev[prev.length - 1];
            if (last && last.role === "assistant" && last.toolCalls) {
              const updated = [...prev];
              updated[prev.length - 1] = {
                ...last,
                toolCalls: applyToolResult(last.toolCalls, toolId, toolName, content),
              };
              return updated;
            }
            return prev;
          });
        }
      },
      onSubagentStarted: ({ agent, path, task }: { agent: string; path: string[]; task?: string }) => {
        queueSubOp(id, (prev) => {
          const next = new Map(prev);
          const existing = next.get(agent);
          if (!existing) {
            next.set(agent, { name: agent, path, task, status: "started", messages: [], toolCalls: [], startedAt: Date.now() });
            return next;
          }
          // The map is keyed by name and accumulates across a thread's turns,
          // so this is the SAME agent being invoked again and it has to be
          // re-armed. Previously the start was silently dropped whenever the
          // name already existed, which left the card showing the previous
          // invocation's `completed` status for the whole of the new run: no
          // spinner while the agent worked, and a row that looked finished.
          // `completedAt` is cleared for the same reason — `SubagentCard`
          // renders elapsed time as `completedAt ?? Date.now()`, so a stale
          // value freezes the clock at the old run's end.
          //
          // The old run's tool calls are settled rather than dropped: keeping
          // them preserves the per-agent record, while leaving one marked
          // `isRunning` would make the row's live label keep reporting a tool
          // call from the previous invocation.
          next.set(agent, {
            ...existing,
            status: "started",
            path,
            task: task ?? existing.task,
            startedAt: Date.now(),
            completedAt: undefined,
            toolCalls: settleRunningToolCalls(existing.toolCalls ?? []),
          });
          return next;
        });
      },
      onSubagentCompleted: ({ agent }: { agent: string; path: string[] }) => {
        queueSubOp(id, (prev) => {
          const next = new Map(prev);
          const existing = next.get(agent);
          if (existing) next.set(agent, { ...existing, status: "completed", completedAt: Date.now() });
          return next;
        });
      },
      onSubagentFailed: ({ agent }: { agent: string; path: string[] }) => {
        queueSubOp(id, (prev) => {
          const next = new Map(prev);
          const existing = next.get(agent);
          if (existing) next.set(agent, { ...existing, status: "failed" as const, completedAt: Date.now() });
          return next;
        });
      },
      onValues: ({ todos: newTodos }: { todos?: Array<{ content: string; status: string }>; agent?: string }) => {
        if (newTodos && newTodos.length > 0) setThreadTodos(id, newTodos as TodoItem[]);
      },
      onTodos: ({ agent, items }: { agent: string; items: TodoItemInfo[] }) => {
        recordTodos(id, agent, items as TodoItem[]);
      },
      onReasoning: ({ agent, content, source }: { agent: string; content: string; source: "model" | "planning" }) => {
        if (source === "model") {
          if (agent) {
            queueSubOp(id, (prev) => {
              const next = new Map(prev);
              const existing = next.get(agent);
              if (existing) {
                const msgs = [...existing.messages];
                const lastMsg = msgs[msgs.length - 1];
                if (lastMsg && lastMsg.role === "assistant") {
                  msgs[msgs.length - 1] = {
                    ...lastMsg,
                    reasoning: (lastMsg.reasoning || "") + content,
                  };
                } else {
                  msgs.push({
                    role: "assistant",
                    content: "",
                    reasoning: content,
                  });
                }
                next.set(agent, { ...existing, messages: msgs });
              }
              return next;
            });
          } else {
            queueMsgOp(id, (prev) => {
              const last = prev[prev.length - 1];
              if (last && last.role === "assistant" && !last.traceUrl) {
                return [
                  ...prev.slice(0, -1),
                  { ...last, reasoning: (last.reasoning || "") + content },
                ];
              }
              return [
                ...prev,
                {
                  id: nextId(),
                  role: "assistant" as const,
                  content: "",
                  reasoning: content,
                  timestamp: Date.now(),
                },
              ];
            });
          }
        }
      },
      onDone: (traceUrl?: string) => {
        setInFlight((prev) => {
          if (!prev.has(id)) return prev;
          const next = new Set(prev);
          next.delete(id);
          return next;
        });
        // Same terminal cleanup the send path does. Without it, re-entering
        // a finished thread left its subagent cards reading "started" and
        // its tool spinners turning, because a replayed run never re-emits
        // the events that would have settled them.
        queueMsgOp(id, (prev) =>
          prev.map((m) =>
            m.toolCalls?.length
              ? { ...m, toolCalls: settleRunningToolCalls(m.toolCalls) }
              : m,
          ),
        );
        queueSubOp(id, (prev) => {
          const next = new Map(prev);
          for (const [key, sa] of next) {
            next.set(key, {
              ...sa,
              status: sa.status === "started" ? "completed" : sa.status,
              toolCalls: settleRunningToolCalls(sa.toolCalls),
            });
          }
          return next;
        });
        if (traceUrl) {
          queueMsgOp(id, (prev) => {
            const idx = [...prev].reverse().findIndex((m) => m.role === "assistant");
            if (idx === -1) return prev;
            const realIdx = prev.length - 1 - idx;
            const updated = [...prev];
            updated[realIdx] = { ...updated[realIdx], traceUrl };
            return updated;
          });
          queueMsgOp(id, (prev) => [
            ...prev,
            {
              id: nextId(),
              role: "system" as const,
              content: "Trace captured",
              traceUrl,
              timestamp: Date.now(),
            },
          ]);
        }
      },
      onError: (detail: string) => {
        console.warn(`Stream error for ${id}:`, detail);
        setInFlight((prev) => {
          if (!prev.has(id)) return prev;
          const next = new Set(prev);
          next.delete(id);
          return next;
        });
        // An error is as terminal as `done`; leaving spinners turning would
        // report "still working" for a run that has stopped.
        queueMsgOp(id, (prev) =>
          prev.map((m) =>
            m.toolCalls?.length
              ? { ...m, toolCalls: settleRunningToolCalls(m.toolCalls) }
              : m,
          ),
        );
        queueSubOp(id, (prev) => {
          const next = new Map(prev);
          for (const [key, sa] of next) {
            next.set(key, {
              ...sa,
              status: sa.status === "started" ? "failed" : sa.status,
              toolCalls: settleRunningToolCalls(sa.toolCalls),
            });
          }
          return next;
        });
        if (surfaceErrors) {
          queueMsgOp(id, (prev) => [
            ...prev,
            {
              id: nextId(),
              role: "system" as const,
              content: `⚠️ ${detail}`,
              timestamp: Date.now(),
            },
          ]);
        }
      },
    }),
    [queueMsgOp, queueSubOp, recordTodos],
  );

  // ── Hydrate from the backend on mount ────────────────────────────
  // Conversations + messages live in Postgres now (replaces the old
  // localStorage flow). The first load on a machine that still has
  // localStorage data also runs a one-time migration so existing chats
  // survive the cutover — see migrateLocalStorageOnce().
  //
  // activeId stays in localStorage (per-device preference) so refreshing
  // lands the user on the same chat.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      await migrateLocalStorageOnce();
      let convs: Conversation[] = [];
      try {
        const remote = await api.listConversations();
        convs = remote.conversations.map(summaryToConversation);
      } catch (e) {
        console.warn("Could not load conversations from backend:", e);
      }
      if (cancelled) return;

      const savedActiveId = localStorage.getItem(STORAGE_KEY_ACTIVE_ID);

      if (convs.length > 0) {
        setConversations(convs);
        const target =
          savedActiveId && convs.some((c) => c.id === savedActiveId)
            ? savedActiveId
            : [...convs].sort((a, b) => b.updatedAt - a.updatedAt)[0].id;
        setActiveId(target);
        localStorage.setItem(STORAGE_KEY_ACTIVE_ID, target);

        try {
          const data = await api.listMessages(target);
          if (cancelled) return;
          const msgs = data.messages.map(storedToMessage);
          if (msgs.length > 0) {
            const { mainMessages, subagents: reconSubagents, todos: reconTodos } = processMessageHistory(msgs);
            hydrateThreadFromStore(target, {
              messages: mainMessages, subagents: reconSubagents, todos: reconTodos,
            });
            // inFlight is in-memory and lost on page refresh. If no assistant
            // response exists yet, the backend may still be running — probe it
            // directly. subscribe() closes immediately when no run is active,
            // so this is cheap for the completed-run case.
            if (shouldResume(mainMessages, target, inFlightRef.current)) {
              activeIdRef.current = target;
              setInFlight((prev) => { const next = new Set(prev); next.add(target); return next; });
              const stillOnThread = () => activeIdRef.current === target;
              subscribe(target, makeStreamCallbacks({ id: target })).then(async () => {
                if (!stillOnThread()) return;
                try {
                  const d2 = await api.listMessages(target);
                  if (!stillOnThread()) return;
                  const msgs2 = d2.messages.map(storedToMessage);
                  const { mainMessages: mm2, subagents: sa2, todos: t2 } = processMessageHistory(msgs2);
                  hydrateThreadFromStore(target, {
                    messages: mm2, subagents: sa2, todos: t2,
                  });
                } catch { /* non-fatal */ }
                // No inFlight clear here: /chat/resume always terminates with
                // `done`, so onDone owns settlement for both call sites.
              });
            }
          }
        } catch (e) {
          console.warn(`Could not load messages for ${target}:`, e);
        }
        return;
      }

      // No conversations yet — create the first one on the backend so the
      // sidebar isn't empty.
      const id = crypto.randomUUID();
      try {
        const created = await api.createConversation({ id, title: "", project_id: "default" });
        if (cancelled) return;
        setConversations([summaryToConversation(created)]);
        setActiveId(id);
        localStorage.setItem(STORAGE_KEY_ACTIVE_ID, id);
        // Fresh start: provision the sandbox for the untitled thread now.
        ensureSandbox(id);
      } catch (e) {
        // Backend unreachable on first load — render a local placeholder so
        // the UI isn't entirely blocked. The user's next message will be
        // attempted against the backend and will fail loudly if it's still
        // down, which is the desired feedback signal.
        console.warn("Backend conversation create failed:", e);
        if (cancelled) return;
        const now = Date.now();
        setConversations([{ id, title: "", createdAt: now, updatedAt: now, projectId: "default", messageCount: 0 }]);
        setActiveId(id);
        localStorage.setItem(STORAGE_KEY_ACTIVE_ID, id);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  // ── Persistence model (Postgres-backed) ──────────────────────────
  // Messages no longer go through a debounced localStorage save. Instead:
  //   * the user message is POSTed to the backend right after the user
  //     hits send (see handleSend),
  //   * the final assistant message is POSTed once the SSE stream's
  //     onDone fires.
  // The ref still exists so callbacks (onDone) can read the current
  // messages snapshot without going through React closures.
  const messagesRef = useRef<ChatMessageType[]>(messages);
  messagesRef.current = messages;

  // Bump the conversation row's updated_at + message_count in *local*
  // state when a new message lands. The backend authoritatively updates
  // its own updated_at on every append, so this is only for the sidebar
  // ordering between hydrations.
  useEffect(() => {
    if (!activeId || messages.length === 0) return;
    setConversations((prev) =>
      prev.map((c) =>
        c.id === activeId
          ? { ...c, updatedAt: Date.now(), messageCount: messages.length }
          : c
      )
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages.length, activeId]);

  // ── Auto-scroll ────────────────────────────────────────────────────
  // During streaming, scroll instantly (smooth animations on every token
  // pile up and stall the main thread) and only when the user is already
  // near the bottom — respect deliberate scroll-up to read prior output.
  // rAF coalesces multiple chunk-driven updates into one scroll per frame.
  const scrollRafRef = useRef<number | null>(null);
  useEffect(() => {
    if (scrollRafRef.current !== null) return;
    scrollRafRef.current = window.requestAnimationFrame(() => {
      scrollRafRef.current = null;
      const node = messagesEndRef.current;
      if (!node) return;
      const scroller = node.parentElement?.parentElement; // .overflow-y-auto
      if (scroller) {
        const distanceFromBottom =
          scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight;
        if (streaming && distanceFromBottom > 200) return; // user scrolled up
      }
      node.scrollIntoView({ behavior: streaming ? "auto" : "smooth" });
    });
  }, [messages, streaming]);

  // ── Artifact refresh ──────────────────────────────────────────────
  // The refresh function does a shallow compare and short-circuits when
  // nothing has changed, so a polling loop can call it at a frequent
  // cadence without thrashing React renders. Equality is by name + status
  // because the backend's `ArtifactInfo` returns those two fields
  // (`agent` is derived, not relevant for "did anything change").
  const refreshArtifacts = useCallback(async () => {
    if (!activeId) return;
    try {
      const data = await api.listArtifacts(projectId, activeId);
      setArtifacts((prev) => {
        if (
          prev.length === data.artifacts.length &&
          prev.every(
            (p, i) =>
              p.name === data.artifacts[i].name &&
              p.status === data.artifacts[i].status
          )
        ) {
          return prev;
        }
        return data.artifacts;
      });
    } catch {
      // ignore — backend may be down or workspace not yet provisioned
    }
  }, [projectId, activeId]);

  // Live polling while an agent is running. The interval is short enough
  // to feel "live" (artifacts appear within ~2s of being written) but
  // long enough to not hammer the backend. The shallow compare in
  // refreshArtifacts means most ticks are no-ops at the React layer.
  useEffect(() => {
    if (!streaming) return;
    // Fire one immediate refresh so the user sees the first artifact
    // appear as soon as the agent writes it, without waiting for the
    // first interval tick.
    refreshArtifacts();
    const interval = window.setInterval(refreshArtifacts, 2000);
    return () => window.clearInterval(interval);
  }, [streaming, refreshArtifacts]);

  // Final refresh after streaming finishes — catches any artifact the
  // backend wrote between the last poll and the stream's end event.
  useEffect(() => {
    if (!streaming && messages.length > 0) {
      const timer = setTimeout(refreshArtifacts, 1000);
      return () => clearTimeout(timer);
    }
  }, [streaming, messages.length, refreshArtifacts]);

  // Refresh immediately when the active chat changes — gives the
  // Inspector the right artifact view for the new chat's container.
  // /projects/{id}/artifacts now auto-creates the workspace on first
  // call, so this also doubles as the "init the project for this chat"
  // step (replacing the manual `+init` click).
  useEffect(() => {
    if (activeId) refreshArtifacts();
  }, [activeId, refreshArtifacts]);

  // ── Conversation management ────────────────────────────────────────

  const createNewConversation = useCallback(async () => {
    // No abort: other threads' runs continue. A brand-new thread has no
    // stream of its own to cancel.
    const id = crypto.randomUUID();
    let created: Conversation;
    try {
      const summary = await api.createConversation({
        id,
        title: "",
        project_id: "default",
      });
      created = summaryToConversation(summary);
    } catch (e) {
      // Backend unreachable — render the row optimistically so the UI
      // doesn't lock up. The next user message will fail loudly if the
      // backend is still down.
      console.warn("createConversation failed, falling back to local row:", e);
      const now = Date.now();
      created = { id, title: "", createdAt: now, updatedAt: now, projectId: "default", messageCount: 0 };
    }
    setConversations((prev) => [...prev, created]);
    setActiveId(id);
    localStorage.setItem(STORAGE_KEY_ACTIVE_ID, id);
    setUploadedFiles([]);
    setSelectedArtifact(null);
    // No subagent/todo reset: a new thread's slot is empty by construction.
    // Spin up the sandbox now so it's ready before the first message.
    ensureSandbox(id);
  }, [abort]);

  const switchConversation = useCallback(
    async (id: string) => {
      if (id === activeId) return;
      // Deliberately no abort() and no queue reset. The thread being left
      // keeps its stream open and keeps writing to its own state slot, which
      // is what makes switching asynchronous rather than destructive. Both
      // were only ever needed because state was shared.
      setActiveId(id);
      activeIdRef.current = id;
      localStorage.setItem(STORAGE_KEY_ACTIVE_ID, id);
      // No blanking: the incoming thread renders from its own slot, so
      // switching is a map lookup rather than clear-then-refetch.
      setUploadedFiles([]);
      setSelectedArtifact(null);
      setSelectedSkill(null);
      // A thread with a live stream is already ahead of postgres — its slot
      // holds tokens the database has not seen yet, because the assistant
      // turn is only persisted when the run ends. Refetching would replace
      // that in-progress output with the older stored state, which is
      // exactly the "it refreshes" behaviour switching is meant to lose.
      const live = isStreaming(id);
      // Only read on the !live branch below, where the fetch assigns it.
      let initialMessages: ChatMessageType[] = [];
      if (!live) {
        try {
          const data = await api.listMessages(id);
          const msgs = data.messages.map(storedToMessage);
          const { mainMessages, subagents: reconSubagents, todos: reconTodos } = processMessageHistory(msgs);
          initialMessages = mainMessages;
          if (hydrateThreadFromStore(id, {
            messages: mainMessages, subagents: reconSubagents, todos: reconTodos,
          })) {
            // The slot was just replaced by stored state, so a replay is the
            // only source of any in-flight output and must apply in full.
            forgetThreadSeq(id);
          }
        } catch (e) {
          console.warn(`Could not load messages for ${id}:`, e);
        }
      }

      // ── Live resume on re-entry ──────────────────────────────────
      // If the user is returning to a thread whose backend run is still
      // in flight, open the GET /chat/resume SSE stream. The backend
      // replays the run's event history so subagent cards, tool blocks
      // and streaming tokens repaint immediately, then tails live events
      // until the runner's `done` event lands. After the stream closes
      // (server-side persist is complete by then), refetch listMessages
      // so the persisted assistant turn becomes the authoritative tail.
      if (!live && shouldResume(initialMessages, id, inFlightRef.current)) {
        const stillOnThread = () => activeIdRef.current === id;
        subscribe(id, makeStreamCallbacks({ id })).then(async () => {
          // Subscribe promise resolves AFTER the SSE stream closes — by
          // then the backend's `_persist_assistant_message` has landed in
          // postgres. One final listMessages call so the UI's tail
          // matches the persisted row exactly.
          if (!stillOnThread()) return;
          try {
            const data = await api.listMessages(id);
            if (!stillOnThread()) return;
            const msgs = data.messages.map(storedToMessage);
            const { mainMessages, subagents: reconSubagents, todos: reconTodos } = processMessageHistory(msgs);
            hydrateThreadFromStore(id, {
              messages: mainMessages, subagents: reconSubagents, todos: reconTodos,
            });
          } catch (e) {
            console.warn(`Post-resume listMessages for ${id} failed:`, e);
          }
        });
      }
    },
    [activeId, subscribe, makeStreamCallbacks, forgetThreadSeq, isStreaming, hydrateThreadFromStore],
  );

  const deleteConversation = useCallback(
    async (id: string) => {
      // Two backend calls: drop the DB row (with cascading messages) and
      // tear down the Docker container. They're independent — both must
      // happen, neither's failure should block the other.
      await Promise.allSettled([
        api.deleteConversationRow(id),
        api.deleteSession(id),
      ]);

      setConversations((prev) => prev.filter((c) => c.id !== id));

      if (id === activeId) {
        abort(id); // only the deleted thread
        const remaining = conversations.filter((c) => c.id !== id);
        if (remaining.length > 0) {
          const next = remaining[remaining.length - 1];
          await switchConversation(next.id);
        } else {
          await createNewConversation();
        }
      }
    },
    [activeId, abort, conversations, createNewConversation, switchConversation]
  );

  // Rename — mirrors the auto-title pattern below: optimistic local
  // update so the sidebar + chat header repaint immediately, then a
  // fire-and-forget PATCH. Backend is authoritative on next page load;
  // a console warn on failure matches auto-title's tolerance.
  const renameConversation = useCallback(
    (id: string, newTitle: string) => {
      setConversations((prev) =>
        prev.map((c) => (c.id === id ? { ...c, title: newTitle } : c))
      );
      api.patchConversation(id, { title: newTitle }).catch((e) =>
        console.warn("patchConversation(rename) failed:", e)
      );
    },
    []
  );

  // ── Send message ──────────────────────────────────────────────────
  const handleSend = useCallback(
    (text: string) => {
      if (!activeId) return;

      if (text.trim().toLowerCase() === "/compact") {
        setCompacting(true);
        api.compactConversation(activeId)
          .then(async () => {
            const data = await api.listMessages(activeId);
            const msgs = data.messages.map(storedToMessage);
            const { mainMessages, subagents: reconSubagents, todos: reconTodos } = processMessageHistory(msgs);
            setThreads((prev) =>
              updateThread(prev, activeId, (t) => ({
                ...t,
                messages: mainMessages,
                subagents: reconSubagents,
                todos: reconTodos,
              })),
            );
          })
          .catch((err: any) => {
            console.error("Compaction failed:", err);
            setThreadMessages(activeId, (prev) => [
              ...prev,
              {
                id: nextId(),
                role: "system",
                content: `⚠️ Compaction failed. ${err.message || String(err)}`,
                timestamp: Date.now(),
              },
            ]);
          })
          .finally(() => {
            setCompacting(false);
          });
        return;
      }

      // Auto-title: set title from first user message — persist both
      // locally (so the sidebar updates immediately) and on the backend.
      setConversations((prev) => {
        const conv = prev.find((c) => c.id === activeId);
        if (conv && !conv.title && text.trim()) {
          const title = autoTitle(text);
          // Fire-and-forget — failure to persist a title is non-fatal.
          api.patchConversation(activeId, { title }).catch((e) =>
            console.warn("patchConversation(title) failed:", e)
          );
          return prev.map((c) =>
            c.id === activeId ? { ...c, title } : c
          );
        }
        return prev;
      });

      // Only forward uploads whose upload has finished successfully.
      // Pending/error chips stay in the composer for the user to manage.
      const readyFiles = uploadedFiles.filter(
        (f): f is Extract<LocalUpload, { kind: "ready" }> => f.kind === "ready"
      );

      // Add user message — stamp attached files onto the bubble so they
      // render as chips inside the user's message (Claude-style), even
      // when the text is empty.
      const userMsg: ChatMessageType = {
        id: nextId(),
        role: "user",
        content: text,
        timestamp: Date.now(),
        attachments: readyFiles.length
          ? readyFiles.map((f) => ({ name: f.original_name, path: f.path }))
          : undefined,
      };
      setThreadMessages(activeId, (prev) => [...prev, userMsg]);

      // Persist the user turn immediately. Don't await — the SSE stream
      // can start in parallel; a write failure is logged but doesn't
      // block the chat (the user's intent is already in the UI).
      api.appendMessage(activeId, messageToWire(userMsg)).catch((e) =>
        console.warn("appendMessage(user) failed:", e)
      );

      // Clear the ready chips from the composer — they've now "moved" into
      // the message bubble above. Keep any pending/error chips so the user
      // can still cancel or retry them.
      if (readyFiles.length) {
        setUploadedFiles((prev) => prev.filter((f) => f.kind !== "ready"));
      }

      const mentionedAgent = text.match(/^@(\w+)/)?.[1];

      // Mark this thread as "running on the backend" so the sidebar
      // shows a WORKING chip and we know to poll listMessages if the
      // user navigates away and comes back before completion.
      setInFlight((prev) => {
        if (prev.has(activeId)) return prev;
        const next = new Set(prev);
        next.add(activeId);
        return next;
      });

      send(
        text,
        activeId,
        projectId,
        readyFiles.map((f) => f.path),
        readyFiles.map((f) => f.original_name),
        // Same routing the resume path uses — see makeStreamCallbacks.
        // The send path guard is belt-and-braces: switchConversation()
        // already abort()s this stream, but that leaves a window in which
        // in-flight handlers could still write into the thread the user
        // just left.
        makeStreamCallbacks({
          id: activeId,
          mentionedAgent,
          surfaceErrors: true,
        })
      );
    },
    [activeId, send, projectId, uploadedFiles, makeStreamCallbacks, setCompacting]
  );

  const handleAbort = useCallback(async () => {
    if (!activeId) return;
    // Stop this thread only — a run on another thread is not what the user
    // pressed Stop on.
    abort(activeId);
    // …and drop anything it queued, so a stopped run cannot keep painting
    // tokens for one more frame after the user pressed Stop.
    resetPendingStreamOps(activeId);
    // Call the backend to cancel the active run
    try {
      await api.abortChat(activeId);
    } catch (e) {
      console.warn("Failed to call abortChat on backend:", e);
    }
    // Refresh artifacts so the UI updates
    refreshArtifacts();
  }, [activeId, abort, refreshArtifacts, resetPendingStreamOps]);

  // ── File upload ────────────────────────────────────────────────────
  // Insert one "pending" chip per file synchronously so the composer
  // reflects the attachment instantly, then upload in the background and
  // swap each chip to "ready" (or "error"). handleSend only forwards
  // chips that have reached "ready".
  const handleUpload = useCallback(
    async (files: FileList) => {
      if (!activeId) return;

      const incoming = Array.from(files).map((f) => ({
        file: f,
        localId: `upl-${crypto.randomUUID()}`,
      }));

      // Synchronous: render pending chips immediately
      setUploadedFiles((prev) => [
        ...prev,
        ...incoming.map(
          ({ file, localId }): LocalUpload => ({
            kind: "pending",
            localId,
            name: file.name,
            size: file.size,
          })
        ),
      ]);

      try {
        const data = await api.uploadFiles(
          projectId,
          activeId,
          incoming.map((i) => i.file)
        );
        // Swap pending \u2192 ready in order. The backend preserves request
        // order, so zipping by index is correct.
        setUploadedFiles((prev) => {
          const next = [...prev];
          incoming.forEach(({ localId, file }, i) => {
            const slot = next.findIndex((f) => f.localId === localId);
            if (slot === -1) return; // user removed the chip mid-upload
            const resp = data.files[i];
            if (!resp) return;
            next[slot] = {
              kind: "ready",
              localId,
              path: resp.path,
              original_name: resp.original_name,
              size: file.size,
            };
          });
          return next;
        });
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        setUploadedFiles((prev) =>
          prev.map((f) => {
            if (!incoming.some((i) => i.localId === f.localId)) return f;
            const name =
              f.kind === "pending" || f.kind === "error"
                ? f.name
                : f.original_name;
            return {
              kind: "error" as const,
              localId: f.localId,
              name,
              message,
            };
          })
        );
        setThreadMessages(activeId, (prev) => [
          ...prev,
          {
            id: nextId(),
            role: "system",
            content: `\u26a0\ufe0f Upload error: ${message}`,
            timestamp: Date.now(),
          },
        ]);
      }
    },
    [projectId, activeId]
  );

  // ── Agent click → insert mention ─────────────────────────────────
  const handleAgentClick = useCallback((name: string) => {
    setMentionInsert(name);
  }, []);

  const [mentionInsert, setMentionInsert] = useState<string | null>(null);
  useEffect(() => {
    if (mentionInsert) {
      const timer = setTimeout(() => setMentionInsert(null), 100);
      return () => clearTimeout(timer);
    }
  }, [mentionInsert]);

  // ── Drag & drop ────────────────────────────────────────────────────
  const [dragOver, setDragOver] = useState(false);

  useEffect(() => {
    const onEnter = (e: DragEvent) => {
      e.preventDefault();
      setDragOver(true);
    };
    const onLeave = (e: DragEvent) => {
      e.preventDefault();
      setDragOver(false);
    };
    const onOver = (e: DragEvent) => e.preventDefault();
    const onDrop = (e: DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (e.dataTransfer?.files.length) handleUpload(e.dataTransfer.files);
    };

    document.addEventListener("dragenter", onEnter);
    document.addEventListener("dragleave", onLeave);
    document.addEventListener("dragover", onOver);
    document.addEventListener("drop", onDrop);
    return () => {
      document.removeEventListener("dragenter", onEnter);
      document.removeEventListener("dragleave", onLeave);
      document.removeEventListener("dragover", onOver);
      document.removeEventListener("drop", onDrop);
    };
  }, [handleUpload]);

  // ── Render ─────────────────────────────────────────────────────────

  const handleSelectArtifact = useCallback((artifactName: string | null) => {
    setSelectedArtifact(artifactName);
    if (artifactName) {
      setSelectedSkill(null);
    }
  }, []);

  const handleSelectSkill = useCallback((skillName: string | null) => {
    setSelectedSkill(skillName);
    if (skillName) {
      setSelectedArtifact(null);
    }
  }, []);

  // Stable element references — used in both the mobile (flex) and desktop
  // (PanelGroup) branches below. Only one branch is rendered at a time, so
  // only one instance exists per element. Local state inside ChatSidebar /
  // InspectorPanel / etc. persists as long as the user stays within one
  // viewport mode; crossing the lg breakpoint remounts them (acceptable
  // edge case for a desktop-first app).
  // Switching sections opens the sidebar: on mobile it is a closed drawer and
  // on desktop it may be collapsed to a rail, so a tab click that changed a
  // hidden panel would look like a no-op.
  const handleTabChange = (next: SidebarTab) => {
    setActiveTab(next);
    setSidebarOpen(true);
    if (sidebarCollapsed) toggleSidebarCollapsed();
  };

  const sidebarEl = (
    <ChatSidebar
      conversations={conversations}
      activeId={activeId}
      inFlight={inFlight}
      onSelect={switchConversation}
      onNew={createNewConversation}
      onDelete={deleteConversation}
      onRename={renameConversation}
      open={sidebarOpen}
      onClose={() => setSidebarOpen(false)}
      collapsed={sidebarCollapsed}
      onToggleCollapsed={toggleSidebarCollapsed}
      selectedSkill={selectedSkill}
      onSelectSkill={handleSelectSkill}
      tab={activeTab}
    />
  );

  const artifactEl =
    selectedArtifact && activeId ? (
      <ArtifactCanvas
        projectId={projectId}
        threadId={activeId}
        artifactName={selectedArtifact}
        onClose={() => handleSelectArtifact(null)}
      />
    ) : null;

  const skillEl =
    selectedSkill ? (
      <SkillCanvas
        skillName={selectedSkill}
        onClose={() => handleSelectSkill(null)}
      />
    ) : null;

  const inspectorEl = (
    <InspectorPanel
      artifacts={artifacts}
      onRefreshArtifacts={refreshArtifacts}
      onArtifactClick={handleSelectArtifact}
      selectedArtifact={selectedArtifact}
      tracing={health.tracing}
      open={inspectorOpen}
      onClose={() => setInspectorOpen(false)}
      onAgentClick={handleAgentClick}
      projectId={projectId}
      threadId={activeId}
    />
  );

  const mainEl = (
    <main id="main-content" className="flex-1 flex flex-col min-w-0 relative">
        {/* Drag overlay */}
        {dragOver && (
          <div className="absolute inset-4 border border-dashed border-blue-400/50 bg-base-950/75 flex items-center justify-center z-50 pointer-events-none backdrop-blur-sm">
            <div className="text-center">
              <div className="label-mono text-blue-400 mb-3">DROP FILES</div>
              <div className="text-[15px] text-base-100 font-medium">
                Release to attach
              </div>
              <div className="label-mono text-base-500 mt-4">
                PDF \u00b7 XLSX \u00b7 DOCX \u00b7 CSV \u00b7 TXT \u00b7 MD \u00b7 PY \u00b7 JSON \u00b7 PNG \u00b7 JPG
              </div>
            </div>
          </div>
        )}

        {/* Header */}
        <header className="flex items-center justify-between pl-5 pr-4 h-14 border-b border-base-700 flex-shrink-0 bg-base-900/70">
          <div className="flex items-center gap-4 min-w-0">
            <button
              onClick={() => setSidebarOpen((o) => !o)}
              className="lg:hidden text-base-400 hover:text-blue-300 transition-colors"
              aria-label="Toggle sidebar"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </svg>
            </button>
            {/* Dossier masthead: wordmark, section, then the document title.
                The thread is a document in a register, so it is labelled the
                way a spec sheet labels itself, not the way a chat app does. */}
            <div className="flex items-baseline gap-3 min-w-0">
              {/* The wordmark lives in AppNav now; this header states the
                  document, not the product. */}
              <span className="label-mono text-base-500 hidden sm:inline">DOSSIER</span>
              <h1 className="dossier-title text-[16px] text-base-100 truncate">
                {conversations.find((c) => c.id === activeId)?.title ||
                  "Untitled"}
              </h1>
              <span className="font-mono text-[10px] text-base-600 hidden lg:inline tabular-nums">
                {activeId ? "\u2116 " + activeId.slice(0, 8) : "\u2116 DRAFT"}
              </span>
            </div>
          </div>

          {/* Artifact viewer for THIS dossier, beside its title. */}
          <ArtifactsMenu
            artifacts={artifacts}
            selectedArtifact={selectedArtifact}
            onSelectArtifact={handleSelectArtifact}
            inspectorOpen={inspectorOpen}
            onToggleInspector={() => setInspectorOpen((open) => !open)}
          />
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden px-4 py-6">
          <div className="max-w-3xl mx-auto">
            {/* Live todo list from agent state */}
            {todos.length > 0 && (
              <div className="mb-4">
                <TodoList items={todos} />
              </div>
            )}
            {messages.length === 0 && !streaming && (
              <div className="py-20 sm:py-24 max-w-xl">
                {/* Deliberately left-aligned and off-centre: the transcript
                    that replaces this is left-aligned too, so a centred
                    splash made the first message look like it jumped. */}
                <div className="flex items-start gap-5 mb-10">
                  {/* SDLC block diagram icon */}
                  <svg width="56" height="56" viewBox="0 0 72 72" className="text-blue-400/60 flex-shrink-0 mt-1" aria-hidden="true">
                    <rect x="4" y="4" width="28" height="20" fill="none" stroke="currentColor" strokeWidth="1" rx="2" />
                    <rect x="40" y="4" width="28" height="20" fill="none" stroke="currentColor" strokeWidth="1" rx="2" />
                    <rect x="4" y="48" width="28" height="20" fill="none" stroke="currentColor" strokeWidth="1" rx="2" />
                    <rect x="40" y="48" width="28" height="20" fill="none" stroke="currentColor" strokeWidth="1" rx="2" />
                    <line x1="32" y1="14" x2="40" y2="14" stroke="currentColor" strokeWidth="1" />
                    <line x1="18" y1="24" x2="18" y2="48" stroke="currentColor" strokeWidth="1" />
                    <line x1="54" y1="24" x2="54" y2="48" stroke="currentColor" strokeWidth="1" />
                    <circle cx="18" cy="14" r="2" fill="currentColor" />
                    <circle cx="54" cy="14" r="2" fill="currentColor" />
                    <circle cx="18" cy="58" r="2" fill="currentColor" />
                    <circle cx="54" cy="58" r="2" fill="currentColor" />
                  </svg>
                  <div>
                    <span className="label-mono text-blue-300 block mb-2">Specification dossier / phases P1–P5</span>
                    <h2 className="dossier-title text-[30px] leading-[1.08] text-base-100 mb-3">
                      Open a dossier.
                    </h2>
                    <p className="text-[14px] text-base-400 leading-relaxed max-w-[54ch]">
                      Drop source material, then @mention a specialist. Every phase
                      writes one validated artifact — OpenAPI, Gherkin, CI pipeline and
                      Mermaid are checked by a tool, not asserted by the model.
                    </p>
                  </div>
                </div>

                {/* Step rail: a connected sequence, not three interchangeable
                    cards. The steps are ordered, so the layout says so. */}
                {/* The register: every phase, its owner, and the artifact it
                    must produce. This is the whole system on one screen,
                    stated as a table instead of an onboarding tour. */}
                <div className="register" aria-label="Pipeline phases and their agents">
                  {[
                    { code: "P1", phase: 1, name: "Sources", agents: "Ingestion", out: "REQUIREMENTS.md · GLOSSARY.md · CONSTRAINTS.md" },
                    { code: "P2", phase: 2, name: "Requirements", agents: "Requirements", out: "USER_STORIES.md · ACCEPTANCE_CRITERIA.md" },
                    { code: "P3", phase: 3, name: "Design", agents: "Architecture · API", out: "ARCHITECTURE.md · DATA_MODEL.md · ADR.md · openapi.yaml" },
                    { code: "P4", phase: 4, name: "Planning", agents: "Planning · DevOps", out: "BACKLOG.md · TEST_PLAN.md · ci/pipeline.yml" },
                    { code: "P5", phase: 5, name: "Diagrams", agents: "Diagram", out: "*.mmd — one validated model per call" },
                  ].map((row) => (
                    <div key={row.code} data-phase={row.phase} className="register-row">
                      <span className="phase-code pt-0.5">{row.code}</span>
                      <div className="min-w-0">
                        <div className="flex items-baseline gap-2.5 flex-wrap">
                          <span className="dossier-title text-[16px] text-base-100">{row.name}</span>
                          <span className="font-mono text-[11px] text-base-400">{row.agents}</span>
                        </div>
                        <div className="font-mono text-[10.5px] text-base-500 mt-1 leading-relaxed">{row.out}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {messages.map((m, i) => {
              // Attach subagent cards to the last assistant message during/after streaming
              const isLastAssistant =
                i === messages.length - 1 &&
                m.role === "assistant" &&
                subagents.size > 0;
              const isLast = i === messages.length - 1;
              return (
                <ChatMessage
                  key={m.id}
                  message={m}
                  subagents={isLastAssistant ? subagentList : undefined}
                  onOptionClick={isLast && !streaming && !compacting ? handleSend : undefined}
                  onArtifactClick={handleSelectArtifact}
                />
              );
            })}
            {compacting && (
              <div className="flex items-center gap-3 my-4 ml-4 animate-pulse">
                <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
                <span className="label-mono text-blue-400 tracking-wider font-semibold">
                  COMPACTING CONVERSATION HISTORY...
                </span>
              </div>
            )}
            {streaming && <TypingIndicator />}
            {/* Synthesis indicator: all subagents done, orchestrator still working */}
            {streaming &&
              subagentList.length > 0 &&
              subagentList.every((s) => s.status === "completed") && (
                <div className="flex items-center gap-3 my-3 ml-4">
                  <div className="w-3 h-3 border border-blue-400 border-t-transparent rounded-full animate-spin" />
                  <span className="label-mono text-blue-400/80 tracking-wider-mono">
                    SYNTHESIZING
                  </span>
                </div>
              )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input — file chips render inside the composer (Claude-style) */}
        <ChatInput
          onSend={handleSend}
          onUpload={handleUpload}
          disabled={streaming || compacting}
          streaming={streaming}
          onAbort={handleAbort}
          files={uploadedFiles}
          onRemoveFile={(localId) =>
            setUploadedFiles((prev) => prev.filter((f) => f.localId !== localId))
          }
          mentionInsert={mentionInsert}
          onMentionConsumed={() => setMentionInsert(null)}
          artifacts={artifacts}
        />
      </main>
    );

  return (
    <div className="flex flex-col h-dvh bg-base-950 text-base-200 overflow-hidden">
      <AppNav
        tab={activeTab}
        onTabChange={handleTabChange}
        inspectorOpen={inspectorOpen}
        onToggleInspector={() => setInspectorOpen((open) => !open)}
        health={health}
        onToggleSidebar={() => setSidebarOpen((open) => !open)}
      />

      <div className="flex flex-1 min-h-0">
      {!isDesktop ? (
        // Mobile (and SSR initial render): the original flex layout with
        // no resize affordance. ChatSidebar handles its own `fixed`-
        // positioned slide-in overlay via internal CSS.
        <>
          {sidebarEl}
          {artifactEl && (
            <div className="w-[50%] min-w-[400px] max-w-[700px] border-l border-base-700 flex-shrink-0">
              {artifactEl}
            </div>
          )}
          {skillEl && (
            <div className="w-[50%] min-w-[400px] max-w-[700px] border-l border-base-700 flex-shrink-0">
              {skillEl}
            </div>
          )}
          {inspectorEl}
          {mainEl}
        </>
      ) : (
        // Desktop: resizable panels. Sizes persist to localStorage under
        // the `harness-main-layout` autoSaveId.
        //
        // When collapsed, the sidebar's 56px rail renders OUTSIDE the
        // PanelGroup as a fixed-width column — no resize handle, so the
        // user can't drag a rail to absurd widths. When expanded, the
        // sidebar lives inside the PanelGroup as a normal resizable Panel.
        <>
          {sidebarCollapsed && (
            <div className="w-14 flex-shrink-0 h-full">{sidebarEl}</div>
          )}
          <PanelGroup
            direction="horizontal"
            autoSaveId="harness-main-layout"
            className="flex flex-1 h-full"
          >
          {!sidebarCollapsed && (
            <>
              <Panel
                ref={sidebarPanelRef}
                id="sidebar"
                order={1}
                defaultSize={18}
                minSize={10}
                maxSize={22}
                className="flex overflow-hidden"
              >
                {sidebarEl}
              </Panel>
              <PanelResizeHandle className="harness-resize-handle" />
            </>
          )}

          {artifactEl && (
            <>
              <Panel
                id="artifact"
                order={2}
                defaultSize={30}
                minSize={20}
                maxSize={55}
                className="flex overflow-hidden"
              >
                {artifactEl}
              </Panel>
              <PanelResizeHandle className="harness-resize-handle" />
            </>
          )}

          {skillEl && (
            <>
              <Panel
                id="skill"
                order={2.5}
                defaultSize={30}
                minSize={20}
                maxSize={55}
                className="flex overflow-hidden"
              >
                {skillEl}
              </Panel>
              <PanelResizeHandle className="harness-resize-handle" />
            </>
          )}

          {inspectorOpen && (
            <>
              <Panel
                id="inspector"
                order={3}
                defaultSize={18}
                minSize={14}
                maxSize={30}
                className="flex overflow-hidden"
              >
                {inspectorEl}
              </Panel>
              <PanelResizeHandle className="harness-resize-handle" />
            </>
          )}

          <Panel id="main" order={4} minSize={25} className="flex overflow-hidden">
            {mainEl}
          </Panel>
          </PanelGroup>
        </>
      )}
      </div>
    </div>
  );
}

/**
 * The route entry point: everything below is the harness, and none of it
 * renders until a session resolves. Splitting the export from HarnessApp keeps
 * the gate a single wrapper instead of a conditional threaded through a
 * 2000-line component, and keeps HarnessApp free of auth concerns.
 */
export default function ChatPage() {
  return (
    <AuthGate>
      <HarnessApp />
    </AuthGate>
  );
}
