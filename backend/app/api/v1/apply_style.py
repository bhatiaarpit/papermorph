# app/api/v1/apply_style.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from typing import Optional
from app.services.formatter import render_html
from app.services.pdf_parser import extract_spans_pymupdf, extract_text_blocks_pdfplumber
from app.services.style_extractor import build_style_profile
from app.services.mapper import spans_group_by_line, build_content_structure_from_spans, build_content_structure_from_text_blocks
from app.services.pdf_renderer import html_to_pdf_bytes  # renderer that tries wkhtmltopdf then Playwright
import io
import os

router = APIRouter()

@router.post("/apply-style-upload")
async def apply_style_upload(
    sample_pdf: UploadFile = File(...),
    input_pdf: UploadFile = File(...),
    output: Optional[str] = Form("html")   # pass "pdf" to get PDF
):
    """
    Accepts multipart form with:
      - sample_pdf: PDF file used as style reference
      - input_pdf: PDF file to be converted
      - output (form field, optional): "html" (default) or "pdf"

    Returns: styled HTML (text/html) or PDF (application/pdf)
    """
    # save uploads to /tmp using your existing util or in-memory read
    from app.utils.file_utils import save_upload_tmpfile

    sample_path = await save_upload_tmpfile(sample_pdf)
    input_path = await save_upload_tmpfile(input_pdf)

    try:
        # 1) Extract spans from sample and build style profile
        sample_spans = extract_spans_pymupdf(sample_path)
        style_profile = build_style_profile(sample_spans)

        # 2) Extract spans & text blocks from input
        input_spans = extract_spans_pymupdf(input_path)
        text_blocks = extract_text_blocks_pdfplumber(input_path)

        # 3) Try building content structure using spans (best fidelity). If spans empty/fails, fallback to text blocks.
        content_structure = []
        grouped_spans = spans_group_by_line(input_spans)
        if grouped_spans:
            content_structure = build_content_structure_from_spans(grouped_spans, style_profile)
        else:
            content_structure = build_content_structure_from_text_blocks(text_blocks)

        # 4) Render HTML using formatter
        title = None
        # attempt to set document title from first heading if present
        for n in content_structure:
            if n.get("type") in ("heading",):
                title = n.get("text")
                break

        html_doc = render_html(content_structure, style_profile, title)

        # Return HTML or PDF based on "output" param
        if (output or "html").lower() == "pdf":
            try:
                pdf_bytes = html_to_pdf_bytes(html_doc)
                return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf",
                                         headers={"Content-Disposition": 'attachment; filename="converted.pdf"'})
            except FileNotFoundError as fe:
                # helpful JSON response if neither renderer is available
                return JSONResponse(status_code=400, content={"error": str(fe), "hint": "Install wkhtmltopdf or playwright (see backend docs)."})
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        else:
            return HTMLResponse(content=html_doc, status_code=200)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
