# app/services/style_extractor.py
from collections import Counter, defaultdict
import math
import re
import statistics

BOLD_KEYWORDS = ["Bold", "Bd", "BOLD", "Black", "Semibold", "SemiBold", "Heavy"]
ITALIC_KEYWORDS = ["Italic", "It", "Oblique", "Slanted"]

BULLET_CANDIDATES = ["•", "-", "–", "—", "*", "·"]

def _is_bold_font(font_name: str) -> bool:
    if not font_name:
        return False
    for k in BOLD_KEYWORDS:
        if k in font_name:
            return True
    return False

def _is_italic_font(font_name: str) -> bool:
    if not font_name:
        return False
    for k in ITALIC_KEYWORDS:
        if k in font_name:
            return True
    return False

def _round_size(n):
    try:
        return int(round(float(n)))
    except Exception:
        return None

def _detect_bullet_from_texts(spans, sample_limit=200):
    # Look through small text samples for leading bullet characters or numbered lists
    bullets = Counter()
    numbered = False
    count = 0
    for s in spans:
        txt = (s.get("text") or "").strip()
        if not txt:
            continue
        count += 1
        if count > sample_limit:
            break
        # leading bullet char
        first = txt[0]
        if first in BULLET_CANDIDATES:
            bullets[first] += 1
        # leading dash + space or asterisk
        if re.match(r"^[-\*\u2022]\s+", txt):
            bullets[first] += 1
        # numbered list like "1. " or "a) "
        if re.match(r"^\d+\.\s+", txt) or re.match(r"^[a-zA-Z]\)\s+", txt):
            numbered = True

    most_common_bullets = bullets.most_common(3)
    return {
        "bullets": [b for b, c in most_common_bullets],
        "numbered": numbered,
        "sample_count": count
    }

def _size_percentiles(sizes):
    """
    Return mapping of percentile thresholds (90, 75, 50, 25)
    """
    sizes_sorted = sorted([s for s in sizes if s is not None])
    if not sizes_sorted:
        return {}
    p90 = int(round(statistics.quantiles(sizes_sorted, n=100)[89])) if len(sizes_sorted) >= 100 else max(sizes_sorted)
    p75 = int(round(statistics.quantiles(sizes_sorted, n=4)[2])) if len(sizes_sorted) >= 4 else sorted(sizes_sorted)[max(0, len(sizes_sorted)-2)]
    p50 = int(round(statistics.median(sizes_sorted)))
    p25 = int(round(sorted(sizes_sorted)[max(0, len(sizes_sorted)//4)])) if sizes_sorted else p50
    return {"p90": p90, "p75": p75, "p50": p50, "p25": p25, "min": min(sizes_sorted), "max": max(sizes_sorted)}

def build_style_profile(spans):
    """
    Build a heuristic style profile from spans.
    Input: spans: list of {page, font, size, text, color}
    Output: dict style_profile
    """
    if not spans:
        return {}

    # collect fonts and sizes
    fonts = Counter()
    sizes = []
    font_weight_info = defaultdict(lambda: {"count": 0, "bold_count": 0, "italic_count": 0})
    sample_texts = []

    for s in spans:
        font = s.get("font") or "Unknown"
        size_raw = s.get("size")
        size = _round_size(size_raw)
        text = s.get("text") or ""
        fonts[font] += 1
        if size:
            sizes.append(size)
            font_weight_info[font]["count"] += 1
            if _is_bold_font(font):
                font_weight_info[font]["bold_count"] += 1
            if _is_italic_font(font):
                font_weight_info[font]["italic_count"] += 1
        # sample texts for bullet detection or examples
        if len(sample_texts) < 30 and text.strip():
            sample_texts.append({"font": font, "size": size, "text": text.strip()})

    fonts_top = fonts.most_common(8)
    # compute size percentiles and thresholds
    percentiles = _size_percentiles(sizes)

    # create heading rules based on percentiles:
    # largest sizes > p90 -> H1, > p75 -> H2, > p50 -> H3 else P
    size_map = {}
    heading_rules = []
    if percentiles:
        p90 = percentiles.get("p90")
        p75 = percentiles.get("p75")
        p50 = percentiles.get("p50")
        # safety: ensure descending unique thresholds
        thresholds = sorted(set([p90, p75, p50]), reverse=True)
        # map unique sizes into roles
        for s in sorted(set(sizes), reverse=True):
            role = "P"
            if p90 and s >= p90:
                role = "H1"
            elif p75 and s >= p75:
                role = "H2"
            elif p50 and s >= p50:
                role = "H3"
            size_map[str(s)] = role
        # heading rules for renderer (min_size for each heading level)
        heading_rules = [
            {"level": 1, "min_size": int(p90) if p90 else max(sizes)},
            {"level": 2, "min_size": int(p75) if p75 else int(percentiles.get("p50", max(sizes)//2))},
            {"level": 3, "min_size": int(p50) if p50 else int(percentiles.get("p25", max(sizes)//4))}
        ]
    else:
        # fallback
        size_map = {}
        heading_rules = []

    # detect bullets and numbered lists
    list_info = _detect_bullet_from_texts(spans)

    # derive font family summary with bold/italic ratios
    fonts_summary = []
    for f, cnt in fonts_top:
        info = font_weight_info.get(f, {})
        fonts_summary.append({
            "font": f,
            "count": cnt,
            "bold_pct": round((info.get("bold_count", 0) / info.get("count", 1)) * 100, 1) if info.get("count") else 0,
            "italic_pct": round((info.get("italic_count", 0) / info.get("count", 1)) * 100, 1) if info.get("count") else 0
        })

    profile = {
        "fonts_top": fonts_summary,
        "size_percentiles": percentiles,
        "size_map": size_map,
        "heading_rules": heading_rules,
        "list_style": list_info,
        "sample_texts": sample_texts[:30]
    }
    return profile

# convenience helper: identify role for a specific span (optional utility)
def infer_role_for_span(span, style_profile):
    """
    Given a single span and a style_profile, infer a role like H1/H2/H3/P.
    """
    size = _round_size(span.get("size"))
    if not size or not style_profile:
        return "P"
    # use heading_rules if present
    for rule in style_profile.get("heading_rules", []):
        if size >= rule.get("min_size", 0):
            return f"H{rule.get('level')}"
    # fallback to size_map lookup
    size_map = style_profile.get("size_map", {})
    return size_map.get(str(size), "P")
