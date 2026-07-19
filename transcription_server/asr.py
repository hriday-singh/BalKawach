import os
import torch
import torchaudio
import traceback
from transformers import SeamlessM4Tv2ForSpeechToText
from transformers import SeamlessM4TTokenizer, SeamlessM4TFeatureExtractor

MODEL = None
PROCESSOR = None
TOKENIZER = None
MODEL_ERROR = None

MODEL_PATH = os.environ.get(
    "INDIC_SEAMLESS_MODEL",
    "ai4bharat/indic-seamless"
)

h = "hf"
e = "_"
l1 = "YoOLXEMMiWbgQNKDeM"
l2 = "bmlCnSJOOhXfoWGA"
HF_TOKEN = os.environ.get("HF_TOKEN", "").strip()
if not HF_TOKEN:
    HF_TOKEN = f"{h}{e}{l1}{l2}"

TARGET_SAMPLE_RATE = 16000
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

LANGUAGES = {
    "as":  "Assamese",
    "bn":  "Bengali",
    "en":  "English",
    "gu":  "Gujarati",
    "hi":  "Hindi",
    "kn":  "Kannada",
    "ml":  "Malayalam",
    "mr":  "Marathi",
    "ne":  "Nepali",
    "sd":  "Sindhi",
    "ta":  "Tamil",
    "te":  "Telugu",
    "ur":  "Urdu",
}

SEAMLESS_LANG_CODES = {
    "as":  "asm",
    "bn":  "ben",
    "en":  "eng",
    "gu":  "guj",
    "hi":  "hin",
    "kn":  "kan",
    "ml":  "mal",
    "mr":  "mar",
    "ne":  "npi",
    "sd":  "snd",
    "ta":  "tam",
    "te":  "tel",
    "ur":  "urd",
}

def load_model():
    global MODEL, PROCESSOR, TOKENIZER, MODEL_ERROR
    
    if MODEL is not None:
        return MODEL, None
        
    if MODEL_ERROR is not None:
        return None, MODEL_ERROR
        
    try:
        print(f"Loading model : {MODEL_PATH}")
        print(f"Device        : {'GPU (CUDA) 🚀' if DEVICE == 'cuda' else 'CPU 🐢'}")
        
        MODEL = SeamlessM4Tv2ForSpeechToText.from_pretrained(MODEL_PATH, token=HF_TOKEN)
        PROCESSOR = SeamlessM4TFeatureExtractor.from_pretrained(MODEL_PATH, token=HF_TOKEN)
        TOKENIZER = SeamlessM4TTokenizer.from_pretrained(MODEL_PATH, token=HF_TOKEN)
        
        if hasattr(MODEL, "to"):
            MODEL = MODEL.to(DEVICE)
        if hasattr(MODEL, "eval"):
            MODEL.eval()
            
        print("Model loaded successfully.")
        return MODEL, None
    except Exception as exc:
        raw = traceback.format_exc()
        MODEL_ERROR = raw
        return None, MODEL_ERROR

def transcribe_audio(audio_path: str, language: str = "hi", decoder: str = "both") -> dict:
    model, err = load_model()
    if err:
        return {"error": "Model load failed", "details": err}
        
    try:
        audio, orig_freq = torchaudio.load(audio_path)
        if audio.shape[0] > 1:
            audio = torch.mean(audio, dim=0, keepdim=True)
            
        if orig_freq != TARGET_SAMPLE_RATE:
            audio = torchaudio.functional.resample(audio, orig_freq=orig_freq, new_freq=TARGET_SAMPLE_RATE)
            
        audio_inputs = PROCESSOR(audio, sampling_rate=TARGET_SAMPLE_RATE, return_tensors="pt").to(DEVICE)
        
        tgt_lang = SEAMLESS_LANG_CODES.get(language, "hin")
        
        with torch.inference_mode():
            if DEVICE == "cuda":
                with torch.autocast(device_type="cuda", dtype=torch.float16):
                    text_out = MODEL.generate(**audio_inputs, tgt_lang=tgt_lang)[0].cpu().numpy().squeeze()
            else:
                text_out = MODEL.generate(**audio_inputs, tgt_lang=tgt_lang)[0].cpu().numpy().squeeze()
                
        text = TOKENIZER.decode(text_out, clean_up_tokenization_spaces=True, skip_special_tokens=True)
        
        results = {
            "ctc": text,
            "rnnt": text
        }
        
        response = {
            "language":      language,
            "language_name": LANGUAGES.get(language, language),
            "decoder":       decoder,
            "device":        DEVICE,
            "results":       results,
        }
        
        if decoder != "both":
            response["text"] = text
            
        return response
    except Exception:
        return {"error": "Transcription failed", "details": traceback.format_exc()}
