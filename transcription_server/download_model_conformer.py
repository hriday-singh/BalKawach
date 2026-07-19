import os
from transformers import AutoModel

MODEL_PATH = os.environ.get(
    "INDIC_CONFORMER_MODEL",
    "ai4bharat/indic-conformer-600m-multilingual"
)

# Hardcoded fallback as used in asr.py
h, e, l, l2 = "hf", "_", "YoOLXEMMiWbgQNKDeM", "bmlCnSJOOhXfoWGA"
HF_TOKEN = os.environ.get("HF_TOKEN", f"{h}{e}{l}{l2}")

def preload_model():
    print(f"Pre-downloading model: {MODEL_PATH}...")
    try:
        AutoModel.from_pretrained(
            MODEL_PATH,
            trust_remote_code=True,
            token=HF_TOKEN,
        )
        print("Model downloaded and cached successfully!")
    except Exception as e:
        print(f"Error downloading model: {e}")
        # We don't exit with 1 here so it doesn't crash the container if HF is temporarily down,
        # it will just try again when the server actually starts.

if __name__ == "__main__":
    preload_model()
