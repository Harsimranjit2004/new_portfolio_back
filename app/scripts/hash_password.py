"""Generate an ADMIN_PASSWORD_HASH value for .env.

Usage:
    python -m app.scripts.hash_password
Prompts for a password (input hidden) and prints the value to paste
into ADMIN_PASSWORD_HASH.
"""

import getpass

from app.services.auth_service import hash_password


def main() -> None:
    password = getpass.getpass("New admin password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        raise SystemExit("Passwords did not match.")
    if not password:
        raise SystemExit("Password cannot be empty.")
    print("\nADMIN_PASSWORD_HASH=" + hash_password(password))


if __name__ == "__main__":
    main()
