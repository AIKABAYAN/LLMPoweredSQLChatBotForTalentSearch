import psycopg2
from psycopg2.extras import RealDictCursor
from src.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS

# =============================================
# Database helpers
# =============================================

def get_conn():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
    )