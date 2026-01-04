from fastapi import FastAPI, HTTPException, File, UploadFile, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
from scheduler import Volunteer, Shift, Scheduler, parse_iso
from auth import (
    verify_api_key, verify_admin_token, verify_master_user,
    create_access_token, create_api_key, get_all_api_keys,
    update_api_key_rate_limit, delete_api_key, get_api_key_usage,
    get_api_key_by_id, ensure_admin_exists, record_detailed_usage
)
import csv, io
import json
import httpx
from datetime import datetime

app = FastAPI(
    title="Volunteer Scheduler API",
    description="API for assigning volunteers to shifts with both greedy and optimal algorithms. Requires API key authentication.",
    version="2.0.0",
    contact={
        "name": "Arnav Shah",
    }
)

# Serve static files for admin interface
app.mount("/static", StaticFiles(directory="static"), name="static")

class AssignmentInput(BaseModel):
    shift_id: str
    volunteer_id: str

class ScheduleInput(BaseModel):
    volunteers: List[VolunteerInput]
    unassigned_shifts: List[ShiftInput]
    current_assignments: List[AssignmentInput] = []

def build_scheduler(vols_input: List[VolunteerInput], shifts_input: List[ShiftInput]) -> Scheduler:
    volunteers = {v.id: Volunteer(**v.dict()) for v in vols_input}
    shifts = {}
    for s in shifts_input:
        shifts[s.id] = Shift(
            id=s.id,
            start=parse_iso(s.start),
            end=parse_iso(s.end),
            required_groups=s.required_groups,
            allowed_groups=set(s.allowed_groups) if s.allowed_groups else None,
            excluded_groups=set(s.excluded_groups) if s.excluded_groups else None
        )
    return Scheduler(volunteers, shifts)

# ==================== ADMIN ENDPOINTS ====================

@app.get("/admin")
async def admin_interface():
    """Serve the admin web interface."""
    # Ensure at least one admin account exists
    ensure_admin_exists()
    return FileResponse("static/index.html")

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/admin/login")
def admin_login(credentials: LoginRequest):
    """Admin login endpoint - returns JWT token."""
    if not verify_master_user(credentials.username, credentials.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token(credentials.username)
    return {"access_token": token, "token_type": "bearer"}

class CreateKeyRequest(BaseModel):
    name: str
    rate_limit: int = 10000

@app.post("/admin/keys")
def generate_key(request: CreateKeyRequest, username: str = Depends(verify_admin_token)):
    """Generate a new API key (admin only)."""
    result = create_api_key(request.name, request.rate_limit)
    return result

@app.get("/")
async def root():
    """Returns API information."""
    return {
        "name": "Volunteer Scheduler API",
        "version": "2.0.0",
        "admin_interface": "/admin",
        "documentation": "/docs"
    }

@app.get("/admin/keys")
def list_keys(username: str = Depends(verify_admin_token)):
    """List all API keys (admin only)."""
    keys = get_all_api_keys()
    return {"keys": keys}

@app.put("/admin/keys/{key_id}")
def update_key_limit(key_id: int, rate_limit: int, username: str = Depends(verify_admin_token)):
    """Update rate limit for an API key (admin only)."""
    success = update_api_key_rate_limit(key_id, rate_limit)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"message": "Rate limit updated successfully"}

@app.delete("/admin/keys/{key_id}")
def revoke_key(key_id: int, username: str = Depends(verify_admin_token)):
    """Revoke/delete an API key (admin only)."""
    success = delete_api_key(key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"message": "API key revoked successfully"}

@app.get("/admin/usage/{key_id}")
def get_usage(key_id: int, days: int = 30, username: str = Depends(verify_admin_token)):
    """Get usage statistics for an API key (admin only)."""
    key_info = get_api_key_by_id(key_id)
    if not key_info:
        raise HTTPException(status_code=404, detail="API key not found")
    
    usage_data = get_api_key_usage(key_id, days)
    return {
        "key_name": key_info["name"],
        "rate_limit": key_info["rate_limit"],
        "usage": usage_data
    }

# ==================== SCHEDULER ENDPOINTS ====================

@app.post("/schedule/json")
def schedule_json(input_data: ScheduleInput, api_key: str = Depends(verify_api_key)):
    try:
        # Combine shifts
        all_shifts = input_data.unassigned_shifts
        # Note: current_assignments refers to existing shift IDs. 
        # For simplicity, we assume they exist in the input_data.unassigned_shifts or are fully defined.
        # The user wants "inputs to current assigned shifts, unassigned shifts, volunteers".
        # This implies unassigned_shifts are the ones we need to work on.
        
        sched = build_scheduler(input_data.volunteers, input_data.unassigned_shifts)
        
        # Prefill existing assignments
        prefill_data = [a.dict() for a in input_data.current_assignments]
        sched.prefill(prefill_data)
        
        # Assign the rest with randomization
        result = sched.assign_simple(shuffle_shifts=True)
        
        # Track detailed usage
        total_volunteers = sum(len(vids) for vids in result["assigned_shifts"].values())
        total_shifts = sum(1 for vids in result["assigned_shifts"].values() if len(vids) > 0)
        record_detailed_usage(api_key, total_shifts, total_volunteers)
        
        return {
            "assigned_shifts": result["assigned_shifts"],
            "unfilled_shifts": result["unfilled_shifts"],
            "volunteers": result["volunteers"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/schedule/csv")
async def schedule_csv(
    volunteers_file: UploadFile = File(...),
    shifts_file: UploadFile = File(...),
    assignments_file: Optional[UploadFile] = File(None),
    api_key: str = Depends(verify_api_key)
):
    try:
        # Read volunteers
        v_text = (await volunteers_file.read()).decode()
        volunteers = {row["id"]: Volunteer(
            id=row["id"], name=row.get("name", row["id"]),
            group=row.get("group") or None,
            max_hours=float(row.get("max_hours", 0))
        ) for row in csv.DictReader(io.StringIO(v_text))}

        # Read shifts
        s_text = (await shifts_file.read()).decode()
        shifts = {}
        for row in csv.DictReader(io.StringIO(s_text)):
            required_groups = {}
            for gpart in row.get("required_groups", "").split("|"):
                if ":" in gpart:
                    g, c = gpart.split(":")
                    required_groups[g.strip()] = int(c.strip())
            shifts[row["id"]] = Shift(
                id=row["id"], start=parse_iso(row["start"]), end=parse_iso(row["end"]),
                required_groups=required_groups,
                allowed_groups=set(row["allowed_groups"].split("|")) if row.get("allowed_groups") else None,
                excluded_groups=set(row["excluded_groups"].split("|")) if row.get("excluded_groups") else None
            )

        sched = Scheduler(volunteers, shifts)

        # Read current assignments if provided
        if assignments_file:
            a_text = (await assignments_file.read()).decode()
            prefill_data = list(csv.DictReader(io.StringIO(a_text)))
            sched.prefill(prefill_data)

        # Standard simple randomized assign
        result = sched.assign_simple(shuffle_shifts=True)

        # Track detailed usage
        total_volunteers = 0
        total_shifts = 0
        for s in sched.shifts.values():
            if s.assigned:
                total_shifts += 1
                total_volunteers += len(s.assigned)
        record_detailed_usage(api_key, total_shifts, total_volunteers)

        # Export CSV
        out_csv = io.StringIO()
        writer = csv.writer(out_csv)
        writer.writerow(["shift_id", "volunteer_id", "volunteer_name", "start", "end", "duration_hours"])
        for s in sched.shifts.values():
            for vid in s.assigned:
                v = sched.volunteers[vid]
                writer.writerow([s.id, v.id, v.name, s.start.isoformat(), s.end.isoformat(), f"{s.duration_hours():.2f}"])
        out_csv.seek(0)
        return {"csv": out_csv.getvalue()}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
# Removed legacy optimal and cpsat solvers to minimize memory and CPU usage as requested.
