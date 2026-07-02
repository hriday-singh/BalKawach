import os
import shutil
import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from transcription_server.db import create_job, get_job, save_final_transcript
from transcription_server.asr import load_model, LANGUAGES

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("/api/languages")
def api_languages():
    return LANGUAGES

@router.post("/api/jobs/submit")
async def submit_job(
    language: str = Form("hi"),
    user_id: str = Form("guest"),
    hearing_id: str = Form(None),
    audio: UploadFile = File(...)
):
    if not audio:
        raise HTTPException(status_code=400, detail="No audio file provided")

    suffix = os.path.splitext(audio.filename)[1] if audio.filename else ".wav"
    file_path = os.path.join(UPLOAD_DIR, f"transcription_{uuid.uuid4()}{suffix}")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)

    job_id = create_job(user_id, file_path, language, hearing_id)
    return {"job_id": job_id, "status": "pending"}

@router.get("/api/jobs/{job_id}")
def get_job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/api/jobs/{job_id}/save")
def save_transcript(job_id: str, final_transcript: str = Form(...)):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    save_final_transcript(job_id, final_transcript)
    return {"success": True, "job_id": job_id}
