
"""
CampusFlow PostgreSQL connection pool.

Used by the Bidholi pedestrian routing system.
Does not modify existing database tables.
"""

import os
import threading
from pathlib import Path

from dotenv import load_dotenv
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

load_dotenv(Path(__file__).resolve().parent / ".env")

_pool = None
_pool_lock = threading.Lock()


def get_pool():
    global _pool

    with _pool_lock:
        if _pool is None:
            _pool = ConnectionPool(
                conninfo="",
                kwargs={
                    "host": os.getenv(
                        "DB_HOST", "127.0.0.1"
                    ),
                    "port": int(
                        os.getenv("DB_PORT", "5432")
                    ),
                    "dbname": os.getenv(
                        "DB_NAME", "campusflow_db"
                    ),
                    "user": os.getenv(
                        "DB_USER", "postgres"
                    ),
                    "password": os.getenv(
                        "DB_PASSWORD"
                    ),
                    "row_factory": dict_row,
                },
                min_size=1,
                max_size=5,
                timeout=10,
                open=False,
            )

            _pool.open()
            _pool.wait(timeout=10)

        return _pool


def close_pool():
    global _pool

    with _pool_lock:
        if _pool is not None:
            _pool.close()
            _pool = None
