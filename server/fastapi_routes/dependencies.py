import uuid
from typing import Optional, List
from fastapi import Request, HTTPException, Depends
from server.db import get_db

ALL_ROLES = ('cci_staff', 'cwc_member', 'cwc_chairperson', 'dcpu_officer', 'wcd_official', 'system_admin')
ADMIN_ROLES = ('system_admin',)
CWC_ROLES = ('cwc_member', 'cwc_chairperson')
CHAIR_ROLES = ('cwc_chairperson',)
DCPU_ROLES = ('dcpu_officer',)
DATA_ENTRY_ROLES = ('cci_staff', 'cwc_member', 'cwc_chairperson', 'dcpu_officer', 'system_admin')
DATA_READ_ROLES = ALL_ROLES

def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

def require_roles(allowed_roles: List[str]):
    def role_checker(user: dict = Depends(get_current_user)):
        if user.get("role") not in allowed_roles:
            raise HTTPException(status_code=403, detail="Forbidden: insufficient role privileges")
        return user
    return role_checker

def audit(request: Request, action: str, details: str = "", entity_type: str = "", entity_id: str = "", conn=None):
    user = request.session.get("user")
    own_conn = conn is None
    if own_conn:
        conn = get_db()
    
    ip_address = request.client.host if request.client else None
    
    conn.execute(
        """INSERT INTO audit_logs
           (id, user_id, action, entity_type, entity_id, details, ip_address)
           VALUES (?,?,?,?,?,?,?)""",
        (
            str(uuid.uuid4()),
            user["id"] if user else "system",
            action,
            entity_type,
            entity_id,
            details,
            ip_address,
        ),
    )
    if own_conn:
        conn.commit()
