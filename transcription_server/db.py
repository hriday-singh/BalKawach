import sqlite3
import os
import uuid
from datetime import datetime

DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "cpms.db"))

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS transcription_jobs (
            job_id TEXT PRIMARY KEY,
            user_id TEXT,
            audio_path TEXT,
            language TEXT,
            status TEXT,
            ctc_transcript TEXT,
            rnnt_transcript TEXT,
            final_transcript TEXT,
            created_at TIMESTAMP,
            completed_at TIMESTAMP
        )
    ''')
    try:
        c.execute('ALTER TABLE transcription_jobs ADD COLUMN hearing_id TEXT')
    except Exception:
        pass
    conn.commit()
    conn.close()

def create_job(user_id, audio_path, language, hearing_id=None):
    job_id = str(uuid.uuid4())
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO transcription_jobs (job_id, user_id, audio_path, language, hearing_id, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (job_id, user_id, audio_path, language, hearing_id, "pending", datetime.now()))
    conn.commit()
    conn.close()
    return job_id

def get_job(job_id):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM transcription_jobs WHERE job_id = ?', (job_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def update_job_status(job_id, status, ctc="", rnnt=""):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE transcription_jobs 
        SET status = ?, ctc_transcript = ?, rnnt_transcript = ?, completed_at = ?
        WHERE job_id = ?
    ''', (status, ctc, rnnt, datetime.now(), job_id))
    conn.commit()
    conn.close()

def save_final_transcript(job_id, final_text):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE transcription_jobs 
        SET final_transcript = ?
        WHERE job_id = ?
    ''', (final_text, job_id))
    conn.commit()
    conn.close()
