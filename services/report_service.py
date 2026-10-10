"""
Report Service Module
Provides analytics, aggregation queries, and safe CSV export functionality.
"""
import csv
import io
from decimal import Decimal
from db import get_db_cursor
from services.employee_service import ALLOWED_SORT_COLUMNS, ALLOWED_SORT_ORDERS


def get_dashboard_stats():
    """
    Computes key performance indicators (KPIs) and data points for Chart.js charts.
    Safely handles empty database states with zero/empty values.
    """
    stats = {
        'total_employees': 0,
        'active_employees': 0,
        'inactive_employees': 0,
        'total_departments': 0,
        'average_salary': Decimal('0.00'),
        'dept_distribution': [],
        'joining_trends': [],
    }

    with get_db_cursor() as cursor:
        # 1. Total & Active & Inactive counts + Average Salary
        cursor.execute("""
            SELECT 
                COUNT(*) AS total_employees,
                COALESCE(SUM(CASE WHEN status = 'Active' THEN 1 ELSE 0 END), 0) AS active_employees,
                COALESCE(SUM(CASE WHEN status = 'Inactive' THEN 1 ELSE 0 END), 0) AS inactive_employees,
                COALESCE(AVG(salary), 0) AS avg_salary
            FROM employees
        """)
        emp_stats = cursor.fetchone()
        if emp_stats:
            stats['total_employees'] = int(emp_stats.get('total_employees') or 0)
            stats['active_employees'] = int(emp_stats.get('active_employees') or 0)
            stats['inactive_employees'] = int(emp_stats.get('inactive_employees') or 0)
            stats['average_salary'] = round(Decimal(str(emp_stats.get('avg_salary') or 0)), 2)

        # 2. Total Departments
        cursor.execute("SELECT COUNT(*) AS total_departments FROM departments")
        dept_count = cursor.fetchone()
        stats['total_departments'] = int(dept_count.get('total_departments') or 0) if dept_count else 0

        # 3. Department distribution for Chart.js (Doughnut / Pie)
        cursor.execute("""
            SELECT 
                COALESCE(d.name, 'Unassigned') AS department_name,
                COUNT(e.id) AS employee_count
            FROM departments d
            LEFT JOIN employees e ON d.id = e.department_id
            GROUP BY d.id, d.name
            HAVING employee_count > 0

            UNION

            SELECT 
                'Unassigned' AS department_name,
                COUNT(e.id) AS employee_count
            FROM employees e
            WHERE e.department_id IS NULL
            HAVING employee_count > 0

            ORDER BY employee_count DESC
        """)
        stats['dept_distribution'] = cursor.fetchall() or []

        # 4. Joining trends for Chart.js (Line chart, grouped by YYYY-MM)
        cursor.execute("""
            SELECT 
                DATE_FORMAT(joining_date, '%Y-%m') AS join_month,
                COUNT(*) AS count
            FROM employees
            GROUP BY DATE_FORMAT(joining_date, '%Y-%m')
            ORDER BY join_month ASC
        """)
        stats['joining_trends'] = cursor.fetchall() or []

    return stats


def get_department_salary_summary():
    """
    Returns aggregated salary metrics grouped by department.
    """
    sql = """
        SELECT 
            COALESCE(d.name, 'Unassigned') AS department_name,
            COUNT(e.id) AS employee_count,
            COALESCE(AVG(e.salary), 0) AS avg_salary,
            COALESCE(MIN(e.salary), 0) AS min_salary,
            COALESCE(MAX(e.salary), 0) AS max_salary,
            COALESCE(SUM(e.salary), 0) AS total_payroll
        FROM departments d
        LEFT JOIN employees e ON d.id = e.department_id
        GROUP BY d.id, d.name

        UNION

        SELECT 
            'Unassigned' AS department_name,
            COUNT(e.id) AS employee_count,
            COALESCE(AVG(e.salary), 0) AS avg_salary,
            COALESCE(MIN(e.salary), 0) AS min_salary,
            COALESCE(MAX(e.salary), 0) AS max_salary,
            COALESCE(SUM(e.salary), 0) AS total_payroll
        FROM employees e
        WHERE e.department_id IS NULL
        HAVING employee_count > 0

        ORDER BY total_payroll DESC
    """
    with get_db_cursor() as cursor:
        cursor.execute(sql)
        results = cursor.fetchall() or []
        for row in results:
            row['avg_salary'] = round(Decimal(str(row['avg_salary'])), 2)
            row['min_salary'] = round(Decimal(str(row['min_salary'])), 2)
            row['max_salary'] = round(Decimal(str(row['max_salary'])), 2)
            row['total_payroll'] = round(Decimal(str(row['total_payroll'])), 2)
        return results


def sanitize_csv_cell(value):
    """
    Sanitizes values to prevent CSV Injection (Formula Injection in Excel/Calc).
    Prepend a single quote if the string begins with =, +, -, @, tab, or carriage return.
    """
    if value is None:
        return ''
    str_val = str(value)
    if str_val and str_val[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + str_val
    return str_val


def export_employees_to_csv(search=None, department_id=None, status=None,
                            start_date=None, end_date=None, sort_by='id', sort_order='desc'):
    """
    Generates a secure CSV string containing employees matching specified filters.
    """
    col_order = ALLOWED_SORT_COLUMNS.get(sort_by, 'e.id')
    dir_order = ALLOWED_SORT_ORDERS.get((sort_order or '').lower(), 'DESC')

    where_clauses = []
    params = []

    if search:
        search_term = f"%{search.strip()}%"
        if search.strip().isdigit():
            where_clauses.append("(e.id = %s OR e.full_name LIKE %s OR e.email LIKE %s OR e.job_title LIKE %s)")
            params.extend([int(search.strip()), search_term, search_term, search_term])
        else:
            where_clauses.append("(e.full_name LIKE %s OR e.email LIKE %s OR e.job_title LIKE %s)")
            params.extend([search_term, search_term, search_term])

    if department_id and str(department_id).isdigit():
        where_clauses.append("e.department_id = %s")
        params.append(int(department_id))

    if status and status in ('Active', 'Inactive'):
        where_clauses.append("e.status = %s")
        params.append(status)

    if start_date:
        where_clauses.append("e.joining_date >= %s")
        params.append(start_date)

    if end_date:
        where_clauses.append("e.joining_date <= %s")
        params.append(end_date)

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    sql = f"""
        SELECT 
            e.id, e.full_name, e.email, e.phone,
            COALESCE(d.name, 'Unassigned') AS department_name,
            e.job_title, e.joining_date, e.salary, e.status, e.address,
            e.created_at
        FROM employees e
        LEFT JOIN departments d ON e.department_id = d.id
        {where_sql}
        ORDER BY {col_order} {dir_order}
    """

    with get_db_cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall() or []

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Header row
    headers = [
        'Employee ID', 'Full Name', 'Email', 'Phone', 'Department',
        'Job Title', 'Joining Date', 'Salary', 'Status', 'Address'
    ]
    writer.writerow(headers)

    for r in rows:
        writer.writerow([
            sanitize_csv_cell(r['id']),
            sanitize_csv_cell(r['full_name']),
            sanitize_csv_cell(r['email']),
            sanitize_csv_cell(r.get('phone') or 'N/A'),
            sanitize_csv_cell(r['department_name']),
            sanitize_csv_cell(r['job_title']),
            sanitize_csv_cell(str(r['joining_date'])),
            sanitize_csv_cell(f"{Decimal(str(r['salary'])):.2f}"),
            sanitize_csv_cell(r['status']),
            sanitize_csv_cell(r.get('address') or '')
        ])

    return output.getvalue()
