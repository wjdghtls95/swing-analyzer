from fastapi import APIRouter, UploadFile, File
from analyze.service import analyze_swing, analyze_from_url
from analyze.schema import AnalyzeResponse, UrlRequest
import os, shutil, uuid

router = APIRouter()

@router.post("", response_model=AnalyzeResponse, tags=["Swing"])
async def analyze(file: UploadFile = File(...)):
    os.makedirs("uploads", exist_ok=True)
    file_id = uuid.uuid4().hex[:8]

    file_path = f"uploads/{file_id}_{file.filename}"

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    result = analyze_swing(file_path)
    return result


@router.post("/url", response_model=AnalyzeResponse, tags=["Swing"])
async def analyze_url(data: UrlRequest):
    result = analyze_from_url(data.s3_url)
    return result