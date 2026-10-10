"""
Service Layer Business Logic Tests
Tests department deletion protection, allowlist sorting safety, and dashboard statistics.
"""
from unittest.mock import MagicMock, patch
from decimal import Decimal
import services.department_service as dept_service
import services.employee_service as emp_service
import services.report_service as report_service
from db import _clean_sql_statements


def test_clean_sql_statements_parses_tables_with_comments():
    """Verify that comments preceding statements do not cause table creation statements to be skipped."""
    sample_sql = """
    -- Comment 1
    CREATE DATABASE IF NOT EXISTS employee_db;

    -- 1. Departments Table
    CREATE TABLE IF NOT EXISTS departments (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL
    );

    -- 2. Employees Table
    CREATE TABLE IF NOT EXISTS employees (
        id INT AUTO_INCREMENT PRIMARY KEY,
        full_name VARCHAR(100) NOT NULL
    );
    """
    stmts = _clean_sql_statements(sample_sql)
    assert len(stmts) == 3
    assert "CREATE DATABASE" in stmts[0]
    assert "CREATE TABLE IF NOT EXISTS departments" in stmts[1]
    assert "CREATE TABLE IF NOT EXISTS employees" in stmts[2]


def test_department_deletion_blocked_when_employees_assigned():
    """Verify that deleting a department with active employees is blocked."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.side_effect = [
        {'name': 'Engineering'},
        {'emp_count': 3}
    ]

    with patch('services.department_service.get_db_cursor') as mock_db:
        mock_db.return_value.__enter__.return_value = mock_cursor
        success, message = dept_service.delete_department(1)

        assert success is False
        assert "Cannot delete department 'Engineering'" in message
        assert "3 associated employee(s)" in message


def test_department_deletion_allowed_when_empty():
    """Verify that deleting a department with 0 employees succeeds."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.side_effect = [
        {'name': 'Research'},
        {'emp_count': 0}
    ]

    with patch('services.department_service.get_db_cursor') as mock_db:
        mock_db.return_value.__enter__.return_value = mock_cursor
        success, message = dept_service.delete_department(2)

        assert success is True
        assert message is None
        assert any("DELETE FROM departments" in str(call) for call in mock_cursor.execute.call_args_list)


def test_department_creation_duplicate_name_blocked():
    """Verify duplicate department names are rejected."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {'id': 1}

    with patch('services.department_service.get_db_cursor') as mock_db:
        mock_db.return_value.__enter__.return_value = mock_cursor
        success, new_id, err = dept_service.create_department('Engineering')

        assert success is False
        assert new_id is None
        assert "already exists" in err


def test_sorting_allowlist_guards_against_injection():
    """Verify that only allowlisted column names and sort orders are permitted."""
    assert 'id' in emp_service.ALLOWED_SORT_COLUMNS
    assert 'salary' in emp_service.ALLOWED_SORT_COLUMNS
    assert 'joining_date' in emp_service.ALLOWED_SORT_COLUMNS
    assert emp_service.ALLOWED_SORT_COLUMNS.get('name') == 'e.full_name'
    assert emp_service.ALLOWED_SORT_COLUMNS.get('full_name') == 'e.full_name'
    
    # An unrecognized sort_by defaults to 'e.id'
    assert emp_service.ALLOWED_SORT_COLUMNS.get('unknown_col; DROP TABLE employees;', 'e.id') == 'e.id'
    assert emp_service.ALLOWED_SORT_ORDERS.get('desc', 'DESC') == 'DESC'
    assert emp_service.ALLOWED_SORT_ORDERS.get('invalid_dir', 'DESC') == 'DESC'


def test_employee_date_range_filtering():
    """Verify that start_date and end_date are incorporated into WHERE clauses."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {'total': 5}
    mock_cursor.fetchall.return_value = []

    with patch('services.employee_service.get_db_cursor') as mock_db:
        mock_db.return_value.__enter__.return_value = mock_cursor
        result = emp_service.get_employees(start_date='2024-01-01', end_date='2024-12-31')

        # Check execute call arguments
        calls = mock_cursor.execute.call_args_list
        assert len(calls) >= 2
        count_sql, count_params = calls[0][0]
        assert "e.joining_date >= %s" in count_sql
        assert "e.joining_date <= %s" in count_sql
        assert '2024-01-01' in count_params
        assert '2024-12-31' in count_params


def test_dashboard_stats_empty_database_handling():
    """Verify that an empty database returns zeroed metrics without crashing."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.side_effect = [
        {'total_employees': 0, 'active_employees': 0, 'inactive_employees': 0, 'avg_salary': 0},
        {'total_departments': 0}
    ]
    mock_cursor.fetchall.side_effect = [
        [],  # Dept distribution
        []   # Trends
    ]

    with patch('services.report_service.get_db_cursor') as mock_db:
        mock_db.return_value.__enter__.return_value = mock_cursor
        stats = report_service.get_dashboard_stats()

        assert stats['total_employees'] == 0
        assert stats['active_employees'] == 0
        assert stats['total_departments'] == 0
        assert stats['average_salary'] == Decimal('0.00')
        assert stats['dept_distribution'] == []
        assert stats['joining_trends'] == []


def test_create_employee_service_success():
    """Verify create_employee successfully inserts a new employee."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None  # No duplicate email
    mock_cursor.lastrowid = 101

    payload = {
        'full_name': 'Test New Employee',
        'email': 'testnew@example.com',
        'phone': '555-123-4567',
        'department_id': '1',
        'job_title': 'QA Tester',
        'joining_date': '2024-05-01',
        'salary': '75000.00',
        'status': 'Active',
        'address': 'Test City'
    }

    with patch('services.employee_service.get_db_cursor') as mock_db:
        mock_db.return_value.__enter__.return_value = mock_cursor
        success, new_id, errors = emp_service.create_employee(payload)

        assert success is True
        assert new_id == 101
        assert errors is None
        assert any("INSERT INTO employees" in str(call) for call in mock_cursor.execute.call_args_list)


def test_create_employee_service_db_duplicate_email():
    """Verify create_employee handles DatabaseError duplicate email gracefully."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None  # Pre-validation passes
    mock_cursor.execute.side_effect = [
        None,  # Validation query
        emp_service.DatabaseError("Duplicate entry 'test@example.com' for key 'email'")
    ]

    payload = {
        'full_name': 'Test Duplicate',
        'email': 'test@example.com',
        'job_title': 'Tester',
        'joining_date': '2024-05-01',
        'salary': '70000.00',
        'status': 'Active'
    }

    with patch('services.employee_service.get_db_cursor') as mock_db:
        mock_db.return_value.__enter__.return_value = mock_cursor
        success, new_id, errors = emp_service.create_employee(payload)

        assert success is False
        assert new_id is None
        assert 'email' in errors
        assert 'already registered' in errors['email'].lower()


def test_update_employee_service_success():
    """Verify update_employee successfully updates an employee record."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None  # No duplicate email

    payload = {
        'full_name': 'Updated Name',
        'email': 'updated@example.com',
        'phone': '555-987-6543',
        'department_id': '2',
        'job_title': 'Lead QA',
        'joining_date': '2023-01-10',
        'salary': '85000.00',
        'status': 'Inactive',
        'address': 'New Street'
    }

    with patch('services.employee_service.get_db_cursor') as mock_db:
        mock_db.return_value.__enter__.return_value = mock_cursor
        success, errors = emp_service.update_employee(10, payload)

        assert success is True
        assert errors is None
        assert any("UPDATE employees" in str(call) for call in mock_cursor.execute.call_args_list)


def test_update_employee_service_preserves_own_email():
    """Verify an employee can keep their own email when updating other fields."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None  # Excluded own ID, so no match found

    payload = {
        'full_name': 'Same Person',
        'email': 'own.email@example.com',
        'job_title': 'Staff Engineer',
        'joining_date': '2022-03-01',
        'salary': '90000.00',
        'status': 'Active'
    }

    with patch('services.employee_service.get_db_cursor') as mock_db:
        mock_db.return_value.__enter__.return_value = mock_cursor
        success, errors = emp_service.update_employee(5, payload)

        assert success is True
        assert errors is None
        # Check validation query excluded own ID
        calls = [c for c in mock_cursor.execute.call_args_list if "SELECT id FROM employees WHERE email = %s AND id != %s" in str(c)]
        assert len(calls) > 0


def test_update_employee_service_rejects_duplicate_email():
    """Verify updating an employee with another existing employee's email is rejected."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {'id': 99}  # Found conflict with employee 99

    payload = {
        'full_name': 'Colliding Person',
        'email': 'other.user@example.com',
        'job_title': 'Specialist',
        'joining_date': '2023-01-01',
        'salary': '60000.00',
        'status': 'Active'
    }

    with patch('services.employee_service.get_db_cursor') as mock_db:
        mock_db.return_value.__enter__.return_value = mock_cursor
        success, errors = emp_service.update_employee(5, payload)

        assert success is False
        assert 'email' in errors
        assert 'already registered' in errors['email'].lower()


def test_delete_employee_service_success():
    """Verify delete_employee deletes record and returns True when row is affected."""
    mock_cursor = MagicMock()
    mock_cursor.rowcount = 1

    with patch('services.employee_service.get_db_cursor') as mock_db:
        mock_db.return_value.__enter__.return_value = mock_cursor
        result = emp_service.delete_employee(7)

        assert result is True
        assert any("DELETE FROM employees WHERE id = %s" in str(call) for call in mock_cursor.execute.call_args_list)


def test_delete_employee_service_non_existent():
    """Verify delete_employee returns False when rowcount is 0."""
    mock_cursor = MagicMock()
    mock_cursor.rowcount = 0

    with patch('services.employee_service.get_db_cursor') as mock_db:
        mock_db.return_value.__enter__.return_value = mock_cursor
        result = emp_service.delete_employee(99999)

        assert result is False


def test_get_employee_by_id_returns_none_when_missing():
    """Verify get_employee_by_id returns None when no matching row is found."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None

    with patch('services.employee_service.get_db_cursor') as mock_db:
        mock_db.return_value.__enter__.return_value = mock_cursor
        result = emp_service.get_employee_by_id(99999)

        assert result is None


def test_get_employees_search_by_string():
    """Verify search by keyword adds full_name, email, and job_title LIKE clauses."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {'total': 1}
    mock_cursor.fetchall.return_value = []

    with patch('services.employee_service.get_db_cursor') as mock_db:
        mock_db.return_value.__enter__.return_value = mock_cursor
        result = emp_service.get_employees(search='engineer')

        calls = mock_cursor.execute.call_args_list
        count_sql, count_params = calls[0][0]
        assert "e.full_name LIKE %s OR e.email LIKE %s OR e.job_title LIKE %s" in count_sql
        assert "%engineer%" in count_params


def test_get_employees_search_by_numeric_id():
    """Verify search by numeric string also searches e.id = %s."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {'total': 1}
    mock_cursor.fetchall.return_value = []

    with patch('services.employee_service.get_db_cursor') as mock_db:
        mock_db.return_value.__enter__.return_value = mock_cursor
        result = emp_service.get_employees(search='42')

        calls = mock_cursor.execute.call_args_list
        count_sql, count_params = calls[0][0]
        assert "e.id = %s" in count_sql
        assert 42 in count_params


def test_update_department_success():
    """Verify update_department successfully updates department record."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None  # No duplicate name

    with patch('services.department_service.get_db_cursor') as mock_db:
        mock_db.return_value.__enter__.return_value = mock_cursor
        success, err = dept_service.update_department(1, 'Product Management', 'Product team')

        assert success is True
        assert err is None
        assert any("UPDATE departments SET name = %s" in str(call) for call in mock_cursor.execute.call_args_list)


def test_get_department_by_id():
    """Verify get_department_by_id queries department with employee count."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {'id': 1, 'name': 'Engineering', 'employee_count': 4}

    with patch('services.department_service.get_db_cursor') as mock_db:
        mock_db.return_value.__enter__.return_value = mock_cursor
        dept = dept_service.get_department_by_id(1)

        assert dept is not None
        assert dept['name'] == 'Engineering'
        assert dept['employee_count'] == 4


def test_production_config_rejects_missing_or_insecure_secret_key():
    """Verify that ProductionConfig strictly rejects missing or placeholder SECRET_KEY."""
    import os
    import pytest
    from config import ProductionConfig

    # 1. Missing / empty SECRET_KEY
    with patch.dict(os.environ, {'SECRET_KEY': ''}, clear=False):
        with pytest.raises(ValueError, match="Production security violation"):
            ProductionConfig.validate_production()

    # 2. Known default insecure placeholder
    with patch.dict(os.environ, {'SECRET_KEY': 'dev-insecure-secret-key-change-me'}, clear=False):
        with pytest.raises(ValueError, match="Production security violation"):
            ProductionConfig.validate_production()

    # 3. Key too short (< 16 characters)
    with patch.dict(os.environ, {'SECRET_KEY': 'short-secret'}, clear=False):
        with pytest.raises(ValueError, match="Production security violation"):
            ProductionConfig.validate_production()


def test_production_config_accepts_strong_secret_key():
    """Verify that ProductionConfig successfully accepts a cryptographically strong SECRET_KEY."""
    import os
    from config import ProductionConfig

    strong_key = "a1b2c3d4e5f678901234567890abcdef"
    with patch.dict(os.environ, {'SECRET_KEY': strong_key}, clear=False):
        validated = ProductionConfig.validate_production()
        assert validated == strong_key
        assert ProductionConfig.SECRET_KEY == strong_key


def test_clean_sql_statements_filters_db_commands_for_cloud():
    """Verify that _clean_sql_statements with skip_db_commands=True strips CREATE DATABASE and USE statements."""
    sample_sql = """
    -- Cloud init script
    CREATE DATABASE IF NOT EXISTS employee_db;
    USE employee_db;

    CREATE TABLE IF NOT EXISTS departments (
        id INT PRIMARY KEY,
        name VARCHAR(100)
    );
    """
    stmts = _clean_sql_statements(sample_sql, skip_db_commands=True)
    assert len(stmts) == 1
    assert "CREATE TABLE IF NOT EXISTS departments" in stmts[0]
    assert not any("CREATE DATABASE" in s for s in stmts)
    assert not any("USE " in s for s in stmts)


def test_resolve_database_config_from_url():
    """Verify that _resolve_database_config correctly parses full connection URLs (DATABASE_URL/MYSQL_URL)."""
    import os
    from config import _resolve_database_config

    cloud_url = "mysql://avnadmin:SecretPass123%21@mysql-project.aivencloud.com:12345/defaultdb"
    env_vars = {
        'DATABASE_URL': cloud_url,
        'DB_HOST': '',
        'DB_PORT': '',
        'DB_USER': '',
        'DB_PASSWORD': '',
        'DB_NAME': '',
    }
    with patch.dict(os.environ, env_vars, clear=False):
        host, port, user, password, dbname = _resolve_database_config()
        assert host == "mysql-project.aivencloud.com"
        assert port == 12345
        assert user == "avnadmin"
        assert password == "SecretPass123!"
        assert dbname == "defaultdb"



