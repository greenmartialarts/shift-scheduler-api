# api_scheduler.py
from fastapi import FastAPI, HTTPException, File, UploadFile, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from scheduler import Volunteer, Shift, Scheduler, parse_iso, OptimizationStrategy
import csv, io

app = FastAPI(title="Volunteer Scheduler API")

class VolunteerInput(BaseModel):
    id: str
    name: str
    group: Optional[str]
    max_hours: float

class ShiftInput(BaseModel):
    id: str
    start: str
    end: str
    required_groups: Dict[str, int]
    allowed_groups: Optional[List[str]] = None
    excluded_groups: Optional[List[str]] = None

class ScheduleInput(BaseModel):
    volunteers: List[VolunteerInput]
    shifts: List[ShiftInput]
    strategy: Optional[str] = Field(
        default="minimize_unfilled",
        description="Optimization strategy: minimize_unfilled, maximize_fairness, or minimize_overtime"
    )

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

@app.post("/schedule/json")
def schedule_json(input_data: ScheduleInput):
    try:
        # Validate strategy
        strategy = input_data.strategy
        valid_strategies = [s.value for s in OptimizationStrategy]
        if strategy not in valid_strategies:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid strategy '{strategy}'. Must be one of: {', '.join(valid_strategies)}"
            )
        
        sched = build_scheduler(input_data.volunteers, input_data.shifts)
        result = sched.assign(strategy=strategy)
        
        # If there are unfilled shifts, return error with partial schedule
        if result["unfilled_shifts"]:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "Unable to fill all shifts",
                    "unfilled_shifts": result["unfilled_shifts"],
                    "assigned_shifts": result["assigned_shifts"],
                    "volunteers": result["volunteers"]
                }
            )
        
        return {
            "assigned_shifts": result["assigned_shifts"],
            "unfilled_shifts": result["unfilled_shifts"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/schedule/csv")
async def schedule_csv(
    volunteers_file: UploadFile = File(...),
    shifts_file: UploadFile = File(...),
    strategy: str = Query(
        default="minimize_unfilled",
        description="Optimization strategy: minimize_unfilled, maximize_fairness, or minimize_overtime"
    )
):
    try:
        # Validate strategy
        valid_strategies = [s.value for s in OptimizationStrategy]
        if strategy not in valid_strategies:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid strategy '{strategy}'. Must be one of: {', '.join(valid_strategies)}"
            )
        # Read volunteers CSV
        v_text = (await volunteers_file.read()).decode()
        volunteers = {}
        for row in csv.DictReader(io.StringIO(v_text)):
            volunteers[row["id"]] = Volunteer(
                id=row["id"],
                name=row.get("name", row["id"]),
                group=row.get("group") or None,
                max_hours=float(row.get("max_hours", 0))
            )

        # Read shifts CSV
        s_text = (await shifts_file.read()).decode()
        shifts = {}
        for row in csv.DictReader(io.StringIO(s_text)):
            required_groups = {}
            req_str = row.get("required_groups", "")
            for gpart in req_str.split("|"):
                if ":" in gpart:
                    g, c = gpart.split(":")
                    required_groups[g.strip()] = int(c.strip())
            allowed_groups = set(row["allowed_groups"].split("|")) if row.get("allowed_groups") else None
            excluded_groups = set(row["excluded_groups"].split("|")) if row.get("excluded_groups") else None
            shifts[row["id"]] = Shift(
                id=row["id"],
                start=parse_iso(row["start"]),
                end=parse_iso(row["end"]),
                required_groups=required_groups,
                allowed_groups=allowed_groups,
                excluded_groups=excluded_groups
            )

        sched = Scheduler(volunteers, shifts)
        result = sched.assign(strategy=strategy)

        # If there are unfilled shifts, return error with partial schedule
        if result["unfilled_shifts"]:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "Unable to fill all shifts",
                    "unfilled_shifts": result["unfilled_shifts"],
                    "assigned_shifts": result["assigned_shifts"],
                    "volunteers": result["volunteers"]
                }
            )

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

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
