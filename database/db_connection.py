try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    print("Warning: psycopg2 not available, using yfinance only")

from contextlib import contextmanager
import os

DB_CONNECTION_STRING = "postgresql://neondb_owner:npg_WgVhOYtnP12l@ep-solitary-silence-a1yoj91r.ap-southeast-1.aws.neon.tech/MarketData?sslmode=require&channel_binding=require"

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    if not PSYCOPG2_AVAILABLE:
        raise Exception("psycopg2 not available")
    
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    try:
        yield conn
    finally:
        conn.close()

def execute_query(query, params=None, fetch_one=False):
    """Execute a query and return results"""
    if not PSYCOPG2_AVAILABLE:
        return None if fetch_one else []
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                if fetch_one:
                    return dict(cur.fetchone()) if cur.rowcount > 0 else None
                return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        print(f"Database query error: {e}")
        return None if fetch_one else []
