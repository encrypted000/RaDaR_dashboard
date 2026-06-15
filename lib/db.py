import os
import pandas as pd
import psycopg2
import streamlit as st
from sshtunnel import SSHTunnelForwarder

SSH_HOST = os.environ.get("SSH_HOST", "db.radar.nhs.uk")
SSH_PORT = int(os.environ.get("SSH_PORT", "22"))
SSH_USER = os.environ.get("SSH_USER", "bidhanp")
SSH_KEY  = os.environ.get("SSH_KEY_PATH", r"c:\Users\bidhan.pant\.ssh\id_rsa")

DB_USER = "radar_ro"
DB_NAME = "radar"
DB_HOST_LOCAL = "127.0.0.1"
DB_PORT_REMOTE = 5432
LOCAL_PORT = 5433


def read_sql_df(conn, sql: str) -> pd.DataFrame:
    return pd.read_sql(sql, conn)


def read_sql_params(conn, sql: str, params: dict) -> pd.DataFrame:
    """Execute a parameterised query (%(name)s placeholders) and return a DataFrame."""
    cur = conn.cursor()
    cur.execute(sql, params)
    cols = [d[0] for d in cur.description]
    df = pd.DataFrame(cur.fetchall(), columns=cols)
    cur.close()
    return df


def read_scalar(conn, sql: str) -> int:
    cur = conn.cursor()
    cur.execute(sql)
    row = cur.fetchone()
    cur.close()
    return int(row[0] or 0) if row is not None else 0


@st.cache_resource
def _shared_conn():
    """One SSH tunnel + one DB connection shared across the entire app."""
    return get_connection()


def get_live_conn():
    """Return a healthy (conn, tunnel). Reconnects automatically if connection dropped."""
    conn, tunnel = _shared_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
    except Exception:
        _shared_conn.clear()
        conn, tunnel = _shared_conn()
    return conn, tunnel


def get_connection():
    db_pass = os.environ.get("RADAR_DB_PASS")

    if not db_pass:
        raise RuntimeError("Set RADAR_DB_PASS environment variable first.")

    tunnel = SSHTunnelForwarder(
        (SSH_HOST, SSH_PORT),
        ssh_username=SSH_USER,
        ssh_pkey=SSH_KEY,
        remote_bind_address=("127.0.0.1", DB_PORT_REMOTE),
        local_bind_address=(DB_HOST_LOCAL, LOCAL_PORT),
        set_keepalive=30,          # SSH-level keepalive every 30 s
    )

    tunnel.start()

    try:
        conn = psycopg2.connect(
            host=DB_HOST_LOCAL,
            port=tunnel.local_bind_port,
            dbname=DB_NAME,
            user=DB_USER,
            password=db_pass,
            keepalives=1,              # TCP keepalive on
            keepalives_idle=30,        # start probing after 30 s idle
            keepalives_interval=10,    # probe every 10 s
            keepalives_count=5,        # drop after 5 missed probes
        )
    except Exception:
        tunnel.stop()
        raise

    return conn, tunnel