#!/usr/bin/env python3
# setup_admin.py
"""
Setup script to create the first master admin account.
Run this once before starting the API server.
"""
import getpass
from auth import create_master_user, init_database

def main():
    print("=" * 50)
    print("Scheduler API - Master Admin Setup")
    print("=" * 50)
    print()
    
    # Initialize database
    print("Initializing database...")
    init_database()
    print("✓ Database initialized")
    print()
    
    # Get admin credentials
    print("Create your master admin account:")
    username = input("Username: ").strip()
    
    if not username:
        print("Error: Username cannot be empty")
        return
    
    while True:
        password = getpass.getpass("Password: ")
        password_confirm = getpass.getpass("Confirm password: ")
        
        if password != password_confirm:
            print("Passwords do not match. Please try again.")
            continue
        
        if len(password) < 8:
            print("Password must be at least 8 characters. Please try again.")
            continue
        
        break
    
    # Create user
    success = create_master_user(username, password)
    
    if success:
        print()
        print("✓ Master admin account created successfully!")
        print()
        print("You can now:")
        print("  1. Start the API server: uvicorn api_scheduler:app --reload")
        print("  2. Access the admin panel at: http://localhost:8000/admin")
        print(f"  3. Login with username: {username}")
    else:
        print()
        print("✗ Error: Username already exists")
        print("Please try again with a different username")

if __name__ == "__main__":
    main()
