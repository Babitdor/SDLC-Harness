"""Binary document preview — converts .docx, .pdf, .xlsx to HTML, and
markdown → PDF for the download flow.

Each preview converter accepts raw bytes and returns an HTML string
suitable for the sandboxed iframe in ArtifactCanvas.  Errors are returned
as styled HTML fragments so the user sees a readable explanation rather
than a blank panel.

``markdown_to_pdf`` returns raw PDF bytes for the download endpoint.
"""

from __future__ import annotations

import html
import logging
import re

logger = logging.getLogger(__name__)


def _error_html(reason: str) -> str:
    """Return a self-contained HTML error page for preview failures."""
    return f"""<!doctype html>
<html>
<head><meta charset="utf-8"><style>
  body {{ margin:48px; font-family:system-ui,sans-serif; background:#1a1a1a; color:#ccc; }}
  h2 {{ color:#e05d5d; font-weight:300; }}
  p {{ font-family:monospace; font-size:13px; color:#999; }}
</style></head>
<body><h2>Preview unavailable</h2><p>{reason}</p></body>
</html>"""


def preview_docx(data: bytes) -> str:
    """Convert a .docx file to clean HTML via mammoth."""
    try:
        from io import BytesIO

        import mammoth

        result = mammoth.convert_to_html(BytesIO(data))
        if result.messages:
            logger.warning("mammoth warnings: %s", result.messages)
        return result.value
    except Exception as exc:
        logger.exception("DOCX preview failed")
        return _error_html(f"Could not convert Word document: {exc}")


def preview_pdf(data: bytes) -> str:
    """Extract text from a PDF and wrap in styled HTML via PyMuPDF.

    PDF text is HTML-escaped before injection — a previous version of this
    code interpolated raw text into the HTML, so any document containing
    ``<``, ``>``, or ``&`` produced broken markup the iframe couldn't
    render. Per-page text is wrapped in a ``<pre>``-equivalent div with
    ``white-space: pre-wrap`` so paragraph breaks survive verbatim.
    """
    try:
        import pymupdf

        doc = pymupdf.open(stream=data, filetype="pdf")
        pages: list[str] = []
        for page in doc:  # type: ignore[union-attr]
            text = page.get_text()  # type: ignore[union-attr]
            if text.strip():
                pages.append(
                    '<div class="page" style="margin-bottom:24px; '
                    "padding:24px; background:#faf6ef; color:#2a1f17; "
                    "font-family:serif; font-size:15px; line-height:1.6; "
                    'white-space:pre-wrap; max-width:720px;">'
                    f"{html.escape(text)}"
                    "</div>"
                )
        doc.close()
        if not pages:
            return _error_html("PDF contains no extractable text (may be scanned/image-based).")
        return f"""<!doctype html>
<html>
<head><meta charset="utf-8"><style>
  body {{ margin:0; padding:16px; background:#0a0a0a; }}
</style></head>
<body>{''.join(pages)}</body>
</html>"""
    except Exception as exc:
        logger.exception("PDF preview failed")
        return _error_html(f"Could not convert PDF: {exc}")


def preview_xlsx(data: bytes) -> str:
    """Convert an .xlsx workbook to an HTML table via xlsx2html."""
    try:
        from io import BytesIO

        from xlsx2html import xlsx2html

        out = xlsx2html(BytesIO(data))
        out.seek(0)
        html = out.read()
        # xlsx2html returns a full HTML document — wrap for iframe
        return html
    except Exception as exc:
        logger.exception("XLSX preview failed")
        return _error_html(f"Could not convert spreadsheet: {exc}")


# ── Dispatcher ──────────────────────────────────────────────────────────

_CONVERTERS: dict[str, callable] = {
    "docx": preview_docx,
    "pdf": preview_pdf,
    "xlsx": preview_xlsx,
    "xls": preview_xlsx,
}


def preview_binary(ext: str, data: bytes) -> str | None:
    """Convert binary file content to HTML preview.

    Returns None if the extension has no registered converter (caller
    should fall back to raw text / hex dump).
    """
    converter = _CONVERTERS.get(ext.lower())
    if converter is None:
        return None
    return converter(data)


# ── Markdown → PDF (download flow) ───────────────────────────────────────


# Minimal print stylesheet — pinned widths, serif body, neutral colors so
# the PDF reads cleanly when printed or shared. Tweaked specifically for
# the SDLC report style (long-form artifacts, code blocks, tables).
_PDF_CSS = """
@page { size: A4; margin: 24mm 18mm; }
body { font-family: 'Helvetica', 'Arial', sans-serif; font-size: 11pt;
       line-height: 1.5; color: #1a1a1a; }
h1, h2, h3, h4 { font-family: 'Times New Roman', Times, serif;
                 font-weight: 600; color: #0a0a0a; margin-top: 18pt;
                 margin-bottom: 6pt; line-height: 1.25; }
h1 { font-size: 22pt; border-bottom: 1pt solid #888; padding-bottom: 4pt; }
h2 { font-size: 17pt; }
h3 { font-size: 13pt; }
h4 { font-size: 11pt; text-transform: uppercase; letter-spacing: 0.06em; }
p, li { margin: 4pt 0; }
ul, ol { padding-left: 18pt; }
code { font-family: 'Courier New', monospace; font-size: 10pt;
       background: #f1efea; padding: 1pt 3pt; border-radius: 2pt; }
pre { background: #f1efea; padding: 8pt 10pt; border-left: 2pt solid #888;
      font-family: 'Courier New', monospace; font-size: 9.5pt;
      line-height: 1.45; white-space: pre-wrap; word-break: break-word; }
pre code { background: transparent; padding: 0; }
blockquote { border-left: 2pt solid #888; padding-left: 10pt; color: #555;
             font-style: italic; margin: 6pt 0; }
table { border-collapse: collapse; margin: 8pt 0; width: 100%; }
th, td { border: 0.5pt solid #888; padding: 4pt 6pt; font-size: 10pt;
         text-align: left; vertical-align: top; }
th { background: #ececec; font-weight: 600; }
hr { border: 0; border-top: 0.5pt solid #888; margin: 12pt 0; }
a { color: #1f5fa8; text-decoration: none; }
img { max-width: 100%; }
"""


# Leading YAML frontmatter block: ``---\n<flat key: value pairs>\n---``.
# Mirrors the frontend's Markdown.tsx extractor so the PDF and the in-app
# preview treat frontmatter identically rather than dumping it as a stray
# <hr> + run-on paragraph at the top of the document.
_FRONTMATTER_RE = re.compile(
    r"^\s*---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)", re.DOTALL
)


def _strip_frontmatter(text: str) -> tuple[list[tuple[str, str]], str]:
    """Split a leading YAML frontmatter block from *text*.

    Returns ``(meta_pairs, body)``. When there's no frontmatter, returns
    ``([], text)`` unchanged. Lightweight line parser — frontmatter here is
    flat ``key: value`` pairs (values may be inline ``[a, b]`` arrays), not
    arbitrary YAML.
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return [], text
    meta: list[tuple[str, str]] = []
    for line in m.group(1).splitlines():
        kv = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if kv:
            meta.append((kv.group(1), kv.group(2).strip()))
    return meta, text[m.end():]


def _frontmatter_markdown(meta: list[tuple[str, str]]) -> str:
    """Render frontmatter pairs as a clean markdown header block.

    Emits bolded ``**Key:** value`` lines so the metadata reads as a tidy
    header in the PDF instead of raw YAML. Returns "" when there's nothing
    to render.
    """
    if not meta:
        return ""
    lines = [f"**{key.capitalize()}:** {value}" for key, value in meta]
    return "  \n".join(lines) + "\n\n---\n\n"


def markdown_to_pdf(text: str, *, title: str | None = None) -> bytes:
    """Render *text* (markdown) to PDF bytes using the ``markdown-pdf`` lib.

    Wraps ``markdown_pdf.MarkdownPdf`` with our print stylesheet so the
    output has consistent typography across machines. The package is built
    on PyMuPDF (already a backend dep), so install footprint is minimal.

    Any leading YAML frontmatter is stripped and re-rendered as a clean
    metadata header so it doesn't leak into the PDF as raw ``key: value``
    text — matching the in-app markdown preview.

    Raises ``RuntimeError`` if the library isn't installed; the caller
    should surface this as a 501 / actionable HTTP error.
    """
    try:
        from markdown_pdf import MarkdownPdf, Section
    except ImportError as exc:
        msg = (
            "markdown-pdf is not installed. Add it to backend dependencies "
            "(`pip install markdown-pdf`) and restart the server."
        )
        raise RuntimeError(msg) from exc

    meta, body = _strip_frontmatter(text)
    rendered = _frontmatter_markdown(meta) + body

    pdf = MarkdownPdf(toc_level=0, optimize=True)
    if title:
        pdf.meta["title"] = title
    section = Section(rendered, paper_size="A4")
    pdf.add_section(section, user_css=_PDF_CSS)

    # ``save_bytes(BytesIO)`` writes the finalised PDF into the buffer;
    # there's no in-place bytes accessor on the underlying DocumentWriter.
    from io import BytesIO

    buf = BytesIO()
    pdf.save_bytes(buf)
    return buf.getvalue()
