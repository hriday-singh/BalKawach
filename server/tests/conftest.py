import os
import tempfile
import sqlite3
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

# Ensure server module can be imported
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import server.db as db_module

# Global temporary file for DB
db_fd, db_path = tempfile.mkstemp(suffix=".db")

# Patch DB_PATH in db module
db_module.DB_PATH = db_path

# Replace get_db
def get_test_db():
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn

# For any module that imports get_db from server.db, it will still get the old function 
# if it was imported directly, but the file shows `from server.db import get_db, _iso_now`
# So we need to mock it properly. Actually, if we just change DB_PATH, get_db will open the test db!
# So we don't even need to mock get_db as long as we mock DB_PATH before get_db is called.
# Wait, fastapi_routes.api might have already imported `get_db`. But `get_db` just uses `DB_PATH`.

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    db_module.DB_PATH = db_path
    db_module.init_db()
    yield
    os.close(db_fd)
    try:
        os.remove(db_path)
    except:
        pass

@pytest.fixture
def test_app():
    from server.fastapi_routes.api import router
    from server.fastapi_routes.dependencies import get_current_user
    import server.fastapi_routes.api as api_mod
    
    # Mock audit to avoid session errors
    api_mod.audit = lambda *args, **kwargs: None
    app = FastAPI()
    
    def override_get_current_user(request: Request):
        role = request.headers.get("X-Test-Role", "system_admin")
        user_id = request.headers.get("X-Test-User-Id", "test_user_id")
        return {
            "id": user_id,
            "username": "test",
            "full_name": "Test User",
            "role": role,
            "district": "Hyderabad",
            "cci_id": "test_cci_id"
        }
        
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.include_router(router)
    return app

@pytest.fixture
def client(test_app):
    return TestClient(test_app)

@pytest.fixture
def db():
    conn = db_module.get_db()
    yield conn
    conn.close()
