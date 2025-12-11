from collections import Counter, defaultdict
import math

def bucket_font_sizes(spans, buckets=5):
    sizes = sorted({round(s["size"]) for s in spans if s.get("size")})
    if not sizes:
        return {}
    # basic mapping: largest -> H1, next -> H2, others -> P
    sizes_sorted = sorted(sizes, reverse=True)
    mapping = {}
    for i, s in enumerate(sizes_sorted):
        if i == 0:
            mapping[s] = "H1"
        elif i == 1:
            mapping[s] = "H2"
        else:
            mapping[s] = "P"
    return mapping

def build_style_profile(spans):
    """
    Heuristic style profile builder:
    - Determine top font sizes and map to H1/H2/P
    - Identify common font families
    """
    if not spans:
        return {}

    fonts = Counter([s.get("font") for s in spans if s.get("font")])
    sizes = Counter([round(s.get("size")) for s in spans if s.get("size")])

    size_map = bucket_font_sizes(spans)
    profile = {
        "fonts_top": fonts.most_common(5),
        "size_map": size_map,
        "sample_texts": spans[:10]
    }
    # Convert to serializable structure
    return profile
