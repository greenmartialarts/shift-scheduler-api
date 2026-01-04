import sqlite3
import psycopg2
from psycopg2 import extras
from psycopg2.extras import RealDictCursor
import secrets
import bcrypt
import jwt
import os
from datetime import datetime, timedelta, date
from typing import Optional, Dict, List, Tuple
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import contextmanager
from passlib.hash import pbkdf2_sha256
from urllib.parse import urlparse

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
# Use DATA_PATH for SQLite persistence if available, otherwise local path
DB_PATH = os.path.join(os.getenv("DATA_PATH", "."), "api_keys.db")
JWT_SECRET = secrets.token_urlsafe(32)  # Generate on startup
JWT_ALGORITHM = "HS256"
DEFAULT_RATE_LIMIT = 10000

security = HTTPBearer()

# Use %s for PostgreSQL and ? for SQLite
def get_ph():
    return "%s" if os.getenv("DATABASE_URL") else "?"

PH = get_ph()

# Database connection context manager
@contextmanager
def get_db():
    """Get database connection based on environment."""
    if DATABASE_URL:
        # Use urlparse for robust parsing of complex connection strings (e.g. Supabase)
        # This prevents issues with dots in usernames which psycopg2 might mis-parse in URI mode.
        try:
            url = urlparse(DATABASE_URL)
            user = url.username
            password = url.password
            host = url.hostname
            port = url.port or 5432
            dbname = url.path[1:] if url.path else 'postgres'
            
            # Diagnostic for debugging
            masked_password = password[:2] + "****" + password[-2:] if password and len(password) > 4 else "****"
            print(f"DEBUG: Connection string length: {len(DATABASE_URL)}")
            print(f"DEBUG: Parsed user: '{user}' (len={len(user) if user else 0})")
            print(f"DEBUG: Parsed host: '{host}' (len={len(host) if host else 0})")
            print(f"DEBUG: Parsed dbname: '{dbname}' (len={len(dbname) if dbname else 0})")
            print(f"DEBUG: Password length: {len(password) if password else 0}")
            
            conn = psycopg2.connect(
                dbname=dbname,
                user=user,
                password=password,
                host=host,
                port=port
            )
        except Exception as e:
            print(f"ERROR: Manual connection failed: {str(e)}")
            # Fallback to direct URI connection if parsing fails, but raise original error if it still fails
            try:
                print("DEBUG: Retrying with direct URI connection...")
                conn = psycopg2.connect(DATABASE_URL)
            except Exception as e_fallback:
                print(f"ERROR: URI connection failed: {str(e_fallback)}")
                raise e
    else:
        # SQLite (Local/Development)
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

def get_cursor(conn):
    if DATABASE_URL:
        return conn.cursor(cursor_factory=extras.RealDictCursor)
    else:
        return conn.cursor()

# Initialize database schema
def init_database():
    """Create database tables if they don't exist."""
    with get_db() as conn:
        cursor = get_cursor(conn)
        
        # Determine appropriate auto-increment and serial based on DB type
        id_type = "SERIAL" if DATABASE_URL else "INTEGER PRIMARY KEY AUTOINCREMENT"
        primary_key_sqlite = "" if DATABASE_URL else "" # Handled in id_type
        
        if DATABASE_URL:
            # PostgreSQL schema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id SERIAL PRIMARY KEY,
                    key TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    rate_limit INTEGER DEFAULT 10000,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_usage (
                    id SERIAL PRIMARY KEY,
                    key_id INTEGER NOT NULL REFERENCES api_keys(id),
                    date TEXT NOT NULL,
                    request_count INTEGER DEFAULT 0,
                    UNIQUE(key_id, date)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS master_users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        else:
            # SQLite schema
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
        cursor = get_cursor(conn)
        cursor.execute(
            f"INSERT INTO api_keys (key, name, rate_limit) VALUES ({PH}, {PH}, {PH})",
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
        cursor = get_cursor(conn)
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
        cursor = get_cursor(conn)
        cursor.execute(f"SELECT * FROM api_keys WHERE id = {PH}", (key_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def update_api_key_rate_limit(key_id: int, rate_limit: int) -> bool:
    """Update the rate limit for an API key."""
    with get_db() as conn:
        cursor = get_cursor(conn)
        cursor.execute(
            f"UPDATE api_keys SET rate_limit = {PH} WHERE id = {PH}",
            (rate_limit, key_id)
        )
        return cursor.rowcount > 0

def delete_api_key(key_id: int) -> bool:
    """Delete/revoke an API key."""
    with get_db() as conn:
        cursor = get_cursor(conn)
        # Delete usage records first (foreign key constraint)
        cursor.execute(f"DELETE FROM api_usage WHERE key_id = {PH}", (key_id,))
        cursor.execute(f"DELETE FROM api_keys WHERE id = {PH}", (key_id,))
        return cursor.rowcount > 0

def get_api_key_usage(key_id: int, days: int = 30) -> list:
    """Get usage statistics for an API key over the last N days."""
    with get_db() as conn:
        cursor = get_cursor(conn)
        cursor.execute(f"""
            SELECT date, request_count
            FROM api_usage
            WHERE key_id = {PH}
            ORDER BY date DESC
            LIMIT {PH}
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
        cursor = get_cursor(conn)
        
        # Get key info
        cursor.execute(f"SELECT id, rate_limit FROM api_keys WHERE key = {PH}", (api_key,))
        key_row = cursor.fetchone()
        if not key_row:
            return False, 0, 0
        
        key_id, rate_limit = key_row["id"], key_row["rate_limit"]
        
        # Get or create today's usage record
        cursor.execute(f"""
            INSERT INTO api_usage (key_id, date, request_count)
            VALUES ({PH}, {PH}, 0)
            ON CONFLICT(key_id, date) DO NOTHING
        """, (key_id, today))
        
        cursor.execute(f"""
            SELECT request_count FROM api_usage
            WHERE key_id = {PH} AND date = {PH}
        """, (key_id, today))
        
        count = cursor.fetchone()["request_count"]
        
        if count >= rate_limit:
            return False, count, rate_limit
        
        # Increment counter
        cursor.execute(f"""
            UPDATE api_usage
            SET request_count = request_count + 1
            WHERE key_id = {PH} AND date = {PH}
        """, (key_id, today))
        
        # Update last_used timestamp
        cursor.execute(f"""
            UPDATE api_keys
            SET last_used = CURRENT_TIMESTAMP
            WHERE id = {PH}
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
                f"INSERT INTO master_users (username, password_hash) VALUES ({PH}, {PH})",
                (username, password_hash)
            )
            return True
    except sqlite3.IntegrityError:
        return False  # Username already exists

def verify_master_user(username: str, password: str) -> bool:
    """Verify master user credentials."""
    with get_db() as conn:
        cursor = get_cursor(conn)
        cursor.execute(
            f"SELECT password_hash FROM master_users WHERE username = {PH}",
            (username,)
        )
        row = cursor.fetchone()
        if not row:
            return False
        return verify_password(password, row["password_hash"])

def ensure_admin_exists():
    """Check if any admin exists, if not create one from environment variables."""
    with get_db() as conn:
        cursor = get_cursor(conn)
        cursor.execute("SELECT COUNT(*) as count FROM master_users")
        row = cursor.fetchone()
        count = row["count"] if DATABASE_URL else row[0]
        
        if count == 0:
            username = os.getenv("ADMIN_USERNAME", "admin")
            password = os.getenv("ADMIN_PASSWORD", "admin123")
            print(f"No admin account found. Creating default admin: {username}")
            create_master_user(username, password)
            return True
    return False

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
        cursor.execute(f"SELECT key FROM api_keys WHERE key = {PH}", (api_key,))
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
try:
    init_database()
except Exception as e:
    print(f"Warning: Database initialization failed: {e}")
    # We don't raise here to allow the app to start and potentially 
    # show a better error message when an endpoint is actually called.
