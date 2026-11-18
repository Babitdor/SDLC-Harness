"use client";

import { memo, useMemo } from "react";

/**
 * Lightweight Mermaid / UML syntax highlighter.
 *
 * react-syntax-highlighter's Prism build has no Mermaid grammar, and the
 * `.mmd` preview would otherwise fall back to a generic tokenizer that
 * mis-colours diagram keywords, cardinality tokens and edge labels. This is
 * a self-contained regex tokenizer instead — deterministic, dependency-free,
 * and accurate for the keyword set the diagram agent actually emits. Colours
 * follow the oneDark palette used by the markdown code blocks so the two
 * previews read consistently.
 */

// Mermaid diagram keywords. Kept flat (single-word) — constructs like
// `autonumber` or `stateDiagram-v2` are matched as whole words where the
// tokenizer sees them.
const MERMAID_KEYWORDS = new Set<string>([
  // Diagram headers + direction
  "sequenceDiagram", "classDiagram", "stateDiagram", "stateDiagram-v2",
  "erDiagram", "flowchart", "graph", "gantt", "journey", "pie", "quadrantChart",
  "gitGraph", "mindmap", "timeline", "TB", "TD", "BT", "RL", "LR", "direction",
  // Blocks + structure
  "subgraph", "end", "class", "classDef", "style", "linkStyle",
  // Sequence
  "participant", "actor", "autonumber", "activate", "deactivate", "Note",
  "loop", "alt", "else", "opt", "par", "and", "rect", "critical", "break",
  // State
  "state", "as",
  // Class / ER members
  "namespace",
]);

type TokenKind =
  | "comment"
  | "string"
  | "number"
  | "keyword"
  | "type"
  | "operator"
  | "plain";

const TOKEN_COLORS: Record<TokenKind, string> = {
  comment: "#7f848e", // muted gray (italic) — %% lines
  string: "#98c379", // green
  number: "#d19a66", // orange
  keyword: "#c678dd", // purple
  type: "#61afef", // blue — Capitalised entity / class names
  operator: "#56b6c2", // cyan — arrows, cardinality, braces
  plain: "#c9c9c9", // default identifier / text
};

// One global tokenizer pass. Order matters: comments and strings first so
// their contents are not re-tokenised, then cardinality tokens, arrows,
// numbers, words, and finally any single punctuation char.
const TOKEN_RE =
  /(%[^\n]*)|("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')|(\|\|--o\{|\|\|--\|\{|\}o--\|\||\|o--\|\||\|\|--\|\|)|(-->>|->>|--x|-x|-->|->|---)|(\b\d+(?:\.\d+)?\b)|([A-Za-z_]\w*)|([=:;,{}()[\]<>+\-*/|.])/g;

interface Token {
  text: string;
  kind: TokenKind;
}

function tokenize(code: string): Token[] {
  const tokens: Token[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  TOKEN_RE.lastIndex = 0;
  while ((m = TOKEN_RE.exec(code)) !== null) {
    // Emit any plain text skipped between matches (whitespace, unknowns).
    if (m.index > last) {
      tokens.push({ text: code.slice(last, m.index), kind: "plain" });
    }
    const [full, comment, str, card, arrow, num, word, op] = m;
    if (comment !== undefined) tokens.push({ text: full, kind: "comment" });
    else if (str !== undefined) tokens.push({ text: full, kind: "string" });
    else if (card !== undefined || arrow !== undefined)
      tokens.push({ text: full, kind: "operator" });
    else if (num !== undefined) tokens.push({ text: full, kind: "number" });
    else if (word !== undefined) {
      const kind: TokenKind = MERMAID_KEYWORDS.has(word)
        ? "keyword"
        : /^[A-Z]/.test(word)
          ? "type" // Capitalised → likely an entity / class name
          : "plain";
      tokens.push({ text: full, kind });
    } else if (op !== undefined) tokens.push({ text: full, kind: "operator" });
    last = TOKEN_RE.lastIndex;
  }
  if (last < code.length) {
    tokens.push({ text: code.slice(last), kind: "plain" });
  }
  return tokens;
}

function MermaidHighlightImpl({ code }: { code: string }) {
  const tokens = useMemo(() => tokenize(code), [code]);
  return (
    <pre className="p-6 font-mono text-[12px] leading-relaxed whitespace-pre overflow-x-auto bg-base-900/40">
      <code>
        {tokens.map((t, i) =>
          t.kind === "plain" ? (
            <span key={i} style={{ color: TOKEN_COLORS.plain }}>
              {t.text}
            </span>
          ) : (
            <span
              key={i}
              style={{
                color: TOKEN_COLORS[t.kind],
                fontStyle: t.kind === "comment" ? "italic" : undefined,
              }}
            >
              {t.text}
            </span>
          )
        )}
      </code>
    </pre>
  );
}

// Memoised — tokenizing is O(n) and only depends on `code`.
const MermaidHighlight = memo(MermaidHighlightImpl);
export default MermaidHighlight;
