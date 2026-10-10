"""
Validation and Security Unit Tests
Tests server-side data validation rules and CSV formula injection sanitization.
"""
from decimal import Decimal
from services.employee_service import validate_employee_data
from services.report_service import sanitize_csv_cell


class DummyCursor:
    """Mock database cursor to simulate uniqueness queries."""
    def __init__(self, existing_emails=None):
        self.existing_emails = existing_emails or []

    def execute(self, query, params=None):
        self.last_query = query
        self.last_params = params

    def fetchone(self):
        if self.last_params and len(self.last_params) > 0:
            email = self.last_params[0]
            if email in self.existing_emails:
                return {'id': 1}
        return None


def test_valid_employee_payload():
    """Verify that a properly filled employee payload passes validation."""
    data = {
        'full_name': 'Jane Doe',
        'email': 'jane.doe@company.com',
        'phone': '+1 (555) 987-6543',
        'job_title': 'Senior Engineer',
        'joining_date': '2024-03-15',
        'salary': '95000.00',
        'status': 'Active',
        'department_id': '1',
        'address': '123 Tech Way'
    }
    cursor = DummyCursor()
    is_valid, errors = validate_employee_data(data, db_cursor=cursor)
    assert is_valid is True
    assert errors == {}


def test_missing_required_fields():
    """Verify that missing required fields trigger individual field errors."""
    data = {}
    cursor = DummyCursor()
    is_valid, errors = validate_employee_data(data, db_cursor=cursor)
    assert is_valid is False
    assert 'full_name' in errors
    assert 'email' in errors
    assert 'job_title' in errors
    assert 'joining_date' in errors
    assert 'salary' in errors
    assert 'status' in errors


def test_invalid_email_format():
    """Verify that malformed emails are rejected."""
    bad_emails = ['not-an-email', '@company.com', 'user@', 'user@domain']
    cursor = DummyCursor()
    for bad_email in bad_emails:
        data = {
            'full_name': 'Test User',
            'email': bad_email,
            'job_title': 'Dev',
            'joining_date': '2024-01-01',
            'salary': '50000',
            'status': 'Active'
        }
        is_valid, errors = validate_employee_data(data, db_cursor=cursor)
        assert is_valid is False
        assert 'email' in errors


def test_duplicate_email_rejected():
    """Verify that an email already in the database is flagged as duplicate."""
    cursor = DummyCursor(existing_emails=['existing@company.com'])
    data = {
        'full_name': 'New Employee',
        'email': 'existing@company.com',
        'job_title': 'Dev',
        'joining_date': '2024-01-01',
        'salary': '50000',
        'status': 'Active'
    }
    is_valid, errors = validate_employee_data(data, db_cursor=cursor)
    assert is_valid is False
    assert 'email' in errors
    assert 'already registered' in errors['email'].lower()


def test_invalid_phone_format():
    """Verify that an improperly formatted phone number is rejected."""
    cursor = DummyCursor()
    data = {
        'full_name': 'Test User',
        'email': 'user@example.com',
        'phone': '123',  # too short
        'job_title': 'Dev',
        'joining_date': '2024-01-01',
        'salary': '50000',
        'status': 'Active'
    }
    is_valid, errors = validate_employee_data(data, db_cursor=cursor)
    assert is_valid is False
    assert 'phone' in errors


def test_negative_and_non_numeric_salary():
    """Verify that negative or non-numeric salaries are rejected."""
    cursor = DummyCursor()
    bad_salaries = ['-500', '-0.01', 'abc', 'fifty thousand', '']
    for bad_sal in bad_salaries:
        data = {
            'full_name': 'Test User',
            'email': 'user@example.com',
            'job_title': 'Dev',
            'joining_date': '2024-01-01',
            'salary': bad_sal,
            'status': 'Active'
        }
        is_valid, errors = validate_employee_data(data, db_cursor=cursor)
        assert is_valid is False
        assert 'salary' in errors


def test_invalid_joining_date():
    """Verify that invalid calendar dates or bad formats are rejected."""
    cursor = DummyCursor()
    bad_dates = ['2024-02-30', '15/03/2024', 'invalid-date', '1800-01-01']
    for bad_date in bad_dates:
        data = {
            'full_name': 'Test User',
            'email': 'user@example.com',
            'job_title': 'Dev',
            'joining_date': bad_date,
            'salary': '50000',
            'status': 'Active'
        }
        is_valid, errors = validate_employee_data(data, db_cursor=cursor)
        assert is_valid is False
        assert 'joining_date' in errors


def test_invalid_status_enum():
    """Verify that statuses other than Active or Inactive are rejected."""
    cursor = DummyCursor()
    data = {
        'full_name': 'Test User',
        'email': 'user@example.com',
        'job_title': 'Dev',
        'joining_date': '2024-01-01',
        'salary': '50000',
        'status': 'Pending'
    }
    is_valid, errors = validate_employee_data(data, db_cursor=cursor)
    assert is_valid is False
    assert 'status' in errors


def test_csv_injection_sanitization():
    """Verify that dangerous CSV formula characters are safely escaped."""
    assert sanitize_csv_cell('=SUM(A1:A10)') == "'=SUM(A1:A10)"
    assert sanitize_csv_cell('+cmd|') == "'+cmd|"
    assert sanitize_csv_cell('-calc') == "'-calc"
    assert sanitize_csv_cell('@exec') == "'@exec"
    assert sanitize_csv_cell('Normal String') == "Normal String"
    assert sanitize_csv_cell(None) == ""
    assert sanitize_csv_cell(12345) == "12345"


def test_invalid_department_id_non_integer():
    """Verify non-integer department_id is rejected."""
    cursor = DummyCursor()
    data = {
        'full_name': 'Test User',
        'email': 'user@example.com',
        'job_title': 'Dev',
        'joining_date': '2024-01-01',
        'salary': '50000',
        'status': 'Active',
        'department_id': 'invalid_dept'
    }
    is_valid, errors = validate_employee_data(data, db_cursor=cursor)
    assert is_valid is False
    assert 'department_id' in errors


def test_excessive_field_lengths():
    """Verify length boundaries for full name, email, job title, and address."""
    cursor = DummyCursor()
    data = {
        'full_name': 'A' * 105,
        'email': 'b' * 155 + '@example.com',
        'job_title': 'J' * 105,
        'joining_date': '2024-01-01',
        'salary': '50000',
        'status': 'Active',
        'address': 'D' * 550
    }
    is_valid, errors = validate_employee_data(data, db_cursor=cursor)
    assert is_valid is False
    assert 'full_name' in errors
    assert 'email' in errors
    assert 'job_title' in errors
    assert 'address' in errors


def test_salary_exceeds_maximum():
    """Verify salaries exceeding 999,999,999.99 are rejected."""
    cursor = DummyCursor()
    data = {
        'full_name': 'Test Billionaire',
        'email': 'rich@example.com',
        'job_title': 'Exec',
        'joining_date': '2024-01-01',
        'salary': '1000000000.00',
        'status': 'Active'
    }
    is_valid, errors = validate_employee_data(data, db_cursor=cursor)
    assert is_valid is False
    assert 'salary' in errors

