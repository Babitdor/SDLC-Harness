import { useState, useEffect, useRef } from "react";
import Markdown from "./Markdown";
import { api } from "../lib/api";
import type { SkillDetailsResponse } from "../lib/types";

interface Props {
  skillName: string;
  onClose: () => void;
}

export default function SkillCanvas({ skillName, onClose }: Props) {
  const [data, setData] = useState<SkillDetailsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [panelWidth, setPanelWidth] = useState(800);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setPanelWidth(entry.contentRect.width);
      }
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const [activeTab, setActiveTab] = useState<"SKILL.md" | "LEARNED.md">("SKILL.md");
  const [editMode, setEditMode] = useState(false);
  
  // Edit buffers
  const [skillBuffer, setSkillBuffer] = useState("");
  const [learnedBuffer, setLearnedBuffer] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  const fetchDetails = () => {
    setLoading(true);
    setError(null);
    api.getSkillDetails(skillName)
      .then((res) => {
        setData(res);
        setSkillBuffer(res.skill_content);
        setLearnedBuffer(res.learned_content);
      })
      .catch((err) => {
        setError(err.message || "Failed to load skill files");
      })
      .finally(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchDetails();
    setEditMode(false);
    setSaveMessage(null);
  }, [skillName]);

  const handleSave = async () => {
    setSaving(true);
    setSaveMessage(null);
    try {
      const updated = await api.updateSkillDetails(skillName, skillBuffer, learnedBuffer);
      setData(updated);
      setSaveMessage("Saved changes successfully!");
      setEditMode(false);
      setTimeout(() => setSaveMessage(null), 3000);
    } catch (err: any) {
      setSaveMessage(`Error saving: ${err.message || String(err)}`);
    } finally {
      setSaving(false);
    }
  };

  const activeContent = activeTab === "SKILL.md" ? (data?.skill_content || "") : (data?.learned_content || "");
  const activeBuffer = activeTab === "SKILL.md" ? skillBuffer : learnedBuffer;
  
  const handleBufferChange = (val: string) => {
    if (activeTab === "SKILL.md") {
      setSkillBuffer(val);
    } else {
      setLearnedBuffer(val);
    }
  };

  const displayName = skillName.replace(/-/g, " ").toUpperCase();

  return (
    <div ref={containerRef} className="flex flex-col h-full w-full bg-base-950 border-l border-base-700">
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-4 h-14 border-b border-base-700 flex-shrink-0 bg-base-950/60 backdrop-blur-sm overflow-hidden">
        <button
          onClick={onClose}
          className="text-base-400 hover:text-blue-300 transition-colors p-1 flex-shrink-0"
          title="Close skill editor"
          aria-label="Close"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
        <div className="w-px h-5 bg-base-700 flex-shrink-0" />
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-blue-400/80 flex-shrink-0">
          <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
          <polyline points="14 2 14 8 20 8" />
        </svg>
        <div className="flex flex-col leading-none min-w-0 mr-auto flex-shrink">
          {panelWidth >= 480 && <span className="label-mono text-base-500 mb-1">SKILL</span>}
          <span className="font-mono text-[13px] text-base-100 truncate max-w-[120px]">
            {displayName}
          </span>
        </div>

        {/* Tab switch inside toolbar */}
        <div className="flex border border-base-700 overflow-hidden ml-2 flex-shrink-0">
          {(["SKILL.md", "LEARNED.md"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => {
                setActiveTab(tab);
                setSaveMessage(null);
              }}
              className={
                "label-mono py-1.5 transition-colors border-r last:border-r-0 border-base-700 flex items-center justify-center " +
                (panelWidth < 520 ? "px-2 text-[10px]" : "px-3") + " " +
                (activeTab === tab
                  ? "bg-blue-400/15 text-blue-300"
                  : "text-base-500 hover:text-base-200")
              }
            >
              {panelWidth < 520 ? tab.replace(".md", "") : tab}
            </button>
          ))}
        </div>

        {/* Save messages / Status indicator */}
        {saveMessage && (
          <span className={`label-mono text-[11px] px-2 py-1 border flex-shrink-0 ${
            saveMessage.startsWith("Error") ? "border-danger-400/30 text-danger-400 bg-danger-400/5" : "border-success/30 text-success bg-success/5"
          }`}>
            {panelWidth < 520 ? (saveMessage.startsWith("Error") ? "ERR" : "SAVED") : saveMessage}
          </span>
        )}

        {/* Edit / Preview toggle */}
        {data && (
          <div className="flex border border-base-700 overflow-hidden flex-shrink-0 ml-2">
            <button
              onClick={() => setEditMode(false)}
              title="Preview Mode"
              className={
                "label-mono py-1.5 transition-colors flex items-center justify-center " +
                (panelWidth < 520 ? "px-2" : "px-2.5") + " " +
                (!editMode
                  ? "bg-blue-400/15 text-blue-300"
                  : "text-base-500 hover:text-base-200")
              }
            >
              {panelWidth < 520 ? (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
              ) : (
                "PREVIEW"
              )}
            </button>
            <div className="w-px bg-base-700" />
            <button
              onClick={() => setEditMode(true)}
              title="Edit Mode"
              className={
                "label-mono py-1.5 transition-colors flex items-center justify-center " +
                (panelWidth < 520 ? "px-2" : "px-2.5") + " " +
                (editMode
                  ? "bg-blue-400/15 text-blue-300"
                  : "text-base-500 hover:text-base-200")
              }
            >
              {panelWidth < 520 ? (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-7" />
                  <path d="M18.5 2.5a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                </svg>
              ) : (
                "EDIT"
              )}
            </button>
          </div>
        )}

        {editMode && (
          <button
            onClick={handleSave}
            disabled={saving}
            className={"label-mono py-1.5 border border-success/60 bg-success/10 text-success hover:bg-success/20 transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0 " + (panelWidth < 520 ? "px-2" : "px-3")}
            title="Save changes"
          >
            {saving ? (
              <div className="w-3 h-3 border border-success border-t-transparent rounded-full animate-spin" />
            ) : (
              panelWidth < 520 ? (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
                  <polyline points="17 21 17 13 7 13 7 21" />
                  <polyline points="7 3 7 8 15 8" />
                </svg>
              ) : null
            )}
            {panelWidth < 520 ? "" : (saving ? "SAVING..." : "SAVE")}
          </button>
        )}
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto relative bg-base-950">
        {loading && (
          <div className="flex items-center justify-center h-full">
            <div className="flex flex-col items-center gap-4">
              <div className="w-5 h-5 border border-blue-400 border-t-transparent rounded-full animate-spin" />
              <span className="label-mono text-base-500">LOADING SKILL</span>
            </div>
          </div>
        )}

        {error && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md">
              <div className="label-mono text-danger-400 mb-2">— FAILED —</div>
              <p className="font-display text-xl text-base-100 italic">
                Could not load skill details.
              </p>
              <p className="font-mono text-[11px] text-base-500 mt-3">{error}</p>
            </div>
          </div>
        )}

        {data && !editMode && (
          <div className="p-8 max-w-4xl min-h-full">
            {activeContent ? (
              <Markdown content={activeContent} />
            ) : (
              <div className="text-center py-24 text-base-500 font-mono text-[13px] border border-dashed border-base-800 rounded">
                This file is empty. Select EDIT to add content.
              </div>
            )}
          </div>
        )}

        {data && editMode && (
          <div className="w-full h-full flex flex-col p-4 bg-base-900/30">
            <textarea
              value={activeBuffer}
              onChange={(e) => handleBufferChange(e.target.value)}
              className="w-full flex-grow p-4 bg-base-950 text-base-300 font-mono text-[12px] leading-relaxed border border-base-800 rounded resize-none focus:outline-none focus:border-blue-400/50 focus:ring-1 focus:ring-blue-400/20"
              placeholder={`Write markdown for ${activeTab}...`}
            />
          </div>
        )}
      </div>
    </div>
  );
}
