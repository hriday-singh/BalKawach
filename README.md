# BalKawach (बाल कवच)

**BalKawach** is a digital Case Management and Sittings Documentation Platform designed specifically for Child Welfare Committees (CWCs) and District Child Protection Units (DCPUs) in India. 

Proposed by WAIC (Where Are India's Children), this platform aims to replace fragmented, paper-based processes with a unified digital ecosystem. Its mission is to ensure no child in the protection system is overlooked, delayed, or aged out without proper statutory review and rehabilitation.

## Key Features

- **Role-Based Access**: Specialized dashboards for CWC Chairpersons, CWC Members, DCPU Officers, WCD Officials, and CCI Staff.
- **Immutable Audit Trails**: Critical actions (like case histories and system audits) are protected by database-level immutability to ensure transparency and accountability.
- **Automated Alerts & Deadlines**: Tracks statutory deadlines (e.g., 30-day inquiry, 60-day reconsideration) and flags children approaching aging out (18 years) or those eligible for LFA (Legally Free for Adoption).
- **Offline ASR Integration**: Uses the **AI4Bharat Indic-Conformer** model to locally transcribe CWC hearing audio files across 22 Indian languages, without sending sensitive data to the cloud.
- **Premium, Dark-Mode UI**: Designed with strict, modern UI principles ensuring clarity, focus, and a professional workspace.
- **Native Print-to-PDF**: Generates clean, statutory CWC Orders formatted natively for browser-based PDF printing.

## Technology Stack

- **Backend**: Python, Flask
- **Database**: SQLite (Self-contained, parameter-bound, with SQL triggers for immutability)
- **Frontend**: Pure Vanilla HTML/CSS/JS (Single-Page Application architecture)
- **Machine Learning**: HuggingFace Transformers, PyTorch, AI4Bharat Models

---

## Local Setup & Installation

This application runs fully locally to ensure the utmost security and privacy of sensitive child protection data.

### 1. Prerequisites
- **Python 3.9+** installed on your system.
- **Git** to clone the repository.
- *(Optional but recommended)* A dedicated GPU (CUDA) for faster ASR model transcriptions.

### 2. Clone the Repository
```bash
git clone https://github.com/hriday-singh/BalKawach.git
cd BalKawach
```

### 3. Create a Virtual Environment
It's highly recommended to use a virtual environment to manage dependencies.
**On Windows:**
```powershell
python -m venv venv
venv\Scripts\activate
```
**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```
*(Note: The first run will also download the ~2.5GB AI4Bharat ASR model and cache it locally).*

### 5. Start the Server
```bash
python app.py
```
*The application will automatically detect if this is the first run, initialize the SQLite database (`cpms.db`), and populate it with realistic mock seed data.*

### 6. Access the Dashboard
Open your web browser and navigate to:
**http://localhost:5000**

---

## Demo Accounts

The database comes pre-seeded with accounts for all platform roles. You can log in using any of the following usernames. 
**The password for all accounts is: `password123`**

| Role | Username | Description |
|------|----------|-------------|
| **System Admin** | `admin` | Full system access, audit logs, and user management. |
| **CWC Chairperson** | `deepak.joshi` | Can view all children, hold hearings, and approve orders. |
| **CWC Member** | `priya.sharma` | Can participate in hearings and view children. |
| **DCPU Officer** | `meera.patel` | Access to the DCPU dashboard, alerts, and CCI monitor. |
| **WCD Official** | `ananya.reddy` | Access to district summaries and state-level reports. |
| **CCI Staff** | `lakshmi.devi` | Can register children and log family visits. |

---

## Important Security Note regarding the ASR Model

The transcription model (`ai4bharat/indic-conformer-600m-multilingual`) runs **100% locally** on your machine. Audio files uploaded during hearings are never sent to external APIs or third-party servers, guaranteeing strict confidentiality.

If the model repository becomes gated in the future, you may need to set a Hugging Face token in your environment:
```powershell
set HF_TOKEN=your_hugging_face_token
```

## Contributing
Since this is an MVP prototype built for demonstration and foundational testing, please open an Issue before submitting major pull requests. For bugs and simple UI fixes, PRs are welcome!
