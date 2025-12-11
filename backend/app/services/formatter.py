# app/services/formatter.py
import html
from typing import List, Dict, Any, Optional

# ---- Helpers ----
def _size_to_px(size):
    try:
        return f"{int(size)}px"
    except Exception:
        return None

def _escape_text(t: str) -> str:
    return html.escape(t or "")

# ---- CSS builder ----
def _build_css_from_profile(style_profile: Dict[str, Any]) -> str:
    css_lines = []

    # Page & print defaults
    css_lines.append("@page { size: A4; margin: 24mm 18mm 24mm 18mm; }")
    css_lines.append("@media print { html, body { height: 100%; } }")

    # Body & typography
    css_lines.append("body { font-family: system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial; color: #111; line-height:1.45; }")
    css_lines.append("div.document { max-width: 800px; margin: 0 auto; }")
    css_lines.append("p { margin: 8px 0; font-size: 12pt; }")
    css_lines.append("h1,h2,h3 { margin: 14px 0 8px; font-weight:700; }")

    # Page break helpers
    css_lines.append(".page-break { page-break-after: always; break-after: page; }")
    css_lines.append("h1 { page-break-inside: avoid; }")
    css_lines.append("table { page-break-inside: avoid; }")
    css_lines.append("img { max-width: 100%; height: auto; }")

    # Table styling
    css_lines.append("table{border-collapse:collapse;width:100%;margin:10px 0} table th, table td{border:1px solid #ddd;padding:8px;text-align:left;}")

    # Preserve margin for lists
    css_lines.append("ul, ol { margin: 6px 0 6px 24px; }")

    # If top font present in style_profile, try to set it
    top_font = None
    fonts = style_profile.get("fonts_top", [])
    if fonts:
        top_font = fonts[0].get("font") if isinstance(fonts[0], dict) else (fonts[0][0] if fonts[0] else None)
    if top_font:
        css_lines.append(f"body {{ font-family: '{top_font}', sans-serif; }}")

    return "<style>\n" + "\n".join(css_lines) + "\n</style>"

# ---- Rendering primitives ----
def _render_paragraph(text: str) -> str:
    return f"<p>{_escape_text(text)}</p>"

def _render_paragraph_with_runs(runs: List[Dict[str, Any]]) -> str:
    """
    runs: list of {text: str, bold: bool, italic: bool}
    """
    out = "<p>"
    for r in runs:
        txt = _escape_text(r.get("text", ""))
        if r.get("bold") and r.get("italic"):
            out += f"<strong><em>{txt}</em></strong>"
        elif r.get("bold"):
            out += f"<strong>{txt}</strong>"
        elif r.get("italic"):
            out += f"<em>{txt}</em>"
        else:
            out += txt
    out += "</p>"
    return out

def _render_heading(text: str, level: int = 1) -> str:
    level = max(1, min(6, level))
    return f"<h{level}>{_escape_text(text)}</h{level}>"

def _render_list(items: List[str], ordered: bool = False) -> str:
    tag = "ol" if ordered else "ul"
    out = f"<{tag}>"
    for it in items:
        out += f"<li>{_escape_text(it)}</li>"
    out += f"</{tag}>"
    return out

# ---- Main renderer ----
def render_html(content_structure: List[Dict[str, Any]], style_profile: Dict[str, Any], title: Optional[str] = None) -> str:
    """
    Renders a full HTML document from the content structure and style_profile.

    content_structure: list of nodes, each node can be:
      - {"type":"heading","level":1,"text":"..."}
      - {"type":"paragraph","text":"..."} OR {"type":"paragraph","runs":[{text,bold,italic},...]}
      - {"type":"list","ordered":False,"items":[...]}
      - {"type":"table","rows":[[...] ], "header": True|False}
      - {"type":"raw_html","html":"..."}
    """
    css = _build_css_from_profile(style_profile)
    body_parts: List[str] = []
    if title:
        body_parts.append(f"<h1>{_escape_text(title)}</h1>")

    for node in content_structure:
        ntype = (node.get("type") or "").lower()

        if ntype in ("heading", "title"):
            level = node.get("level", 1)
            body_parts.append(_render_heading(node.get("text", ""), level))

        elif ntype in ("paragraph", "p", "text"):
            # prefer 'runs' if present (for inline bold/italic)
            runs = node.get("runs")
            if runs and isinstance(runs, list):
                body_parts.append(_render_paragraph_with_runs(runs))
            else:
                body_parts.append(_render_paragraph(node.get("text", "") or ""))

        elif ntype == "list":
            items = node.get("items", []) or []
            ordered = bool(node.get("ordered", False))
            body_parts.append(_render_list(items, ordered))

        elif ntype == "table":
            rows = node.get("rows", []) or []
            tbl = "<table>"
            for i, r in enumerate(rows):
                tbl += "<tr>"
                for c in r:
                    if i == 0 and node.get("header", False):
                        tbl += f"<th>{_escape_text(c)}</th>"
                    else:
                        tbl += f"<td>{_escape_text(c)}</td>"
                tbl += "</tr>"
            tbl += "</table>"
            body_parts.append(tbl)

        elif ntype == "raw_html":
            # raw_html is inserted as-is — use carefully
            body_parts.append(node.get("html", ""))

        else:
            # fallback: render as paragraph
            text = node.get("text") or node.get("content") or ""
            body_parts.append(_render_paragraph(text))

        # optional page break after node
        if node.get("page_break_after"):
            body_parts.append("<div class='page-break'></div>")

    html_doc = "<!doctype html><html><head><meta charset='utf-8'/>"
    html_doc += css
    html_doc += "</head><body>"
    html_doc += "<div class='document'>"
    html_doc += "\n".join(body_parts)
    html_doc += "</div></body></html>"
    return html_doc
