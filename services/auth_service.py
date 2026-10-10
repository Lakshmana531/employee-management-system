"""
Authentication Service Module
Handles password hashing, credential verification, and administrator account management.
"""
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db_cursor, DatabaseError


def authenticate_admin(username_or_email, password):
    """
    Verifies administrator credentials against stored password hashes.
    Returns:
        dict: Admin record without password hash if authenticated, else None.
    """
    if not username_or_email or not password:
        return None

    identifier = username_or_email.strip().lower()
    sql = """
        SELECT id, username, email, password_hash, full_name
        FROM admins
        WHERE LOWER(username) = %s OR LOWER(email) = %s
    """
    with get_db_cursor() as cursor:
        cursor.execute(sql, [identifier, identifier])
        admin = cursor.fetchone()

    if admin and check_password_hash(admin['password_hash'], password):
        # Do not keep password hash in memory
        del admin['password_hash']
        return admin
    return None


def get_admin_by_id(admin_id):
    """Retrieves administrator details by ID for session hydration."""
    sql = "SELECT id, username, email, full_name, created_at FROM admins WHERE id = %s"
    with get_db_cursor() as cursor:
        cursor.execute(sql, [admin_id])
        return cursor.fetchone()


def create_admin(username, email, password, full_name):
    """
    Creates a new administrator account with secure password hashing.
    Returns:
        tuple (bool success, int new_id_or_none, str error_message_or_none)
    """
    username = (username or '').strip().lower()
    email = (email or '').strip().lower()
    full_name = (full_name or '').strip()

    if not username or len(username) < 3:
        return False, None, "Username must be at least 3 characters long."
    if not email or '@' not in email:
        return False, None, "Valid email address is required."
    if not password or len(password) < 6:
        return False, None, "Password must be at least 6 characters long."
    if not full_name:
        return False, None, "Full name is required."

    pw_hash = generate_password_hash(password, method='scrypt')

    with get_db_cursor(commit=True) as cursor:
        # Check uniqueness of username and email
        cursor.execute("SELECT id FROM admins WHERE LOWER(username) = %s OR LOWER(email) = %s", [username, email])
        if cursor.fetchone():
            return False, None, "An administrator with this username or email already exists."

        cursor.execute(
            "INSERT INTO admins (username, email, password_hash, full_name) VALUES (%s, %s, %s, %s)",
            [username, email, pw_hash, full_name]
        )
        return True, cursor.lastrowid, None
