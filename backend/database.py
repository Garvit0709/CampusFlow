
import os
from pathlib import Path

import psycopg
from psycopg.errors import UniqueViolation
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")


def get_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "campusflow_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
        connect_timeout=5,
    )


# =====================================
# CAMPUS DATA
# =====================================

def get_locations():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, latitude, longitude
                FROM locations
                ORDER BY name
            """)
            rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "name": row[1],
            "position": [row[2], row[3]],
        }
        for row in rows
    ]


def get_edges():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT source_id, destination_id, distance
                FROM edges
                ORDER BY id
            """)
            rows = cur.fetchall()

    return [
        {
            "from": row[0],
            "to": row[1],
            "distance": row[2],
        }
        for row in rows
    ]


# =====================================
# CROWD REPORTING
# =====================================

def save_crowd_report(location_id, crowd_level):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO crowd_reports
                    (location_id, crowd_level)
                VALUES (%s, %s)
                RETURNING id, location_id,
                          crowd_level, reported_at
            """, (location_id, crowd_level))

            row = cur.fetchone()

    return {
        "id": row[0],
        "location_id": row[1],
        "crowd_level": row[2],
        "reported_at": row[3],
    }


def get_crowd_reports():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    cr.id,
                    cr.location_id,
                    l.name,
                    cr.crowd_level,
                    cr.reported_at
                FROM crowd_reports cr
                JOIN locations l
                    ON cr.location_id = l.id
                ORDER BY cr.reported_at DESC, cr.id DESC
                LIMIT 100
            """)
            rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "location_id": row[1],
            "location_name": row[2],
            "crowd_level": row[3],
            "reported_at": row[4],
        }
        for row in rows
    ]


def get_current_crowd_levels():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT ON (location_id)
                    location_id, crowd_level
                FROM crowd_reports
                WHERE reported_at >=
                    CURRENT_TIMESTAMP - INTERVAL '60 minutes'
                ORDER BY location_id,
                         reported_at DESC, id DESC
            """)
            rows = cur.fetchall()

    return {
        row[0]: row[1]
        for row in rows
    }


# =====================================
# ADMIN ANALYTICS
# =====================================

def get_analytics_summary():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    (SELECT COUNT(*) FROM locations),
                    (SELECT COUNT(*) FROM edges),
                    (SELECT COUNT(*) FROM crowd_reports),
                    (SELECT COUNT(*)
                     FROM crowd_reports
                     WHERE crowd_level = 'high')
            """)
            row = cur.fetchone()

    return {
        "total_locations": row[0],
        "total_edges": row[1],
        "total_reports": row[2],
        "high_crowd_reports": row[3],
    }


def get_crowd_distribution():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT crowd_level, COUNT(*)
                FROM crowd_reports
                GROUP BY crowd_level
            """)
            rows = cur.fetchall()

    counts = {
        "low": 0,
        "medium": 0,
        "high": 0,
    }

    for level, count in rows:
        counts[level] = count

    return [
        {"level": level, "count": count}
        for level, count in counts.items()
    ]


def get_analytics_hotspots():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    l.id,
                    l.name,
                    COUNT(cr.id),
                    COUNT(cr.id) FILTER (
                        WHERE cr.crowd_level = 'high'
                    )
                FROM locations l
                LEFT JOIN crowd_reports cr
                    ON l.id = cr.location_id
                GROUP BY l.id, l.name
                ORDER BY 4 DESC, 3 DESC, l.name
            """)
            rows = cur.fetchall()

    return [
        {
            "location_id": row[0],
            "location_name": row[1],
            "total_reports": row[2],
            "high_reports": row[3],
        }
        for row in rows
    ]


def get_hourly_crowd_analytics():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    EXTRACT(HOUR FROM
                        reported_at AT TIME ZONE 'Asia/Kolkata'
                    )::INTEGER AS hour,
                    crowd_level,
                    COUNT(*)
                FROM crowd_reports
                GROUP BY hour, crowd_level
                ORDER BY hour
            """)
            rows = cur.fetchall()

    hourly = {
        hour: {
            "hour": hour,
            "low": 0,
            "medium": 0,
            "high": 0,
        }
        for hour in range(24)
    }

    for hour, level, count in rows:
        hourly[hour][level] = count

    return list(hourly.values())


# =====================================
# USER ACCOUNT FUNCTIONS
# =====================================

USER_COLUMNS = """
    id, full_name, email,
    password_hash, role, is_active, created_at
"""


def user_from_row(row):
    if row is None:
        return None

    return {
        "id": row[0],
        "full_name": row[1],
        "email": row[2],
        "password_hash": row[3],
        "role": row[4],
        "is_active": row[5],
        "created_at": row[6],
    }


def get_user_by_email(email):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT {USER_COLUMNS}
                FROM users
                WHERE email = %s
                """,
                (email.strip().lower(),),
            )

            row = cur.fetchone()

    return user_from_row(row)


def get_user_by_id(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT {USER_COLUMNS}
                FROM users
                WHERE id = %s
                """,
                (user_id,),
            )

            row = cur.fetchone()

    return user_from_row(row)


def create_student(full_name, email, password_hash):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users
                    (full_name, email, password_hash, role)
                VALUES (%s, %s, %s, 'student')
                RETURNING id
            """, (
                full_name.strip(),
                email.strip().lower(),
                password_hash,
            ))

            user_id = cur.fetchone()[0]

    return get_user_by_id(user_id)


def create_admin(full_name, email, password_hash):
    """
    Used only by the local administrator
    setup script, not by public registration.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users
                    (full_name, email, password_hash, role)
                VALUES (%s, %s, %s, 'admin')
                RETURNING id
            """, (
                full_name.strip(),
                email.strip().lower(),
                password_hash,
            ))

            user_id = cur.fetchone()[0]

    return get_user_by_id(user_id)
