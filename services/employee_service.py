"""
Employee Service Module
Encapsulates business logic, data validation, and database operations for Employees.
"""
import math
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from db import get_db_cursor, DatabaseError

# Allowlisted columns for safe sorting
ALLOWED_SORT_COLUMNS = {
    'id': 'e.id',
    'full_name': 'e.full_name',
    'name': 'e.full_name',
    'email': 'e.email',
    'department_name': 'd.name',
    'job_title': 'e.job_title',
    'joining_date': 'e.joining_date',
    'salary': 'e.salary',
    'status': 'e.status'
}

ALLOWED_SORT_ORDERS = {'asc': 'ASC', 'desc': 'DESC'}

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
PHONE_REGEX = re.compile(r'^[0-9+\-() ]{7,20}$')


def validate_employee_data(data, employee_id=None, db_cursor=None):
    """
    Validates employee input fields on the server.
    Returns:
        tuple (bool is_valid, dict errors)
    """
    errors = {}
    
    # 1. Full Name
    full_name = (data.get('full_name') or '').strip()
    if not full_name:
        errors['full_name'] = 'Full name is required.'
    elif len(full_name) < 2 or len(full_name) > 100:
        errors['full_name'] = 'Full name must be between 2 and 100 characters.'

    # 2. Email Address
    email = (data.get('email') or '').strip().lower()
    if not email:
        errors['email'] = 'Email address is required.'
    elif not EMAIL_REGEX.match(email):
        errors['email'] = 'Please enter a valid email address (e.g., name@example.com).'
    elif len(email) > 150:
        errors['email'] = 'Email address cannot exceed 150 characters.'
    else:
        # Check duplicate email in database
        try:
            if db_cursor is not None:
                query = "SELECT id FROM employees WHERE email = %s"
                params = [email]
                if employee_id:
                    query += " AND id != %s"
                    params.append(employee_id)
                db_cursor.execute(query, params)
                if db_cursor.fetchone():
                    errors['email'] = 'This email address is already registered to another employee.'
            else:
                with get_db_cursor() as cursor:
                    query = "SELECT id FROM employees WHERE email = %s"
                    params = [email]
                    if employee_id:
                        query += " AND id != %s"
                        params.append(employee_id)
                    cursor.execute(query, params)
                    if cursor.fetchone():
                        errors['email'] = 'This email address is already registered to another employee.'
        except Exception:
            # If DB is mocked or connection fails in testing, catch cleanly
            pass

    # 3. Phone Number (optional, but validated if provided)
    phone = (data.get('phone') or '').strip()
    if phone and not PHONE_REGEX.match(phone):
        errors['phone'] = 'Please enter a valid phone number (7-20 digits, spaces, hyphens, or plus sign).'

    # 4. Job Title
    job_title = (data.get('job_title') or '').strip()
    if not job_title:
        errors['job_title'] = 'Job title is required.'
    elif len(job_title) > 100:
        errors['job_title'] = 'Job title cannot exceed 100 characters.'

    # 5. Joining Date
    joining_date = (data.get('joining_date') or '').strip()
    if not joining_date:
        errors['joining_date'] = 'Joining date is required.'
    else:
        try:
            parsed_date = datetime.strptime(joining_date, '%Y-%m-%d').date()
            if parsed_date.year < 1950 or parsed_date.year > 2100:
                errors['joining_date'] = 'Joining date year must be between 1950 and 2100.'
        except ValueError:
            errors['joining_date'] = 'Joining date must be in YYYY-MM-DD format.'

    # 6. Salary
    salary_raw = str(data.get('salary') or '').strip()
    if not salary_raw:
        errors['salary'] = 'Salary is required.'
    else:
        try:
            salary_val = Decimal(salary_raw)
            if salary_val < 0:
                errors['salary'] = 'Salary cannot be negative.'
            elif salary_val > Decimal('999999999.99'):
                errors['salary'] = 'Salary exceeds maximum allowable amount.'
        except (InvalidOperation, ValueError):
            errors['salary'] = 'Salary must be a valid numeric value.'

    # 7. Employment Status
    status = (data.get('status') or '').strip()
    if not status:
        errors['status'] = 'Employment status is required.'
    elif status not in ('Active', 'Inactive'):
        errors['status'] = 'Status must be either Active or Inactive.'

    # 8. Department ID (nullable/optional or valid integer)
    dept_id = data.get('department_id')
    if dept_id and str(dept_id).strip():
        try:
            int(dept_id)
        except (ValueError, TypeError):
            errors['department_id'] = 'Invalid department selection.'

    # 9. Address (optional, check length)
    address = (data.get('address') or '').strip()
    if address and len(address) > 500:
        errors['address'] = 'Address cannot exceed 500 characters.'

    return len(errors) == 0, errors


def get_employees(search=None, department_id=None, status=None,
                  start_date=None, end_date=None,
                  sort_by='id', sort_order='desc', page=1, per_page=10):
    """
    Retrieves a paginated list of employees matching search/filter criteria.
    Uses parameterized SQL and allowlist sorting to guarantee SQL injection safety.
    """
    page = max(1, int(page or 1))
    per_page = max(1, min(100, int(per_page or 10)))
    offset = (page - 1) * per_page

    col_order = ALLOWED_SORT_COLUMNS.get(sort_by, 'e.id')
    dir_order = ALLOWED_SORT_ORDERS.get((sort_order or '').lower(), 'DESC')

    where_clauses = []
    params = []

    # Text search across ID, Full Name, Email, Job Title
    if search:
        search_term = f"%{search.strip()}%"
        if search.strip().isdigit():
            where_clauses.append("(e.id = %s OR e.full_name LIKE %s OR e.email LIKE %s OR e.job_title LIKE %s)")
            params.extend([int(search.strip()), search_term, search_term, search_term])
        else:
            where_clauses.append("(e.full_name LIKE %s OR e.email LIKE %s OR e.job_title LIKE %s)")
            params.extend([search_term, search_term, search_term])

    # Department filter
    if department_id and str(department_id).isdigit():
        where_clauses.append("e.department_id = %s")
        params.append(int(department_id))

    # Status filter
    if status and status in ('Active', 'Inactive'):
        where_clauses.append("e.status = %s")
        params.append(status)

    # Date range filters
    if start_date:
        where_clauses.append("e.joining_date >= %s")
        params.append(start_date)

    if end_date:
        where_clauses.append("e.joining_date <= %s")
        params.append(end_date)

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    # Count total matching records
    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM employees e
        LEFT JOIN departments d ON e.department_id = d.id
        {where_sql}
    """

    # Fetch paginated rows
    data_sql = f"""
        SELECT e.id, e.full_name, e.email, e.phone, e.department_id,
               e.job_title, e.joining_date, e.salary, e.status, e.address,
               e.created_at, e.updated_at,
               COALESCE(d.name, 'Unassigned') AS department_name
        FROM employees e
        LEFT JOIN departments d ON e.department_id = d.id
        {where_sql}
        ORDER BY {col_order} {dir_order}
        LIMIT %s OFFSET %s
    """

    with get_db_cursor() as cursor:
        cursor.execute(count_sql, params)
        total_result = cursor.fetchone()
        total = total_result['total'] if total_result else 0

        data_params = list(params) + [per_page, offset]
        cursor.execute(data_sql, data_params)
        employees = cursor.fetchall()

    total_pages = math.ceil(total / per_page) if total > 0 else 1

    return {
        'employees': employees,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_num': page - 1 if page > 1 else None,
        'next_num': page + 1 if page < total_pages else None,
    }


def get_employee_by_id(employee_id):
    """Fetches a single employee record by ID with department details."""
    sql = """
        SELECT e.id, e.full_name, e.email, e.phone, e.department_id,
               e.job_title, e.joining_date, e.salary, e.status, e.address,
               e.created_at, e.updated_at,
               COALESCE(d.name, 'Unassigned') AS department_name,
               d.description AS department_description
        FROM employees e
        LEFT JOIN departments d ON e.department_id = d.id
        WHERE e.id = %s
    """
    with get_db_cursor() as cursor:
        cursor.execute(sql, [employee_id])
        return cursor.fetchone()


def create_employee(data):
    """
    Validates and creates a new employee.
    Returns:
        tuple (bool success, int new_id_or_none, dict errors_or_none)
    """
    try:
        with get_db_cursor(commit=True) as cursor:
            is_valid, errors = validate_employee_data(data, employee_id=None, db_cursor=cursor)
            if not is_valid:
                return False, None, errors

            dept_id = data.get('department_id')
            dept_id = int(dept_id) if dept_id and str(dept_id).strip() else None

            sql = """
                INSERT INTO employees (full_name, email, phone, department_id, job_title,
                                       joining_date, salary, status, address)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = [
                data['full_name'].strip(),
                data['email'].strip().lower(),
                (data.get('phone') or '').strip() or None,
                dept_id,
                data['job_title'].strip(),
                data['joining_date'].strip(),
                Decimal(str(data['salary']).strip()),
                data['status'].strip(),
                (data.get('address') or '').strip() or None
            ]
            cursor.execute(sql, params)
            new_id = cursor.lastrowid
            return True, new_id, None
    except DatabaseError as e:
        err_str = str(e).lower()
        if 'duplicate entry' in err_str and 'email' in err_str:
            return False, None, {'email': 'This email address is already registered to another employee.'}
        if 'foreign key constraint' in err_str or 'fk_employee_department' in err_str:
            return False, None, {'department_id': 'Selected department does not exist.'}
        return False, None, {'general': f'Database error: {e}'}


def update_employee(employee_id, data):
    """
    Validates and updates an existing employee record.
    Returns:
        tuple (bool success, dict errors_or_none)
    """
    try:
        with get_db_cursor(commit=True) as cursor:
            is_valid, errors = validate_employee_data(data, employee_id=employee_id, db_cursor=cursor)
            if not is_valid:
                return False, errors

            dept_id = data.get('department_id')
            dept_id = int(dept_id) if dept_id and str(dept_id).strip() else None

            sql = """
                UPDATE employees
                SET full_name = %s, email = %s, phone = %s, department_id = %s,
                    job_title = %s, joining_date = %s, salary = %s, status = %s, address = %s
                WHERE id = %s
            """
            params = [
                data['full_name'].strip(),
                data['email'].strip().lower(),
                (data.get('phone') or '').strip() or None,
                dept_id,
                data['job_title'].strip(),
                data['joining_date'].strip(),
                Decimal(str(data['salary']).strip()),
                data['status'].strip(),
                (data.get('address') or '').strip() or None,
                employee_id
            ]
            cursor.execute(sql, params)
            return True, None
    except DatabaseError as e:
        err_str = str(e).lower()
        if 'duplicate entry' in err_str and 'email' in err_str:
            return False, {'email': 'This email address is already registered to another employee.'}
        if 'foreign key constraint' in err_str or 'fk_employee_department' in err_str:
            return False, {'department_id': 'Selected department does not exist.'}
        return False, {'general': f'Database error: {e}'}


def delete_employee(employee_id):
    """Deletes an employee record by ID."""
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("DELETE FROM employees WHERE id = %s", [employee_id])
        return cursor.rowcount > 0


def get_recent_employees(limit=5):
    """Retrieves the most recently added employees for dashboard display."""
    sql = """
        SELECT e.id, e.full_name, e.email, e.job_title, e.joining_date,
               e.salary, e.status, COALESCE(d.name, 'Unassigned') AS department_name
        FROM employees e
        LEFT JOIN departments d ON e.department_id = d.id
        ORDER BY e.id DESC
        LIMIT %s
    """
    with get_db_cursor() as cursor:
        cursor.execute(sql, [limit])
        return cursor.fetchall()
