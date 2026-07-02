import weasyprint
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response

from server.db import get_db
from server.utils import _row_to_dict
from server.fastapi_routes.dependencies import require_roles, DATA_READ_ROLES

router = APIRouter()

@router.get("/api/orders/{order_id}/pdf")
def export_order_pdf(order_id: str, user: dict = Depends(require_roles(DATA_READ_ROLES))):
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    order_dict = _row_to_dict(order)
    
    if order_dict.get("child_id"):
        child = conn.execute("SELECT * FROM children WHERE id = ?", (order_dict["child_id"],)).fetchone()
        if child:
            order_dict["child"] = _row_to_dict(child)
            
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Order {order_dict.get('order_number', 'N/A')}</title>
        <style>
            @page {{
                size: A4;
                margin: 2cm;
            }}
            body {{ 
                font-family: Arial, sans-serif; 
                line-height: 1.6;
                color: #333;
            }}
            .header {{
                text-align: center;
                border-bottom: 2px solid #333;
                padding-bottom: 20px;
                margin-bottom: 30px;
            }}
            .header h1 {{ margin: 0 0 10px 0; font-size: 24px; }}
            .header p {{ margin: 0; font-size: 14px; color: #666; }}
            .section {{ margin-bottom: 30px; }}
            .section h2 {{
                font-size: 18px;
                border-bottom: 1px solid #ccc;
                padding-bottom: 5px;
                margin-bottom: 15px;
            }}
            .grid {{
                display: table;
                width: 100%;
            }}
            .row {{
                display: table-row;
            }}
            .label {{
                display: table-cell;
                font-weight: bold;
                padding: 5px 10px 5px 0;
                width: 150px;
            }}
            .value {{
                display: table-cell;
                padding: 5px 0;
            }}
            .content-box {{
                background-color: #f9f9f9;
                border: 1px solid #eee;
                padding: 15px;
                min-height: 100px;
                white-space: pre-wrap;
            }}
            .footer {{
                margin-top: 50px;
                text-align: right;
                font-style: italic;
            }}
            .signature {{
                margin-top: 30px;
                padding-top: 10px;
                border-top: 1px solid #333;
                display: inline-block;
                min-width: 200px;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>CHILD WELFARE COMMITTEE</h1>
            <p>Order Document</p>
            <p>District: {order_dict.get('district', 'N/A')}</p>
        </div>
        
        <div class="section">
            <h2>Order Details</h2>
            <div class="grid">
                <div class="row">
                    <div class="label">Order Number:</div>
                    <div class="value">{order_dict.get('order_number', 'N/A')}</div>
                </div>
                <div class="row">
                    <div class="label">Order Date:</div>
                    <div class="value">{order_dict.get('created_at', 'N/A')}</div>
                </div>
                <div class="row">
                    <div class="label">Status:</div>
                    <div class="value">{str(order_dict.get('status', 'N/A')).title()}</div>
                </div>
                <div class="row">
                    <div class="label">Type:</div>
                    <div class="value">{str(order_dict.get('order_type', 'N/A')).replace('_', ' ').title()}</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>Child Information</h2>
            <div class="grid">
                <div class="row">
                    <div class="label">Name:</div>
                    <div class="value">{order_dict.get('child', {{}}).get('name', 'N/A')}</div>
                </div>
                <div class="row">
                    <div class="label">Child Code:</div>
                    <div class="value">{order_dict.get('child', {{}}).get('child_code', 'N/A')}</div>
                </div>
                <div class="row">
                    <div class="label">Gender:</div>
                    <div class="value">{order_dict.get('child', {{}}).get('gender', 'N/A')}</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>Findings</h2>
            <div class="content-box">{order_dict.get('findings', 'No findings recorded.')}</div>
        </div>
        
        <div class="section">
            <h2>Order / Directives</h2>
            <div class="content-box">{order_dict.get('order_body', 'No directives recorded.')}</div>
        </div>
        
        <div class="footer">
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <br><br><br>
            <div class="signature">
                {order_dict.get('approved_by', '_________________________')}
                <br>CWC Member / Chairperson
            </div>
        </div>
    </body>
    </html>
    """
    
    pdf_bytes = weasyprint.HTML(string=html_content).write_pdf()
    
    filename = f"Order_{order_dict.get('order_number', 'export')}.pdf"
    headers = {
        "Content-Disposition": f"attachment; filename={filename}"
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
