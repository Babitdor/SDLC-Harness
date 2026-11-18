"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { ComponentPropsWithoutRef, memo, useMemo } from "react";
import TodoList, { extractTodoList } from "./TodoList";

interface MarkdownProps {
  content: string;
  className?: string;
}

/**
 * Renders markdown with syntax highlighting and todo list extraction.
 * Detects Deep Agents "Updated todo list to [...]" patterns and
 * renders them as a proper progress tracker.
 */
function MarkdownImpl({ content, className }: MarkdownProps) {
  // Strip YAML frontmatter first — react-markdown/remark-gfm don't parse it,
  // so an un-stripped `---\nkey: val\n---` block spills into the body as a
  // run-on paragraph. We render it as a styled metadata header instead.
  const fm = useMemo(() => extractFrontmatter(content), [content]);
  const body = fm ? fm.body : content;

  // fenceCodeBlocks is O(N) line-scan with multiple regex tests; it runs
  // for every sibling state update unless memoized. extractTodoList does
  // a similar full-content scan. Skip both when `content` is unchanged.
  const processed = useMemo(() => fenceCodeBlocks(body), [body]);
  const todo = useMemo(() => extractTodoList(processed), [processed]);

  const frontmatter = fm && fm.meta.length > 0 ? <FrontmatterCard meta={fm.meta} /> : null;

  const fencedBefore = useMemo(
    () => (todo?.before ? fenceCodeBlocks(todo.before) : ""),
    [todo?.before]
  );
  const fencedAfter = useMemo(
    () => (todo?.after ? fenceCodeBlocks(todo.after) : ""),
    [todo?.after]
  );

  if (todo) {
    return (
      <div className={`min-w-0 overflow-hidden ${className || ""}`}>
        {frontmatter}
        {todo.before && (
          <div className="prose-sm">
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
              {fencedBefore}
            </ReactMarkdown>
          </div>
        )}
        <TodoList items={todo.items} />
        {todo.after && (
          <div className="prose-sm">
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
              {fencedAfter}
            </ReactMarkdown>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={`min-w-0 overflow-hidden ${className || ""}`}>
      {frontmatter}
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
        {processed}
      </ReactMarkdown>
    </div>
  );
}

/**
 * Extract a leading YAML frontmatter block (`---\n…\n---`) from markdown.
 * Returns the parsed key/value pairs (order-preserving) plus the remaining
 * body, or null when the content has no frontmatter. Intentionally a
 * lightweight line parser — frontmatter here is flat `key: value` pairs
 * (values may be inline `[a, b]` arrays), not arbitrary YAML.
 */
function extractFrontmatter(
  content: string
): { meta: Array<[string, string]>; body: string } | null {
  const m = /^\s*---[ \t]*\r?\n([\s\S]*?)\r?\n---[ \t]*(?:\r?\n|$)/.exec(content);
  if (!m) return null;
  const meta: Array<[string, string]> = [];
  for (const line of m[1].split(/\r?\n/)) {
    const kv = /^([A-Za-z0-9_-]+):\s*(.*)$/.exec(line);
    if (kv) meta.push([kv[1], kv[2].trim()]);
  }
  return { meta, body: content.slice(m[0].length) };
}

/** Render extracted frontmatter as a compact metadata header. */
function FrontmatterCard({ meta }: { meta: Array<[string, string]> }) {
  const parseTags = (v: string): string[] =>
    v
      .replace(/^\[|\]$/g, "")
      .split(",")
      .map((t) => t.trim().replace(/^["']|["']$/g, ""))
      .filter(Boolean);

  return (
    <div className="mb-4 border border-base-700/50 rounded-md bg-base-900/40 px-4 py-3">
      <dl className="space-y-1.5">
        {meta.map(([key, value]) => {
          const isTags = key.toLowerCase() === "tags" && value.includes("[");
          return (
            <div key={key} className="flex gap-3 items-baseline">
              <dt className="label-mono text-base-500 shrink-0 w-24 truncate uppercase">
                {key}
              </dt>
              <dd className="text-sm text-base-300 min-w-0 break-words">
                {isTags ? (
                  <span className="flex flex-wrap gap-1.5">
                    {parseTags(value).map((t) => (
                      <span
                        key={t}
                        className="px-1.5 py-0.5 rounded bg-base-800 text-blue-300 text-xs font-mono border border-base-700/30"
                      >
                        {t}
                      </span>
                    ))}
                  </span>
                ) : (
                  value
                )}
              </dd>
            </div>
          );
        })}
      </dl>
    </div>
  );
}

// Memoized so a parent re-render (e.g. a sibling subagent token) doesn't
// re-walk markdown for unchanged content. Default shallow compare is safe:
// `content` is a string and `className` is a stable literal.
const Markdown = memo(MarkdownImpl);
export default Markdown;

/**
 * Detect un-fenced code blocks in markdown content and wrap them.
 * Handles agent output that includes code without triple-backtick fences,
 * including line-numbered code and orphan line numbers on their own line.
 */
function fenceCodeBlocks(content: string): string {
  const lines = content.split("\n");
  const result: string[] = [];
  let i = 0;

  // Keywords that signal we're in a code block — Mermaid diagram headers,
  // Gherkin steps and OpenAPI/YAML top-level keys.
  const codeKeywords = /\b(openapi|asyncapi|sequenceDiagram|classDiagram|erDiagram|flowchart|Scenario|Given|When|Then)\b/;
  // Mermaid diagrams start with a bare header line, which is the reliable
  // signal that the block is a diagram rather than prose.
  const mermaidPattern = /^\s*(sequenceDiagram|classDiagram|stateDiagram(-v2)?|erDiagram|flowchart|graph)\b/;

  function isNumberedLine(l: string): boolean {
    return /^\s*\d{1,4}\s{2,}\S/.test(l);
  }
  function isOrphanNumber(l: string): boolean {
    return /^\s*\d{1,4}\s*$/.test(l);
  }
  function isCodeLine(l: string): boolean {
    return codeKeywords.test(l) || mermaidPattern.test(l) || /^\s*\/\//.test(l);
  }

  while (i < lines.length) {
    const line = lines[i];

    // Check if this line starts a code block
    const isNumbered = isNumberedLine(line);
    const isOrphan = isOrphanNumber(line);
    const isCode = isCodeLine(line);

    // Start of a code block: numbered line with >= 3 chars of code,
    // or an orphan number followed by code, or a strong code keyword.
    const startsBlock =
      (isNumbered && line.length > 8) ||  // numbered + substantial code
      (isOrphan && i + 1 < lines.length && (isCodeLine(lines[i + 1]) || isNumberedLine(lines[i + 1]))) ||
      (isCode && line.length > 10 && !line.startsWith("#"));

    if (startsBlock) {
      const codeLines: string[] = [];

      while (i < lines.length) {
        const l = lines[i];

        // Stop at markdown headings, todo lists, or horizontal rules
        if (/^#{1,4}\s/.test(l)) break;
        if (/^Updated todo list/.test(l)) break;
        if (/^---/.test(l) && l.replace(/-/g, "").trim() === "") break;

        // Numbered line — strip the number
        const nm = l.match(/^\s*(\d{1,4})\s{2,}(.*)/);
        if (nm) {
          codeLines.push(nm[2] || "");
          i++;
          continue;
        }

        // Orphan number — skip it, code follows on next line
        if (isOrphanNumber(l)) {
          i++;
          continue;
        }

        // Blank line within code block — keep it
        if (l.trim() === "") {
          codeLines.push("");
          i++;
          continue;
        }

        // Regular code line (no number) — keep if we're in a code block
        if (codeLines.length > 0 && (isCodeLine(l) || /^[\s{}()]/.test(l) || /^\s*\w+.*[:{]/.test(l))) {
          codeLines.push(l);
          i++;
          continue;
        }

        // Not code — stop
        break;
      }

      if (codeLines.filter((c) => c.trim()).length >= 3) {
        const combined = codeLines.join("\n");
        const lang = mermaidPattern.test(combined) ? "mermaid" : "text";
        result.push("```" + lang);
        result.push(...codeLines);
        result.push("```");
        continue;
      }

      // Not enough lines to form a code block — add raw and ensure we
      // advance past the start line so the loop doesn't spin forever.
      if (codeLines.length > 0) {
        result.push(...codeLines);
      } else {
        result.push(line);
        i++;  // ← critical: prevents infinite loop on false starts
      }
      continue;
    }

    result.push(line);
    i++;
  }

  return result.join("\n");
}

/** Shared markdown component overrides */
const mdComponents: Record<string, React.ComponentType<any>> = {
  code(props: ComponentPropsWithoutRef<"code"> & { className?: string; inline?: boolean }) {
    const { className: cls, children, inline, ...rest } = props;
    const match = /language-(\w+)/.exec(cls || "");
    const codeString = String(children).replace(/\n$/, "");

    // ── Fenced code block (with or without language) ─────────────────
    if (!inline && (match || String(children).includes("\n"))) {
      const lang = match?.[1] || "text";
      // Map unsupported languages to fallbacks that produce reasonable highlighting
      const languageMap: Record<string, string> = {
        mermaid: "jsx",  // Mermaid looks like structured text; jsx gives decent highlighting
      };
      return (
        <div className="my-3 rounded-md border border-base-700/40 overflow-hidden max-w-full">
          <SyntaxHighlighter
            style={oneDark}
            language={languageMap[lang] || lang}
            PreTag="div"
            className="!bg-base-900 !m-0 max-w-full"
            customStyle={{
              fontSize: "0.8rem",
              lineHeight: "1.5",
              overflowX: "auto",
              whiteSpace: "pre",
            }}
          >
            {codeString}
          </SyntaxHighlighter>
        </div>
      );
    }

    // ── Inline code ──────────────────────────────────────────────────
    return (
      <code
        className="bg-base-800 text-blue-300 px-1.5 py-0.5 rounded text-sm font-mono border border-base-700/30"
        {...rest}
      >
        {children}
      </code>
    );
  },

  table({ children }) {
    return (
      <div className="overflow-x-auto my-3">
        <table className="min-w-full border border-base-600/40 rounded-md overflow-hidden">
          {children}
        </table>
      </div>
    );
  },

  th({ children }) {
    return (
      <th className="bg-base-800/80 px-3 py-2 text-left text-sm font-mono font-semibold text-base-200 border-b border-base-600/40">
        {children}
      </th>
    );
  },

  td({ children }) {
    return (
      <td className="px-3 py-2 text-sm text-base-300 border-b border-base-700/30">
        {children}
      </td>
    );
  },

  a({ href, children }) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="text-cyan-400 hover:text-cyan-300 underline underline-offset-2 transition-colors"
      >
        {children}
      </a>
    );
  },

  blockquote({ children }) {
    return (
      <blockquote className="border-l-4 border-cyan-500/30 pl-4 my-3 text-base-400 italic">
        {children}
      </blockquote>
    );
  },

  // Headings — display serif italic, the Instrument Serif character
  // shows best at these sizes. Italic ties them visually to the rest
  // of the editorial display language used in the app shell.
  h1: ({ children }) => <h1 className="text-3xl font-display italic mt-6 mb-3 text-base-100 leading-tight">{children}</h1>,
  h2: ({ children }) => <h2 className="text-2xl font-display italic mt-5 mb-2 text-base-100 leading-tight">{children}</h2>,
  h3: ({ children }) => <h3 className="text-xl font-display italic mt-4 mb-2 text-base-100 leading-tight">{children}</h3>,

  ul({ children }) {
    return <ul className="list-disc list-inside my-2 space-y-1 text-base-300">{children}</ul>;
  },

  ol({ children }) {
    return <ol className="list-decimal list-inside my-2 space-y-1 text-base-300">{children}</ol>;
  },

  p({ children }) {
    return <p className="my-1.5 leading-relaxed text-base-300">{children}</p>;
  },

  hr() {
    return <hr className="border-base-700 my-4" />;
  },
};