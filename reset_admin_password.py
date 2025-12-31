#!/usr/bin/env python3
# reset_admin_password.py
"""
Quick script to reset admin password if you forgot it.
"""
from auth import hash_password, get_db

def reset_password():
    username = input("Enter admin username (default: admin): ").strip() or "admin"
    new_password = input("Enter new password: ").strip()
    
    if not new_password:
        print("Error: Password cannot be empty")
        return
    
    password_hash = hash_password(new_password)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE master_users SET password_hash = ? WHERE username = ?",
            (password_hash, username)
        )
        
        if cursor.rowcount > 0:
            print(f"✓ Password updated for user: {username}")
        else:
            print(f"✗ User not found: {username}")

if __name__ == "__main__":
    reset_password()
