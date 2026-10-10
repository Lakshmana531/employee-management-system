"""
Employee Management System (EMS)
Main Application Entrypoint & Factory
"""
import os
import click
from decimal import Decimal
from datetime import datetime
from flask import Flask, render_template, session, request
from flask_wtf.csrf import CSRFProtect
from config import get_config, ProductionConfig
from db import close_db_connection, init_db, DatabaseConnectionError, DatabaseError
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.employees import employees_bp
from routes.departments import departments_bp
from routes.reports import reports_bp
from routes.settings import settings_bp
from services.auth_service import create_admin, get_admin_by_id

csrf = CSRFProtect()


def create_app(config_object=None):
    """
    Application factory for the Employee Management System.
    """
    app = Flask(__name__)

    if config_object:
        if isinstance(config_object, type) and issubclass(config_object, ProductionConfig):
            config_object.validate_production()
        app.config.from_object(config_object)
    else:
        app.config.from_object(get_config())


    # Initialize CSRF protection
    csrf.init_app(app)

    # Register automatic database connection teardown
    app.teardown_appcontext(close_db_connection)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(employees_bp)
    app.register_blueprint(departments_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(settings_bp)

    # Register Custom Jinja2 Filters
    @app.template_filter('currency')
    def currency_filter(value):
        """Formats a numeric or Decimal value as localized currency."""
        if value is None:
            return "$0.00"
        try:
            val = Decimal(str(value))
            sym = session.get('currency_symbol', app.config.get('CURRENCY_SYMBOL', '$'))
            return f"{sym}{val:,.2f}"
        except Exception:
            return f"${value}"

    @app.template_filter('format_date')
    def format_date_filter(value):
        """Formats a date object or string into 'Mon DD, YYYY' format."""
        if not value:
            return "N/A"
        try:
            if isinstance(value, str):
                dt = datetime.strptime(value.split()[0], '%Y-%m-%d')
            else:
                dt = value
            return dt.strftime('%b %d, %Y')
        except Exception:
            return str(value)

    # Context Processor for Global Template Data
    @app.context_processor
    def inject_global_data():
        user = None
        if session.get('user_id'):
            user = {
                'id': session.get('user_id'),
                'username': session.get('username'),
                'full_name': session.get('full_name', 'Administrator'),
                'initials': ''.join([p[0].upper() for p in session.get('full_name', 'A').split()[:2]])
            }
        return {
            'current_user': user,
            'active_path': request.path,
            'app_name': 'Employee Management System'
        }

    # Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    @app.errorhandler(DatabaseConnectionError)
    def database_connection_handler(e):
        return render_template('errors/db_error.html', error_message=str(e)), 503

    # CLI Management Commands
    @app.cli.command('init-db')
    def init_db_command():
        """Initialize database schema tables."""
        init_db()
        click.echo("Initialized database schema.")

    @app.cli.command('seed-db')
    def seed_db_command():
        """Seed starter departments, employees, and default admin."""
        from seed import seed_departments, seed_employees, seed_admin
        init_db()
        seed_admin()
        seed_departments()
        seed_employees()
        click.echo("Seeded database with initial data.")

    @app.cli.command('create-admin')
    @click.option('--username', prompt=True, help="Admin username")
    @click.option('--email', prompt=True, help="Admin email")
    @click.option('--full-name', prompt=True, help="Admin full name")
    @click.password_option(help="Admin password")
    def create_admin_command(username, email, full_name, password):
        """Create a new administrator account."""
        success, admin_id, err = create_admin(username, email, password, full_name)
        if success:
            click.echo(f"Administrator '{username}' created successfully (ID: {admin_id}).")
        else:
            click.echo(f"Failed to create administrator: {err}", err=True)

    return app


# Create default application instance
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '127.0.0.1')
    is_production = os.environ.get('FLASK_ENV', '').lower() == 'production'
    debug = False if is_production else app.config.get('DEBUG', False)
    app.run(host=host, port=port, debug=debug)

