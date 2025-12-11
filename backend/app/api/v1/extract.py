from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from app.services.pdf_parser import extract_spans_pymupdf, extract_text_blocks_pdfplumber
from app.services.style_extractor import build_style_profile
from app.utils.file_utils import save_upload_tmpfile

router = APIRouter()

@router.post("/extract-style")
async def extract_style(sample_pdf: UploadFile = File(...)):
    path = await save_upload_tmpfile(sample_pdf)
    try:
        spans = extract_spans_pymupdf(path)
        style_profile = build_style_profile(spans)  # returns minimal style profile JSON
        return JSONResponse({"style_profile": style_profile})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/extract-content")
async def extract_content(input_pdf: UploadFile = File(...)):
    path = await save_upload_tmpfile(input_pdf)
    try:
        blocks = extract_text_blocks_pdfplumber(path)
        return JSONResponse({"content_blocks": blocks})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
