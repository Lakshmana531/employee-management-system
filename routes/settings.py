"""
Settings & System Diagnostics Blueprint
Displays database health checks, application environment status, and preferences.
"""
import sys
import flask
from flask import Blueprint, render_template, current_app, session, request, flash, redirect, url_for
from routes.auth import login_required
from db import check_db_connection

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')


@settings_bp.route('', methods=['GET', 'POST'])
@settings_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    """Renders system diagnostics, environment variables, and active preferences."""
    if request.method == 'POST':
        # Handle preference updates (e.g. currency symbol or page size for current session)
        new_symbol = request.form.get('currency_symbol', '').strip()
        new_per_page = request.form.get('items_per_page', '').strip()

        if new_symbol:
            session['currency_symbol'] = new_symbol
        if new_per_page and new_per_page.isdigit():
            session['items_per_page'] = int(new_per_page)

        flash("Display preferences updated for this session.", "success")
        return redirect(url_for('settings.index'))

    is_healthy, db_info = check_db_connection()

    sys_info = {
        'python_version': sys.version.split()[0],
        'flask_version': flask.__version__,
        'os_name': sys.platform,
        'debug_mode': current_app.debug,
        'app_env': current_app.config.get('ENV', 'development'),
        'items_per_page': session.get('items_per_page', current_app.config.get('ITEMS_PER_PAGE', 10)),
        'currency_symbol': session.get('currency_symbol', current_app.config.get('CURRENCY_SYMBOL', '$')),
    }

    return render_template(
        'settings/index.html',
        is_healthy=is_healthy,
        db_info=db_info,
        sys_info=sys_info
    )
