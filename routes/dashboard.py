"""
Dashboard Blueprint
Displays executive metrics, Chart.js visualizations, and recently added employees.
"""
import json
from flask import Blueprint, render_template, current_app
from routes.auth import login_required
from services.report_service import get_dashboard_stats
from services.employee_service import get_recent_employees
from services.department_service import get_all_departments

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    """Renders the executive dashboard overview."""
    stats = get_dashboard_stats()
    recent_employees = get_recent_employees(limit=5)
    departments = get_all_departments()

    # Prepare data for Chart.js
    dept_labels = [d['department_name'] for d in stats['dept_distribution']]
    dept_counts = [d['employee_count'] for d in stats['dept_distribution']]

    trend_labels = [t['join_month'] for t in stats['joining_trends']]
    trend_counts = [t['count'] for t in stats['joining_trends']]

    chart_data = {
        'dept_labels': dept_labels,
        'dept_counts': dept_counts,
        'trend_labels': trend_labels,
        'trend_counts': trend_counts,
    }

    return render_template(
        'dashboard.html',
        stats=stats,
        recent_employees=recent_employees,
        departments=departments,
        chart_data=chart_data,
        currency_symbol=current_app.config.get('CURRENCY_SYMBOL', '$')
    )
