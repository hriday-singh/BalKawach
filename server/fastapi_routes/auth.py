import uuid
from typing import Optional, List
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from werkzeug.security import generate_password_hash, check_password_hash
from server.db import get_db
from server.utils import _row_to_dict, _rows_to_list
from server.fastapi_routes.dependencies import get_current_user, require_roles, audit, ADMIN_ROLES

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    full_name: str
    role: Optional[str] = "cci_staff"
    district: Optional[str] = "Hyderabad"
    cci_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    district: Optional[str] = None
    cci_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[int] = None

class UserResponse(BaseModel):
    id: str
    username: str
    full_name: str
    role: str
    district: str
    location: Optional[str] = None
    cci_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    is_active: int
    created_at: Optional[str] = None

class LoginResponse(BaseModel):
    message: str
    user: UserResponse

class MessageResponse(BaseModel):
    message: str

@router.post("/api/auth/login", response_model=LoginResponse)
def auth_login(data: LoginRequest, request: Request):
    username = data.username.strip()
    password = data.password.strip()

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

    if user is None or not check_password_hash(user["password_hash"], password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user["is_active"] == 0:
        raise HTTPException(status_code=403, detail="Account pending admin approval")

    user_dict = _row_to_dict(user)
    user_dict.pop("password_hash", None)
    request.session["user"] = user_dict

    audit(request, "LOGIN", f"User {username} logged in", "user", user_dict["id"])

    return {"message": "Login successful", "user": user_dict}

@router.post("/api/auth/register", response_model=MessageResponse, status_code=201)
def auth_register(data: RegisterRequest):
    username = data.username.strip()
    password = data.password.strip()
    full_name = data.full_name.strip()
    role = data.role
    
    if not username or not password or not full_name:
        raise HTTPException(status_code=400, detail="Missing required fields")
        
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")

    if role in ("system_admin", "wcd_official"):
        role = "cci_staff"
        
    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
        
    user_id = str(uuid.uuid4())
    pw_hash = generate_password_hash(password)
    
    conn.execute(
        """INSERT INTO users 
           (id, username, password_hash, full_name, role, district, cci_id, email, phone, is_active) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, username, pw_hash, full_name, role, data.district, data.cci_id, data.email, data.phone, 0)
    )
    conn.commit()
    return {"message": "Registration successful. Pending admin approval."}

@router.post("/api/auth/logout", response_model=MessageResponse)
def auth_logout(request: Request):
    user = request.session.get("user")
    if user:
        audit(request, "LOGOUT", f"User {user['full_name']} logged out", "user", user["id"])
    request.session.clear()
    return {"message": "Logged out"}

@router.get("/api/auth/me", response_model=UserResponse)
def auth_me(user: dict = Depends(get_current_user)):
    return user

@router.get("/api/auth/users", response_model=List[UserResponse])
def auth_users(user: dict = Depends(require_roles(ADMIN_ROLES))):
    conn = get_db()
    rows = conn.execute(
        "SELECT id, username, full_name as name, full_name, role, district, cci_id, email, phone, is_active, created_at FROM users"
    ).fetchall()
    return _rows_to_list(rows)

@router.post("/api/auth/users", response_model=MessageResponse, status_code=201)
def admin_create_user(data: RegisterRequest, request: Request, user: dict = Depends(require_roles(ADMIN_ROLES))):
    username = data.username.strip()
    password = data.password.strip()
    full_name = data.full_name.strip()
    
    if not username or not password or not full_name:
        raise HTTPException(status_code=400, detail="Missing required fields")
        
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")

    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
        
    user_id = str(uuid.uuid4())
    pw_hash = generate_password_hash(password)
    
    conn.execute(
        """INSERT INTO users 
           (id, username, password_hash, full_name, role, district, cci_id, email, phone, is_active) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, username, pw_hash, full_name, data.role, data.district, data.cci_id, data.email, data.phone, 1)
    )
    conn.commit()
    audit(request, "CREATE_USER", f"Admin created user {username}", "user", user_id, conn=conn)
    return {"message": "User created successfully"}

@router.put("/api/auth/users/{user_id}/approve", response_model=MessageResponse)
def admin_approve_user(user_id: str, request: Request, user: dict = Depends(require_roles(ADMIN_ROLES))):
    conn = get_db()
    conn.execute("UPDATE users SET is_active = 1 WHERE id = ?", (user_id,))
    conn.commit()
    audit(request, "APPROVE_USER", f"Admin approved user ID {user_id}", "user", user_id, conn=conn)
    return {"message": "User approved successfully"}

@router.put("/api/auth/users/{user_id}", response_model=MessageResponse)
def admin_update_user(user_id: str, data: UserUpdate, request: Request, user: dict = Depends(require_roles(ADMIN_ROLES))):
    conn = get_db()
    target_user = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    updates = []
    params = []
    
    fields = {
        "full_name": data.full_name,
        "role": data.role,
        "district": data.district,
        "cci_id": data.cci_id,
        "email": data.email,
        "phone": data.phone
    }

    for field, value in fields.items():
        if value is not None:
            updates.append(f"{field} = ?")
            params.append(value)

    if data.password is not None and data.password != "":
        if len(data.password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")
        updates.append("password_hash = ?")
        params.append(generate_password_hash(data.password))
        
    if data.is_active is not None:
        updates.append("is_active = ?")
        params.append(int(data.is_active))

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    params.append(user_id)
    conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", tuple(params))
    conn.commit()
    
    audit(request, "UPDATE_USER", f"Admin updated user ID {user_id}", "user", user_id, conn=conn)
    return {"message": "User updated successfully"}

@router.delete("/api/auth/users/{user_id}", response_model=MessageResponse)
def admin_delete_user(user_id: str, request: Request, user: dict = Depends(require_roles(ADMIN_ROLES))):
    conn = get_db()
    conn.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
    conn.commit()
    
    audit(request, "DEACTIVATE_USER", f"Admin deactivated user ID {user_id}", "user", user_id, conn=conn)
    return {"message": "User deactivated successfully"}
