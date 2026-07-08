import httpx
from fastapi import APIRouter, Request, Response, Form, UploadFile, File
import logging

router = APIRouter()
import os
TRANSCRIPTION_SERVER_URL = os.environ.get("TRANSCRIPTION_SERVER_URL", "http://127.0.0.1:9121")

@router.get("/api/languages")
async def proxy_languages():
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{TRANSCRIPTION_SERVER_URL}/api/languages")
        return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))

@router.post("/api/transcribe/submit")
async def proxy_transcribe_submit(
    language: str = Form("hi"),
    user_id: str = Form("guest"),
    hearing_id: str = Form(None),
    audio: UploadFile = File(...)
):
    async with httpx.AsyncClient(timeout=60.0) as client:
        files = {"audio": (audio.filename, await audio.read(), audio.content_type)}
        data = {"language": language, "user_id": user_id}
        if hearing_id:
            data["hearing_id"] = hearing_id
        resp = await client.post(f"{TRANSCRIPTION_SERVER_URL}/api/jobs/submit", data=data, files=files)
        return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))

@router.get("/api/transcribe/status/{job_id}")
async def proxy_transcribe_status(job_id: str):
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{TRANSCRIPTION_SERVER_URL}/api/jobs/{job_id}")
        return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))

@router.post("/api/transcribe/save/{job_id}")
async def proxy_transcribe_save(job_id: str, final_transcript: str = Form(...)):
    async with httpx.AsyncClient(timeout=60.0) as client:
        data = {"final_transcript": final_transcript}
        resp = await client.post(f"{TRANSCRIPTION_SERVER_URL}/api/jobs/{job_id}/save", data=data)
        return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))

import sqlite3
import os

@router.get("/api/transcriptions")
def get_all_transcriptions():
    db_path = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "cpms.db"))
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''
        SELECT t.job_id, t.user_id, t.audio_path, t.language, t.status, 
               t.final_transcript, t.created_at, t.hearing_id,
               u.full_name, u.username, u.role,
               c.name as child_name, c.child_code
        FROM transcription_jobs t
        LEFT JOIN users u ON t.user_id = u.id
        LEFT JOIN hearings h ON t.hearing_id = h.id
        LEFT JOIN children c ON h.child_id = c.id
        ORDER BY t.created_at DESC
    ''')
    rows = c.fetchall()
    conn.close()
    
    results = []
    for r in rows:
        results.append({
            "job_id": r["job_id"],
            "user_id": r["user_id"],
            "full_name": r["full_name"],
            "username": r["username"],
            "role": r["role"],
            "hearing_id": r["hearing_id"],
            "child_name": r["child_name"],
            "child_code": r["child_code"],
            "audio_path": r["audio_path"],
            "language": r["language"],
            "status": r["status"],
            "final_transcript": r["final_transcript"],
            "created_at": r["created_at"]
        })
    return results

@router.delete("/api/transcriptions/{job_id}")
def delete_transcription(job_id: str):
    db_path = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "cpms.db"))
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    c.execute("SELECT audio_path FROM transcription_jobs WHERE job_id = ?", (job_id,))
    row = c.fetchone()
    if row and row[0] and os.path.exists(row[0]):
        try:
            os.remove(row[0])
        except Exception as e:
            logging.error(f"Failed to delete audio file: {e}")
            
    c.execute("DELETE FROM transcription_jobs WHERE job_id = ?", (job_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}

@router.get("/api/hearings/{hearing_id}/recordings")
def get_hearing_recordings(hearing_id: str):
    db_path = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "cpms.db"))
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''
        SELECT t.job_id, t.user_id, t.audio_path, t.language, t.status, 
               t.ctc_transcript, t.rnnt_transcript, t.final_transcript, t.created_at,
               u.full_name, u.username, u.role
        FROM transcription_jobs t
        LEFT JOIN users u ON t.user_id = u.id
        WHERE t.hearing_id = ?
        ORDER BY t.created_at ASC
    ''', (hearing_id,))
    rows = c.fetchall()
    conn.close()
    
    results = []
    for r in rows:
        results.append({
            "id": r["job_id"],
            "user": {
                "id": r["user_id"],
                "full_name": r["full_name"] or r["username"] or r["user_id"],
                "role": r["role"]
            },
            "timestamp": r["created_at"] + "Z" if r["created_at"] else None,
            "language": r["language"],
            "status": r["status"],
            "transcript": r["final_transcript"] or '',
            "transcripts": [r["ctc_transcript"], r["rnnt_transcript"]] if r["ctc_transcript"] and r["rnnt_transcript"] else [],
            "selectedTranscriptIndex": None,
            "audioUrl": f"/api/audio/{os.path.basename(r['audio_path'])}" if r["audio_path"] else None,
            "duration": 0,
            "amplitudeHistory": []
        })
    return results
