import uuid
from pathlib import Path
from flask import Blueprint, jsonify, request
from server.asr import transcribe_audio, load_model, LANGUAGES, DEVICE, MODEL, MODEL_PATH, HF_TOKEN, MODEL_ERROR
from server.auth import current_user

asr_bp = Blueprint("asr", __name__)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

def _save_upload(file_obj):
    """Save an uploaded file and return the path string."""
    suffix = Path(file_obj.filename).suffix if file_obj.filename else ".wav"
    if suffix not in {".wav", ".mp3", ".ogg", ".flac", ".m4a", ".webm", ".opus"}:
        suffix = ".wav"
    tmp_path = UPLOAD_DIR / f"{uuid.uuid4()}{suffix}"
    file_obj.save(str(tmp_path))
    return str(tmp_path)

@asr_bp.route("/api/languages")
def api_languages():
    """Return the dict of supported Indic languages."""
    return jsonify(LANGUAGES)

@asr_bp.route("/api/model-status")
def api_model_status():
    """Return whether the ASR model is loaded and ready."""
    return jsonify({
        "loaded":     MODEL is not None,
        "path":       MODEL_PATH,
        "device":     DEVICE,
        "token_set":  HF_TOKEN is not None,
        "load_error": MODEL_ERROR,
    })

@asr_bp.route("/api/model/load", methods=["POST"])
def api_model_load():
    """Manually load the ASR model (Admin action)."""
    user = current_user()
    if not user or user["role"] != "system_admin":
        return jsonify({"error": "Unauthorized"}), 403
    
    model, err = load_model()
    if err:
        return jsonify({"error": err}), 500
    
    return jsonify({"success": True, "message": "Model loaded successfully!"})

@asr_bp.route("/api/transcribe", methods=["POST"])
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

@asr_bp.route("/api/transcribe/chunk", methods=["POST"])
def api_transcribe_chunk():
    """Transcribe an audio chunk via the Indic Conformer model."""
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
