"use client";

/**
 * Detects and renders Deep Agents todo lists from assistant messages.
 *
 * Pattern: Updated todo list to [{...}]
 * Also handles simpler numbered/bulleted task lists.
 */

export interface TodoItem {
  content: string;
  status: "in_progress" | "pending" | "completed" | "failed";
}

/**
 * Parse "Updated todo list to [{...}]" from message content.
 * Returns { before, items, after } or null if no todo list found.
 */
export function extractTodoList(content: string): {
  before: string;
  items: TodoItem[];
  after: string;
} | null {
  // Pattern: "Updated todo list to [...]" at start of a line
  const todoPattern = /Updated todo list to \[([\s\S]*?)\]/;
  const match = content.match(todoPattern);
  if (!match) return null;

  const fullMatch = match[0];
  const arrayStr = match[1];

  const items: TodoItem[] = [];

  // Try to parse as Python-style dicts: {'content': '...', 'status': '...'}
  // They use single quotes, not double quotes
  const dictPattern = /\{[^}]*'content':\s*'([^']*)'[^}]*'status':\s*'([^']*)'[^}]*\}/g;
  let m;
  while ((m = dictPattern.exec(arrayStr)) !== null) {
    items.push({
      content: m[1],
      status: m[2] as TodoItem["status"],
    });
  }

  // Fallback: try double-quoted dicts
  if (items.length === 0) {
    const dictPattern2 = /\{[^}]*"content":\s*"([^"]*)"[^}]*"status":\s*"([^"]*)"[^}]*\}/g;
    while ((m = dictPattern2.exec(arrayStr)) !== null) {
      items.push({
        content: m[1],
        status: m[2] as TodoItem["status"],
      });
    }
  }

  if (items.length === 0) return null;

  const matchStart = content.indexOf(fullMatch);
  const before = content.substring(0, matchStart).trim();
  const after = content.substring(matchStart + fullMatch.length).trim();

  return { before, items, after };
}

// Drafting-style status marks — hand-built shapes, not emoji. Reads
// as engineering iconography (checkmark, square, hourglass-bar, cross).
function StatusMark({ status }: { status: TodoItem["status"] }) {
  switch (status) {
    case "in_progress":
      return (
        <span className="relative flex items-center justify-center w-4 h-4 flex-shrink-0">
          <span className="absolute inset-0 border border-blue-500 rotate-45" />
          <span className="absolute inset-[3px] bg-blue-500 rotate-45 animate-pulse-glow" />
        </span>
      );
    case "completed":
      return (
        <svg width="14" height="14" viewBox="0 0 14 14" className="text-success flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="2 7 6 11 12 3" />
        </svg>
      );
    case "failed":
      return (
        <svg width="14" height="14" viewBox="0 0 14 14" className="text-danger-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
          <line x1="3" y1="3" x2="11" y2="11" />
          <line x1="11" y1="3" x2="3" y2="11" />
        </svg>
      );
    default:
      return <span className="w-3 h-3 border border-base-600 rotate-45 flex-shrink-0 mt-0.5" />;
  }
}

const STATUS_TEXT = {
  in_progress: "text-blue-300",
  pending: "text-base-500",
  completed: "text-base-500 line-through decoration-base-700",
  failed: "text-danger-400",
} as const;

const STATUS_LABEL = {
  in_progress: "ACTIVE",
  pending: "PENDING",
  completed: "DONE",
  failed: "FAILED",
} as const;

const STATUS_LABEL_TONE = {
  in_progress: "text-blue-300",
  pending: "text-base-600",
  completed: "text-success",
  failed: "text-danger-400",
} as const;

interface TodoListProps {
  items: TodoItem[];
}

export default function TodoList({ items }: TodoListProps) {
  const completed = items.filter((i) => i.status === "completed").length;
  const total = items.length;
  const pct = total > 0 ? (completed / total) * 100 : 0;

  return (
    <div className="my-6 border border-base-700 bg-base-900/60 relative tick-corners-4">
      {/* Header — drafting plate. Title is a binder tab, progress is an
          instrument bar with discrete tick marks. */}
      <div className="px-5 py-4 border-b border-base-700">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-baseline gap-3">
            <span className="label-mono text-blue-400">PIPELINE</span>
            <h3 className="font-display text-base text-base-100 italic font-light">
              {completed === total ? "Complete." : "In progress…"}
            </h3>
          </div>
          <span className="label-mono text-base-400 tabular-nums">
            {completed.toString().padStart(2, "0")}
            <span className="text-base-700 mx-0.5">/</span>
            {total.toString().padStart(2, "0")}
            <span className="text-base-600 mx-1.5">·</span>
            <span className={completed === total ? "text-success" : "text-blue-300"}>
              {Math.round(pct).toString().padStart(2, "0")}%
            </span>
          </span>
        </div>

        {/* Instrument bar: thin baseline + amber fill + tick marks at
            each task boundary so it reads as a measurement rule. */}
        <div className="relative h-2 bg-base-950 border border-base-700">
          <div
            className="absolute inset-y-0 left-0 bg-blue-500 transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
          {total > 1 && Array.from({ length: total - 1 }).map((_, i) => (
            <div
              key={i}
              className="absolute top-0 bottom-0 w-px bg-base-700"
              style={{ left: `${((i + 1) / total) * 100}%` }}
            />
          ))}
        </div>
      </div>

      {/* Items — numbered, drafting-list style. Each row gets a small
          mono index, the status mark, the task text in serif italic for
          "in progress" / regular for the rest. */}
      <ol className="divide-y divide-base-700">
        {items.map((item, i) => (
          <li
            key={i}
            className={
              "flex items-start gap-3 px-5 py-3 transition-colors " +
              (item.status === "in_progress" ? "bg-blue-500/[0.05]" : "")
            }
          >
            <span className="label-mono text-base-600 tabular-nums w-5 flex-shrink-0 mt-0.5">
              {(i + 1).toString().padStart(2, "0")}
            </span>
            <StatusMark status={item.status} />
            <p
              className={
                "flex-1 text-[13px] leading-snug " +
                (item.status === "in_progress" ? "font-medium " : "") +
                STATUS_TEXT[item.status]
              }
            >
              {item.content}
            </p>
            <span className={"label-mono flex-shrink-0 mt-1 " + STATUS_LABEL_TONE[item.status]}>
              {STATUS_LABEL[item.status]}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}