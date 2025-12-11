from fastapi import FastAPI
from app.api.v1 import extract

app = FastAPI(title="PaperMorph Backend (v0.1)")

app.include_router(extract.router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "ok"}
