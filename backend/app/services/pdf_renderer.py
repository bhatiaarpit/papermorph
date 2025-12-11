# app/services/pdf_renderer.py
import shutil
import subprocess
import tempfile
import os
from typing import Optional


# -----------------------------------------
# 1) wkhtmltopdf renderer (preferred)
# -----------------------------------------
def _html_to_pdf_wkhtmltopdf(html_str: str) -> bytes:
    wk_path = shutil.which("wkhtmltopdf") or r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.EXE"
    if not wk_path:
        raise FileNotFoundError("wkhtmltopdf not found")

    # Write HTML to temp file
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as fh:
        fh.write(html_str.encode("utf-8"))
        tmp_html = fh.name

    tmp_pdf = tmp_html + ".pdf"

    try:
        cmd = [
            wk_path,
            "--quiet",
            "--disable-smart-shrinking",
            "--enable-local-file-access",
            "--print-media-type",
            "--no-stop-slow-scripts",
            "--enable-javascript",
            "--javascript-delay", "100",
            "--dpi", "300",
            "--margin-top", "24mm",
            "--margin-bottom", "24mm",
            "--margin-left", "18mm",
            "--margin-right", "18mm",
            tmp_html,
            tmp_pdf,
        ]

        subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Read back the PDF
        with open(tmp_pdf, "rb") as pf:
            return pf.read()

    finally:
        try:
            os.remove(tmp_html)
        except Exception:
            pass

        try:
            os.remove(tmp_pdf)
        except Exception:
            pass


# -----------------------------------------
# 2) Playwright synchronous fallback
# -----------------------------------------
def _html_to_pdf_playwright_sync(html_str: str, viewport: Optional[dict] = None) -> bytes:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise ModuleNotFoundError("playwright is not installed") from e

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport=viewport or {"width": 1200, "height": 800})
        page.set_content(html_str, wait_until="networkidle")
        pdf_bytes = page.pdf(format="A4", print_background=True)
        browser.close()
        return pdf_bytes


# -----------------------------------------
# 3) Main API used by FastAPI
# -----------------------------------------
def html_to_pdf_bytes(html_str: str) -> bytes:
    """
    Convert HTML string -> PDF bytes.
    Uses wkhtmltopdf first (fast, stable),
    otherwise tries synchronous Playwright.
    """
    # Try wkhtmltopdf
    try:
        return _html_to_pdf_wkhtmltopdf(html_str)

    except Exception as wk_err:
        # fallback to Playwright if wkhtmltopdf fails
        try:
            return _html_to_pdf_playwright_sync(html_str)
        except ModuleNotFoundError:
            raise FileNotFoundError(
                "wkhtmltopdf failed AND Playwright not installed.\n"
                "Install wkhtmltopdf or run:\n"
                "  pip install playwright\n"
                "  python -m playwright install"
            )
        except Exception as e:
            raise e
