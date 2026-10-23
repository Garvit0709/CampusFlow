
from database import get_connection, get_locations, get_edges

try:
    with get_connection() as conn:
        print("PostgreSQL connected successfully!")

    locations = get_locations()
    edges = get_edges()

    print("Total locations:", len(locations))
    print("Total edges:", len(edges))

    print("\nCampus Locations:")
    for location in locations:
        print(location["name"])

except Exception as error:
    print("Database connection failed!")
    print(type(error).__name__, str(error))
