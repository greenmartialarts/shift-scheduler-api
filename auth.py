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
import sys

# Configuration
# Support both manual DATABASE_URL and official Vercel/Supabase integration variables
# We prioritize NON_POOLING for stability if available
DATABASE_URL = os.getenv("POSTGRES_URL_NON_POOLING") or os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")

# Component variables from official integration
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = os.getenv("POSTGRES_PORT") or "5432"  # Default to direct port
DB_NAME = os.getenv("POSTGRES_DATABASE", "postgres")
ADMIN_MASTER_KEY = os.getenv("ADMIN_MASTER_KEY")

# Use DATA_PATH for SQLite persistence if available, otherwise local path
DB_PATH = os.path.join(os.getenv("DATA_PATH", "."), "api_keys.db")
JWT_SECRET = secrets.token_urlsafe(32)  # Generate on startup
JWT_ALGORITHM = "HS256"
DEFAULT_RATE_LIMIT = 10000

# Helper to extract project ID from various sources
def get_project_id():
    # Priority 1: From SUPABASE_URL (most reliable)
    s_url = os.getenv("SUPABASE_URL")
    if s_url:
        try:
            parsed = urlparse(s_url)
            if parsed.hostname:
                # xyz.supabase.co -> xyz
                pid = parsed.hostname.split('.')[0]
                if pid and pid != 'supabase':
                    return pid
        except: pass

    # Priority 2: From POSTGRES_URL (in the username part)
    p_url = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")
    if p_url:
        try:
            parsed = urlparse(p_url)
            if parsed.username and '.' in parsed.username:
                # postgres.xyz -> xyz
                pid = parsed.username.split('.')[-1]
                if pid: return pid
        except: pass
    
    return None

PROJECT_ID = get_project_id()

security = HTTPBearer()

# Use %s for PostgreSQL and ? for SQLite
def get_ph():
    has_postgres = DATABASE_URL or (DB_USER and DB_PASSWORD and DB_HOST)
    return "%s" if has_postgres else "?"

PH = get_ph()

# Database connection context manager
@contextmanager
def get_db():
    """Get database connection based on environment."""
    # Check if we have enough info for a Postgres connection
    has_postgres_info = DATABASE_URL or (DB_USER and DB_PASSWORD and DB_HOST)
    
    if has_postgres_info:
        # Sanitize input if using URL
        clean_url = DATABASE_URL.strip().replace('\r', '').replace('\n', '') if DATABASE_URL else None
        
        try:
            if clean_url:
                url = urlparse(clean_url)
                user = url.username
                password = url.password
                host = url.hostname
                port = url.port or 5432
                dbname = url.path[1:] if url.path else 'postgres'
            else:
                user = DB_USER
                password = DB_PASSWORD
                host = DB_HOST
                port = int(DB_PORT)
                dbname = DB_NAME

            # AUTO-CORRECT Supabase Pooler Username
            # If host is a pooler and user doesn't have a dot, we MUST add the project ID suffix
            is_pooler = host and ('pooler.supabase.com' in host or port == 6543)
            if is_pooler and user and '.' not in user and PROJECT_ID:
                user = f"{user}.{PROJECT_ID}"
            
            # Final sanity check: strip whitespace from every individual component
            user = user.strip() if user else user
            password = password.strip() if password else password
            host = host.strip() if host else host
            dbname = dbname.strip() if dbname else dbname
            
            conn = psycopg2.connect(
                dbname=dbname,
                user=user,
                password=password,
                host=host,
                port=port,
                sslmode='require',
                connect_timeout=15
            )
        except Exception as e:
            sys.stderr.write(f"DIAGNOSTIC_ERROR: Postgres connect failed for {user}@{host}: {str(e)}\n")
            # Try a direct connection with the URL string if it was provided
            if clean_url:
                try:
                    sys.stderr.write("DIAGNOSTIC: Final fallback to direct URI string attempt...\n")
                    conn = psycopg2.connect(clean_url)
                except Exception as e_direct:
                    sys.stderr.write(f"DIAGNOSTIC_ERROR: Direct URI also failed: {str(e_direct)}\n")
                    raise e
            else:
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
                    total_shifts INTEGER DEFAULT 0,
                    total_volunteers INTEGER DEFAULT 0,
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
                    total_shifts INTEGER DEFAULT 0,
                    total_volunteers INTEGER DEFAULT 0,
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
        
        # Migration: Add columns if they don't exist
        try:
            if DATABASE_URL:
                cursor.execute("ALTER TABLE api_usage ADD COLUMN IF NOT EXISTS total_shifts INTEGER DEFAULT 0")
                cursor.execute("ALTER TABLE api_usage ADD COLUMN IF NOT EXISTS total_volunteers INTEGER DEFAULT 0")
            else:
                # SQLite PRAGMA table_info returns (id, name, type, notnull, dflt_value, pk)
                cursor.execute("PRAGMA table_info(api_usage)")
                col_rows = cursor.fetchall()
                columns = []
                for row in col_rows:
                    if isinstance(row, dict):
                        columns.append(row['name'])
                    else:
                        columns.append(row[1])
                
                if 'total_shifts' not in columns:
                    cursor.execute("ALTER TABLE api_usage ADD COLUMN total_shifts INTEGER DEFAULT 0")
                if 'total_volunteers' not in columns:
                    cursor.execute("ALTER TABLE api_usage ADD COLUMN total_volunteers INTEGER DEFAULT 0")
        except Exception as e:
            print(f"Migration error: {e}")

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
            SELECT date, request_count, total_shifts, total_volunteers
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

def record_detailed_usage(api_key: str, shifts_count: int, volunteers_count: int):
    """ Record the number of shifts and volunteers scheduled for a request. """
    today = date.today().isoformat()
    with get_db() as conn:
        cursor = get_cursor(conn)
        cursor.execute(f"SELECT id FROM api_keys WHERE key = {PH}", (api_key,))
        row = cursor.fetchone()
        if not row:
            return
        
        key_id = row["id"]
        
        # We assume the row for today was already created by check_rate_limit
        cursor.execute(f"""
            UPDATE api_usage
            SET total_shifts = total_shifts + {PH},
                total_volunteers = total_volunteers + {PH}
            WHERE key_id = {PH} AND date = {PH}
        """, (shifts_count, volunteers_count, key_id, today))

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
    """FastAPI dependency to verify admin JWT token or Master Key."""
    token = credentials.credentials
    
    # 1. Check for Master Key first (Stateless)
    if ADMIN_MASTER_KEY and token == ADMIN_MASTER_KEY:
        return "admin_master_key"
    
    # 2. Fallback to JWT verification (Session-based)
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
