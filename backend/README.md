# PaperMorph - Backend (fastapi)

## Setup (local)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd app
uvicorn app.main:app --reload --port 8000
# or from repo root:
uvicorn app.main:app --reload --port 8000

Health check:
curl http://localhost:8000/health

Upload sample style:
curl -F "sample_pdf=@/path/to/sample.pdf" http://localhost:8000/api/v1/extract-style

Upload input content:
curl -F "input_pdf=@/path/to/input.pdf" http://localhost:8000/api/v1/extract-content
