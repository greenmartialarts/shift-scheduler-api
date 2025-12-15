# scheduler.py

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Set, Tuple
import csv
import io
import time

ISO_FMT = "%Y-%m-%dT%H:%M"

def parse_iso(s: str) -> datetime:
    """Parse ISO datetime in scheduler format."""
    return datetime.strptime(s, ISO_FMT)

def duration_hours(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / 3600.0

def overlap(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return not (a_end <= b_start or b_end <= a_start)

@dataclass
class Volunteer:
    id: str
    name: str
    group: Optional[str]
    max_hours: float = float('inf')
    assigned_hours: float = 0.0
    assigned_shifts: List[str] = field(default_factory=list)

@dataclass
class Shift:
    id: str
    start: datetime
    end: datetime
    required_groups: Dict[str, int]  # e.g., {"Delegates":2, "Adults":2}
    allowed_groups: Optional[Set[str]] = None
    excluded_groups: Optional[Set[str]] = None
    assigned: List[str] = field(default_factory=list)

    def duration_hours(self) -> float:
        return duration_hours(self.start, self.end)

    def allows(self, volunteer: Volunteer) -> bool:
        if self.allowed_groups and volunteer.group not in self.allowed_groups:
            return False
        if self.excluded_groups and volunteer.group in self.excluded_groups:
            return False
        return True

    def unfilled_count(self) -> int:
        """Total number of unfilled positions for this shift."""
        return sum(self.required_groups.values()) - len(self.assigned)

class Scheduler:
    def __init__(self, volunteers: Dict[str, Volunteer], shifts: Dict[str, Shift]):
        self.volunteers = volunteers
        self.shifts = shifts
        self._assign_map: Dict[str, List[Tuple[str, datetime, datetime]]] = {vid: [] for vid in volunteers}

        # Pre-index volunteers by group
        self.volunteers_by_group: Dict[Optional[str], List[Volunteer]] = {}
        for v in volunteers.values():
            self.volunteers_by_group.setdefault(v.group, []).append(v)

        for s in self.shifts.values():
            setattr(s, "_scheduler_shift_times_for_volunteer", self._scheduler_shift_times_for_volunteer)

    def _scheduler_shift_times_for_volunteer(self, volunteer_id: str):
        return self._assign_map.get(volunteer_id, [])

    def _would_overlap(self, volunteer: Volunteer, shift: Shift) -> bool:
        for sid, s_start, s_end in self._assign_map.get(volunteer.id, []):
            if overlap(s_start, s_end, shift.start, shift.end):
                return True
        return False

    # --------------------
    # Simple greedy assign (backward-compatible)
    # --------------------
    def assign(self):
        unfilled_shifts = []

        for shift in self.shifts.values():
            for group, count in shift.required_groups.items():
                # eligible volunteers of this group
                candidates = [v for v in self.volunteers.values()
                              if v.group == group and shift.allows(v) and not self._would_overlap(v, shift)
                              and v.assigned_hours + shift.duration_hours() <= v.max_hours + 1e-9]
                # sort by least hours assigned
                candidates.sort(key=lambda x: (x.assigned_hours, len(x.assigned_shifts), -x.max_hours))
                assigned_count = 0
                for v in candidates:
                    if assigned_count >= count:
                        break
                    # assign
                    v.assigned_hours += shift.duration_hours()
                    v.assigned_shifts.append(shift.id)
                    shift.assigned.append(v.id)
                    self._assign_map[v.id].append((shift.id, shift.start, shift.end))
                    assigned_count += 1
                if assigned_count < count:
                    unfilled_shifts.append((shift.id, group, count - assigned_count))
        return {
            "assigned_shifts": {sid: s.assigned for sid, s in self.shifts.items()},
            "unfilled_shifts": unfilled_shifts,
            "volunteers": {vid: {"assigned_hours": v.assigned_hours, "assigned_shifts": v.assigned_shifts} for vid, v in self.volunteers.items()},
        }

    # --------------------
    # Backtracking solver
    # --------------------
    def assign_optimal(self, timeout: float = 5.0):
        """Attempt to assign all shifts optimally with backtracking and scoring weights."""
        slots = []  # List of (shift_id, group)
        for shift in sorted(self.shifts.values(), key=lambda s: -sum(s.required_groups.values())):  # hardest first
            for group, count in shift.required_groups.items():
                for _ in range(count):
                    slots.append((shift.id, group))

        best_solution = {"score": -1, "assignments": {}}
        start_time = time.time()

        def score_solution():
            """Simple scoring: fewer unfilled shifts + balanced volunteer hours"""
            filled = sum(len(s.assigned) for s in self.shifts.values())
            total_hours = sum(v.assigned_hours for v in self.volunteers.values())
            return filled + 0.01 * total_hours  # slight weight for balanced hours

        def backtrack(i):
            if time.time() - start_time > timeout:
                return  # stop after timeout

            if i >= len(slots):
                s = score_solution()
                if s > best_solution["score"]:
                    best_solution["score"] = s
                    best_solution["assignments"] = {sid: list(s.assigned) for sid, s in self.shifts.items()}
                return

            shift_id, group = slots[i]
            shift = self.shifts[shift_id]
            candidates = [v for v in self.volunteers_by_group.get(group, [])
                          if shift.allows(v)
                          and not self._would_overlap(v, shift)
                          and shift.id not in v.assigned_shifts
                          and v.assigned_hours + shift.duration_hours() <= v.max_hours + 1e-9]

            # sort candidates by least hours, least shifts
            candidates.sort(key=lambda x: (x.assigned_hours, len(x.assigned_shifts), -x.max_hours))

            if not candidates:
                backtrack(i + 1)  # skip if no candidate
                return

            for v in candidates:
                # assign
                v.assigned_hours += shift.duration_hours()
                v.assigned_shifts.append(shift.id)
                shift.assigned.append(v.id)
                self._assign_map[v.id].append((shift.id, shift.start, shift.end))

                backtrack(i + 1)

                # undo
                v.assigned_hours -= shift.duration_hours()
                v.assigned_shifts.pop()
                shift.assigned.pop()
                self._assign_map[v.id].pop()

        backtrack(0)

        # Apply best found
        for sid, assigned in best_solution["assignments"].items():
            self.shifts[sid].assigned = assigned
        for v in self.volunteers.values():
            v.assigned_shifts = [s.id for s in self.shifts.values() if v.id in s.assigned]
            v.assigned_hours = sum(self.shifts[sid].duration_hours() for sid in v.assigned_shifts)

        unfilled = []
        for s in self.shifts.values():
            for g, c in s.required_groups.items():
                assigned_count = sum(1 for vid in s.assigned if self.volunteers[vid].group == g)
                if assigned_count < c:
                    unfilled.append((s.id, g, c - assigned_count))

        return {
            "assigned_shifts": {sid: s.assigned for sid, s in self.shifts.items()},
            "unfilled_shifts": unfilled,
            "volunteers": {vid: {"assigned_hours": v.assigned_hours, "assigned_shifts": v.assigned_shifts} for vid, v in self.volunteers.items()},
        }

    # --------------------
    # Reporting & CSV export
    # --------------------
    def report(self):
        group_totals: Dict[Optional[str], float] = {}
        for v in self.volunteers.values():
            group_totals.setdefault(v.group, 0.0)
            group_totals[v.group] += v.assigned_hours
        return {
            "group_totals": group_totals,
            "volunteer_details": {vid: {"name": v.name, "group": v.group, "assigned_hours": v.assigned_hours, "assigned_shifts": v.assigned_shifts} for vid, v in self.volunteers.items()}
        }

    def export_assignments_csv(self) -> str:
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["shift_id", "volunteer_id", "volunteer_name", "start", "end", "duration_hours"])
        for s in sorted(self.shifts.values(), key=lambda x: (x.start, x.id)):
            for vid in s.assigned:
                v = self.volunteers[vid]
                writer.writerow([s.id, v.id, v.name, s.start.strftime(ISO_FMT), s.end.strftime(ISO_FMT), f"{s.duration_hours():.2f}"])
        return out.getvalue()
