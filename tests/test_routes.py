"""
Route & Blueprint Integration Tests
Tests HTTP endpoints, authentication guards, status codes, and template rendering.
"""
from unittest.mock import patch, MagicMock
from decimal import Decimal
from datetime import date


def test_login_page_renders_cleanly(client):
    """Verify that unauthenticated GET /login returns 200."""
    response = client.get('/login')
    assert response.status_code == 200
    assert b"Administrator Sign In" in response.data or b"EMS Portal" in response.data


def test_protected_routes_redirect_unauthenticated_users(client):
    """Verify that protected pages redirect unauthenticated visitors to /login."""
    protected_urls = ['/', '/dashboard', '/employees', '/employees/add', '/departments', '/reports', '/settings']
    for url in protected_urls:
        response = client.get(url, follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.headers['Location']


def test_failed_login_shows_error(client):
    """Verify that submitting bad credentials displays an error message."""
    with patch('routes.auth.authenticate_admin', return_value=None):
        response = client.post('/login', data={
            'username_or_email': 'wrong_user',
            'password': 'wrong_password'
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b"Invalid credentials" in response.data


def test_successful_login_redirects(client):
    """Verify that valid credentials log the user in and redirect."""
    mock_admin = {
        'id': 1,
        'username': 'admin',
        'full_name': 'Test Admin',
        'email': 'admin@test.com'
    }
    with patch('routes.auth.authenticate_admin', return_value=mock_admin):
        response = client.post('/login', data={
            'username_or_email': 'admin',
            'password': 'correct_password'
        }, follow_redirects=False)
        assert response.status_code == 302
        assert response.headers['Location'].endswith('/dashboard') or response.headers['Location'] == '/'


def test_dashboard_renders_with_mock_data(auth_client):
    """Verify that dashboard loads successfully with statistics and charts."""
    mock_stats = {
        'total_employees': 10,
        'active_employees': 9,
        'inactive_employees': 1,
        'total_departments': 4,
        'average_salary': Decimal('75000.00'),
        'dept_distribution': [{'department_name': 'Engineering', 'employee_count': 5}],
        'joining_trends': [{'join_month': '2024-01', 'count': 2}],
    }
    with patch('routes.dashboard.get_dashboard_stats', return_value=mock_stats), \
         patch('routes.dashboard.get_recent_employees', return_value=[]), \
         patch('routes.dashboard.get_all_departments', return_value=[]):
        response = auth_client.get('/dashboard')
        assert response.status_code == 200
        assert b"Executive Dashboard" in response.data
        assert b"Total Workforce" in response.data


def test_employee_list_renders(auth_client):
    """Verify employee list view renders with pagination data."""
    mock_pagination = {
        'employees': [
            {
                'id': 1,
                'full_name': 'Alice Smith',
                'email': 'alice@example.com',
                'phone': '555-1234',
                'department_id': 1,
                'job_title': 'Developer',
                'joining_date': date(2023, 1, 15),
                'salary': Decimal('90000.00'),
                'status': 'Active',
                'department_name': 'Engineering'
            }
        ],
        'total': 1,
        'page': 1,
        'per_page': 10,
        'total_pages': 1,
        'has_prev': False,
        'has_next': False,
    }
    with patch('routes.employees.get_employees', return_value=mock_pagination), \
         patch('routes.employees.get_all_departments', return_value=[]):
        response = auth_client.get('/employees')
        assert response.status_code == 200
        assert b"Alice Smith" in response.data
        assert b"Developer" in response.data


def test_missing_employee_returns_404(auth_client):
    """Verify that requesting an nonexistent employee ID yields a friendly 404."""
    with patch('routes.employees.get_employee_by_id', return_value=None):
        response = auth_client.get('/employees/99999')
        assert response.status_code == 404
        assert b"Employee Not Found" in response.data or b"404" in response.data


def test_department_list_renders(auth_client):
    """Verify departments directory page renders."""
    mock_depts = [
        {'id': 1, 'name': 'Engineering', 'description': 'Dev team', 'employee_count': 5}
    ]
    with patch('routes.departments.get_all_departments', return_value=mock_depts):
        response = auth_client.get('/departments')
        assert response.status_code == 200
        assert b"Departments Directory" in response.data
        assert b"Engineering" in response.data


def test_csv_export_endpoint(auth_client):
    """Verify employee CSV export returns proper text/csv headers and body."""
    mock_csv = "Employee ID,Full Name,Email,Phone,Department,Job Title,Joining Date,Salary,Status,Address\n1,Bob Ross,bob@example.com,N/A,Design,Artist,2023-01-01,70000.00,Active,"
    with patch('routes.reports.export_employees_to_csv', return_value=mock_csv):
        response = auth_client.get('/reports/export/employees')
        assert response.status_code == 200
        assert response.mimetype == 'text/csv'
        assert 'attachment;' in response.headers.get('Content-Disposition', '')
        assert b"Bob Ross" in response.data
        assert b"Employee ID" in response.data


def test_employee_detail_renders(auth_client):
    """Verify employee detail page renders for existing employee."""
    mock_emp = {
        'id': 1,
        'full_name': 'Jane Doe',
        'email': 'jane.doe@example.com',
        'phone': '555-0100',
        'job_title': 'Senior Engineer',
        'joining_date': date(2023, 5, 20),
        'salary': Decimal('95000.00'),
        'status': 'Active',
        'department_name': 'Engineering',
        'department_description': 'Software group',
        'address': '123 Tech Way',
    }
    with patch('routes.employees.get_employee_by_id', return_value=mock_emp):
        response = auth_client.get('/employees/1')
        assert response.status_code == 200
        assert b"Jane Doe" in response.data
        assert b"Senior Engineer" in response.data
        assert b"Engineering" in response.data


def test_add_employee_get_renders_form(auth_client):
    """Verify GET /employees/add loads registration form."""
    with patch('routes.employees.get_all_departments', return_value=[{'id': 1, 'name': 'Engineering'}]):
        response = auth_client.get('/employees/add')
        assert response.status_code == 200
        assert b"Register New Employee" in response.data or b"Add Employee" in response.data


def test_add_employee_post_success(auth_client):
    """Verify POST /employees/add creates employee and redirects to detail view."""
    payload = {
        'full_name': 'John New',
        'email': 'john.new@example.com',
        'phone': '555-9999',
        'department_id': '1',
        'job_title': 'Analyst',
        'joining_date': '2024-01-01',
        'salary': '75000.00',
        'status': 'Active',
        'address': 'Some Address'
    }
    with patch('routes.employees.create_employee', return_value=(True, 42, None)):
        response = auth_client.post('/employees/add', data=payload, follow_redirects=False)
        assert response.status_code == 302
        assert response.headers['Location'].endswith('/employees/42')


def test_add_employee_post_validation_error(auth_client):
    """Verify POST /employees/add with validation error re-renders form with errors."""
    payload = {'full_name': '', 'email': 'bad'}
    errors = {'full_name': 'Full name is required.', 'email': 'Invalid email format.'}
    with patch('routes.employees.create_employee', return_value=(False, None, errors)), \
         patch('routes.employees.get_all_departments', return_value=[]):
        response = auth_client.post('/employees/add', data=payload, follow_redirects=False)
        assert response.status_code == 200
        assert b"Full name is required." in response.data


def test_edit_employee_get_renders_form(auth_client):
    """Verify GET /employees/<id>/edit pre-populates form with employee data."""
    mock_emp = {
        'id': 5,
        'full_name': 'Existing Person',
        'email': 'existing@example.com',
        'phone': '555-5555',
        'department_id': 1,
        'job_title': 'Specialist',
        'joining_date': date(2022, 6, 1),
        'salary': Decimal('60000.00'),
        'status': 'Active',
        'address': 'Existing Place'
    }
    with patch('routes.employees.get_employee_by_id', return_value=mock_emp), \
         patch('routes.employees.get_all_departments', return_value=[]):
        response = auth_client.get('/employees/5/edit')
        assert response.status_code == 200
        assert b"Existing Person" in response.data


def test_edit_employee_get_missing_returns_404(auth_client):
    """Verify GET /employees/<id>/edit for non-existent employee returns 404."""
    with patch('routes.employees.get_employee_by_id', return_value=None):
        response = auth_client.get('/employees/99999/edit')
        assert response.status_code == 404


def test_edit_employee_post_success(auth_client):
    """Verify POST /employees/<id>/edit successfully updates and redirects."""
    mock_emp = {'id': 5, 'full_name': 'Existing Person'}
    payload = {
        'full_name': 'Updated Person',
        'email': 'updated@example.com',
        'phone': '555-5555',
        'department_id': '1',
        'job_title': 'Specialist',
        'joining_date': '2022-06-01',
        'salary': '65000.00',
        'status': 'Active',
        'address': 'New Place'
    }
    with patch('routes.employees.get_employee_by_id', return_value=mock_emp), \
         patch('routes.employees.update_employee', return_value=(True, None)):
        response = auth_client.post('/employees/5/edit', data=payload, follow_redirects=False)
        assert response.status_code == 302
        assert response.headers['Location'].endswith('/employees/5')


def test_edit_employee_post_validation_error(auth_client):
    """Verify POST /employees/<id>/edit with invalid data redisplays form with error."""
    mock_emp = {'id': 5, 'full_name': 'Existing Person'}
    payload = {'full_name': '', 'salary': '-500'}
    errors = {'full_name': 'Full name is required.', 'salary': 'Salary cannot be negative.'}
    with patch('routes.employees.get_employee_by_id', return_value=mock_emp), \
         patch('routes.employees.update_employee', return_value=(False, errors)), \
         patch('routes.employees.get_all_departments', return_value=[]):
        response = auth_client.post('/employees/5/edit', data=payload, follow_redirects=False)
        assert response.status_code == 200
        assert b"Full name is required." in response.data


def test_edit_employee_post_missing_returns_404(auth_client):
    """Verify POST /employees/<id>/edit for missing employee returns 404."""
    with patch('routes.employees.get_employee_by_id', return_value=None):
        response = auth_client.post('/employees/99999/edit', data={}, follow_redirects=False)
        assert response.status_code == 404


def test_delete_employee_post_success(auth_client):
    """Verify POST /employees/<id>/delete removes record and redirects."""
    mock_emp = {'id': 5, 'full_name': 'Employee To Delete'}
    with patch('routes.employees.get_employee_by_id', return_value=mock_emp), \
         patch('routes.employees.delete_employee', return_value=True):
        response = auth_client.post('/employees/5/delete', follow_redirects=False)
        assert response.status_code == 302
        assert response.headers['Location'].rstrip('/').endswith('/employees')


def test_delete_employee_post_missing(auth_client):
    """Verify POST /employees/<id>/delete handles missing record gracefully."""
    with patch('routes.employees.get_employee_by_id', return_value=None):
        response = auth_client.post('/employees/99999/delete', follow_redirects=False)
        assert response.status_code == 302
        assert response.headers['Location'].rstrip('/').endswith('/employees')


def test_employee_search_and_filter_query_params(auth_client):
    """Verify query parameters are correctly forwarded to employee service."""
    with patch('routes.employees.get_employees') as mock_get, \
         patch('routes.employees.get_all_departments', return_value=[]):
        mock_get.return_value = {
            'employees': [], 'total': 0, 'page': 1, 'per_page': 10,
            'total_pages': 1, 'has_prev': False, 'has_next': False
        }
        response = auth_client.get('/employees?search=architect&department=2&status=Active&sort_by=salary&sort_order=asc')
        assert response.status_code == 200
        mock_get.assert_called_once_with(
            search='architect',
            department_id='2',
            status='Active',
            start_date='',
            end_date='',
            sort_by='salary',
            sort_order='asc',
            page=1,
            per_page=10
        )


def test_department_add_post(auth_client):
    """Verify POST /departments/add creates department and redirects."""
    with patch('routes.departments.create_department', return_value=(True, 7, None)):
        response = auth_client.post('/departments/add', data={
            'name': 'Customer Success',
            'description': 'Client onboarding and support'
        }, follow_redirects=False)
        assert response.status_code == 302
        assert response.headers['Location'].rstrip('/').endswith('/departments')


def test_department_edit_post(auth_client):
    """Verify POST /departments/<id>/edit modifies department and redirects."""
    with patch('routes.departments.update_department', return_value=(True, None)):
        response = auth_client.post('/departments/2/edit', data={
            'name': 'People & Culture',
            'description': 'HR and Culture'
        }, follow_redirects=False)
        assert response.status_code == 302
        assert response.headers['Location'].rstrip('/').endswith('/departments')


def test_department_delete_post_success(auth_client):
    """Verify POST /departments/<id>/delete removes empty department."""
    with patch('routes.departments.delete_department', return_value=(True, None)):
        response = auth_client.post('/departments/2/delete', follow_redirects=False)
        assert response.status_code == 302
        assert response.headers['Location'].rstrip('/').endswith('/departments')


def test_department_delete_blocked_when_employees_assigned(auth_client):
    """Verify POST /departments/<id>/delete displays warning when deletion is blocked."""
    with patch('routes.departments.delete_department', return_value=(False, 'Cannot delete department')):
        response = auth_client.post('/departments/2/delete', follow_redirects=False)
        assert response.status_code == 302
        assert response.headers['Location'].rstrip('/').endswith('/departments')

