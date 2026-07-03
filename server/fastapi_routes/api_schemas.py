from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class CaseHistoryEntry(BaseModel):
    id: str
    child_id: str
    event_type: str
    event_date: str
    description: str
    performed_by: str
    performed_by_name: Optional[str] = None
    performed_by_role: Optional[str] = None
    performed_by_location: Optional[str] = None
    metadata: Optional[str] = None
    created_at: str

class ChildResponse(BaseModel):
    id: str
    child_code: str
    name: str
    date_of_birth: Optional[str] = None
    estimated_age: Optional[int] = None
    gender: str
    admission_date: str
    admission_category: str
    physical_description: Optional[str] = None
    cci_id: str
    cci_name: Optional[str] = None
    cci_district: Optional[str] = None
    district: str
    legal_status: str
    is_lfa_eligible: int
    lfa_flag_reason: Optional[str] = None
    created_at: str
    updated_at: str
    case_history: Optional[List[CaseHistoryEntry]] = None

class ChildRegisterRequest(BaseModel):
    name: str
    date_of_birth: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = "Other"
    admission_date: Optional[str] = None
    admission_category: Optional[str] = "other"
    physical_description: Optional[str] = ""
    cci_id: Optional[str] = "none"
    district: Optional[str] = "Hyderabad"
    is_lfa_eligible: Optional[int] = 0
    lfa_flag_reason: Optional[str] = ""

class ChildStatusUpdateRequest(BaseModel):
    legal_status: str
    notes: Optional[str] = ""

class HearingResponse(BaseModel):
    id: str
    child_id: str
    child_name: Optional[str] = None
    child_code: Optional[str] = None
    hearing_date: str
    scheduled_time: Optional[str] = None
    status: str
    reschedule_reason: Optional[str] = None
    attendees: Optional[str] = None
    transcript_raw: Optional[str] = None
    transcript_edited: Optional[str] = None
    transcript_language: str
    notes: Optional[str] = None
    audio_url: Optional[str] = None
    transcript_finalized: Optional[int] = 0
    transcript_finalized_at: Optional[str] = None
    transcript_finalized_by: Optional[str] = None
    created_by: str
    district: str
    created_at: str
    updated_at: str

class HearingCreateRequest(BaseModel):
    child_id: str
    hearing_date: Optional[str] = None
    hearing_time: Optional[str] = ""
    attendees: Optional[str] = "[]"
    notes: Optional[str] = ""
    district: Optional[str] = "Hyderabad"

class HearingUpdateRequest(BaseModel):
    status: Optional[str] = None
    transcript_raw: Optional[str] = None
    transcript_edited: Optional[str] = None
    transcript_finalized: Optional[int] = None
    transcript: Optional[str] = None
    notes: Optional[str] = None
    attendees: Optional[str] = None
    hearing_date: Optional[str] = None
    scheduled_time: Optional[str] = None
    hearing_time: Optional[str] = None
    district: Optional[str] = None
    location: Optional[str] = None

class OrderResponse(BaseModel):
    id: str
    order_number: str
    child_id: str
    hearing_id: Optional[str] = None
    order_type: str
    order_body: str
    findings: Optional[str] = None
    status: str
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    created_by: str
    district: str
    created_at: str
    updated_at: str
    updated_by: Optional[str] = None
    child: Optional[dict] = None
    print_format: Optional[bool] = None
    generated_at: Optional[str] = None

class OrderCreateRequest(BaseModel):
    child_id: Optional[str] = ""
    hearing_id: Optional[str] = ""
    order_type: Optional[str] = "other"
    district: Optional[str] = "Hyderabad"
    order_body: Optional[str] = ""
    findings: Optional[str] = ""
    transcript: Optional[str] = ""

class CCIResponse(BaseModel):
    id: str
    name: str
    district: str
    state: str
    address: Optional[str] = None
    capacity: int
    current_occupancy: Optional[int] = 0
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    staffing_details: Optional[str] = None
    last_inspection_date: Optional[str] = None
    created_at: str
    children_count: Optional[int] = None
    occupancy_pct: Optional[float] = None
    inspections: Optional[List[Any]] = None

class FamilyVisitResponse(BaseModel):
    id: str
    child_id: str
    visit_date: str
    visitor_name: str
    relationship: str
    duration_minutes: Optional[int] = 0
    notes: Optional[str] = None
    logged_by: str
    created_at: str

class FamilyVisitRequest(BaseModel):
    visit_date: Optional[str] = None
    visitor_name: str
    relationship: str
    duration_minutes: Optional[int] = 0
    notes: Optional[str] = ""

class CCIVisitResponse(BaseModel):
    id: str
    cci_id: str
    visit_date: str
    officer_id: str
    findings: Optional[str] = None
    recommendations: Optional[str] = None
    created_at: str

class CCIVisitRequest(BaseModel):
    visit_date: Optional[str] = None
    findings: Optional[str] = ""
    recommendations: Optional[str] = ""

class DeadlineResponse(BaseModel):
    id: str
    child_id: str
    deadline_type: str
    due_date: str
    status: str
    assigned_to: Optional[str] = None
    completed_at: Optional[str] = None
    escalated_to: Optional[str] = None
    escalated_at: Optional[str] = None
    notes: Optional[str] = None
    created_at: str
    urgency: Optional[str] = None
    child_code: Optional[str] = None
    child_name: Optional[str] = None

class DashboardStatsResponse(BaseModel):
    total_children: int
    by_status: Dict[str, int]
    by_category: Dict[str, int]
    total_ccis: int
    total_hearings: int
    total_orders: int
    overdue_deadlines: int
    approaching_deadlines: int
    children_approaching_ageout: int
    children_no_family_contact: int
    lfa_eligible_count: int

class AlertResponse(BaseModel):
    type: str
    severity: str
    child_id: str
    child_code: str
    message: str
    days_left: Optional[int] = None
    days_diff: Optional[int] = None
    time_metric: Optional[str] = None
    title: Optional[str] = None
    subtitle: Optional[str] = None

class MonthlyReportResponse(BaseModel):
    month: int
    year: int
    admissions: int
    hearings_held: int
    orders_issued: int
    restorations: int
    adoptions: int

class QuarterlyReportResponse(BaseModel):
    quarter: int
    year: int
    total_children: int
    new_admissions: int
    hearings_held: int
    orders_issued: int
    by_status: Dict[str, int]
    cci_occupancy: List[Dict[str, Any]]

class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str
    role: str
    district: str
    location: Optional[str] = None
    cci_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = True

class User(BaseModel):
    id: str
    username: str
    full_name: str
    role: str
    district: str
    location: Optional[str] = None
    cci_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    created_at: str

class AuditLogResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: str

class ChildUpdateRequest(BaseModel):
    name: Optional[str] = None
    date_of_birth: Optional[str] = None
    estimated_age: Optional[int] = None
    gender: Optional[str] = None
    physical_description: Optional[str] = None
    cci_id: Optional[str] = None
    district: Optional[str] = None
    is_lfa_eligible: Optional[int] = None
    lfa_flag_reason: Optional[str] = None

class CCICreateRequest(BaseModel):
    name: str
    district: str
    capacity: int
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    staffing_details: Optional[str] = None

class CCIUpdateRequest(BaseModel):
    name: Optional[str] = None
    district: Optional[str] = None
    capacity: Optional[int] = None
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    staffing_details: Optional[str] = None

class NotificationResponse(BaseModel):
    id: str
    user_id: str
    type: str
    title: str
    message: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    is_read: int
    created_at: str

class OrderUpdateRequest(BaseModel):
    order_body: Optional[str] = None
    findings: Optional[str] = None

class SuccessResponse(BaseModel):
    success: bool
    error: Optional[str] = None
