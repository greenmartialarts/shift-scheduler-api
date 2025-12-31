#!/usr/bin/env python3
# railway_setup.py
"""
Automated setup script for Railway deployment.
Creates admin account from environment variables.
"""
import os
from auth import create_master_user, init_database

def main():
    # Initialize database
    init_database()
    print("✓ Database initialized")
    
    # Get credentials from environment or use defaults
    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD", "admin123")
    
    # Create admin user (silently skips if already exists)
    if create_master_user(username, password):
        print(f"✓ Admin account created: {username}")
        if password == "admin123":
            print("⚠️  WARNING: Using default password! Set ADMIN_PASSWORD env var for security.")
    else:
        print(f"ℹ️  Admin account already exists: {username}")

if __name__ == "__main__":
    main()
