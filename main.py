import os
import traceback
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv

load_dotenv()

from server.db import init_db
from server.fastapi_routes.auth import router as auth_router
from server.fastapi_routes.api import router as api_router
from server.fastapi_routes.pdf import router as pdf_router
from server.fastapi_routes.transcription_proxy import router as asr_proxy_router

app = FastAPI(title="Child Protection Case Management Platform")

# SessionMiddleware must be added BEFORE CORSMiddleware so request.session works
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("FLASK_SECRET_KEY", "balkawach-fallback-secret-key"),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:9122",
        "http://localhost:5173",
        "http://localhost:3000",
        "https://balkawach.stratizone.com",
        "https://balkawach.app.stratizone.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(asr_proxy_router)
app.include_router(auth_router)
app.include_router(api_router)
app.include_router(pdf_router)

# Mount audio uploads under /api/audio so it goes through existing vite proxy without restart
uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/api/audio", StaticFiles(directory=uploads_dir), name="audio")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if os.environ.get("FASTAPI_DEBUG", "0") == "1":
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": str(exc),
                "traceback": traceback.format_exc()
            }
        )
    return JSONResponse(status_code=500, content={"error": "Internal Server Error"})

from server.cron import cron_worker
import asyncio

# Initialize DB on startup
@app.on_event("startup")
async def startup_event():
    init_db()
    asyncio.create_task(cron_worker())

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  Child Protection Case Management Platform (FastAPI) [Port 9120]")
    print("  URL       : http://localhost:9120")
    print("=" * 60)
    uvicorn.run("main:app", host="0.0.0.0", port=9120, reload=True)
