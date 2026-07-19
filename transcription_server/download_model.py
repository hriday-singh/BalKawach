import os
from transformers import SeamlessM4Tv2ForSpeechToText, SeamlessM4TTokenizer, SeamlessM4TFeatureExtractor

MODEL_PATH = os.environ.get(
    "INDIC_SEAMLESS_MODEL",
    "ai4bharat/indic-seamless"
)

def preload_model():
    print(f"Pre-downloading model: {MODEL_PATH}...")
    try:
        SeamlessM4Tv2ForSpeechToText.from_pretrained(MODEL_PATH)
        SeamlessM4TFeatureExtractor.from_pretrained(MODEL_PATH)
        SeamlessM4TTokenizer.from_pretrained(MODEL_PATH)
        print("Model downloaded and cached successfully!")
    except Exception as e:
        print(f"Error downloading model: {e}")

if __name__ == "__main__":
    preload_model()
