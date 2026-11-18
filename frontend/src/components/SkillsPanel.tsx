"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import type { SkillInfo } from "../lib/types";

interface Props {
  /** Visible when the SKILLS tab is active. */
  active: boolean;
  onSelectSkill: (name: string | null) => void;
  selectedSkill: string | null;
}

export default function SkillsPanel({ active, onSelectSkill, selectedSkill }: Props) {
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listSkills();
      setSkills(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (active) refresh();
  }, [active, refresh]);

  return (
    <div className="flex-grow flex flex-col min-h-0 bg-base-900/10">
      {/* Panel header instructions */}
      <div className="flex-shrink-0 px-5 pt-4 pb-3 border-b border-base-700 bg-base-950/20">
        <h3 className="label-mono text-base-300">AGENT SKILLS</h3>
        <p className="font-display text-[12px] text-base-500 italic mt-1.5 leading-snug">
          Instructions and learned patterns that guide specialist agent behavior. Click a skill to edit.
        </p>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-4">
        {loading && skills.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 gap-3">
            <div className="w-4 h-4 border border-blue-400 border-t-transparent rounded-full animate-spin" />
            <span className="label-mono text-base-500">LOADING SKILLS</span>
          </div>
        )}

        {error && (
          <div className="p-3 border border-danger-400/30 bg-danger-400/5 text-danger-400 text-[12px] rounded mb-3">
            {error}
          </div>
        )}

        {!loading && skills.length === 0 && !error && (
          <div className="text-center py-12 text-base-500 font-mono text-[12px]">
            No skills found in the filesystem.
          </div>
        )}

        <div className="space-y-1">
          {skills.map((skill) => {
            const isSelected = selectedSkill === skill.name;
            return (
              <button
                key={skill.name}
                onClick={() => onSelectSkill(isSelected ? null : skill.name)}
                className={
                  "w-full text-left px-4 py-3 transition-all relative flex flex-col gap-1 border border-transparent rounded " +
                  (isSelected
                    ? "bg-blue-400/10 border-blue-400/30 text-blue-300"
                    : "hover:bg-base-800/40 text-base-300 hover:text-base-100")
                }
              >
                {/* Active indicator bar */}
                {isSelected && (
                  <div className="absolute left-0 top-0 bottom-0 w-1 bg-blue-400 rounded-l" />
                )}
                
                <div className="font-mono text-[13px] font-medium truncate uppercase tracking-wider">
                  {skill.name.replace(/-/g, " ")}
                </div>
                
                <div className="flex items-center gap-3 mt-1.5">
                  <span className={
                    "text-[10px] font-mono px-1.5 py-0.5 rounded border " + 
                    (skill.has_skill 
                      ? "border-blue-400/30 bg-blue-400/5 text-blue-300/80" 
                      : "border-base-700 bg-base-800/20 text-base-500")
                  }>
                    SKILL.md
                  </span>
                  <span className={
                    "text-[10px] font-mono px-1.5 py-0.5 rounded border " + 
                    (skill.has_learned 
                      ? "border-amber-400/30 bg-amber-400/5 text-amber-300/80" 
                      : "border-base-700 bg-base-800/20 text-base-500")
                  }>
                    LEARNED.md
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
