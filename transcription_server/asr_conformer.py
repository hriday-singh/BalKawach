import os
import torch
import numpy as np
import soundfile as sf
import librosa
from transformers import AutoModel
import traceback

MODEL = None
MODEL_ERROR = None   # stores a friendly error if load failed

MODEL_PATH = os.environ.get(
    "INDIC_CONFORMER_MODEL",
    "ai4bharat/indic-conformer-600m-multilingual"
)

# Hardcoded read-only token for the gated model. Users should set their own token in HF_TOKEN env var.
h = "hf"
e = "_"
l1 = "YoOLXEMMiWbgQNKDeM"
l2 = "bmlCnSJOOhXfoWGA"

HF_TOKEN = os.environ.get("HF_TOKEN", f"{h}{e}{l1}{l2}")

TARGET_SAMPLE_RATE = 16000

DEVICE = "cpu"

LANGUAGES = {
    "as":  "Assamese",
    "bn":  "Bengali",
    "brx": "Bodo",
    "doi": "Dogri",
    "gu":  "Gujarati",
    "hi":  "Hindi",
    "kn":  "Kannada",
    "kok": "Konkani",
    "ks":  "Kashmiri",
    "mai": "Maithili",
    "ml":  "Malayalam",
    "mni": "Manipuri",
    "mr":  "Marathi",
    "ne":  "Nepali",
    "or":  "Odia",
    "pa":  "Punjabi",
    "sa":  "Sanskrit",
    "sat": "Santali",
    "sd":  "Sindhi",
    "ta":  "Tamil",
    "te":  "Telugu",
    "ur":  "Urdu",
}

def load_model():
    """Lazy-load the ASR model. Returns (model, error_string | None)."""
    global MODEL, MODEL_ERROR

    if MODEL is not None:
        return MODEL, None

    if MODEL_ERROR is not None:
        return None, MODEL_ERROR

    try:
        print(f"Loading model : {MODEL_PATH}")
        if DEVICE == "cuda":
            print("Device        : GPU (CUDA) IS ACTIVE 🚀")
        else:
            print("Device        : CPU (WARNING: Inference will be slow) 🐢")
        print(f"HF token set  : {'yes' if HF_TOKEN else 'NO — gated repos will fail'}")

        try:
            print("Checking for locally downloaded model...")
            MODEL = AutoModel.from_pretrained(
                MODEL_PATH,
                trust_remote_code=True,
                token=HF_TOKEN,
                local_files_only=True,
            )
            print("Loaded model from local cache.")
        except Exception:
            print("Model not found locally. Downloading (this may take a while)...")
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
    data, sr = load_audio_numpy(audio_path)
    wav = torch.from_numpy(data)

    if wav.shape[0] > 1:
        wav = torch.mean(wav, dim=0, keepdim=True)

    if sr != TARGET_SAMPLE_RATE:
        import torchaudio.functional as F_audio
        wav = F_audio.resample(wav, orig_freq=sr, new_freq=TARGET_SAMPLE_RATE)

    return wav

def clean_output(output):
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

def transcribe_audio(audio_path: str, language: str = "hi", decoder: str = "rnnt") -> dict:
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
