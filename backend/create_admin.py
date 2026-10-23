
import getpass

from psycopg.errors import UniqueViolation

from auth import hash_password
from database import create_admin


def main():
    print("\nCampusFlow Administrator Setup")
    print("-" * 35)

    name = input("Admin full name: ").strip()
    email = input("Admin email: ").strip().lower()

    if len(name) < 2 or "@" not in email:
        print("Invalid name or email.")
        return

    password = getpass.getpass(
        "Create admin password (12+ characters): "
    )

    confirm = getpass.getpass(
        "Confirm admin password: "
    )

    if len(password) < 12:
        print("Password must contain at least 12 characters.")
        return

    if password != confirm:
        print("Passwords do not match.")
        return

    try:
        user = create_admin(
            full_name=name,
            email=email,
            password_hash=hash_password(password),
        )

        print("\nAdministrator created successfully!")
        print("User ID:", user["id"])
        print("Email:", user["email"])
        print("Role:", user["role"])

    except UniqueViolation:
        print("An account with this email already exists.")


if __name__ == "__main__":
    main()
