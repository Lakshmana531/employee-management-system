"""
Reports & Analytics Blueprint
Handles department metrics, payroll aggregations, and CSV exports.
"""
from datetime import datetime
from flask import Blueprint, render_template, request, Response, current_app
from routes.auth import login_required
from services.report_service import (
    get_dashboard_stats, get_department_salary_summary,
    export_employees_to_csv
)
from services.department_service import get_all_departments

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')


@reports_bp.route('')
@reports_bp.route('/')
@login_required
def index():
    """Renders comprehensive reports, payroll aggregations, and headcount analysis."""
    stats = get_dashboard_stats()
    salary_summary = get_department_salary_summary()
    departments = get_all_departments()

    # Calculate total company payroll
    total_payroll = sum(item['total_payroll'] for item in salary_summary)

    return render_template(
        'reports/index.html',
        stats=stats,
        salary_summary=salary_summary,
        total_payroll=total_payroll,
        departments=departments,
        currency_symbol=current_app.config.get('CURRENCY_SYMBOL', '$')
    )


@reports_bp.route('/export/employees')
@login_required
def export_employees():
    """Generates and downloads a clean, safe CSV file of employee records."""
    search = request.args.get('search', '').strip()
    dept_id = request.args.get('department', '').strip()
    status = request.args.get('status', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    sort_by = request.args.get('sort_by', 'id').strip()
    sort_order = request.args.get('sort_order', 'desc').strip()

    csv_data = export_employees_to_csv(
        search=search,
        department_id=dept_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by,
        sort_order=sort_order
    )

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"employees_export_{timestamp}.csv"

    # Prepend UTF-8 BOM so Excel opens it with correct encoding on Windows
    csv_bytes = ('\ufeff' + csv_data).encode('utf-8')

    return Response(
        csv_bytes,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "text/csv; charset=utf-8"
        }
    )
