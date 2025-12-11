import uuid
import os
from fastapi import UploadFile

TMP_DIR = "/tmp/papermorph"
os.makedirs(TMP_DIR, exist_ok=True)

async def save_upload_tmpfile(upload_file: UploadFile) -> str:
    ext = os.path.splitext(upload_file.filename)[1] or ".pdf"
    fname = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(TMP_DIR, fname)
    contents = await upload_file.read()
    with open(path, "wb") as f:
        f.write(contents)
    return path
