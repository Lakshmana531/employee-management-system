"""
Authentication Blueprint
Handles administrator login, logout, and session lifecycle.
"""
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from services.auth_service import authenticate_admin

auth_bp = Blueprint('auth', __name__)


def login_required(f):
    """Decorator ensuring that a route can only be accessed by authenticated users."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Renders login page and handles credentials verification."""
    if session.get('user_id'):
        return redirect(url_for('dashboard.index'))

    next_url = request.args.get('next')

    if request.method == 'POST':
        identifier = request.form.get('username_or_email', '').strip()
        password = request.form.get('password', '')

        if not identifier or not password:
            flash("Please provide both username/email and password.", "danger")
            return render_template('auth/login.html', identifier=identifier)

        admin = authenticate_admin(identifier, password)
        if admin:
            session.clear()
            session['user_id'] = admin['id']
            session['username'] = admin['username']
            session['full_name'] = admin['full_name']
            session['email'] = admin['email']
            session.permanent = True

            flash(f"Welcome back, {admin['full_name']}!", "success")
            
            # Avoid open redirect vulnerabilities
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            return redirect(url_for('dashboard.index'))
        else:
            flash("Invalid credentials. Please verify your username and password.", "danger")
            return render_template('auth/login.html', identifier=identifier)

    return render_template('auth/login.html')


@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    """Terminates administrator session."""
    session.clear()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for('auth.login'))
