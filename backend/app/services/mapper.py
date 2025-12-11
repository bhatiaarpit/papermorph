# app/services/mapper.py
import re
from typing import List, Dict, Any
from app.services.style_extractor import build_style_profile, infer_role_for_span

LIST_LEAD_RE = re.compile(r"^(\u2022|•|[-\*\u2022]|\d+\.)\s+")

def _is_list_line(text: str) -> bool:
    if not text:
        return False
    return bool(LIST_LEAD_RE.match(text.strip()))

def _strip_list_lead(text: str) -> str:
    return re.sub(r"^(\u2022|•|[-\*\u2022]|\d+\.)\s+", "", text.strip())

def spans_group_by_line(spans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Group a list of pymupdf spans by approximate line order to form small units.
    Each returned unit: { 'page': int, 'font': str, 'size': int, 'text': str }
    This is a lightweight grouping — it assumes spans are already in reading order.
    """
    grouped = []
    for s in spans:
        text = (s.get("text") or "").strip()
        if not text:
            continue
        grouped.append({
            "page": s.get("page"),
            "font": s.get("font"),
            "size": int(round(s.get("size"))) if s.get("size") else None,
            "text": text
        })
    return grouped

def build_content_structure_from_spans(spans: List[Dict[str, Any]], style_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert spans into a content structure suitable for the formatter.
    Heuristics:
      - If a span's size >= heading_rules.min_size => heading node
      - Consecutive non-heading spans are combined into paragraphs
      - Lines starting with list markers become list nodes
    """
    nodes = []
    if not spans:
        return nodes

    # Use infer_role_for_span where possible
    para_buffer = []
    list_buffer = []
    in_list = False

    for s in spans:
        role = infer_role_for_span(s, style_profile)
        text = (s.get("text") or "").strip()
        # detect explicit list lines first
        if _is_list_line(text):
            # flush paragraph buffer
            if para_buffer:
                nodes.append({"type": "paragraph", "text": " ".join(para_buffer)})
                para_buffer = []
            # append stripped list item
            item = _strip_list_lead(text)
            if not in_list:
                list_buffer = [item]
                in_list = True
            else:
                list_buffer.append(item)
            continue
        # if previously we were in list and current line is not list -> flush list
        if in_list and not _is_list_line(text):
            nodes.append({"type": "list", "ordered": False, "items": list_buffer})
            list_buffer = []
            in_list = False

        # heading detection
        if role and role.startswith("H"):
            # flush paragraph buffer if exists
            if para_buffer:
                nodes.append({"type": "paragraph", "text": " ".join(para_buffer)})
                para_buffer = []
            # interpret heading level from role like "H1" -> level 1
            try:
                level = int(role[1])
            except Exception:
                level = 1
            nodes.append({"type": "heading", "level": level, "text": text})
        else:
            # non-heading -> accumulate into paragraph
            para_buffer.append(text)

    # flush remaining buffers
    if in_list and list_buffer:
        nodes.append({"type": "list", "ordered": False, "items": list_buffer})
    if para_buffer:
        nodes.append({"type": "paragraph", "text": " ".join(para_buffer)})

    return nodes

def build_content_structure_from_text_blocks(blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Fallback mapping from pdfplumber text blocks (page-wise text) into paragraphs and lists.
    Simpler: split by newline, detect list markers, treat short uppercase lines as headings.
    """
    nodes = []
    for b in blocks:
        text = b.get("text") or ""
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        para_buffer = []
        list_buffer = []
        in_list = False

        for ln in lines:
            # list detection
            if _is_list_line(ln):
                if para_buffer:
                    nodes.append({"type": "paragraph", "text": " ".join(para_buffer)})
                    para_buffer = []
                item = _strip_list_lead(ln)
                if not in_list:
                    list_buffer = [item]
                    in_list = True
                else:
                    list_buffer.append(item)
                continue
            # flush list if needed
            if in_list and not _is_list_line(ln):
                nodes.append({"type": "list", "ordered": False, "items": list_buffer})
                list_buffer = []
                in_list = False

            # heading heuristic: short line and mostly uppercase or TitleCase
            if len(ln) < 80 and (ln.isupper() or (ln[0].isupper() and len(ln.split()) <= 6)):
                if para_buffer:
                    nodes.append({"type": "paragraph", "text": " ".join(para_buffer)})
                    para_buffer = []
                nodes.append({"type": "heading", "level": 2, "text": ln})
            else:
                para_buffer.append(ln)
        if in_list and list_buffer:
            nodes.append({"type": "list", "ordered": False, "items": list_buffer})
        if para_buffer:
            nodes.append({"type": "paragraph", "text": " ".join(para_buffer)})
    return nodes
