#!/usr/bin/env python3
# quick_setup.py
"""Quick setup script for creating admin account programmatically."""
from auth import create_master_user, init_database

# Initialize database
init_database()

# Create admin with default credentials
username = "admin"
password = "admin123"
success = create_master_user(username, password)

if success:
    print(f"✓ Admin account created: {username}")
    print(f"  Password: {password}")
    print("\n⚠️  Please change the password after first login!")
else:
    print("✗ Admin account already exists")
