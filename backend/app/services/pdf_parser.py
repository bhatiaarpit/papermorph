import pdfplumber
import fitz  # PyMuPDF

def extract_text_blocks_pdfplumber(path: str):
    """
    Returns list of pages with plain extracted text (pdfplumber).
    """
    blocks = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            blocks.append({"page": i+1, "text": text})
    return blocks

def extract_spans_pymupdf(path: str):
    """
    Returns list of spans with font metadata (pymupdf).
    Each span: {page, font, size, color, text}
    """
    doc = fitz.open(path)
    spans = []
    for page in doc:
        blocks = page.get_text("dict").get("blocks", [])
        for b in blocks:
            for line in b.get("lines", []):
                for span in line.get("spans", []):
                    spans.append({
                        "page": page.number + 1,
                        "font": span.get("font"),
                        "size": span.get("size"),
                        "text": span.get("text"),
                        "color": span.get("color", None)
                    })
    return spans
