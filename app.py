"""
Child Protection Case Management Platform — Flask Backend
==========================================================
Combines the IndicConformer ASR engine with a full case-management
REST API backed by SQLite (via db.py).
"""

import os
import uuid
import traceback
from pathlib import Path
from datetime import datetime, timedelta

from flask import (
    Flask, request, jsonify, render_template, session
)

import numpy as np
import torch
import soundfile as sf
import librosa
from transformers import AutoModel

import db
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

# ════════════════════════════════════════════════════════════════════════
#  App initialisation
# ════════════════════════════════════════════════════════════════════════

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "cpms-dev-secret-key-change-in-prod")
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


# ════════════════════════════════════════════════════════════════════════
#  ASR Model — ai4bharat/indic-conformer-600m-multilingual
# ════════════════════════════════════════════════════════════════════════

MODEL = None
MODEL_ERROR = None   # stores a friendly error if load failed

MODEL_PATH = os.environ.get(
    "INDIC_CONFORMER_MODEL",
    "ai4bharat/indic-conformer-600m-multilingual"
)

# Set via:  set HF_TOKEN=hf_xxxxxxxxxxxx   (Windows)
#       or: export HF_TOKEN=hf_xxxxxxxxxxxx (Linux/Mac)
HF_TOKEN = os.environ.get("HF_TOKEN", None)

TARGET_SAMPLE_RATE = 16000

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

LANGUAGES = {
    "hi":  "Hindi",
    "bn":  "Bengali",
    "gu":  "Gujarati",
    "kn":  "Kannada",
    "ml":  "Malayalam",
    "mr":  "Marathi",
    "or":  "Odia",
    "pa":  "Punjabi",
    "sa":  "Sanskrit",
    "ta":  "Tamil",
    "te":  "Telugu",
    "ur":  "Urdu",
    "as":  "Assamese",
    "brx": "Bodo",
    "ks":  "Kashmiri",
    "mai": "Maithili",
    "mni": "Manipuri",
    "ne":  "Nepali",
    "si":  "Sinhala",
    "sd":  "Sindhi",
    "en":  "English",
    "doi": "Dogri",
}


def load_model():
    """Lazy-load the ASR model. Returns (model, error_string | None)."""
    global MODEL, MODEL_ERROR

    if MODEL is not None:
        return MODEL, None

    # Don't retry after a permanent failure (e.g. 403 gated repo)
    if MODEL_ERROR is not None:
        return None, MODEL_ERROR

    try:
        print(f"Loading model : {MODEL_PATH}")
        if DEVICE == "cuda":
            print("Device        : GPU (CUDA) IS ACTIVE 🚀")
        else:
            print("Device        : CPU (WARNING: Inference will be slow) 🐢")
        print(f"HF token set  : {'yes' if HF_TOKEN else 'NO — gated repos will fail'}")

        MODEL = AutoModel.from_pretrained(
            MODEL_PATH,
            trust_remote_code=True,
            token=HF_TOKEN,
        )

        if hasattr(MODEL, "to"):
            MODEL = MODEL.to(DEVICE)
        if hasattr(MODEL, "eval"):
            MODEL.eval()

        print("Model loaded successfully.")
        return MODEL, None

    except Exception as exc:
        raw = traceback.format_exc()

        if "GatedRepoError" in raw or "403" in raw:
            MODEL_ERROR = (
                "ACCESS DENIED — This HuggingFace model is gated.\n\n"
                "Steps to fix:\n"
                "  1. Visit https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual\n"
                "  2. Click 'Request access' and wait for approval.\n"
                "  3. Go to https://huggingface.co/settings/tokens and create a token.\n"
                "  4. Before starting the app run:\n"
                "       set HF_TOKEN=hf_your_token_here\n"
                "       python app.py\n\n"
                f"Raw error:\n{raw}"
            )
        else:
            MODEL_ERROR = raw

        return None, MODEL_ERROR


def load_audio_numpy(audio_path: str):
    """
    Load any audio file → (samples: np.float32, sample_rate: int).
    Strategy:
      1. soundfile  — fast, zero-dependency, handles WAV / FLAC / OGG / AIFF
      2. librosa    — handles MP3, M4A, WebM, Opus via audioread/ffmpeg
    """
    path = str(audio_path)
    try:
        data, sr = sf.read(path, dtype="float32", always_2d=True)
        return data.T, sr
    except Exception:
        pass

    data, sr = librosa.load(path, sr=None, mono=False, dtype=np.float32)
    if data.ndim == 1:
        data = data[np.newaxis, :]
    return data, sr


def prepare_audio(audio_path: str):
    """Load audio, collapse to mono, resample to 16 kHz, return torch tensor."""
    data, sr = load_audio_numpy(audio_path)

    wav = torch.from_numpy(data)  # (C, T)

    if wav.shape[0] > 1:
        wav = torch.mean(wav, dim=0, keepdim=True)

    if sr != TARGET_SAMPLE_RATE:
        import torchaudio.functional as F_audio
        wav = F_audio.resample(wav, orig_freq=sr, new_freq=TARGET_SAMPLE_RATE)

    return wav


def clean_output(output):
    """Normalise model output to plain text."""
    if hasattr(output, "text"):
        return output.text
    if isinstance(output, (list, tuple)):
        if len(output) == 0:
            return ""
        if len(output) == 1:
            return clean_output(output[0])
        return [clean_output(x) for x in output]
    if isinstance(output, dict):
        return output.get("text", output)
    return str(output)


def transcribe_audio(audio_path: str, language: str = "hi",
                     decoder: str = "rnnt") -> dict:
    """Run the ASR pipeline on a single audio file."""
    model, err = load_model()

    if err:
        return {"error": "Model load failed", "details": err}

    try:
        wav = prepare_audio(audio_path)
        wav = wav.to(DEVICE)

        if decoder not in {"ctc", "rnnt", "both"}:
            decoder = "rnnt"

        selected_decoders = ["ctc", "rnnt"] if decoder == "both" else [decoder]

        results = {}
        
        # Optimize for speed: use inference_mode (faster than no_grad) and autocast (mixed precision)
        autocast_device = "cuda" if DEVICE == "cuda" else "cpu"
        # Use bfloat16 on CPU if supported, else autocast gracefully ignores or uses bfloat16 (requires newer CPUs). 
        # For maximum safety on diverse hardware, we'll use float16 on CUDA, and disable autocast on CPU.
        
        with torch.inference_mode():
            if DEVICE == "cuda":
                with torch.autocast(device_type="cuda", dtype=torch.float16):
                    for dec in selected_decoders:
                        output = model(wav, language, dec)
                        results[dec] = clean_output(output)
            else:
                for dec in selected_decoders:
                    output = model(wav, language, dec)
                    results[dec] = clean_output(output)

        response = {
            "language":      language,
            "language_name": LANGUAGES.get(language, language),
            "decoder":       decoder,
            "device":        DEVICE,
            "results":       results,
        }

        if decoder != "both":
            response["text"] = results.get(decoder, "")

        return response

    except Exception:
        return {"error": "Transcription failed", "details": traceback.format_exc()}


# ════════════════════════════════════════════════════════════════════════
#  Helpers
# ════════════════════════════════════════════════════════════════════════

def _now_iso():
    """Current UTC-ish timestamp as ISO string."""
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _current_user():
    """Return the user dict stored in session, or None."""
    return session.get("user")


def _require_login():
    """Return (user_dict, None) or (None, error_response)."""
    user = _current_user()
    if user is None:
        return None, (jsonify({"error": "Not authenticated"}), 401)
    return user, None


def _audit(action: str, details: str = "", entity_type: str = "",
           entity_id: str = ""):
    """Write one row to the audit_logs table."""
    user = _current_user()
    conn = db.get_db()
    conn.execute(
        """INSERT INTO audit_logs
           (id, timestamp, user_id, user_name, role, action,
            entity_type, entity_id, details, ip_address)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            str(uuid.uuid4()),
            _now_iso(),
            user["id"] if user else "system",
            user["name"] if user else "system",
            user["role"] if user else "system",
            action,
            entity_type,
            entity_id,
            details,
            request.remote_addr,
        ),
    )
    conn.commit()


def _row_to_dict(row):
    """Convert a sqlite3.Row to a plain dict."""
    if row is None:
        return None
    return dict(row)


def _rows_to_list(rows):
    """Convert a list of sqlite3.Row objects to a list of dicts."""
    return [dict(r) for r in rows]


def _save_upload(file_obj):
    """Save an uploaded file and return the path string."""
    suffix = Path(file_obj.filename).suffix if file_obj.filename else ".wav"
    if suffix not in {".wav", ".mp3", ".ogg", ".flac", ".m4a", ".webm", ".opus"}:
        suffix = ".wav"
    tmp_path = UPLOAD_DIR / f"{uuid.uuid4()}{suffix}"
    file_obj.save(str(tmp_path))
    return str(tmp_path)


# ════════════════════════════════════════════════════════════════════════
#  Main route
# ════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template(
        "index.html",
        languages=LANGUAGES,
        device=DEVICE,
    )


# ════════════════════════════════════════════════════════════════════════
#  ASR / Transcription routes  (preserved from original)
# ════════════════════════════════════════════════════════════════════════

@app.route("/api/languages")
def api_languages():
    """Return the dict of supported Indic languages."""
    return jsonify(LANGUAGES)


@app.route("/api/model-status")
def api_model_status():
    """Return whether the ASR model is loaded and ready."""
    return jsonify({
        "loaded":     MODEL is not None,
        "path":       MODEL_PATH,
        "device":     DEVICE,
        "token_set":  HF_TOKEN is not None,
        "load_error": MODEL_ERROR,
    })


@app.route("/api/transcribe", methods=["POST"])
def api_transcribe():
    """Transcribe an uploaded audio file via the Indic Conformer model."""
    language = request.form.get("language", "hi")
    decoder  = request.form.get("decoder", "rnnt")
    audio_file = request.files.get("audio")

    if not audio_file:
        return jsonify({"error": "No audio file provided"}), 400

    tmp_path = _save_upload(audio_file)

    try:
        result = transcribe_audio(tmp_path, language, decoder)
    finally:
        try:
            Path(tmp_path).unlink()
        except Exception:
            pass

    if "error" in result:
        return jsonify(result), 500
    return jsonify(result)


# ════════════════════════════════════════════════════════════════════════
#  Authentication
# ════════════════════════════════════════════════════════════════════════

@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    """Authenticate a user and store their profile in the session."""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    conn = db.get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()

    if user is None:
        return jsonify({"error": "Invalid credentials"}), 401

    if not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid credentials"}), 401
        
    if user["is_active"] == 0:
        return jsonify({"error": "Account pending admin approval"}), 403

    user_dict = _row_to_dict(user)
    user_dict.pop("password_hash", None)
    session["user"] = user_dict

    _audit("LOGIN", f"User {username} logged in", "user", user_dict["id"])

    return jsonify({"message": "Login successful", "user": user_dict})


@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    """Public registration endpoint (creates pending user)."""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    full_name = data.get("full_name", "").strip()
    role = data.get("role", "cci_staff")
    district = data.get("district", "Hyderabad")
    
    if not username or not password or not full_name:
        return jsonify({"error": "Missing required fields"}), 400
        
    conn = db.get_db()
    existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if existing:
        return jsonify({"error": "Username already exists"}), 400
        
    user_id = str(uuid.uuid4())
    pw_hash = generate_password_hash(password)
    
    conn.execute(
        "INSERT INTO users (id, username, password_hash, full_name, role, district, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, username, pw_hash, full_name, role, district, 0)
    )
    conn.commit()
    return jsonify({"message": "Registration successful. Pending admin approval."}), 201


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    """Clear the current session."""
    user = _current_user()
    if user:
        _audit("LOGOUT", f"User {user['full_name']} logged out", "user", user["id"])
    session.clear()
    return jsonify({"message": "Logged out"})


@app.route("/api/auth/me")
def auth_me():
    """Return the currently logged-in user's profile."""
    user = _current_user()
    if user is None:
        return jsonify({"error": "Not authenticated"}), 401
    return jsonify(user)


@app.route("/api/auth/users", methods=["GET"])
def auth_users():
    """List all users."""
    conn = db.get_db()
    rows = conn.execute(
        "SELECT id, username, full_name as name, role, district, is_active FROM users"
    ).fetchall()
    return jsonify(_rows_to_list(rows))


@app.route("/api/auth/users", methods=["POST"])
def admin_create_user():
    """Admin endpoint to create an instantly active user."""
    user = _current_user()
    if not user or user["role"] != "system_admin":
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    full_name = data.get("full_name", "").strip()
    role = data.get("role", "cci_staff")
    district = data.get("district", "Hyderabad")
    
    if not username or not password or not full_name:
        return jsonify({"error": "Missing required fields"}), 400
        
    conn = db.get_db()
    existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if existing:
        return jsonify({"error": "Username already exists"}), 400
        
    user_id = str(uuid.uuid4())
    pw_hash = generate_password_hash(password)
    
    conn.execute(
        "INSERT INTO users (id, username, password_hash, full_name, role, district, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, username, pw_hash, full_name, role, district, 1)
    )
    conn.commit()
    _audit("CREATE_USER", f"Admin created user {username}", "user", user_id)
    return jsonify({"message": "User created successfully"}), 201


@app.route("/api/auth/users/<user_id>/approve", methods=["PUT"])
def admin_approve_user(user_id):
    """Admin endpoint to approve a pending user."""
    user = _current_user()
    if not user or user["role"] != "system_admin":
        return jsonify({"error": "Unauthorized"}), 403
        
    conn = db.get_db()
    conn.execute("UPDATE users SET is_active = 1 WHERE id = ?", (user_id,))
    conn.commit()
    _audit("APPROVE_USER", f"Admin approved user ID {user_id}", "user", user_id)
    return jsonify({"message": "User approved successfully"})


# ════════════════════════════════════════════════════════════════════════
#  Children
# ════════════════════════════════════════════════════════════════════════

@app.route("/api/children")
def list_children():
    """List children with optional filters."""
    conn = db.get_db()
    query = "SELECT * FROM children WHERE 1=1"
    params = []

    for col in ("cci_id", "district", "legal_status",
                "admission_category", "is_lfa_eligible"):
        val = request.args.get(col)
        if val is not None:
            query += f" AND {col} = ?"
            params.append(val)

    rows = conn.execute(query + " ORDER BY created_at DESC", params).fetchall()
    return jsonify(_rows_to_list(rows))


@app.route("/api/children/<child_id>")
def get_child(child_id):
    """Get a single child's details with their case history."""
    conn = db.get_db()
    child = conn.execute(
        "SELECT * FROM children WHERE id = ?", (child_id,)
    ).fetchone()
    if child is None:
        return jsonify({"error": "Child not found"}), 404

    history = conn.execute(
        "SELECT * FROM case_history WHERE child_id = ? ORDER BY timestamp ASC",
        (child_id,),
    ).fetchall()

    result = _row_to_dict(child)
    result["case_history"] = _rows_to_list(history)
    return jsonify(result)


@app.route("/api/children", methods=["POST"])
def register_child():
    """Register a new child, auto-generate child_code, create case history
    entry and a 30-day CWC hearing deadline."""
    user, err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    conn = db.get_db()

    # Auto-generate child code
    year = datetime.now().year
    count = conn.execute(
        "SELECT COUNT(*) as cnt FROM children"
    ).fetchone()["cnt"]
    child_code = f"CWC-HYD-{year}-{count + 1:04d}"

    child_id = str(uuid.uuid4())
    now = _now_iso()

    conn.execute(
        """INSERT INTO children
           (id, child_code, name, age, gender, date_of_birth, district,
            cci_id, admission_date, admission_category, legal_status,
            is_lfa_eligible, father_name, mother_name, guardian_name,
            contact_phone, address, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            child_id,
            child_code,
            data.get("name", ""),
            data.get("age"),
            data.get("gender", ""),
            data.get("date_of_birth", ""),
            data.get("district", "Hyderabad"),
            data.get("cci_id", ""),
            data.get("admission_date", now[:10]),
            data.get("admission_category", "CNCP"),
            data.get("legal_status", "Newly Admitted"),
            data.get("is_lfa_eligible", 0),
            data.get("father_name", ""),
            data.get("mother_name", ""),
            data.get("guardian_name", ""),
            data.get("contact_phone", ""),
            data.get("address", ""),
            now,
            now,
        ),
    )

    # Case history entry for admission
    conn.execute(
        """INSERT INTO case_history
           (id, child_id, timestamp, action, old_status, new_status,
            performed_by, notes)
           VALUES (?,?,?,?,?,?,?,?)""",
        (
            str(uuid.uuid4()),
            child_id,
            now,
            "ADMISSION",
            "",
            "Newly Admitted",
            user["name"],
            f"Child registered with code {child_code}",
        ),
    )

    # 30-day CWC hearing deadline
    due_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    conn.execute(
        """INSERT INTO deadlines
           (id, child_id, type, description, due_date, status, created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (
            str(uuid.uuid4()),
            child_id,
            "CWC_HEARING",
            "First CWC hearing within 30 days of admission",
            due_date,
            "pending",
            now,
        ),
    )

    conn.commit()

    _audit("REGISTER_CHILD", f"Registered child {child_code}",
           "child", child_id)

    child = conn.execute(
        "SELECT * FROM children WHERE id = ?", (child_id,)
    ).fetchone()
    return jsonify(_row_to_dict(child)), 201


@app.route("/api/children/<child_id>/status", methods=["PUT"])
def update_child_status(child_id):
    """Update a child's legal status and record it in case history."""
    user, err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    new_status = data.get("legal_status", "").strip()
    if not new_status:
        return jsonify({"error": "legal_status is required"}), 400

    conn = db.get_db()
    child = conn.execute(
        "SELECT * FROM children WHERE id = ?", (child_id,)
    ).fetchone()
    if child is None:
        return jsonify({"error": "Child not found"}), 404

    old_status = child["legal_status"]
    now = _now_iso()

    conn.execute(
        "UPDATE children SET legal_status = ?, updated_at = ? WHERE id = ?",
        (new_status, now, child_id),
    )

    conn.execute(
        """INSERT INTO case_history
           (id, child_id, timestamp, action, old_status, new_status,
            performed_by, notes)
           VALUES (?,?,?,?,?,?,?,?)""",
        (
            str(uuid.uuid4()),
            child_id,
            now,
            "STATUS_CHANGE",
            old_status,
            new_status,
            user["name"],
            data.get("notes", ""),
        ),
    )
    conn.commit()

    _audit("UPDATE_CHILD_STATUS",
           f"Child {child['child_code']}: {old_status} → {new_status}",
           "child", child_id)

    updated = conn.execute(
        "SELECT * FROM children WHERE id = ?", (child_id,)
    ).fetchone()
    return jsonify(_row_to_dict(updated))


# ════════════════════════════════════════════════════════════════════════
#  Case History
# ════════════════════════════════════════════════════════════════════════

@app.route("/api/children/<child_id>/history")
def child_history(child_id):
    """Return the immutable case-history timeline for a child."""
    conn = db.get_db()
    rows = conn.execute(
        "SELECT * FROM case_history WHERE child_id = ? ORDER BY timestamp ASC",
        (child_id,),
    ).fetchall()
    return jsonify(_rows_to_list(rows))


# ════════════════════════════════════════════════════════════════════════
#  Hearings
# ════════════════════════════════════════════════════════════════════════

@app.route("/api/hearings")
def list_hearings():
    """List hearings with optional filters."""
    conn = db.get_db()
    query = "SELECT * FROM hearings WHERE 1=1"
    params = []

    for col in ("district", "status", "child_id"):
        val = request.args.get(col)
        if val is not None:
            query += f" AND {col} = ?"
            params.append(val)

    rows = conn.execute(
        query + " ORDER BY hearing_date DESC", params
    ).fetchall()
    return jsonify(_rows_to_list(rows))


@app.route("/api/hearings/<hearing_id>")
def get_hearing(hearing_id):
    """Get a single hearing's details."""
    conn = db.get_db()
    row = conn.execute(
        "SELECT * FROM hearings WHERE id = ?", (hearing_id,)
    ).fetchone()
    if row is None:
        return jsonify({"error": "Hearing not found"}), 404
    return jsonify(_row_to_dict(row))


@app.route("/api/hearings", methods=["POST"])
def create_hearing():
    """Schedule a new hearing."""
    user, err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    conn = db.get_db()
    hearing_id = str(uuid.uuid4())
    now = _now_iso()

    conn.execute(
        """INSERT INTO hearings
           (id, child_id, hearing_date, hearing_time, hearing_type,
            district, status, location, notes, transcript,
            attendees, created_by, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            hearing_id,
            data.get("child_id", ""),
            data.get("hearing_date", ""),
            data.get("hearing_time", ""),
            data.get("hearing_type", "Regular"),
            data.get("district", "Hyderabad"),
            "Scheduled",
            data.get("location", ""),
            data.get("notes", ""),
            "",
            data.get("attendees", ""),
            user["id"],
            now,
            now,
        ),
    )
    conn.commit()

    _audit("SCHEDULE_HEARING", f"Hearing scheduled for child {data.get('child_id','')}",
           "hearing", hearing_id)

    row = conn.execute(
        "SELECT * FROM hearings WHERE id = ?", (hearing_id,)
    ).fetchone()
    return jsonify(_row_to_dict(row)), 201


@app.route("/api/hearings/<hearing_id>", methods=["PUT"])
def update_hearing(hearing_id):
    """Update hearing details (status, transcript, notes, attendees)."""
    user, err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    conn = db.get_db()

    row = conn.execute(
        "SELECT * FROM hearings WHERE id = ?", (hearing_id,)
    ).fetchone()
    if row is None:
        return jsonify({"error": "Hearing not found"}), 404

    updates = []
    params = []
    for col in ("status", "transcript", "notes", "attendees",
                "hearing_date", "hearing_time", "location"):
        if col in data:
            updates.append(f"{col} = ?")
            params.append(data[col])

    if updates:
        updates.append("updated_at = ?")
        params.append(_now_iso())
        params.append(hearing_id)
        conn.execute(
            f"UPDATE hearings SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        conn.commit()

    _audit("UPDATE_HEARING", f"Hearing {hearing_id} updated",
           "hearing", hearing_id)

    updated = conn.execute(
        "SELECT * FROM hearings WHERE id = ?", (hearing_id,)
    ).fetchone()
    return jsonify(_row_to_dict(updated))


@app.route("/api/hearings/<hearing_id>/transcribe", methods=["POST"])
def transcribe_hearing(hearing_id):
    """Accept audio upload, transcribe via ASR, save to hearing record."""
    user, err = _require_login()
    if err:
        return err

    conn = db.get_db()
    hearing = conn.execute(
        "SELECT * FROM hearings WHERE id = ?", (hearing_id,)
    ).fetchone()
    if hearing is None:
        return jsonify({"error": "Hearing not found"}), 404

    audio_file = request.files.get("audio")
    if not audio_file:
        return jsonify({"error": "No audio file provided"}), 400

    language = request.form.get("language", "hi")
    decoder  = request.form.get("decoder", "rnnt")

    tmp_path = _save_upload(audio_file)

    try:
        result = transcribe_audio(tmp_path, language, decoder)
    finally:
        try:
            Path(tmp_path).unlink()
        except Exception:
            pass

    if "error" in result:
        return jsonify(result), 500

    # Save transcription to the hearing record
    transcript_text = result.get("text", "")
    now = _now_iso()
    conn.execute(
        "UPDATE hearings SET transcript = ?, updated_at = ? WHERE id = ?",
        (transcript_text, now, hearing_id),
    )
    conn.commit()

    _audit("TRANSCRIBE_HEARING",
           f"Audio transcribed for hearing {hearing_id}",
           "hearing", hearing_id)

    result["hearing_id"] = hearing_id
    result["saved"] = True
    return jsonify(result)


# ════════════════════════════════════════════════════════════════════════
#  Orders
# ════════════════════════════════════════════════════════════════════════

@app.route("/api/orders")
def list_orders():
    """List orders with optional filters."""
    conn = db.get_db()
    query = "SELECT * FROM orders WHERE 1=1"
    params = []

    for col in ("district", "status", "child_id"):
        val = request.args.get(col)
        if val is not None:
            query += f" AND {col} = ?"
            params.append(val)

    rows = conn.execute(
        query + " ORDER BY created_at DESC", params
    ).fetchall()
    return jsonify(_rows_to_list(rows))


@app.route("/api/orders/<order_id>")
def get_order(order_id):
    """Get a single order's details."""
    conn = db.get_db()
    row = conn.execute(
        "SELECT * FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    if row is None:
        return jsonify({"error": "Order not found"}), 404
    return jsonify(_row_to_dict(row))


@app.route("/api/orders", methods=["POST"])
def create_order():
    """Create a new order. Auto-generates order_number and pre-fills from
    child data and the latest hearing transcript."""
    user, err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    conn = db.get_db()

    # Auto-generate order number
    year = datetime.now().year
    count = conn.execute(
        "SELECT COUNT(*) as cnt FROM orders"
    ).fetchone()["cnt"]
    order_number = f"ORD-HYD-{year}-{count + 1:04d}"

    order_id = str(uuid.uuid4())
    now = _now_iso()

    # Pre-fill from child data if child_id provided
    child_id = data.get("child_id", "")
    child_name = ""
    child_code = ""
    transcript = data.get("transcript", "")

    if child_id:
        child = conn.execute(
            "SELECT * FROM children WHERE id = ?", (child_id,)
        ).fetchone()
        if child:
            child_name = child["name"]
            child_code = child["child_code"]

        # Grab latest hearing transcript if not supplied
        if not transcript:
            latest_hearing = conn.execute(
                """SELECT transcript FROM hearings
                   WHERE child_id = ? AND transcript != ''
                   ORDER BY hearing_date DESC LIMIT 1""",
                (child_id,),
            ).fetchone()
            if latest_hearing:
                transcript = latest_hearing["transcript"]

    conn.execute(
        """INSERT INTO orders
           (id, order_number, child_id, child_name, child_code, order_type,
            district, status, order_date, content, transcript,
            created_by, approved_by, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            order_id,
            order_number,
            child_id,
            child_name,
            child_code,
            data.get("order_type", "CWC Order"),
            data.get("district", "Hyderabad"),
            "Draft",
            data.get("order_date", now[:10]),
            data.get("content", ""),
            transcript,
            user["id"],
            "",
            now,
            now,
        ),
    )
    conn.commit()

    _audit("CREATE_ORDER", f"Order {order_number} created",
           "order", order_id)

    row = conn.execute(
        "SELECT * FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    return jsonify(_row_to_dict(row)), 201


@app.route("/api/orders/<order_id>/approve", methods=["PUT"])
def approve_order(order_id):
    """Approve an order. In production, only chairperson; in prototype any
    authenticated user may approve."""
    user, err = _require_login()
    if err:
        return err

    conn = db.get_db()
    row = conn.execute(
        "SELECT * FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    if row is None:
        return jsonify({"error": "Order not found"}), 404

    now = _now_iso()
    conn.execute(
        """UPDATE orders SET status = 'Approved', approved_by = ?,
           updated_at = ? WHERE id = ?""",
        (user["name"], now, order_id),
    )
    conn.commit()

    _audit("APPROVE_ORDER",
           f"Order {row['order_number']} approved by {user['name']}",
           "order", order_id)

    updated = conn.execute(
        "SELECT * FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    return jsonify(_row_to_dict(updated))


@app.route("/api/orders/<order_id>/print")
def print_order(order_id):
    """Return the order data formatted for print / PDF generation."""
    conn = db.get_db()
    order = conn.execute(
        "SELECT * FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    if order is None:
        return jsonify({"error": "Order not found"}), 404

    order_dict = _row_to_dict(order)

    # Enrich with child data if available
    if order_dict.get("child_id"):
        child = conn.execute(
            "SELECT * FROM children WHERE id = ?",
            (order_dict["child_id"],),
        ).fetchone()
        if child:
            order_dict["child"] = _row_to_dict(child)

    order_dict["print_format"] = True
    order_dict["generated_at"] = _now_iso()
    return jsonify(order_dict)


# ════════════════════════════════════════════════════════════════════════
#  CCIs  (Child Care Institutions)
# ════════════════════════════════════════════════════════════════════════

@app.route("/api/ccis")
def list_ccis():
    """List all registered CCIs."""
    conn = db.get_db()
    rows = conn.execute("SELECT * FROM ccis ORDER BY name").fetchall()
    return jsonify(_rows_to_list(rows))


@app.route("/api/ccis/<cci_id>")
def get_cci(cci_id):
    """Get CCI detail with occupancy, children count, and visit history."""
    conn = db.get_db()
    cci = conn.execute(
        "SELECT * FROM ccis WHERE id = ?", (cci_id,)
    ).fetchone()
    if cci is None:
        return jsonify({"error": "CCI not found"}), 404

    result = _row_to_dict(cci)

    children_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM children WHERE cci_id = ?", (cci_id,)
    ).fetchone()["cnt"]
    result["children_count"] = children_count
    result["occupancy_pct"] = (
        round(children_count / result["capacity"] * 100, 1)
        if result.get("capacity") and result["capacity"] > 0 else 0
    )

    visits = conn.execute(
        """SELECT * FROM cci_visits WHERE cci_id = ?
           ORDER BY visit_date DESC""",
        (cci_id,),
    ).fetchall()
    result["inspections"] = _rows_to_list(visits)

    return jsonify(result)


# ════════════════════════════════════════════════════════════════════════
#  Family Visits
# ════════════════════════════════════════════════════════════════════════

@app.route("/api/children/<child_id>/visits")
def list_family_visits(child_id):
    """Get the family-visit log for a child."""
    conn = db.get_db()
    rows = conn.execute(
        """SELECT * FROM family_visits WHERE child_id = ?
           ORDER BY visit_date DESC""",
        (child_id,),
    ).fetchall()
    return jsonify(_rows_to_list(rows))


@app.route("/api/children/<child_id>/visits", methods=["POST"])
def log_family_visit(child_id):
    """Log a new family visit for a child."""
    user, err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    conn = db.get_db()

    visit_id = str(uuid.uuid4())
    now = _now_iso()

    conn.execute(
        """INSERT INTO family_visits
           (id, child_id, visit_date, visitor_name, relationship,
            duration_minutes, notes, logged_by, created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            visit_id,
            child_id,
            data.get("visit_date", now[:10]),
            data.get("visitor_name", ""),
            data.get("relationship", ""),
            data.get("duration_minutes", 0),
            data.get("notes", ""),
            user["name"],
            now,
        ),
    )

    # Update last_family_contact on the child record
    conn.execute(
        "UPDATE children SET last_family_contact = ?, updated_at = ? WHERE id = ?",
        (data.get("visit_date", now[:10]), now, child_id),
    )

    conn.commit()

    _audit("LOG_FAMILY_VISIT",
           f"Family visit logged for child {child_id}",
           "family_visit", visit_id)

    row = conn.execute(
        "SELECT * FROM family_visits WHERE id = ?", (visit_id,)
    ).fetchone()
    return jsonify(_row_to_dict(row)), 201


# ════════════════════════════════════════════════════════════════════════
#  CCI Inspections
# ════════════════════════════════════════════════════════════════════════

@app.route("/api/ccis/<cci_id>/inspections")
def list_inspections(cci_id):
    """Get the inspection visit log for a CCI."""
    conn = db.get_db()
    rows = conn.execute(
        """SELECT * FROM cci_visits WHERE cci_id = ?
           ORDER BY visit_date DESC""",
        (cci_id,),
    ).fetchall()
    return jsonify(_rows_to_list(rows))


@app.route("/api/ccis/<cci_id>/inspections", methods=["POST"])
def log_inspection(cci_id):
    """Log a DCPU inspection visit to a CCI."""
    user, err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    conn = db.get_db()

    inspection_id = str(uuid.uuid4())
    now = _now_iso()

    conn.execute(
        """INSERT INTO cci_visits
           (id, cci_id, visit_date, inspector_name, visit_type,
            findings, recommendations, rating, logged_by, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            inspection_id,
            cci_id,
            data.get("visit_date", now[:10]),
            data.get("inspector_name", user["name"]),
            data.get("visit_type", "Routine"),
            data.get("findings", ""),
            data.get("recommendations", ""),
            data.get("rating", ""),
            user["name"],
            now,
        ),
    )

    # Update last_inspection on the CCI
    conn.execute(
        "UPDATE ccis SET last_inspection = ?, updated_at = ? WHERE id = ?",
        (data.get("visit_date", now[:10]), now, cci_id),
    )

    conn.commit()

    _audit("LOG_INSPECTION",
           f"Inspection logged for CCI {cci_id}",
           "cci_inspection", inspection_id)

    row = conn.execute(
        "SELECT * FROM cci_visits WHERE id = ?", (inspection_id,)
    ).fetchone()
    return jsonify(_row_to_dict(row)), 201


# ════════════════════════════════════════════════════════════════════════
#  Dashboard & Alerts
# ════════════════════════════════════════════════════════════════════════

@app.route("/api/dashboard/stats")
def dashboard_stats():
    """Return aggregate statistics for the dashboard."""
    conn = db.get_db()
    now = datetime.now()
    six_months_ago = (now - timedelta(days=180)).strftime("%Y-%m-%d")

    total_children = conn.execute(
        "SELECT COUNT(*) as cnt FROM children"
    ).fetchone()["cnt"]

    # By legal status
    status_rows = conn.execute(
        """SELECT legal_status, COUNT(*) as cnt FROM children
           GROUP BY legal_status"""
    ).fetchall()
    by_status = {r["legal_status"]: r["cnt"] for r in status_rows}

    # By admission category
    cat_rows = conn.execute(
        """SELECT admission_category, COUNT(*) as cnt FROM children
           GROUP BY admission_category"""
    ).fetchall()
    by_category = {r["admission_category"]: r["cnt"] for r in cat_rows}

    total_ccis = conn.execute(
        "SELECT COUNT(*) as cnt FROM ccis"
    ).fetchone()["cnt"]
    total_hearings = conn.execute(
        "SELECT COUNT(*) as cnt FROM hearings"
    ).fetchone()["cnt"]
    total_orders = conn.execute(
        "SELECT COUNT(*) as cnt FROM orders"
    ).fetchone()["cnt"]

    # Deadline statistics
    today = now.strftime("%Y-%m-%d")
    seven_days = (now + timedelta(days=7)).strftime("%Y-%m-%d")

    overdue = conn.execute(
        """SELECT COUNT(*) as cnt FROM deadlines
           WHERE status = 'pending' AND due_date < ?""",
        (today,),
    ).fetchone()["cnt"]

    approaching = conn.execute(
        """SELECT COUNT(*) as cnt FROM deadlines
           WHERE status = 'pending' AND due_date >= ? AND due_date <= ?""",
        (today, seven_days),
    ).fetchone()["cnt"]

    # Children approaching age-out (17+ years old)
    ageout = conn.execute(
        "SELECT COUNT(*) as cnt FROM children WHERE age >= 17"
    ).fetchone()["cnt"]

    # Children with no family contact for 6+ months
    no_contact = conn.execute(
        """SELECT COUNT(*) as cnt FROM children
           WHERE last_family_contact IS NULL
              OR last_family_contact < ?""",
        (six_months_ago,),
    ).fetchone()["cnt"]

    # LFA eligible
    lfa = conn.execute(
        "SELECT COUNT(*) as cnt FROM children WHERE is_lfa_eligible = 1"
    ).fetchone()["cnt"]

    return jsonify({
        "total_children":               total_children,
        "by_status":                    by_status,
        "by_category":                  by_category,
        "total_ccis":                   total_ccis,
        "total_hearings":               total_hearings,
        "total_orders":                 total_orders,
        "overdue_deadlines":            overdue,
        "approaching_deadlines":        approaching,
        "children_approaching_ageout":  ageout,
        "children_no_family_contact":   no_contact,
        "lfa_eligible_count":           lfa,
    })


@app.route("/api/dashboard/deadlines")
def dashboard_deadlines():
    """List all deadlines with urgency colour coding."""
    conn = db.get_db()
    rows = conn.execute(
        "SELECT * FROM deadlines ORDER BY due_date ASC"
    ).fetchall()

    now = datetime.now()
    seven_days = now + timedelta(days=7)
    result = []

    for r in rows:
        d = _row_to_dict(r)
        try:
            due = datetime.strptime(d["due_date"], "%Y-%m-%d")
        except (ValueError, TypeError):
            due = now

        if d.get("status") == "completed":
            d["urgency"] = "green"
        elif due < now:
            d["urgency"] = "red"
        elif due <= seven_days:
            d["urgency"] = "amber"
        else:
            d["urgency"] = "green"

        result.append(d)

    return jsonify(result)


@app.route("/api/dashboard/alerts")
def dashboard_alerts():
    """Generate alerts: age-out, LFA flags, no-contact, overdue deadlines."""
    conn = db.get_db()
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    six_months_ago = (now - timedelta(days=180)).strftime("%Y-%m-%d")
    alerts = []

    # Age-out alerts (children aged 17+)
    ageout_children = conn.execute(
        "SELECT id, child_code, name, age FROM children WHERE age >= 17"
    ).fetchall()
    for c in ageout_children:
        alerts.append({
            "type":     "AGE_OUT",
            "severity": "high",
            "child_id": c["id"],
            "child_code": c["child_code"],
            "message":  f"{c['name']} (age {c['age']}) is approaching age-out",
        })

    # LFA eligible children
    lfa_children = conn.execute(
        """SELECT id, child_code, name FROM children
           WHERE is_lfa_eligible = 1"""
    ).fetchall()
    for c in lfa_children:
        alerts.append({
            "type":     "LFA_ELIGIBLE",
            "severity": "medium",
            "child_id": c["id"],
            "child_code": c["child_code"],
            "message":  f"{c['name']} is eligible for Legal Free for Adoption",
        })

    # No family contact for 6+ months
    no_contact = conn.execute(
        """SELECT id, child_code, name, last_family_contact FROM children
           WHERE last_family_contact IS NULL
              OR last_family_contact < ?""",
        (six_months_ago,),
    ).fetchall()
    for c in no_contact:
        alerts.append({
            "type":     "NO_FAMILY_CONTACT",
            "severity": "medium",
            "child_id": c["id"],
            "child_code": c["child_code"],
            "message":  f"{c['name']} has had no family contact for 6+ months",
        })

    # Overdue deadlines
    overdue = conn.execute(
        """SELECT d.*, c.child_code, c.name as child_name
           FROM deadlines d
           LEFT JOIN children c ON d.child_id = c.id
           WHERE d.status = 'pending' AND d.due_date < ?""",
        (today,),
    ).fetchall()
    for d in overdue:
        alerts.append({
            "type":     "OVERDUE_DEADLINE",
            "severity": "high",
            "child_id": d["child_id"],
            "child_code": d["child_code"] or "",
            "message":  (f"Overdue: {d['description']} for "
                         f"{d['child_name'] or 'unknown'} "
                         f"(due {d['due_date']})"),
        })

    return jsonify(alerts)


# ════════════════════════════════════════════════════════════════════════
#  Reports
# ════════════════════════════════════════════════════════════════════════

@app.route("/api/reports/monthly")
def monthly_report():
    """Generate monthly district report data."""
    month = request.args.get("month", datetime.now().month, type=int)
    year  = request.args.get("year", datetime.now().year, type=int)

    # Build date range for the month
    start = f"{year}-{month:02d}-01"
    if month == 12:
        end = f"{year + 1}-01-01"
    else:
        end = f"{year}-{month + 1:02d}-01"

    conn = db.get_db()

    admissions = conn.execute(
        """SELECT COUNT(*) as cnt FROM children
           WHERE admission_date >= ? AND admission_date < ?""",
        (start, end),
    ).fetchone()["cnt"]

    hearings = conn.execute(
        """SELECT COUNT(*) as cnt FROM hearings
           WHERE hearing_date >= ? AND hearing_date < ?""",
        (start, end),
    ).fetchone()["cnt"]

    orders = conn.execute(
        """SELECT COUNT(*) as cnt FROM orders
           WHERE order_date >= ? AND order_date < ?""",
        (start, end),
    ).fetchone()["cnt"]

    restorations = conn.execute(
        """SELECT COUNT(*) as cnt FROM case_history
           WHERE action = 'STATUS_CHANGE' AND new_status = 'Restored'
             AND timestamp >= ? AND timestamp < ?""",
        (start, end),
    ).fetchone()["cnt"]

    adoptions = conn.execute(
        """SELECT COUNT(*) as cnt FROM case_history
           WHERE action = 'STATUS_CHANGE' AND new_status = 'Adopted'
             AND timestamp >= ? AND timestamp < ?""",
        (start, end),
    ).fetchone()["cnt"]

    return jsonify({
        "month":          month,
        "year":           year,
        "admissions":     admissions,
        "hearings_held":  hearings,
        "orders_issued":  orders,
        "restorations":   restorations,
        "adoptions":      adoptions,
    })


@app.route("/api/reports/quarterly")
def quarterly_report():
    """Generate quarterly state report data."""
    quarter = request.args.get("quarter", 1, type=int)
    year    = request.args.get("year", datetime.now().year, type=int)

    quarter_starts = {1: 1, 2: 4, 3: 7, 4: 10}
    start_month = quarter_starts.get(quarter, 1)
    end_month   = start_month + 3

    start = f"{year}-{start_month:02d}-01"
    if end_month > 12:
        end = f"{year + 1}-01-01"
    else:
        end = f"{year}-{end_month:02d}-01"

    conn = db.get_db()

    total_children = conn.execute(
        "SELECT COUNT(*) as cnt FROM children"
    ).fetchone()["cnt"]

    new_admissions = conn.execute(
        """SELECT COUNT(*) as cnt FROM children
           WHERE admission_date >= ? AND admission_date < ?""",
        (start, end),
    ).fetchone()["cnt"]

    hearings = conn.execute(
        """SELECT COUNT(*) as cnt FROM hearings
           WHERE hearing_date >= ? AND hearing_date < ?""",
        (start, end),
    ).fetchone()["cnt"]

    orders = conn.execute(
        """SELECT COUNT(*) as cnt FROM orders
           WHERE order_date >= ? AND order_date < ?""",
        (start, end),
    ).fetchone()["cnt"]

    # Status breakdown at current point
    status_rows = conn.execute(
        """SELECT legal_status, COUNT(*) as cnt FROM children
           GROUP BY legal_status"""
    ).fetchall()
    by_status = {r["legal_status"]: r["cnt"] for r in status_rows}

    # CCI occupancy summary
    ccis = conn.execute("SELECT * FROM ccis").fetchall()
    cci_summary = []
    for cci in ccis:
        count = conn.execute(
            "SELECT COUNT(*) as cnt FROM children WHERE cci_id = ?",
            (cci["id"],),
        ).fetchone()["cnt"]
        cci_summary.append({
            "name":       cci["name"],
            "capacity":   cci["capacity"],
            "current":    count,
            "occupancy":  round(count / cci["capacity"] * 100, 1)
                          if cci["capacity"] and cci["capacity"] > 0 else 0,
        })

    return jsonify({
        "quarter":          quarter,
        "year":             year,
        "total_children":   total_children,
        "new_admissions":   new_admissions,
        "hearings_held":    hearings,
        "orders_issued":    orders,
        "by_status":        by_status,
        "cci_occupancy":    cci_summary,
    })


# ════════════════════════════════════════════════════════════════════════
#  Audit Log
# ════════════════════════════════════════════════════════════════════════

@app.route("/api/audit")
def audit_log():
    """Return audit log entries (all roles may view in prototype)."""
    conn = db.get_db()
    limit = request.args.get("limit", 200, type=int)
    rows = conn.execute(
        "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return jsonify(_rows_to_list(rows))


# ════════════════════════════════════════════════════════════════════════
#  Database init on startup
# ════════════════════════════════════════════════════════════════════════

with app.app_context():
    db.init_db()


# ════════════════════════════════════════════════════════════════════════
#  Entry point
# ════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  Child Protection Case Management Platform")
    print(f"  ASR Model : {MODEL_PATH}")
    print(f"  Device    : {DEVICE}")
    print(f"  HF token  : {'SET (OK)' if HF_TOKEN else 'NOT SET - gated repos will fail'}")
    print("  URL       : http://localhost:5000")
    print("=" * 60)
    if not HF_TOKEN:
        print()
        print("  !  No HF_TOKEN found. If the model is gated, set it with:")
        print("       set HF_TOKEN=hf_your_token_here")
        print("     Then restart the app.")
        print()
    app.run(debug=False, host="0.0.0.0", port=5000)
