import time
import threading
import sqlite3
from transcription_server.db import get_connection, update_job_status
from transcription_server.asr import transcribe_audio

def process_job(job):
    job_id = job['job_id']
    audio_path = job['audio_path']
    language = job['language']
    
    update_job_status(job_id, "processing")
    print(f"[Worker] Processing job {job_id} for {audio_path}")
    
    result = transcribe_audio(audio_path, language, decoder="both")
    
    if "error" in result:
        print(f"[Worker] Job {job_id} failed: {result['error']}")
        if "details" in result:
            print(f"[Worker] Details: {result['details']}")
        update_job_status(job_id, "failed")
    else:
        ctc = result.get('results', {}).get('ctc', '')
        rnnt = result.get('results', {}).get('rnnt', '')
        update_job_status(job_id, "completed", ctc, rnnt)
        print(f"============================================================")
        print(f"[TRANSCRIPTION COMPLETE] Job ID: {job_id}")
        print(f"[-] CTC Output : {ctc}")
        print(f"[-] RNNT Output: {rnnt}")
        print(f"============================================================")

def worker_loop():
    while True:
        try:
            conn = get_connection()
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute('SELECT * FROM transcription_jobs WHERE status = ? LIMIT 1', ("pending",))
            row = c.fetchone()
            conn.close()
            
            if row:
                process_job(dict(row))
            else:
                time.sleep(2)
        except Exception as e:
            print(f"[Worker] Error in loop: {e}")
            time.sleep(5)

def start_worker():
    t = threading.Thread(target=worker_loop, daemon=True)
    t.start()
