// Agent definitions shared across components

export interface AgentInfo {
  name: string;
  icon: string;
  desc: string;
  phase: number;
  produces: string;
  /** True for user-created subagents. Rendered with a CUSTOM badge instead
   * of a phase number; the backend orchestrator routes @mentions identically. */
  custom?: boolean;
}

/** Adapt a backend-stored CustomAgent into the UI's AgentInfo shape so the
 * mention dropdown can list it alongside built-in subagents. */
export function customAgentToInfo(c: {
  name: string;
  description: string;
}): AgentInfo {
  return {
    name: c.name,
    icon: "✨",
    desc: c.description,
    phase: 0,
    produces: "",
    custom: true,
  };
}

/** Event name dispatched by AgentsPanel after a successful create/update/
 * delete. Any listener — currently ChatInput — refetches its local copy
 * of the custom-agent roster so the @mention dropdown stays in sync
 * without an explicit prop pipe. */
export const CUSTOM_AGENTS_CHANGED_EVENT = "custom-agents-changed";

export const SUBAGENTS: AgentInfo[] = [
  { name: "Ingestion", icon: "📥", desc: "Extract requirements, glossary & constraints", phase: 1, produces: "REQUIREMENTS.md, GLOSSARY.md, CONSTRAINTS.md" },
  { name: "Requirements", icon: "📋", desc: "User stories & acceptance criteria", phase: 2, produces: "USER_STORIES.md, ACCEPTANCE_CRITERIA.md" },
  { name: "Architecture", icon: "📐", desc: "Components, data model & ADRs", phase: 3, produces: "ARCHITECTURE.md, DATA_MODEL.md, ADR.md" },
  { name: "API", icon: "🔌", desc: "Endpoint contract & validated OpenAPI", phase: 3, produces: "API_SPEC.md, openapi.yaml" },
  { name: "Planning", icon: "🗂️", desc: "Backlog & test plan", phase: 4, produces: "BACKLOG.md, TEST_PLAN.md" },
  { name: "DevOps", icon: "⚙️", desc: "CI stages & validated pipeline file", phase: 4, produces: "CI_CD.md, ci/pipeline.yml" },
  { name: "Diagram", icon: "🔧", desc: "One validated Mermaid model per call", phase: 5, produces: "*.mmd" },
];

export const AGENT_MAP = Object.fromEntries(SUBAGENTS.map((a) => [a.name, a]));

// Case-insensitive lookup. The backend emits subagent names in lowercase
// ("ingestion", "architecture", "devops") because that's how they're keyed
// in the Deep Agents subagent dict, but the UI's canonical AgentInfo uses
// display casing ("Ingestion", "Architecture", "DevOps"). This helper
// bridges the two without forcing either side to match the other's
// convention.
const AGENT_MAP_LOWER: Record<string, AgentInfo> = Object.fromEntries(
  SUBAGENTS.map((a) => [a.name.toLowerCase(), a])
);
export function findAgent(name: string | undefined): AgentInfo | undefined {
  if (!name) return undefined;
  return AGENT_MAP[name] ?? AGENT_MAP_LOWER[name.toLowerCase()];
}

/**
 * True when a subagent "name" is actually an unresolved LangGraph namespace
 * that leaked through instead of a real agent — e.g. "tools:01199e4f-b184-…"
 * (the internal tool-execution subgraph the backend couldn't map back to a
 * `@subagent` delegation) or a bare run UUID. These should never be shown to
 * the user as-is; callers render the activity instead, or drop the entry.
 */
export function isUnresolvedAgentName(name: string | undefined): boolean {
  if (!name) return false;
  return (
    /^tools:/i.test(name) ||
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i.test(name)
  );
}

// Phase folders in the wiki-style workspace layout. Matches the backend's
// EXPECTED_ARTIFACTS keys (see backend/src/sdlc/services/artifacts.py).
export type WorkspacePhase =
  | "sources"
  | "requirements"
  | "design"
  | "planning"
  | "diagrams";

export interface ArtifactInfo {
  /** Phase-qualified path, e.g. "requirements/REQUIREMENTS.md". */
  name: string;
  /** Which phase folder this artifact lives in. */
  phase: WorkspacePhase;
  status: "ready" | "pending";
  agent: string;
}

// Render order for phase groups in the Inspector + display labels.
export const PHASE_ORDER: WorkspacePhase[] = [
  "sources",
  "requirements",
  "design",
  "planning",
  "diagrams",
];

export const PHASE_LABELS: Record<WorkspacePhase, string> = {
  sources: "SOURCES",
  requirements: "REQUIREMENTS",
  design: "DESIGN",
  planning: "PLANNING",
  diagrams: "DIAGRAMS",
};