import { describe, it, expect } from "vitest";
import {
  SUBAGENTS,
  AGENT_MAP,
  findAgent,
  isUnresolvedAgentName,
  customAgentToInfo,
  CUSTOM_AGENTS_CHANGED_EVENT,
  PHASE_ORDER,
  PHASE_LABELS,
} from "../agents";

describe("SUBAGENTS", () => {
  it("should have exactly 7 agents", () => {
    expect(SUBAGENTS).toHaveLength(7);
  });

  it("should include all expected agents", () => {
    const names = SUBAGENTS.map((a) => a.name);
    expect(names).toContain("Ingestion");
    expect(names).toContain("Requirements");
    expect(names).toContain("Architecture");
    expect(names).toContain("API");
    expect(names).toContain("Planning");
    expect(names).toContain("DevOps");
    expect(names).toContain("Diagram");
  });

  it("should have unique names", () => {
    const names = SUBAGENTS.map((a) => a.name);
    expect(new Set(names).size).toBe(names.length);
  });

  it("should run in phase order 1-5", () => {
    // Two agents share a phase where the work is parallel (design, planning).
    const phases = SUBAGENTS.map((a) => a.phase).sort((a, b) => a - b);
    expect(phases).toEqual([1, 2, 3, 3, 4, 4, 5]);
  });

  it("should have icons for all agents", () => {
    for (const agent of SUBAGENTS) {
      expect(agent.icon).toBeTruthy();
    }
  });

  it("should have descriptions for all agents", () => {
    for (const agent of SUBAGENTS) {
      expect(agent.desc).toBeTruthy();
    }
  });

  it("should have produces for all agents", () => {
    for (const agent of SUBAGENTS) {
      expect(agent.produces).toBeTruthy();
    }
  });
});

describe("AGENT_MAP", () => {
  it("should map all agent names to their info", () => {
    for (const agent of SUBAGENTS) {
      expect(AGENT_MAP[agent.name]).toEqual(agent);
    }
  });
});

describe("findAgent", () => {
  it("should find agents by display name", () => {
    const agent = findAgent("Architecture");
    expect(agent).toBeDefined();
    expect(agent!.name).toBe("Architecture");
  });

  it("should find agents case-insensitively", () => {
    const agent = findAgent("architecture");
    expect(agent).toBeDefined();
    expect(agent!.name).toBe("Architecture");
  });

  it("should find agents in mixed case", () => {
    const agent = findAgent("ARCHitecture");
    expect(agent).toBeDefined();
    expect(agent!.name).toBe("Architecture");
  });

  it("should return undefined for unknown agents", () => {
    expect(findAgent("UnknownAgent")).toBeUndefined();
  });

  it("should return undefined for undefined input", () => {
    expect(findAgent(undefined)).toBeUndefined();
  });

  it("should return undefined for empty string", () => {
    expect(findAgent("")).toBeUndefined();
  });
});

describe("isUnresolvedAgentName", () => {
  it("flags leaked LangGraph tool namespaces", () => {
    expect(
      isUnresolvedAgentName("tools:01199e4f-b184-c4af-7d01-6ea442580424"),
    ).toBe(true);
    expect(isUnresolvedAgentName("01199e4f-b184-c4af-7d01-6ea442580424")).toBe(true);
  });

  it("does not flag real agent names or empty input", () => {
    expect(isUnresolvedAgentName("architecture")).toBe(false);
    expect(isUnresolvedAgentName("Ingestion")).toBe(false);
    expect(isUnresolvedAgentName("my-custom-agent")).toBe(false);
    expect(isUnresolvedAgentName("")).toBe(false);
    expect(isUnresolvedAgentName(undefined)).toBe(false);
  });
});

describe("customAgentToInfo", () => {
  it("should convert a custom agent to AgentInfo shape", () => {
    const result = customAgentToInfo({
      name: "my-helper",
      description: "A helpful custom agent",
    });
    expect(result.name).toBe("my-helper");
    expect(result.desc).toBe("A helpful custom agent");
    expect(result.icon).toBe("✨");
    expect(result.phase).toBe(0);
    expect(result.produces).toBe("");
    expect(result.custom).toBe(true);
  });
});

describe("CUSTOM_AGENTS_CHANGED_EVENT", () => {
  it("should be a string event name", () => {
    expect(CUSTOM_AGENTS_CHANGED_EVENT).toBe("custom-agents-changed");
  });
});

describe("PHASE_ORDER", () => {
  it("should have 5 phases in the correct order", () => {
    expect(PHASE_ORDER).toEqual([
      "sources",
      "requirements",
      "design",
      "planning",
      "diagrams",
    ]);
  });
});

describe("PHASE_LABELS", () => {
  it("should have labels for all phases", () => {
    for (const phase of PHASE_ORDER) {
      expect(PHASE_LABELS[phase]).toBeTruthy();
    }
  });

  it("should have uppercase labels", () => {
    expect(PHASE_LABELS.sources).toBe("SOURCES");
    expect(PHASE_LABELS.requirements).toBe("REQUIREMENTS");
    expect(PHASE_LABELS.design).toBe("DESIGN");
    expect(PHASE_LABELS.planning).toBe("PLANNING");
    expect(PHASE_LABELS.diagrams).toBe("DIAGRAMS");
  });
});
