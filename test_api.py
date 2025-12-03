#!/usr/bin/env python3
"""Test API with optimization strategies"""

import sys
import json

# Add current directory to path
sys.path.insert(0, '/Users/arnavshah/Documents/scheduler_api')

from api_scheduler import app, ScheduleInput
from fastapi.testclient import TestClient

client = TestClient(app)

print("\n" + "="*60)
print("API ENDPOINT TESTS")
print("="*60)

# Test 1: Backward compatibility - no strategy parameter
print("\n[TEST 1] Backward compatibility (no strategy parameter)")
payload_no_strategy = {
    "volunteers": [
        {"id": "v1", "name": "Alice", "group": "Delegates", "max_hours": 8.0},
        {"id": "v2", "name": "Bob", "group": "Adults", "max_hours": 8.0}
    ],
    "shifts": [
        {
            "id": "s1",
            "start": "2025-12-01T09:00",
            "end": "2025-12-01T11:00",
            "required_groups": {"Delegates": 1, "Adults": 1}
        }
    ]
}

response = client.post("/schedule/json", json=payload_no_strategy)
print(f"Status Code: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")
assert response.status_code == 200, "Should succeed with default strategy"
print("✓ PASS")

# Test 2: With minimize_unfilled strategy
print("\n[TEST 2] With 'minimize_unfilled' strategy")
payload_minimize = {**payload_no_strategy, "strategy": "minimize_unfilled"}
response = client.post("/schedule/json", json=payload_minimize)
print(f"Status Code: {response.status_code}")
assert response.status_code == 200, "Should succeed"
print("✓ PASS")

# Test 3: With maximize_fairness strategy
print("\n[TEST 3] With 'maximize_fairness' strategy")
payload_fairness = {**payload_no_strategy, "strategy": "maximize_fairness"}
response = client.post("/schedule/json", json=payload_fairness)
print(f"Status Code: {response.status_code}")
assert response.status_code == 200, "Should succeed"
print("✓ PASS")

# Test 4: With minimize_overtime strategy
print("\n[TEST 4] With 'minimize_overtime' strategy")
payload_overtime = {**payload_no_strategy, "strategy": "minimize_overtime"}
response = client.post("/schedule/json", json=payload_overtime)
print(f"Status Code: {response.status_code}")
assert response.status_code == 200, "Should succeed"
print("✓ PASS")

# Test 5: Invalid strategy
print("\n[TEST 5] Invalid strategy (should fail)")
payload_invalid = {**payload_no_strategy, "strategy": "invalid_strategy"}
response = client.post("/schedule/json", json=payload_invalid)
print(f"Status Code: {response.status_code}")
print(f"Error: {response.json()['detail']}")
assert response.status_code == 400, "Should return 400 for invalid strategy"
print("✓ PASS")

print("\n" + "="*60)
print("ALL API TESTS PASSED!")
print("="*60)
