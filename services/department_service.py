"""
Department Service Module
Encapsulates business logic and database queries for Departments.
"""
from db import get_db_cursor, DatabaseError


def get_all_departments():
    """
    Returns all departments with employee counts and basic metadata.
    """
    sql = """
        SELECT d.id, d.name, d.description, d.created_at,
               COUNT(e.id) AS employee_count
        FROM departments d
        LEFT JOIN employees e ON d.id = e.department_id
        GROUP BY d.id, d.name, d.description, d.created_at
        ORDER BY d.name ASC
    """
    with get_db_cursor() as cursor:
        cursor.execute(sql)
        return cursor.fetchall()


def get_department_by_id(dept_id):
    """Fetches a single department by ID."""
    sql = """
        SELECT d.id, d.name, d.description, d.created_at,
               COUNT(e.id) AS employee_count
        FROM departments d
        LEFT JOIN employees e ON d.id = e.department_id
        WHERE d.id = %s
        GROUP BY d.id, d.name, d.description, d.created_at
    """
    with get_db_cursor() as cursor:
        cursor.execute(sql, [dept_id])
        return cursor.fetchone()


def create_department(name, description=None):
    """
    Creates a new department.
    Validates non-empty name and uniqueness.
    Returns:
        tuple (bool success, int new_id_or_none, str error_message_or_none)
    """
    name = (name or '').strip()
    description = (description or '').strip() or None

    if not name:
        return False, None, "Department name is required."
    if len(name) > 100:
        return False, None, "Department name cannot exceed 100 characters."

    with get_db_cursor(commit=True) as cursor:
        cursor.execute("SELECT id FROM departments WHERE name = %s", [name])
        if cursor.fetchone():
            return False, None, f"A department named '{name}' already exists."

        cursor.execute(
            "INSERT INTO departments (name, description) VALUES (%s, %s)",
            [name, description]
        )
        new_id = cursor.lastrowid
        return True, new_id, None


def update_department(dept_id, name, description=None):
    """
    Updates an existing department's name and description.
    Returns:
        tuple (bool success, str error_message_or_none)
    """
    name = (name or '').strip()
    description = (description or '').strip() or None

    if not name:
        return False, "Department name is required."
    if len(name) > 100:
        return False, "Department name cannot exceed 100 characters."

    with get_db_cursor(commit=True) as cursor:
        # Check uniqueness against other departments
        cursor.execute("SELECT id FROM departments WHERE name = %s AND id != %s", [name, dept_id])
        if cursor.fetchone():
            return False, f"A department named '{name}' already exists."

        cursor.execute(
            "UPDATE departments SET name = %s, description = %s WHERE id = %s",
            [name, description, dept_id]
        )
        return True, None


def delete_department(dept_id):
    """
    Deletes a department only if there are no associated employees.
    Returns:
        tuple (bool success, str error_message_or_none)
    """
    with get_db_cursor(commit=True) as cursor:
        # Check if department exists
        cursor.execute("SELECT name FROM departments WHERE id = %s", [dept_id])
        dept = cursor.fetchone()
        if not dept:
            return False, "Department not found."

        # Check for associated employees
        cursor.execute("SELECT COUNT(*) AS emp_count FROM employees WHERE department_id = %s", [dept_id])
        res = cursor.fetchone()
        emp_count = res['emp_count'] if res else 0

        if emp_count > 0:
            return False, (
                f"Cannot delete department '{dept['name']}' because it has {emp_count} "
                f"associated employee(s). Please reassign or remove employees first."
            )

        cursor.execute("DELETE FROM departments WHERE id = %s", [dept_id])
        return True, None
