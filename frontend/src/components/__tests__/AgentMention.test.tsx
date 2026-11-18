import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AgentMention, renderWithAgentMentions } from "../AgentMention";
import { SUBAGENTS } from "../../lib/agents";

describe("AgentMention", () => {
  it("should render the agent name with @ prefix", () => {
    const agent = SUBAGENTS[0]; // Ingestion
    render(<AgentMention agent={agent} />);
    expect(screen.getByText(`@${agent.name}`)).toBeTruthy();
  });

  it("should render the agent icon", () => {
    const agent = SUBAGENTS[0];
    const { container } = render(<AgentMention agent={agent} />);
    expect(container.querySelector("span")?.textContent).toContain(agent.icon);
  });

  it("should have a title attribute with the agent description", () => {
    const agent = SUBAGENTS[0];
    const { container } = render(<AgentMention agent={agent} />);
    // The outer span has the title attribute
    const outerSpan = container.querySelector("span[title]");
    expect(outerSpan?.getAttribute("title")).toBe(agent.desc);
  });
});

describe("renderWithAgentMentions", () => {
  it("should return empty array for empty text", () => {
    expect(renderWithAgentMentions("")).toEqual([]);
  });

  it("should return empty array for falsy text", () => {
    expect(renderWithAgentMentions("")).toEqual([]);
  });

  it("should render plain text without mentions", () => {
    const nodes = renderWithAgentMentions("Hello world");
    expect(nodes).toHaveLength(1);
  });

  it("should render known @mentions as AgentMention components", () => {
    const nodes = renderWithAgentMentions("Run @Architecture on this");
    // Should have: text before, AgentMention, text after
    expect(nodes.length).toBeGreaterThanOrEqual(3);
  });

  it("should render unknown @tokens as plain text", () => {
    const nodes = renderWithAgentMentions("ping me @later");
    // @later is matched by regex but not found in agent map, so it renders as
    // two fragments: text before + the unmatched @token
    expect(nodes.length).toBe(2);
  });

  it("should handle multiple mentions", () => {
    const nodes = renderWithAgentMentions("@Ingestion then @Architecture");
    expect(nodes.length).toBeGreaterThanOrEqual(3);
  });

  it("should not match email-like patterns", () => {
    const nodes = renderWithAgentMentions("email@Architecture.com");
    // The @Architecture part should not match because of the negative lookbehind
    expect(nodes).toHaveLength(1);
  });
});
