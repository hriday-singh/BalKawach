import re

def main():
    file_path = "c:/Users/clash/OneDrive/Desktop/Codes/AI-ML/AI4Bharat/server/fastapi_routes/api.py"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. list_children
    content = re.sub(
        r'def list_children\([^)]*\):.*?rows = conn\.execute\(query \+ " ORDER BY created_at DESC", params\)\.fetchall\(\)\s*return _rows_to_list\(rows\)',
        r'''def list_children(
    request: Request,
    cci_id: Optional[str] = None,
    district: Optional[str] = None,
    legal_status: Optional[str] = None,
    admission_category: Optional[str] = None,
    is_lfa_eligible: Optional[int] = None,
    user: dict = Depends(require_roles(DATA_READ_ROLES))
):
    conn = get_db()
    auth_sql, auth_params = get_dashboard_filter(user)
    
    query = f"SELECT * FROM children WHERE {auth_sql}"
    params = list(auth_params)

    filters = {
        "cci_id": cci_id,
        "district": district,
        "legal_status": legal_status,
        "admission_category": admission_category,
        "is_lfa_eligible": is_lfa_eligible
    }

    for col, val in filters.items():
        if val is not None:
            query += f" AND {col} = ?"
            params.append(val)

    rows = conn.execute(query + " ORDER BY created_at DESC", params).fetchall()
    return _rows_to_list(rows)''',
        content,
        flags=re.DOTALL
    )

    # 2. search_children
    content = re.sub(
        r'def search_children\([^)]*\):.*?return _rows_to_list\(rows\)',
        r'''def search_children(q: str = "", user: dict = Depends(require_roles(DATA_READ_ROLES))):
    q = q.strip()
    if not q:
        return []

    conn = get_db()
    auth_sql, auth_params = get_dashboard_filter(user)
    
    rows = conn.execute(
        f"SELECT * FROM children WHERE ({auth_sql}) AND (name LIKE ? OR child_code LIKE ?) ORDER BY created_at DESC LIMIT 50",
        (*auth_params, f"%{q}%", f"%{q}%")
    ).fetchall()
    return _rows_to_list(rows)''',
        content,
        flags=re.DOTALL
    )

    # 3. get_child
    content = re.sub(
        r'def get_child\([^)]*\):.*?WHERE children\.id = \?",\s*\(child_id,\)\s*\)\.fetchone\(\)',
        r'''def get_child(child_id: str, user: dict = Depends(require_roles(DATA_READ_ROLES))):
    conn = get_db()
    auth_sql, auth_params = get_dashboard_filter(user, "children")
    
    child = conn.execute(
        f"""SELECT children.*, ccis.name as cci_name, ccis.district as cci_district 
           FROM children 
           LEFT JOIN ccis ON children.cci_id = ccis.id 
           WHERE children.id = ? AND {auth_sql}""", 
        (child_id, *auth_params)
    ).fetchone()''',
        content,
        flags=re.DOTALL
    )

    # 4. list_hearings
    content = re.sub(
        r'def list_hearings\([^)]*\):.*?rows = conn\.execute\(query \+ " ORDER BY h\.hearing_date DESC", params\)\.fetchall\(\)\s*return _rows_to_list\(rows\)',
        r'''def list_hearings(
    district: Optional[str] = None,
    status: Optional[str] = None,
    child_id: Optional[str] = None,
    user: dict = Depends(require_roles(DATA_READ_ROLES))
):
    conn = get_db()
    auth_sql, auth_params = get_dashboard_filter(user, "c")
    
    query = f"""
        SELECT h.*, c.name as child_name, c.child_code 
        FROM hearings h
        LEFT JOIN children c ON h.child_id = c.id
        WHERE {auth_sql}
    """
    params = list(auth_params)

    filters = {"h.district": district, "h.status": status, "h.child_id": child_id}

    for col, val in filters.items():
        if val is not None:
            query += f" AND {col} = ?"
            params.append(val)

    rows = conn.execute(query + " ORDER BY h.hearing_date DESC", params).fetchall()
    return _rows_to_list(rows)''',
        content,
        flags=re.DOTALL
    )

    # 5. list_orders
    content = re.sub(
        r'def list_orders\([^)]*\):.*?return result',
        r'''def list_orders(
    district: Optional[str] = None,
    status: Optional[str] = None,
    child_id: Optional[str] = None,
    user: dict = Depends(require_roles(DATA_READ_ROLES))
):
    conn = get_db()
    auth_sql, auth_params = get_dashboard_filter(user, "c")
    
    query = f"""
        SELECT o.*, c.name as child_name, c.child_code 
        FROM orders o
        LEFT JOIN children c ON o.child_id = c.id
        WHERE {auth_sql}
    """
    params = list(auth_params)

    filters = {"o.district": district, "o.status": status, "o.child_id": child_id}
    for col, val in filters.items():
        if val is not None:
            query += f" AND {col} = ?"
            params.append(val)

    rows = conn.execute(query + " ORDER BY o.created_at DESC", params).fetchall()
    
    result = []
    for r in rows:
        rd = dict(r)
        rd["child"] = {"name": r["child_name"], "id": r["child_id"], "child_code": r["child_code"]}
        result.append(rd)
    return result''',
        content,
        flags=re.DOTALL
    )

    # 6. list_ccis
    content = re.sub(
        r'def list_ccis\([^)]*\):.*?rows = conn\.execute\("SELECT \* FROM ccis ORDER BY name"\)\.fetchall\(\)\s*return _rows_to_list\(rows\)',
        r'''def list_ccis(user: dict = Depends(require_roles(DATA_READ_ROLES))):
    conn = get_db()
    conn.execute(\'''
        UPDATE ccis 
        SET current_occupancy = (
            SELECT COUNT(*) FROM children WHERE children.cci_id = ccis.id
        )
    \''')
    conn.commit()
    
    auth_sql, auth_params = get_dashboard_filter(user, "ccis")
    rows = conn.execute(f"SELECT * FROM ccis WHERE {auth_sql} ORDER BY name", auth_params).fetchall()
    return _rows_to_list(rows)''',
        content,
        flags=re.DOTALL
    )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
        print("Patched api.py")

if __name__ == "__main__":
    main()
