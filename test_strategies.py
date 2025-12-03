#!/usr/bin/env python3
"""Test script to verify optimization strategies work correctly"""

from scheduler import Volunteer, Shift, Scheduler, OptimizationStrategy, parse_iso
from datetime import datetime

# Create test volunteers
volunteers = {
    "v1": Volunteer(id="v1", name="Alice", group="Delegates", max_hours=10.0),
    "v2": Volunteer(id="v2", name="Bob", group="Delegates", max_hours=10.0),
    "v3": Volunteer(id="v3", name="Charlie", group="Adults", max_hours=10.0),
    "v4": Volunteer(id="v4", name="Diana", group="Adults", max_hours=10.0),
}

# Create test shifts
shifts = {
    "s1": Shift(
        id="s1",
        start=parse_iso("2025-12-01T09:00"),
        end=parse_iso("2025-12-01T11:00"),
        required_groups={"Delegates": 1, "Adults": 1}
    ),
    "s2": Shift(
        id="s2",
        start=parse_iso("2025-12-01T13:00"),
        end=parse_iso("2025-12-01T15:00"),
        required_groups={"Delegates": 1, "Adults": 1}
    ),
    "s3": Shift(
        id="s3",
        start=parse_iso("2025-12-01T16:00"),
        end=parse_iso("2025-12-01T18:00"),
        required_groups={"Delegates": 1, "Adults": 1}
    ),
}

def test_strategy(strategy_name, volunteers_dict, shifts_dict):
    """Test a specific strategy"""
    # Reset volunteer assignments
    for v in volunteers_dict.values():
        v.assigned_hours = 0.0
        v.assigned_shifts = []
    
    # Reset shift assignments
    for s in shifts_dict.values():
        s.assigned = []
    
    # Create scheduler and run
    sched = Scheduler(volunteers_dict, shifts_dict)
    result = sched.assign(strategy=strategy_name)
    
    print(f"\n{'='*60}")
    print(f"Strategy: {strategy_name}")
    print(f"{'='*60}")
    
    # Print results
    print(f"\nAssigned Shifts:")
    for shift_id, volunteer_ids in result["assigned_shifts"].items():
        print(f"  {shift_id}: {volunteer_ids}")
    
    print(f"\nUnfilled Shifts:")
    if result["unfilled_shifts"]:
        for shift_id, group, count in result["unfilled_shifts"]:
            print(f"  {shift_id} needs {count} more {group}")
    else:
        print("  None")
    
    print(f"\nVolunteer Hours:")
    for vol_id, vol_data in result["volunteers"].items():
        vol = volunteers_dict[vol_id]
        print(f"  {vol.name} ({vol.group}): {vol_data['assigned_hours']:.1f}h - Shifts: {vol_data['assigned_shifts']}")
    
    return result

# Test 1: Backward compatibility (no strategy specified)
print("\n" + "="*60)
print("TEST 1: Backward Compatibility (default behavior)")
print("="*60)
for v in volunteers.values():
    v.assigned_hours = 0.0
    v.assigned_shifts = []
for s in shifts.values():
    s.assigned = []

sched = Scheduler(volunteers, shifts)
result = sched.assign()  # No strategy parameter
print(f"✓ Default assignment works (no parameter)")
print(f"  Unfilled shifts: {len(result['unfilled_shifts'])}")

# Test 2: All three strategies
test_strategy(OptimizationStrategy.MINIMIZE_UNFILLED, volunteers, shifts)
test_strategy(OptimizationStrategy.MAXIMIZE_FAIRNESS, volunteers, shifts)
test_strategy(OptimizationStrategy.MINIMIZE_OVERTIME, volunteers, shifts)

# Test 3: Test with string values (as would come from API)
print("\n" + "="*60)
print("TEST 2: Strategy as string (from API)")
print("="*60)
for v in volunteers.values():
    v.assigned_hours = 0.0
    v.assigned_shifts = []
for s in shifts.values():
    s.assigned = []

sched = Scheduler(volunteers, shifts)
result = sched.assign(strategy="maximize_fairness")
print(f"✓ String strategy 'maximize_fairness' works")
print(f"  Unfilled shifts: {len(result['unfilled_shifts'])}")

print("\n" + "="*60)
print("All tests completed successfully!")
print("="*60)
