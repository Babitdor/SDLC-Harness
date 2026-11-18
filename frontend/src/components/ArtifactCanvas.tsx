"use client";

import { useState, useEffect, useMemo, startTransition, useRef } from "react";
import Markdown from "./Markdown";
import MermaidHighlight from "./MermaidHighlight";
import { api } from "../lib/api";
import type { ArtifactContent } from "../lib/types";

interface Props {
  projectId: string;
  threadId: string;
  artifactName: string | null;
  onClose: () => void;
}

const LANG_LABELS: Record<string, string> = {
  markdown: "MARKDOWN",
  mermaid: "MERMAID",
  html: "HTML",
  drawio: "DRAW.IO",
  json: "JSON",
  yaml: "YAML",
  gherkin: "GHERKIN",
  text: "TEXT",
};

// Hand-built glyph per language — a tiny SVG sigil instead of generic
// emoji. Reads as a technical sigil column on the toolbar.
function LangGlyph({ language }: { language: string }) {
  const cls = "text-blue-400/80 flex-shrink-0";
  switch (language) {
    case "markdown":
      return (
        <svg width="14" height="14" viewBox="0 0 14 14" className={cls} fill="none" stroke="currentColor" strokeWidth="1.25">
          <rect x="1" y="2" width="12" height="10" />
          <path d="M3 9 V5 L5 7 L7 5 V9" />
          <path d="M9 5 V9 M9 9 L11 7" />
        </svg>
      );
    case "mermaid":
      return (
        <svg width="14" height="14" viewBox="0 0 14 14" className={cls} fill="none" stroke="currentColor" strokeWidth="1.25">
          <rect x="1" y="1" width="5" height="5" />
          <rect x="8" y="8" width="5" height="5" />
          <line x1="6" y1="3.5" x2="8" y2="3.5" />
          <line x1="3.5" y1="6" x2="3.5" y2="8" />
          <line x1="6" y1="6" x2="8" y2="8" />
        </svg>
      );
    case "html":
      return (
        <svg width="14" height="14" viewBox="0 0 14 14" className={cls} fill="none" stroke="currentColor" strokeWidth="1.25">
          <path d="M2 4 L5 7 L2 10" />
          <path d="M12 4 L9 7 L12 10" />
          <line x1="6" y1="11" x2="8" y2="3" />
        </svg>
      );
    case "drawio":
      return (
        <svg width="14" height="14" viewBox="0 0 14 14" className={cls} fill="none" stroke="currentColor" strokeWidth="1.25">
          <rect x="1" y="2" width="4" height="3" />
          <rect x="9" y="2" width="4" height="3" />
          <rect x="5" y="9" width="4" height="3" />
          <line x1="3" y1="5" x2="7" y2="9" />
          <line x1="11" y1="5" x2="7" y2="9" />
        </svg>
      );
    case "json":
      return (
        <svg width="14" height="14" viewBox="0 0 14 14" className={cls} fill="none" stroke="currentColor" strokeWidth="1.25">
          <path d="M4 2 Q1 2 1 5 V6 Q1 7 0.5 7 Q1 7 1 8 V9 Q1 12 4 12" />
          <path d="M10 2 Q13 2 13 5 V6 Q13 7 13.5 7 Q13 7 13 8 V9 Q13 12 10 12" />
        </svg>
      );
    default:
      return (
        <svg width="14" height="14" viewBox="0 0 14 14" className={cls} fill="none" stroke="currentColor" strokeWidth="1.25">
          <rect x="2" y="1" width="10" height="12" />
          <line x1="4" y1="4" x2="10" y2="4" />
          <line x1="4" y1="7" x2="10" y2="7" />
          <line x1="4" y1="10" x2="8" y2="10" />
        </svg>
      );
  }
}

// Above this many bytes, markdown defaults to source mode (ReactMarkdown
// + remark-gfm + syntax-highlighter is synchronous and can lock the main
// thread for tens of seconds on big files — long enough that users assume
// the tab is hung. The user can still flip to preview manually if they
// accept the wait.
const HEAVY_PREVIEW_BYTES = 8 * 1024;

// Hard cap on chars rendered inline (both preview and source). Above this
// we render only the prefix and show a "Show full content" button — the
// same pattern as ToolCallBlock. 12 KB keeps first paint well under 200ms
// even with syntax-highlighter doing prism tokenization.
const MAX_INLINE_CHARS = 12 * 1024;

export default function ArtifactCanvas({ projectId, threadId, artifactName, onClose }: Props) {
  const [content, setContent] = useState<ArtifactContent | null>(null);
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

  // "preview" | "source" — preview is the rendered view (markdown / html
  // iframe); source is the raw text. Mermaid diagrams and the yaml /
  // gherkin artifacts preview as highlighted source.
  const [viewMode, setViewMode] = useState<"preview" | "source">("preview");
  // Opt-in flag for rendering past MAX_INLINE_CHARS. Resets whenever the
  // active artifact changes.
  const [showFull, setShowFull] = useState(false);
  const [actionsOpen, setActionsOpen] = useState(false);

  useEffect(() => {
    if (!artifactName) {
      setContent(null);
      return;
    }
    let cancelled = false;
    // Clear the previous file's content so we don't render the OLD heavy
    // markdown while the NEW file is being fetched — that was making the
    // click feel like it locked the tab even though the freeze was just
    // re-renders of the prior content.
    setContent(null);
    setLoading(true);
    setError(null);
    setShowFull(false);
    setActionsOpen(false);
    api
      .getArtifactContent(projectId, threadId, artifactName)
      .then((data) => {
        if (cancelled) return;
        const canPreview =
          data.language === "markdown" ||
          data.language === "html" ||
          data.language === "drawio" ||
          data.language === "mermaid" ||
          data.language === "yaml" ||
          data.language === "gherkin";
        // For markdown over HEAVY_PREVIEW_BYTES, default to source mode.
        // ReactMarkdown and the Mermaid tokenizer are synchronous and can
        // freeze the tab on a big file. HTML / drawio stay in preview
        // because the iframe parses in its own document.
        const heavyText =
          data.language === "markdown" &&
          data.size > HEAVY_PREVIEW_BYTES;
        const nextMode: "preview" | "source" =
          canPreview && !heavyText ? "preview" : "source";

        // startTransition deprioritises the (potentially heavy) commit
        // that draws the file body, so the loading spinner / artifact
        // toolbar update first and the click doesn't appear to hang.
        startTransition(() => {
          setContent(data);
          setViewMode(nextMode);
        });
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [projectId, threadId, artifactName]);


  // Build the iframe srcdoc for .drawio previews. The vendored
  // viewer-static.min.js (from jgraph/drawio) is served from
  // /drawio/viewer-static.min.js and exposes GraphViewer globally; it
  // auto-renders any element with class "mxgraph" and a data-mxgraph
  // JSON config. We embed the raw XML inside a hidden <textarea> (which
  // safely round-trips entities) and let an inline script wire the config
  // up after the script loads — this avoids the awkward JSON-in-attribute
  // escape dance and keeps the XML readable in the DOM for debugging.
  const drawioSrcDoc = useMemo(() => {
    if (!content || content.language !== "drawio") return "";
    const escaped = content.content
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
    return `<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  html, body { margin: 0; padding: 0; height: 100%; background: #faf6ef; }
  #viewer { width: 100vw; height: 100vh; }
  .mxgraph { width: 100% !important; max-width: 100% !important; }
  /* draw.io's viewer injects a toolbar — give it a warm-paper background
     so it blends with the surrounding artifact panel. */
  .geToolbarContainer { background: #f3ecdd !important; border-bottom: 1px solid #d6c7a8 !important; }
</style>
</head>
<body>
<textarea id="xml-source" style="display:none">${escaped}</textarea>
<div id="viewer"></div>
<script src="/drawio/viewer-static.min.js"></script>
<script>
  (function () {
    var src = document.getElementById('xml-source').value;
    var host = document.getElementById('viewer');
    host.className = 'mxgraph';
    host.setAttribute('data-mxgraph', JSON.stringify({
      xml: src,
      highlight: '#cb7421',
      nav: true,
      resize: true,
      'toolbar-position': 'inside',
      toolbar: 'zoom layers tags',
      'auto-fit': true,
      'allow-zoom-in': true,
      'allow-zoom-out': true
    }));
    if (typeof GraphViewer !== 'undefined' && GraphViewer.processElements) {
      GraphViewer.processElements();
    }
  })();
</script>
</body>
</html>`;
  }, [content]);

  // Build the iframe srcdoc for HTML previews. We wrap the file content
  // in a host shell that injects a minimal stylesheet ONLY if the
  // document is fragment-shaped (no <html>/<body>) — so a complete
  // HTML artifact with its own styles renders untouched, while a bare
  // fragment still gets readable defaults. Sandboxed: scripts run but
  // no top-level navigation.
  const previewSrcDoc = useMemo(() => {
    if (!content || content.language !== "html") return "";
    const raw = content.content;
    const looksLikeFullDoc = /<html[\s>]/i.test(raw) || /<!doctype/i.test(raw);
    if (looksLikeFullDoc) return raw;
    // Fragment shell — gives an HTML artifact emitted as a partial doc a
    // sane background, decent font, and readable SVG defaults.
    return `<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  html, body { margin: 0; padding: 0; background: #faf6ef; color: #2a1f17; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }
  body { padding: 24px; min-height: 100vh; box-sizing: border-box; }
  svg { display: block; max-width: 100%; height: auto; }
  /* Warm palette for partial fragments so they read cohesively
     rather than as black-on-white. */
  .node rect { stroke: #2a1f17; stroke-width: 0.5; }
  .node text { fill: #2a1f17; font-size: 12px; }
  .link { fill: none; stroke-opacity: 0.35; }
  .link:hover { stroke-opacity: 0.65; }
</style>
</head>
<body>
${raw}
</body>
</html>`;
  }, [content]);

  if (!artifactName) return null;

  const basename = artifactName.includes("/")
    ? artifactName.split("/").pop()!
    : artifactName;

  const canPreview =
    content &&
    (content.language === "markdown" ||
      content.language === "html" ||
      content.language === "drawio" ||
      content.language === "mermaid" ||
      content.language === "yaml" ||
      content.language === "gherkin");

  return (
    <div ref={containerRef} className="flex flex-col h-full w-full bg-base-950 border-l border-base-700">
      {/* Toolbar — instrument bar matching the main header */}
      <div className="flex items-center gap-3 px-4 h-14 border-b border-base-700 flex-shrink-0 bg-base-950/60 backdrop-blur-sm overflow-hidden">
        <button
          onClick={onClose}
          className="text-base-400 hover:text-blue-300 transition-colors p-1"
          title="Close preview"
          aria-label="Close"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
        <div className="w-px h-5 bg-base-700 flex-shrink-0" />
        <LangGlyph language={content?.language || "text"} />
        <div className="flex flex-col leading-none min-w-0 flex-shrink mr-auto">
          {panelWidth >= 480 && <span className="label-mono text-base-500 mb-1">ARTIFACT</span>}
          <span className="font-mono text-[13px] text-base-100 truncate max-w-[120px]">
            {basename}
          </span>
        </div>
        {content && panelWidth >= 550 && (
          <span className="label-mono px-2 py-1 border border-base-700 text-base-400 flex-shrink-0">
            {LANG_LABELS[content.language] || content.language.toUpperCase()}
          </span>
        )}
        {content && panelWidth >= 620 && (
          <span className="label-mono text-base-600 tabular-nums flex-shrink-0">
            {content.size > 1024
              ? `${(content.size / 1024).toFixed(1)} KB`
              : `${content.size} B`}
          </span>
        )}


        {/* Preview / Source toggle — shown for markdown and html */}
        {canPreview && (
          <div className="flex border border-base-700 overflow-hidden flex-shrink-0">
            <button
              onClick={() => setViewMode("preview")}
              title="Preview Mode"
              className={
                "label-mono py-1.5 transition-colors flex items-center justify-center " +
                (panelWidth < 680 ? "px-2" : "px-2.5") + " " +
                (viewMode === "preview"
                  ? "bg-blue-400/15 text-blue-300"
                  : "text-base-500 hover:text-base-200")
              }
            >
              {panelWidth < 680 ? (
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
              onClick={() => setViewMode("source")}
              title="Source Code"
              className={
                "label-mono py-1.5 transition-colors flex items-center justify-center " +
                (panelWidth < 680 ? "px-2" : "px-2.5") + " " +
                (viewMode === "source"
                  ? "bg-blue-400/15 text-blue-300"
                  : "text-base-500 hover:text-base-200")
              }
            >
              {panelWidth < 680 ? (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="16 18 22 12 16 6" />
                  <polyline points="8 6 2 12 8 18" />
                </svg>
              ) : (
                "SOURCE"
              )}
            </button>
          </div>
        )}

        {content && panelWidth >= 550 && (
          <button
            onClick={() => navigator.clipboard.writeText(content.content)}
            className={"label-mono text-base-500 hover:text-blue-300 py-1.5 border border-base-700 hover:border-base-500 transition-colors flex items-center justify-center flex-shrink-0 " + (panelWidth < 680 ? "px-2" : "px-3")}
            title="Copy to clipboard"
          >
            {panelWidth < 680 ? (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
              </svg>
            ) : (
              "COPY"
            )}
          </button>
        )}

        {/* Download — always available once the file resolves. */}
        {artifactName && panelWidth >= 550 && (
          <div className="flex border border-base-700 overflow-hidden flex-shrink-0">
            <a
              href={api.downloadUrl(projectId, threadId, artifactName)}
              className={"label-mono text-base-500 hover:text-blue-300 py-1.5 transition-colors flex items-center justify-center " + (panelWidth < 680 ? "px-2" : "px-2.5")}
              title={`Download ${basename}`}
              download={basename}
            >
              {panelWidth < 680 ? (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2-2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="7 10 12 15 17 10" />
                  <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
              ) : (
                "DOWNLOAD"
              )}
            </a>
            {artifactName.toLowerCase().endsWith(".md") && (
              <>
                <div className="w-px bg-base-700" />
                <a
                  href={api.downloadUrl(projectId, threadId, artifactName, "pdf")}
                  className={"label-mono text-blue-400/80 hover:text-blue-300 py-1.5 transition-colors flex items-center justify-center " + (panelWidth < 680 ? "px-2" : "px-2.5")}
                  title="Render this markdown as a PDF and download it"
                  download={basename.replace(/\.md$/i, ".pdf")}
                >
                  PDF
                </a>
              </>
            )}
          </div>
        )}

        {/* More Actions dropdown menu for small width */}
        {content && panelWidth < 550 && (
          <div className="relative flex-shrink-0">
            <button
              onClick={() => setActionsOpen(!actionsOpen)}
              className="label-mono text-base-500 hover:text-blue-300 py-1.5 px-2 border border-base-700 hover:border-base-500 transition-colors flex items-center justify-center"
              title="More actions"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="1.5" />
                <circle cx="12" cy="5" r="1.5" />
                <circle cx="12" cy="19" r="1.5" />
              </svg>
            </button>
            {actionsOpen && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setActionsOpen(false)} />
                <div className="absolute right-0 mt-1 w-48 bg-base-900 border border-base-700 shadow-xl z-20 flex flex-col py-1">
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(content.content);
                      setActionsOpen(false);
                    }}
                    className="w-full text-left px-3 py-2 text-[12px] font-mono text-base-300 hover:bg-base-800 transition-colors flex items-center gap-2"
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                    </svg>
                    COPY TO CLIPBOARD
                  </button>
                  <div className="h-px bg-base-800 my-1" />
                  <a
                    href={api.downloadUrl(projectId, threadId, artifactName)}
                    className="w-full text-left px-3 py-2 text-[12px] font-mono text-base-300 hover:bg-base-800 transition-colors flex items-center gap-2"
                    title={`Download ${basename}`}
                    download={basename}
                    onClick={() => setActionsOpen(false)}
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                      <polyline points="7 10 12 15 17 10" />
                      <line x1="12" y1="15" x2="12" y2="3" />
                    </svg>
                    DOWNLOAD RAW
                  </a>
                  {artifactName.toLowerCase().endsWith(".md") && (
                    <>
                      <div className="h-px bg-base-800 my-1" />
                      <a
                        href={api.downloadUrl(projectId, threadId, artifactName, "pdf")}
                        className="w-full text-left px-3 py-2 text-[12px] font-mono text-blue-400 hover:bg-base-800 transition-colors flex items-center gap-2"
                        title="Download as PDF"
                        download={basename.replace(/\.md$/i, ".pdf")}
                        onClick={() => setActionsOpen(false)}
                      >
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                          <polyline points="14 2 14 8 20 8" />
                          <line x1="16" y1="13" x2="8" y2="13" />
                          <line x1="16" y1="17" x2="8" y2="17" />
                          <polyline points="10 9 9 9 8 9" />
                        </svg>
                        DOWNLOAD PDF
                      </a>
                    </>
                  )}
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* Content area */}
      <div className="flex-1 overflow-y-auto overflow-x-auto relative">
        {loading && (
          <div className="flex items-center justify-center h-full">
            <div className="flex flex-col items-center gap-4">
              <div className="w-5 h-5 border border-blue-400 border-t-transparent rounded-full animate-spin" />
              <span className="label-mono text-base-500">LOADING ARTIFACT</span>
            </div>
          </div>
        )}

        {error && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md">
              <div className="label-mono text-danger-400 mb-2">— FAILED —</div>
              <p className="font-display text-xl text-base-100 italic">
                Could not load this artifact.
              </p>
              <p className="font-mono text-[11px] text-base-500 mt-3">{error}</p>
            </div>
          </div>
        )}

        {/* HTML PREVIEW — sandboxed iframe so embedded styles/scripts
            render properly. allow-scripts is required because some
            artifacts compute layout in JS. */}
        {content && viewMode === "preview" && content.language === "html" && (
          <iframe
            srcDoc={previewSrcDoc}
            // allow-same-origin needed so cross-origin CDN scripts (Plotly,
            // D3) load correctly. Without it, the sandboxed document has an
            // opaque `null` origin and integrity-checked CDN script loads
            // silently fail. Same trade-off the drawio iframe below
            // already makes.
            sandbox="allow-scripts allow-same-origin"
            title={basename}
            className="w-full h-full border-0 bg-[#faf6ef]"
          />
        )}

        {/* DRAW.IO PREVIEW — vendored viewer-static.min.js renders the
            mxGraphModel XML into a pan/zoom canvas. allow-scripts is
            required (GraphViewer parses XML and lays out the graph in
            JS); allow-same-origin lets the viewer fetch its shape
            stencils + styles from /drawio/ relative URLs on this host. */}
        {content && viewMode === "preview" && content.language === "drawio" && (
          <iframe
            srcDoc={drawioSrcDoc}
            sandbox="allow-scripts allow-same-origin"
            title={basename}
            className="w-full h-full border-0 bg-[#faf6ef]"
          />
        )}

        {content && viewMode === "preview" && content.language === "markdown" && (() => {
          const oversized = content.content.length > MAX_INLINE_CHARS && !showFull;
          const rendered = oversized
            ? content.content.slice(0, MAX_INLINE_CHARS)
            : content.content;
          return (
            <div className="p-8 max-w-4xl">
              <Markdown content={rendered} />
              {oversized && (
                <TruncationNotice
                  hidden={content.content.length - MAX_INLINE_CHARS}
                  warning="Rendering the full markdown can take several seconds for large files."
                  onShowFull={() => setShowFull(true)}
                />
              )}
            </div>
          );
        })()}

        {/* Mermaid diagrams preview as highlighted source — rendering the
            SVG needs a mermaid runtime, which the toolchain does not ship. */}
        {content && viewMode === "preview" && content.language === "mermaid" && (
          <MermaidHighlight code={content.content} />
        )}

        {content && viewMode === "source" && (() => {
          const oversized = content.content.length > MAX_INLINE_CHARS && !showFull;
          const rendered = oversized
            ? content.content.slice(0, MAX_INLINE_CHARS)
            : content.content;
          return (
            <div>
              {/* whitespace-pre (no break-words) avoids the per-character
                  break-opportunity calculation that locks the layout
                  engine on files with very long unbroken lines (JSON
                  dumps, log files, base64 blobs). Long lines scroll
                  horizontally instead. */}
              <pre className="p-6 font-mono text-[12px] text-base-300 leading-relaxed whitespace-pre overflow-x-auto">
                <code>{rendered}</code>
              </pre>
              {oversized && (
                <div className="px-6 pb-6">
                  <TruncationNotice
                    hidden={content.content.length - MAX_INLINE_CHARS}
                    warning="Showing the full file requires laying out every line — may briefly freeze the tab."
                    onShowFull={() => setShowFull(true)}
                  />
                </div>
              )}
            </div>
          );
        })()}

      </div>
    </div>
  );
}


// ── Inline truncation notice ────────────────────────────────────────────
// Shown at the bottom of large markdown / source previews so the user can
// opt into rendering the full file. Phrased to make it clear that doing so
// can be slow — same trade-off pattern as ToolCallBlock.

function TruncationNotice({
  hidden,
  warning,
  onShowFull,
}: {
  hidden: number;
  warning: string;
  onShowFull: () => void;
}) {
  return (
    <div className="my-4 px-4 py-3 border border-blue-400/40 bg-blue-400/[0.04] flex flex-col gap-2">
      <div className="label-mono text-blue-400/80">
        TRUNCATED · {hidden.toLocaleString()} CHARS HIDDEN
      </div>
      <p className="font-display text-[12px] text-base-400 italic leading-snug">
        {warning}
      </p>
      <button
        onClick={onShowFull}
        className="self-start mt-1 label-mono px-3 py-1.5 border border-blue-400/60 bg-blue-400/10 text-blue-300 hover:bg-blue-400/20 transition-all"
      >
        SHOW FULL CONTENT ↓
      </button>
    </div>
  );
}
