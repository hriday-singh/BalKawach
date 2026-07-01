"""
Child Protection Case Management Platform — Flask Backend
==========================================================
Combines the IndicConformer ASR engine with a full case-management
REST API backed by SQLite (via server/db.py).
"""

import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

from server import create_app
from server.asr import MODEL_PATH, DEVICE, HF_TOKEN

app = create_app()

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
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(
        debug=debug_mode, 
        host="0.0.0.0", 
        port=5000, 
        exclude_patterns=["*/site-packages/*", "*/site-packages/*/*"]
    )
