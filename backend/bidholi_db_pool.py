
"""
CampusFlow PostgreSQL connection pool.

Supports:
- Local PostgreSQL
- Neon PostgreSQL
- SSL connections
- Thread-safe pool initialization
- FastAPI startup and shutdown
"""

import os
import threading
from pathlib import Path

from dotenv import load_dotenv
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


# =====================================
# ENVIRONMENT CONFIGURATION
# =====================================

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

load_dotenv(
    BASE_DIR.parent / ".env.local",
    override=False,
)


# =====================================
# POOL CONFIGURATION
# =====================================

_pool = None
_pool_lock = threading.Lock()


# =====================================
# GET POSTGRESQL POOL
# =====================================

def get_pool():
    global _pool

    with _pool_lock:

        if _pool is None:

            database_url = (
                os.getenv("DATABASE_URL_UNPOOLED")
                or os.getenv("DATABASE_URL")
            )

            if database_url:

                # Neon PostgreSQL
                new_pool = ConnectionPool(
                    conninfo=database_url,
                    kwargs={
                        "row_factory": dict_row,
                        "connect_timeout": 10,
                        "sslmode": "require",
                        "channel_binding": "require",
                    },
                    min_size=0,
                    max_size=3,
                    timeout=15,
                    open=False,
                )

            else:

                # Local PostgreSQL
                new_pool = ConnectionPool(
                    conninfo="",
                    kwargs={
                        "host": os.getenv(
                            "DB_HOST",
                            "127.0.0.1"
                        ),
                        "port": int(
                            os.getenv(
                                "DB_PORT",
                                "5432"
                            )
                        ),
                        "dbname": os.getenv(
                            "DB_NAME",
                            "campusflow_db"
                        ),
                        "user": os.getenv(
                            "DB_USER",
                            "postgres"
                        ),
                        "password": os.getenv(
                            "DB_PASSWORD"
                        ),
                        "row_factory": dict_row,
                        "sslmode": os.getenv(
                            "DB_SSLMODE",
                            "prefer"
                        ),
                    },
                    min_size=1,
                    max_size=5,
                    timeout=10,
                    open=False,
                )

            try:
                new_pool.open()
                new_pool.wait(timeout=15)

            except Exception:
                new_pool.close()
                raise

            _pool = new_pool

        return _pool


# =====================================
# CLOSE POSTGRESQL POOL
# =====================================

def close_pool():
    global _pool

    with _pool_lock:

        if _pool is not None:
            _pool.close()
            _pool = None
