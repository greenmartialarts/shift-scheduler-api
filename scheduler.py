# scheduler.py

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Set, Tuple
from enum import Enum
import csv
import json
import io

ISO_FMT = "%Y-%m-%dT%H:%M"

class OptimizationStrategy(str, Enum):
    """Optimization strategies for shift assignment"""
    MINIMIZE_UNFILLED = "minimize_unfilled"  # Default: Fill as many shifts as possible (current behavior)
    MAXIMIZE_FAIRNESS = "maximize_fairness"  # Distribute hours evenly across volunteers
    MINIMIZE_OVERTIME = "minimize_overtime"  # Prioritize volunteers with most available capacity

def parse_iso(s: str) -> datetime:
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

class Scheduler:
    def __init__(self, volunteers: Dict[str, Volunteer], shifts: Dict[str, Shift]):
        self.volunteers = volunteers
        self.shifts = shifts
        self._assign_map: Dict[str, List[Tuple[str, datetime, datetime]]] = {vid: [] for vid in volunteers}
        for s in self.shifts.values():
            setattr(s, "_scheduler_shift_times_for_volunteer", self._scheduler_shift_times_for_volunteer)

    def _scheduler_shift_times_for_volunteer(self, volunteer_id: str):
        return self._assign_map.get(volunteer_id, [])

    def _would_overlap(self, volunteer: Volunteer, shift: Shift) -> bool:
        for sid, s_start, s_end in self._assign_map.get(volunteer.id, []):
            if overlap(s_start, s_end, shift.start, shift.end):
                return True
        return False

    def assign(self, strategy: str = OptimizationStrategy.MINIMIZE_UNFILLED):
        """
        Assign volunteers to shifts using the specified optimization strategy.
        
        Args:
            strategy: Optimization strategy to use. Options:
                - "minimize_unfilled": Fill as many shifts as possible (default, current behavior)
                - "maximize_fairness": Distribute hours evenly across volunteers
                - "minimize_overtime": Prioritize volunteers with most available capacity
        
        Returns:
            Dictionary containing assigned_shifts, unfilled_shifts, and volunteer details
        """
        unfilled_shifts = []

        for shift in self.shifts.values():
            for group, count in shift.required_groups.items():
                # eligible volunteers of this group
                candidates = [v for v in self.volunteers.values()
                              if v.group == group and shift.allows(v) and not self._would_overlap(v, shift)
                              and v.assigned_hours + shift.duration_hours() <= v.max_hours + 1e-9]
                
                # Apply strategy-specific sorting
                if strategy == OptimizationStrategy.MINIMIZE_UNFILLED:
                    # Default: Prioritize volunteers with least hours (greedy approach)
                    candidates.sort(key=lambda x: (x.assigned_hours, len(x.assigned_shifts), -x.max_hours))
                
                elif strategy == OptimizationStrategy.MAXIMIZE_FAIRNESS:
                    # Fairness: Prioritize volunteers with least hours, then least shifts
                    # This naturally balances workload by always choosing least-loaded volunteers
                    candidates.sort(key=lambda x: (x.assigned_hours, len(x.assigned_shifts)))
                
                elif strategy == OptimizationStrategy.MINIMIZE_OVERTIME:
                    # Minimize overtime: Prioritize volunteers with most available capacity
                    # Helps prevent approaching max_hours limits
                    candidates.sort(key=lambda x: (
                        x.assigned_hours / x.max_hours if x.max_hours != float('inf') else 0,  # Percentage used
                        x.assigned_hours,  # Then by absolute hours
                        len(x.assigned_shifts)
                    ))
                
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
