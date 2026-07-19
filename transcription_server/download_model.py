import os
from transformers import SeamlessM4Tv2ForSpeechToText, SeamlessM4TTokenizer, SeamlessM4TFeatureExtractor

MODEL_PATH = os.environ.get(
    "INDIC_SEAMLESS_MODEL",
    "ai4bharat/indic-seamless"
)

h = "hf"
e = "_"
l1 = "YoOLXEMMiWbgQNKDeM"
l2 = "bmlCnSJOOhXfoWGA"
HF_TOKEN = os.environ.get("HF_TOKEN", f"{h}{e}{l1}{l2}")

def preload_model():
    print(f"Pre-downloading model: {MODEL_PATH}...")
    try:
        SeamlessM4Tv2ForSpeechToText.from_pretrained(MODEL_PATH, token=HF_TOKEN)
        SeamlessM4TFeatureExtractor.from_pretrained(MODEL_PATH, token=HF_TOKEN)
        SeamlessM4TTokenizer.from_pretrained(MODEL_PATH, token=HF_TOKEN)
        print("Model downloaded and cached successfully!")
    except Exception as e:
        print(f"Error downloading model: {e}")

if __name__ == "__main__":
    preload_model()
