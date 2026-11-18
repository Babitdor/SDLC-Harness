"use client";

// Renders an `@AgentName` token as an inline chip — small cyan-bordered
// plate with the agent's emoji + canonical display name. Mirrors the
// assistant agent badge in ChatMessage (cyan-500/40 border, cyan-500/[0.07]
// fill) so a user's invocation visually links to the agent that will
// answer it.
//
// Unknown @tokens (custom agents not in the static SUBAGENTS list, plain
// prose like "email@gmail.com") render as untouched text — the negative
// lookbehind in the regex prevents mid-word matches, and findAgent()
// gates chip styling on a real agent match.

import { Fragment, type ReactNode } from "react";
import { findAgent, type AgentInfo } from "../lib/agents";

// Negative lookbehind keeps `email@Architecture` from matching while still
// catching mentions at the start of a string or after whitespace /
// punctuation. The captured group is the bare name (no leading `@`).
const MENTION_RE = /(?<![A-Za-z0-9_])@([A-Za-z][A-Za-z0-9_-]*)/g;

interface AgentMentionProps {
  agent: AgentInfo;
}

export function AgentMention({ agent }: AgentMentionProps) {
  return (
    <span
      // align-baseline keeps the chip on the message's text baseline so
      // it doesn't push surrounding lines apart in a multi-line message.
      // Whitespace inside the chip is non-breaking — the icon + name
      // never split across a wrap.
      className="inline-flex items-center gap-1 px-1.5 py-0.5 mx-0.5 border border-cyan-500/40 bg-cyan-500/[0.07] text-cyan-300 font-medium text-[12px] align-baseline whitespace-nowrap"
      title={agent.desc}
    >
      <span className="text-[10px] leading-none">{agent.icon}</span>
      <span>@{agent.name}</span>
    </span>
  );
}

/**
 * Split a message string into React nodes, replacing each known
 * `@AgentName` with an <AgentMention> chip. Unknown tokens stay as text.
 * Returns a flat array so the caller can drop it directly inside a JSX
 * paragraph that already has whitespace-pre-wrap for newline handling.
 */
export function renderWithAgentMentions(text: string): ReactNode[] {
  if (!text) return [];

  const nodes: ReactNode[] = [];
  let cursor = 0;
  let matchIdx = 0;

  // Reset the regex's lastIndex defensively — the global flag mutates
  // shared state if we ever reuse the same RegExp object across calls.
  MENTION_RE.lastIndex = 0;

  for (const match of text.matchAll(MENTION_RE)) {
    const [whole, name] = match;
    const start = match.index ?? 0;
    const agent = findAgent(name);

    // Leading text before this @mention, if any.
    if (start > cursor) {
      nodes.push(
        <Fragment key={`t-${matchIdx}`}>{text.slice(cursor, start)}</Fragment>
      );
    }

    if (agent) {
      nodes.push(<AgentMention key={`m-${matchIdx}`} agent={agent} />);
    } else {
      // Not a known agent — surface as plain text so prose like
      // "ping me @later" doesn't get mangled.
      nodes.push(<Fragment key={`u-${matchIdx}`}>{whole}</Fragment>);
    }

    cursor = start + whole.length;
    matchIdx += 1;
  }

  // Trailing text after the last match.
  if (cursor < text.length) {
    nodes.push(<Fragment key="t-tail">{text.slice(cursor)}</Fragment>);
  }

  return nodes;
}
