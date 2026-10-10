"""
Employee Management Blueprint
Handles employee CRUD workflows, search, filtering, sorting, and pagination.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, abort
from routes.auth import login_required
from services.employee_service import (
    get_employees, get_employee_by_id, create_employee,
    update_employee, delete_employee
)
from services.department_service import get_all_departments

employees_bp = Blueprint('employees', __name__, url_prefix='/employees')


@employees_bp.route('')
@employees_bp.route('/')
@login_required
def list_employees():
    """Renders the employee roster with server-side search, filtering, sorting, and pagination."""
    search = request.args.get('search', '').strip()
    dept_id = request.args.get('department', '').strip()
    status = request.args.get('status', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    sort_by = request.args.get('sort_by', 'id').strip()
    sort_order = request.args.get('sort_order', 'desc').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', current_app.config.get('ITEMS_PER_PAGE', 10), type=int)

    pagination_data = get_employees(
        search=search,
        department_id=dept_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        per_page=per_page
    )

    departments = get_all_departments()

    return render_template(
        'employees/list.html',
        employees=pagination_data['employees'],
        pagination=pagination_data,
        departments=departments,
        current_search=search,
        current_dept=dept_id,
        current_status=status,
        current_start_date=start_date,
        current_end_date=end_date,
        current_sort_by=sort_by,
        current_sort_order=sort_order,
        currency_symbol=current_app.config.get('CURRENCY_SYMBOL', '$')
    )


@employees_bp.route('/<int:emp_id>')
@login_required
def detail(emp_id):
    """Displays comprehensive profile information for a specific employee."""
    employee = get_employee_by_id(emp_id)
    if not employee:
        return render_template(
            'errors/404.html',
            resource_name="Employee",
            message=f"No employee found with ID #{emp_id}."
        ), 404

    return render_template(
        'employees/detail.html',
        employee=employee,
        currency_symbol=current_app.config.get('CURRENCY_SYMBOL', '$')
    )


@employees_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Renders registration form and processes new employee creation."""
    if request.method == 'POST':
        form_data = {
            'full_name': request.form.get('full_name', '').strip(),
            'email': request.form.get('email', '').strip(),
            'phone': request.form.get('phone', '').strip(),
            'department_id': request.form.get('department_id', '').strip(),
            'job_title': request.form.get('job_title', '').strip(),
            'joining_date': request.form.get('joining_date', '').strip(),
            'salary': request.form.get('salary', '').strip(),
            'status': request.form.get('status', 'Active').strip(),
            'address': request.form.get('address', '').strip(),
        }

        success, new_id, errors = create_employee(form_data)
        if success:
            flash(f"Employee '{form_data['full_name']}' registered successfully!", "success")
            return redirect(url_for('employees.detail', emp_id=new_id))

        departments = get_all_departments()
        flash("Please resolve the validation errors highlighted below.", "danger")
        return render_template(
            'employees/add.html',
            departments=departments,
            form=form_data,
            errors=errors or {}
        )

    # Empty form for GET
    departments = get_all_departments()
    return render_template(
        'employees/add.html',
        departments=departments,
        form={'status': 'Active'},
        errors={}
    )


@employees_bp.route('/<int:emp_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(emp_id):
    """Loads existing record, renders edit form, and saves verified updates."""
    employee = get_employee_by_id(emp_id)
    if not employee:
        return render_template(
            'errors/404.html',
            resource_name="Employee",
            message=f"No employee found with ID #{emp_id}."
        ), 404

    if request.method == 'POST':
        form_data = {
            'full_name': request.form.get('full_name', '').strip(),
            'email': request.form.get('email', '').strip(),
            'phone': request.form.get('phone', '').strip(),
            'department_id': request.form.get('department_id', '').strip(),
            'job_title': request.form.get('job_title', '').strip(),
            'joining_date': request.form.get('joining_date', '').strip(),
            'salary': request.form.get('salary', '').strip(),
            'status': request.form.get('status', 'Active').strip(),
            'address': request.form.get('address', '').strip(),
        }

        success, errors = update_employee(emp_id, form_data)
        if success:
            flash(f"Employee '{form_data['full_name']}' updated successfully!", "success")
            return redirect(url_for('employees.detail', emp_id=emp_id))

        departments = get_all_departments()
        flash("Please resolve the validation errors highlighted below.", "danger")
        form_data['id'] = emp_id
        return render_template(
            'employees/edit.html',
            employee=employee,
            departments=departments,
            form=form_data,
            errors=errors or {}
        )

    # Prepopulate form with existing values for GET
    departments = get_all_departments()
    initial_form = {
        'id': employee['id'],
        'full_name': employee['full_name'],
        'email': employee['email'],
        'phone': employee['phone'] or '',
        'department_id': str(employee['department_id'] or ''),
        'job_title': employee['job_title'],
        'joining_date': str(employee['joining_date']),
        'salary': str(employee['salary']),
        'status': employee['status'],
        'address': employee['address'] or '',
    }

    return render_template(
        'employees/edit.html',
        employee=employee,
        departments=departments,
        form=initial_form,
        errors={}
    )


@employees_bp.route('/<int:emp_id>/delete', methods=['POST'])
@login_required
def delete(emp_id):
    """Deletes an employee record and redirects back to roster."""
    employee = get_employee_by_id(emp_id)
    if not employee:
        flash("Employee not found.", "warning")
        return redirect(url_for('employees.list_employees'))

    name = employee['full_name']
    if delete_employee(emp_id):
        flash(f"Employee '{name}' (ID #{emp_id}) was successfully deleted.", "success")
    else:
        flash(f"Failed to delete employee '{name}'.", "danger")

    return redirect(url_for('employees.list_employees'))
