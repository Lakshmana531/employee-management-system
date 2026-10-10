"""
Department Management Blueprint
Handles department listing, additions, edits, and deletion protection rules.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from routes.auth import login_required
from services.department_service import (
    get_all_departments, get_department_by_id,
    create_department, update_department, delete_department
)

departments_bp = Blueprint('departments', __name__, url_prefix='/departments')


@departments_bp.route('')
@departments_bp.route('/')
@login_required
def index():
    """Lists all departments along with current headcounts."""
    departments = get_all_departments()
    return render_template('departments/list.html', departments=departments)


@departments_bp.route('/add', methods=['POST'])
@login_required
def add():
    """Creates a new organizational department."""
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()

    success, new_id, err = create_department(name, description)
    if success:
        flash(f"Department '{name}' created successfully!", "success")
    else:
        flash(err or "Failed to create department.", "danger")

    return redirect(url_for('departments.index'))


@departments_bp.route('/<int:dept_id>/edit', methods=['POST'])
@login_required
def edit(dept_id):
    """Updates department name and description."""
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()

    success, err = update_department(dept_id, name, description)
    if success:
        flash(f"Department '{name}' updated successfully!", "success")
    else:
        flash(err or "Failed to update department.", "danger")

    return redirect(url_for('departments.index'))


@departments_bp.route('/<int:dept_id>/delete', methods=['POST'])
@login_required
def delete(dept_id):
    """
    Deletes department if no active employees belong to it.
    Rejects deletion with a helpful message if employees are assigned.
    """
    success, err = delete_department(dept_id)
    if success:
        flash("Department deleted successfully.", "success")
    else:
        flash(err, "warning")

    return redirect(url_for('departments.index'))
