# auth.py
import sqlite3
import secrets
import bcrypt
import jwt
import os
from datetime import datetime, timedelta, date
from typing import Optional, Dict
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import contextmanager

# Configuration
# Use Railway volume if available, otherwise local path
DB_PATH = os.path.join(os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "."), "api_keys.db")
JWT_SECRET = secrets.token_urlsafe(32)  # Generate on startup
JWT_ALGORITHM = "HS256"
DEFAULT_RATE_LIMIT = 10000

security = HTTPBearer()

# Database connection context manager
@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# Initialize database schema
def init_database():
    """Create database tables if they don't exist."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # API Keys table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                rate_limit INTEGER DEFAULT 10000,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP
            )
        """)
        
        # API Usage tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                request_count INTEGER DEFAULT 0,
                FOREIGN KEY (key_id) REFERENCES api_keys(id),
                UNIQUE(key_id, date)
            )
        """)
        
        # Master users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS master_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

# API Key Management
def generate_api_key() -> str:
    """Generate a secure random API key."""
    return f"sk_{secrets.token_urlsafe(32)}"

def create_api_key(name: str, rate_limit: int = DEFAULT_RATE_LIMIT) -> Dict:
    """Create a new API key in the database."""
    key = generate_api_key()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO api_keys (key, name, rate_limit) VALUES (?, ?, ?)",
            (key, name, rate_limit)
        )
        key_id = cursor.lastrowid
        return {
            "id": key_id,
            "key": key,
            "name": name,
            "rate_limit": rate_limit,
            "created_at": datetime.now().isoformat()
        }

def get_all_api_keys() -> list:
    """Retrieve all API keys (without exposing full key)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, SUBSTR(key, 1, 10) || '...' as key_preview, name, 
                   rate_limit, created_at, last_used
            FROM api_keys
            ORDER BY created_at DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

def get_api_key_by_id(key_id: int) -> Optional[Dict]:
    """Get API key details by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM api_keys WHERE id = ?", (key_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def update_api_key_rate_limit(key_id: int, rate_limit: int) -> bool:
    """Update the rate limit for an API key."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE api_keys SET rate_limit = ? WHERE id = ?",
            (rate_limit, key_id)
        )
        return cursor.rowcount > 0

def delete_api_key(key_id: int) -> bool:
    """Delete/revoke an API key."""
    with get_db() as conn:
        cursor = conn.cursor()
        # Delete usage records first (foreign key constraint)
        cursor.execute("DELETE FROM api_usage WHERE key_id = ?", (key_id,))
        cursor.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
        return cursor.rowcount > 0

def get_api_key_usage(key_id: int, days: int = 30) -> list:
    """Get usage statistics for an API key over the last N days."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT date, request_count
            FROM api_usage
            WHERE key_id = ?
            ORDER BY date DESC
            LIMIT ?
        """, (key_id, days))
        return [dict(row) for row in cursor.fetchall()]

# Rate Limiting
def check_rate_limit(api_key: str) -> tuple[bool, int, int]:
    """
    Check if API key is within rate limit.
    Returns: (is_allowed, current_count, limit)
    """
    today = date.today().isoformat()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get key info
        cursor.execute("SELECT id, rate_limit FROM api_keys WHERE key = ?", (api_key,))
        key_row = cursor.fetchone()
        if not key_row:
            return False, 0, 0
        
        key_id, rate_limit = key_row["id"], key_row["rate_limit"]
        
        # Get or create today's usage record
        cursor.execute("""
            INSERT INTO api_usage (key_id, date, request_count)
            VALUES (?, ?, 0)
            ON CONFLICT(key_id, date) DO NOTHING
        """, (key_id, today))
        
        cursor.execute("""
            SELECT request_count FROM api_usage
            WHERE key_id = ? AND date = ?
        """, (key_id, today))
        
        count = cursor.fetchone()["request_count"]
        
        if count >= rate_limit:
            return False, count, rate_limit
        
        # Increment counter
        cursor.execute("""
            UPDATE api_usage
            SET request_count = request_count + 1
            WHERE key_id = ? AND date = ?
        """, (key_id, today))
        
        # Update last_used timestamp
        cursor.execute("""
            UPDATE api_keys
            SET last_used = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (key_id,))
        
        return True, count + 1, rate_limit

# Master User Management
def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_master_user(username: str, password: str) -> bool:
    """Create a master admin user."""
    password_hash = hash_password(password)
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO master_users (username, password_hash) VALUES (?, ?)",
                (username, password_hash)
            )
            return True
    except sqlite3.IntegrityError:
        return False  # Username already exists

def verify_master_user(username: str, password: str) -> bool:
    """Verify master user credentials."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT password_hash FROM master_users WHERE username = ?",
            (username,)
        )
        row = cursor.fetchone()
        if not row:
            return False
        return verify_password(password, row["password_hash"])

# JWT Token Management
def create_access_token(username: str, expires_delta: timedelta = timedelta(hours=24)) -> str:
    """Create a JWT access token for admin sessions."""
    expire = datetime.utcnow() + expires_delta
    to_encode = {"sub": username, "exp": expire}
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_access_token(token: str) -> Optional[str]:
    """Verify JWT token and return username if valid."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        return username
    except jwt.PyJWTError:
        return None

# FastAPI Dependencies
async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """FastAPI dependency to verify API key and enforce rate limits."""
    api_key = credentials.credentials
    
    # Validate key exists
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key FROM api_keys WHERE key = ?", (api_key,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=401,
                detail="Invalid API key"
            )
    
    # Check rate limit
    is_allowed, current_count, limit = check_rate_limit(api_key)
    if not is_allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Current: {current_count}/{limit} requests today."
        )
    
    return api_key

async def verify_admin_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """FastAPI dependency to verify admin JWT token."""
    token = credentials.credentials
    username = verify_access_token(token)
    if not username:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired admin token"
        )
    return username

# Initialize database on module import
init_database()
