
import os
import time
import statistics
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

RUNS = 30

connection_times = []
query_times = []

for i in range(RUNS):
    start = time.perf_counter()

    conn = psycopg.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "campusflow_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )

    connected = time.perf_counter()

    with conn.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()

    queried = time.perf_counter()
    conn.close()

    connection_times.append(
        (connected - start) * 1000
    )

    query_times.append(
        (queried - connected) * 1000
    )

print("\nCAMPUSFLOW POSTGRESQL BENCHMARK")
print("=" * 42)

print("Iterations:", RUNS)

print(
    "Average connection time:",
    round(statistics.mean(connection_times), 3),
    "ms"
)

print(
    "Average query time:",
    round(statistics.mean(query_times), 3),
    "ms"
)

print(
    "Maximum connection time:",
    round(max(connection_times), 3),
    "ms"
)

print(
    "Minimum connection time:",
    round(min(connection_times), 3),
    "ms"
)

print("\nDatabase records were not modified.")
