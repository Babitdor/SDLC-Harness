"use client";

import { memo, useState } from "react";
import { findAgent } from "../lib/agents";
import { renderWithAgentMentions } from "./AgentMention";
import Markdown from "./Markdown";
import ToolCallBlock from "./ToolCallBlock";
import SubagentCard from "./SubagentCard";
import SimpleActivityFeed from "./SimpleActivityFeed";
import AgentActivity from "./AgentActivity";
import ArtifactCard, { toArtifactPath } from "./ArtifactCard";
import type { ChatMessage as ChatMessageType, ToolCallInfo, SubagentInfo } from "../lib/types";

// Pull subagent_type out of a `task` tool's streaming JSON args. The
// args build up chunk-by-chunk so we can't JSON.parse safely; the regex
// matches once the LLM has emitted enough of the key to be unambiguous.
const SUBAGENT_TYPE_RE = /"subagent_type"\s*:\s*"([^"]+)"/;

/**
 * Pretty name for a tool call. The orchestrator's `task` tool spawns
 * subagents — relabel it as "Delegate → <Agent>" once we can resolve the
 * subagent_type from the streaming args. Falls back to the raw tool
 * name for everything else.
 */
function formatToolName(tc: ToolCallInfo): string {
  if (tc.toolName === "task") {
    const m = tc.toolArgs?.match(SUBAGENT_TYPE_RE);
    if (m) {
      const resolved = findAgent(m[1])?.name ?? m[1];
      return `Delegate → ${resolved}`;
    }
    return "Delegate";
  }
  return tc.toolName;
}

function parseArgs(raw: string | undefined): Record<string, unknown> | null {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Record<string, unknown>;
  } catch {
    return null;
  }
}

interface Props {
  message: ChatMessageType;
  subagents?: SubagentInfo[];
  onOptionClick?: (text: string) => void;
  /** Open a produced file in the artifact panel. Omit to hide the cards. */
  onArtifactClick?: (path: string) => void;
}

/**
 * Project-relative paths this message wrote, in call order, de-duplicated.
 *
 * Derived from the message's own `write_file` / `edit_file` calls rather
 * than the run-level artifact list, so a card sits with the turn that
 * produced it and a re-render cannot attribute a file to the wrong message.
 * A file edited several times in one turn yields one card.
 */
export function producedFiles(
  toolCalls?: ToolCallInfo[],
  subagents?: SubagentInfo[],
): string[] {
  // Subagents do the writing. While a run streams, an agent-tagged
  // tool_call is routed to the subagent map rather than onto the message
  // (see the `if (agent)` branch in the SSE handlers), so reading only
  // `message.toolCalls` found nothing and no card appeared. Persistence
  // then merges the whole run's calls onto the assistant row, which is why
  // the cards showed up on refresh and only on refresh.
  //
  // Scan both, so the live view matches the reloaded one.
  const seen = new Set<string>();
  const scan = (tcs?: ToolCallInfo[]) => {
    for (const tc of tcs || []) {
      if (tc.toolName !== "write_file" && tc.toolName !== "edit_file") continue;
      let filePath: unknown;
      try {
        filePath = (JSON.parse(tc.toolArgs) as Record<string, unknown>).file_path;
      } catch {
        continue; // args still streaming, or not JSON — no card yet
      }
      if (typeof filePath !== "string") continue;
      const rel = toArtifactPath(filePath);
      if (rel) seen.add(rel);
    }
  };
  scan(toolCalls);
  for (const sa of subagents || []) scan(sa.toolCalls);
  return [...seen];
}

/** Parse raw content to extract tool calls and clean text. */
function parseContent(raw: string, toolCalls?: ToolCallInfo[]) {
  const blocks: Array<{ type: "text" | "tool"; content: string; tool?: ToolCallInfo }> = [];

  // If we have structured tool calls, render those directly
  if (toolCalls && toolCalls.length > 0) {
    // Split content around tool call markers and tool result markers
    // The content may include [Command succeeded...] etc.
    // We extract those into tool blocks
    const toolResultPattern = /\[Command (succeeded|failed) with exit code \d+\]/g;
    const parts = raw.split(toolResultPattern);

    let currentText = "";
    let toolIdx = 0;

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      if (part === "succeeded" || part === "failed") {
        // This is a capture group from the regex, skip
        continue;
      }
      if (part.trim()) {
        currentText += part;
      }
    }

    // If there's clean text (not just tool output), show it as markdown
    const cleanText = currentText.trim();
    if (cleanText) {
      blocks.push({ type: "text", content: cleanText });
    }

    // Add tool call blocks
    for (const tc of toolCalls) {
      blocks.push({ type: "tool", content: "", tool: tc });
    }

    return blocks;
  }

  // No structured tool calls — parse patterns from raw text
  // Pattern: [Command succeeded/failed with exit code N]
  const lines = raw.split("\n");
  let textBuffer: string[] = [];
  let currentToolResult: string[] = [];
  let inToolResult = false;

  function flushText() {
    if (textBuffer.length > 0) {
      const text = textBuffer.join("\n").trim();
      if (text) blocks.push({ type: "text", content: text });
      textBuffer = [];
    }
  }

  for (const line of lines) {
    if (/^\[Command (succeeded|failed) with exit code/.test(line)) {
      // End of a tool result block, or standalone marker
      if (inToolResult) {
        currentToolResult.push(line);
        flushText();
        blocks.push({
          type: "tool",
          content: currentToolResult.join("\n"),
          tool: {
            toolId: "",
            toolName: "Shell Command",
            toolArgs: "",
            result: currentToolResult.join("\n"),
            isRunning: false,
          },
        });
        currentToolResult = [];
        inToolResult = false;
      } else {
        flushText();
        blocks.push({
          type: "tool",
          content: line,
          tool: {
            toolId: "",
            toolName: "Shell Command",
            toolArgs: "",
            result: line,
            isRunning: false,
          },
        });
      }
    } else if (/^\/bin\/(sh|bash|zsh)/.test(line) || /^file: not found/.test(line)) {
      // Start of shell output
      flushText();
      inToolResult = true;
      currentToolResult.push(line);
    } else if (inToolResult) {
      currentToolResult.push(line);
    } else {
      textBuffer.push(line);
    }
  }

  // Flush remaining
  if (inToolResult && currentToolResult.length > 0) {
    flushText();
    blocks.push({
      type: "tool",
      content: currentToolResult.join("\n"),
      tool: {
        toolId: "",
        toolName: "Shell Command",
        toolArgs: "",
        result: currentToolResult.join("\n"),
        isRunning: false,
      },
    });
  }
  flushText();

  // If no blocks were created (no patterns found), just return the raw text
  if (blocks.length === 0) {
    return [{ type: "text" as const, content: raw }];
  }

  return blocks;
}

function ChatMessageImpl({ message, subagents, onOptionClick, onArtifactClick }: Props) {
  const files = producedFiles(message.toolCalls, subagents);
  const [thinkingExpanded, setThinkingExpanded] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const { role, content, agentName, traceUrl, toolCalls, attachments, reasoning } = message;

  // ── System notes — centered, with a thin blue rule above/below.
  if (role === "system") {
    const isCompacted = content.includes("CONVERSATION COMPACTED");

    if (isCompacted) {
      return (
        <div className="my-8 px-6 py-5 bg-base-900/40 border border-blue-500/20 tick-corners shadow-lg shadow-base-950/20 max-w-[90%] mx-auto animate-message-in">
          <div className="flex items-center gap-2 mb-4 pb-2 border-b border-base-800">
            <span className="text-blue-400 text-lg">⚙️</span>
            <span className="label-mono text-blue-400 font-semibold tracking-wider">SYSTEM COMPACTION</span>
            <div className="flex-1 h-px bg-base-800" />
          </div>
          <div className="text-[14.5px] text-base-200 leading-relaxed markdown-container select-text">
            <Markdown content={content} />
          </div>
        </div>
      );
    }

    return (
      <div className="flex justify-center my-6 animate-message-in">
        <div className="max-w-[80%] flex items-center gap-3 px-4 py-2 border-y border-blue-400/25">
          <span className="label-mono text-blue-400/80 flex-shrink-0">— NOTE —</span>
          <div className="text-[14px] text-base-300 select-text">
            <Markdown content={content} />
          </div>
          {traceUrl && (
            <a
              href={traceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="label-mono text-blue-400 hover:text-blue-300 underline underline-offset-4 ml-2 flex-shrink-0"
            >
              TRACE ↗
            </a>
          )}
        </div>
      </div>
    );
  }

  const agent = findAgent(agentName);
  const blocks = parseContent(content, toolCalls);

  // The agent's own non-interactive tool calls, collapsed into the minimal
  // plain-English AgentActivity feed by default. Always excludes clarifying
  // questions (rendered as interactive cards). Also drops `task` delegations
  // when the subagent feed below is present, since they'd otherwise double up
  // (kept otherwise so a delegation still shows as "Delegating…").
  // "Show technical details" swaps this for the raw ToolCallBlocks.
  const hasSubagents = (subagents?.length ?? 0) > 0;
  const activityTools = blocks
    .filter(
      (b) =>
        b.type === "tool" &&
        b.tool &&
        b.tool.toolName !== "ask_question" &&
        !(hasSubagents && b.tool.toolName === "task"),
    )
    .map((b) => b.tool!)
    .filter(Boolean) as ToolCallInfo[];
  const hasActivity = activityTools.length > 0 || hasSubagents;

  // User messages — right-aligned, clean bubble.
  if (role === "user") {
    return (
      <div className="flex justify-end mb-8 animate-message-in">
        <div className="max-w-[78%]">
          <div className="text-right mb-2 flex items-center justify-end gap-2">
            <span className="label-mono text-base-500">YOU</span>
            <span className="text-[9px] font-mono text-base-600 tabular-nums">
              {new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </span>
          </div>

          {attachments && attachments.length > 0 && (
            <div className="flex flex-wrap gap-2 justify-end mb-3">
              {attachments.map((a) => (
                <span
                  key={a.path}
                  title={a.path}
                  className="inline-flex items-center gap-2 px-2.5 py-1 border border-base-600 bg-base-900/60 font-mono text-[11px] text-base-300"
                >
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-blue-400/70">
                    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                  </svg>
                  {a.name}
                </span>
              ))}
            </div>
          )}

          {content ? (
            <p className="text-[14px] text-base-100 leading-relaxed whitespace-pre-wrap text-right">
              {renderWithAgentMentions(content)}
            </p>
          ) : !attachments || attachments.length === 0 ? (
            <p className="text-[14px] text-base-500 text-right">(empty message)</p>
          ) : null}
        </div>
      </div>
    );
  }

  // Assistant — clean left border.
  const accentColor = agent ? "text-blue-300" : "text-blue-300";
  const accentSubtle = agent ? "text-cyan-400/80" : "text-blue-400/80";

  return (
    <div className="mb-8 animate-message-in">
      <div className="max-w-full overflow-hidden">
        {/* Speaker plate */}
        <div className="flex items-center gap-3 mb-3">
          {agent && (
            <div className="w-6 h-6 border border-blue-400/30 bg-blue-400/5 flex items-center justify-center text-[11px]">
              {agent.icon}
            </div>
          )}
          <div className="flex items-baseline gap-3">
            <span className={"label-mono " + accentColor}>
              {agent ? agent.name.toUpperCase() : "ORCHESTRATOR"}
            </span>
            {agent && (
              <span className={"label-mono " + accentSubtle}>
                PHASE {agent.phase.toString().padStart(2, "0")}
              </span>
            )}
            <span className="text-[9px] font-mono text-base-600 tabular-nums">
              {new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </span>
          </div>
        </div>

        {reasoning && (
          <div className="mb-4 border border-base-800 bg-base-950/30 tick-corners">
            <button
              onClick={() => setThinkingExpanded(!thinkingExpanded)}
              className="w-full flex items-center justify-between px-3 py-2 text-[12px] font-mono text-cyan-400/80 hover:text-cyan-300 hover:bg-base-900/20 transition-colors"
            >
              <div className="flex items-center gap-2">
                <svg
                  width="10"
                  height="10"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  className={`transition-transform duration-200 ${thinkingExpanded ? "rotate-90" : ""}`}
                >
                  <polyline points="9 18 15 12 9 6" />
                </svg>
                <span>THINKING PROCESS</span>
              </div>
              <span className="text-[10px] text-base-500">
                {thinkingExpanded ? "COLLAPSE" : "EXPAND"}
              </span>
            </button>
            {thinkingExpanded && (
              <div className="px-4 py-3 border-t border-base-800 text-[13px] text-base-400 leading-relaxed max-h-[300px] overflow-y-auto">
                <Markdown content={reasoning} />
              </div>
            )}
          </div>
        )}

        {/* Content blocks — body sans for paragraphs. Markdown inside
            will inherit; titles inside markdown get serif via their own
            styling. */}
        <div className="text-[14px] text-base-200 leading-relaxed overflow-x-auto">
          {blocks.map((block, i) =>
            block.type === "tool" && block.tool ? (
              block.tool.toolName === "ask_question" ? (
                (() => {
                  const parsed = parseArgs(block.tool.toolArgs);
                  const question = parsed?.question as string || block.tool.toolArgs;
                  const options = parsed?.options as string[] | undefined;

                  return (
                    <div key={i} className="my-6 p-5 border border-base-700 border-l-2 border-l-cyan-400 bg-base-900/30 backdrop-blur-sm tick-corners shadow-lg shadow-base-950/40 animate-message-in">
                      <div className="flex items-center gap-3 mb-3">
                        <div className="relative flex h-2 w-2">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                          <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
                        </div>
                        <span className="label-mono text-cyan-400 font-semibold tracking-wider text-[11px]">CLARIFYING QUESTION</span>
                        <div className="flex-1 h-px bg-base-800/80" />
                      </div>
                      <div className="text-[14.5px] text-base-100 leading-relaxed font-display font-light select-text pr-2">
                        <Markdown content={question} />
                      </div>
                      {options && options.length > 0 && (
                        <div className="mt-4 flex flex-col gap-2">
                          {options.map((option, idx) => (
                            onOptionClick ? (
                              <button
                                key={idx}
                                onClick={() => onOptionClick(option)}
                                className="flex items-center gap-3 px-4 py-2.5 bg-base-900/60 border border-base-700 hover:border-cyan-500/50 hover:bg-cyan-500/[0.03] transition-all text-base-200 hover:text-cyan-300 tick-corners text-[13px] font-mono text-left group"
                              >
                                <span className="w-4 h-4 rounded-full border border-base-600 group-hover:border-cyan-500 flex items-center justify-center text-[9px] font-sans text-base-500 group-hover:text-cyan-400 font-bold transition-all">
                                  {String.fromCharCode(65 + idx)}
                                </span>
                                <span>{option}</span>
                              </button>
                            ) : (
                              <button
                                key={idx}
                                disabled
                                className="flex items-center gap-3 px-4 py-2.5 bg-base-900/20 border border-base-800 text-base-500 tick-corners text-[13px] font-mono text-left cursor-not-allowed opacity-60"
                              >
                                <span className="w-4 h-4 rounded-full border border-base-800 flex items-center justify-center text-[9px] font-sans text-base-600 font-bold">
                                  {String.fromCharCode(65 + idx)}
                                </span>
                                <span>{option}</span>
                              </button>
                            )
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })()
              ) : showDetails ? (
                <ToolCallBlock
                  key={i}
                  toolName={formatToolName(block.tool) || "Tool"}
                  toolArgs={block.tool.toolArgs}
                  result={block.tool.result}
                  isRunning={block.tool.isRunning}
                />
              ) : null // collapsed into AgentActivity below when not in detail mode
            ) : block.content.trim() ? (
              <Markdown key={i} content={block.content} />
            ) : null
          )}

          {/* Minimal, non-technical activity feed (default view) */}
          {!showDetails && <AgentActivity toolCalls={activityTools} />}

          {/* Files this turn produced. Shown at the message's own level (not
              behind the technical-details toggle) because the deliverable is
              the point of the turn for a non-technical reader, while the
              tool call that made it is an implementation detail. */}
          {onArtifactClick && files.length > 0 && (
            <div className="mt-4 space-y-2">
              <span className="label-mono block text-base-500">
                {files.length === 1 ? "FILE" : `FILES · ${files.length}`}
              </span>
              {files.map((f) => (
                <ArtifactCard key={f} path={f} onOpen={onArtifactClick} />
              ))}
            </div>
          )}
        </div>

        {/* Subagent activity — simple by default, detailed on toggle */}
        {hasActivity && (
          <div className="mt-5 pt-4 border-t border-base-700">
            {subagents && subagents.length > 0 && (
              showDetails ? (
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <span className="label-mono text-base-500">FLEET</span>
                    <div className="flex-1 flex items-center gap-2">
                      <div className="flex-1 h-px bg-base-700 relative overflow-hidden">
                        <div
                          className="absolute inset-y-0 left-0 bg-blue-400 transition-all duration-500"
                          style={{
                            width: `${subagents.length > 0 ? Math.round((subagents.filter((s) => s.status !== "started").length / subagents.length) * 100) : 0}%`,
                          }}
                        />
                      </div>
                      <span className="label-mono text-base-400 tabular-nums">
                        {subagents.filter((s) => s.status !== "started").length.toString().padStart(2, "0")}
                        <span className="text-base-600 mx-0.5">/</span>
                        {subagents.length.toString().padStart(2, "0")}
                      </span>
                    </div>
                  </div>
                  {subagents.map((sa) => (
                    <SubagentCard key={sa.name} subagent={sa} />
                  ))}
                </div>
              ) : (
                <SimpleActivityFeed subagents={subagents} />
              )
            )}

            {/* Single toggle for the whole message's detail level. Non-technical
                users stay in the plain-English view; anyone who wants the raw
                tool calls / subagent fleet can opt in. */}
            <button
              onClick={() => setShowDetails((v) => !v)}
              className="mt-2 text-[12px] text-blue-400/70 hover:text-blue-300 transition-colors px-3 py-1"
            >
              {showDetails ? "← Simple view" : "Show technical details →"}
            </button>
          </div>
        )}

        {/* Trace */}
        {traceUrl && (
          <div className="mt-4 pt-3 border-t border-base-700">
            <a
              href={traceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="label-mono text-blue-400/80 hover:text-blue-300 inline-flex items-center gap-2 transition-colors"
            >
              <svg width="11" height="11" viewBox="0 0 16 16" fill="none">
                <path d="M6 3H3a1 1 0 00-1 1v9a1 1 0 001 1h9a1 1 0 001-1v-3M10 3h3v3M6 10L13.5 2.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              LANGSMITH TRACE
            </a>
          </div>
        )}
      </div>
    </div>
  );
}

// Memoized: previous messages must not re-render when a streaming token
// mutates the tail message. Comparing the actual fields that drive output
// keeps the equality check cheap even for long histories — no array deep
// scans, just reference checks on content / toolCalls / attachments /
// subagents. The streaming message's content reference changes per token
// (setMessages spreads a new object) so React still updates it.
function areEqual(prev: Props, next: Props) {
  const a = prev.message;
  const b = next.message;
  return (
    a.id === b.id &&
    a.content === b.content &&
    a.role === b.role &&
    a.agentName === b.agentName &&
    a.traceUrl === b.traceUrl &&
    a.toolCalls === b.toolCalls &&
    a.attachments === b.attachments &&
    a.reasoning === b.reasoning &&
    prev.subagents === next.subagents &&
    prev.onOptionClick === next.onOptionClick &&
    prev.onArtifactClick === next.onArtifactClick
  );
}

const ChatMessage = memo(ChatMessageImpl, areEqual);
export default ChatMessage;
