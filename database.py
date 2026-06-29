import psycopg2, mysql.connector
import os
from psycopg2.extras import RealDictCursor

def get_pg_conn():
    return psycopg2.connect(
        host=os.getenv("PG_HOST"), database="provedor_db",
        user=os.getenv("PG_USER"), password=os.getenv("PG_PASSWORD")
    )

def get_mysql_conn():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"), user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"), database=os.getenv("DB_NAME")
    )
