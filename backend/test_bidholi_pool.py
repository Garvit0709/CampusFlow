
# CampusFlow Phase 9.9.2.5
# PostgreSQL Connection Pool Performance Test

import statistics
import time

from bidholi_db_pool import get_pool, close_pool

RUNS = 30


def main():
    print("\nCAMPUSFLOW POSTGRESQL POOL TEST")
    print("=" * 42)

    pool = get_pool()
    times = []

    try:
        for index in range(RUNS):
            start = time.perf_counter()

            with pool.connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()

                    if result is None or list(result.values())[0] != 1:
                        raise RuntimeError(
                            "Unexpected PostgreSQL result"
                        )

            elapsed = (
                time.perf_counter() - start
            ) * 1000

            times.append(elapsed)

        print("Requests:", len(times))
        print(
            "Average pooled query:",
            round(statistics.mean(times), 3),
            "ms"
        )
        print(
            "Minimum:",
            round(min(times), 3),
            "ms"
        )
        print(
            "Maximum:",
            round(max(times), 3),
            "ms"
        )
        print("\nAll pool queries passed.")

    finally:
        close_pool()


if __name__ == "__main__":
    main()
