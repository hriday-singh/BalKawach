import uvicorn
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from transcription_server.db import init_db
from transcription_server.routes import router
from transcription_server.worker import start_worker

class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find('GET /api/languages') == -1

logging.getLogger("uvicorn.access").addFilter(EndpointFilter())


app = FastAPI(title="Transcription Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:9122",
        "http://localhost:5173",
        "https://balkawach.stratizone.com",
        "https://balkawach.app.stratizone.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.on_event("startup")
def startup_event():
    init_db()
    start_worker()

if __name__ == "__main__":
    print("Starting Transcription Server on port 9121...")
    uvicorn.run("transcription_server.main:app", host="0.0.0.0", port=9121, reload=True)
