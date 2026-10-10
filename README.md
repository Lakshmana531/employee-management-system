# Employee Management System (EMS)

A complete, production-grade, web-based Employee Management System built with **Python 3**, **Flask**, and **MySQL**, designed for modern HR administration with clean architecture, SaaS-inspired UI/UX, and strict data validation.

---

## Table of Contents

- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [Project Architecture](#project-architecture)
- [Database Schema](#database-schema)
- [Step-by-Step Windows & VS Code Setup Guide](#step-by-step-windows--vs-code-setup-guide)
  - [1. Prerequisites](#1-prerequisites)
  - [2. Open the Project in VS Code](#2-open-the-project-in-vs-code)
  - [3. Create and Activate a Python Virtual Environment](#3-create-and-activate-a-python-virtual-environment)
  - [4. Install Required Packages](#4-install-required-packages)
  - [5. Setup and Configure MySQL](#5-setup-and-configure-mysql)
  - [6. Configure Environment Variables (.env)](#6-configure-environment-variables-env)
  - [7. Seed Starter Departments and Sample Employees](#7-seed-starter-departments-and-sample-employees)
  - [8. Launch the Flask Server](#8-launch-the-flask-server)
  - [9. Access the Application](#9-access-the-application)
- [Running Automated Tests](#running-automated-tests)
- [Security and Data Protection](#security-and-data-protection)
- [Troubleshooting Common Issues on Windows](#troubleshooting-common-issues-on-windows)

---

## Key Features

1. **Executive Dashboard**:
   - Dynamic KPI metric cards: Total workforce, active staff, department count, and average compensation.
   - Interactive **Chart.js** visualizations: Department headcount doughnut chart and 12-month onboarding trends line chart.
   - Recent employee additions table with quick profile navigation.
   - Robust empty-state handling that displays clean guidance rather than errors when the database is empty.

2. **Employee Management (Full CRUD)**:
   - Server-side search across Employee ID, Full Name, Email, and Job Title.
   - Server-side filtering by Department and Status (Active/Inactive).
   - Allowlist-protected sorting by Name, Joining Date, Salary, or ID.
   - Server-side pagination with query parameter retention across pages and filters.
   - Detailed employee profile view with full audit timestamps.
   - Edit employee workflow with form pre-population and duplicate email detection.
   - Deletion with modal confirmation dialog.

3. **Strict Server-Side Validation**:
   - Required field verification, email regex validation, phone format checking, date boundary checks, and non-negative salary constraints.
   - Field-level feedback messages that preserve valid user inputs upon validation failure.

4. **Department Management**:
   - Organization business unit listing with real-time employee counts.
   - Department creation and renaming modals.
   - **Referential Integrity Protection**: Departments with assigned employees cannot be deleted until employees are reassigned or removed.

5. **Workforce Reports & CSV Export**:
   - Department compensation summaries: average salary, minimum, maximum, and total department payroll.
   - Filtered employee data export to CSV with UTF-8 BOM encoding for seamless Microsoft Excel compatibility on Windows.
   - Automatic sanitization against CSV Formula Injection (`=`, `+`, `-`, `@`).

6. **Authentication & Session Security**:
   - Session-based administrator login with scrypt password hashing via Werkzeug.
   - CSRF protection enabled on all state-changing forms using Flask-WTF.
   - Automatic connection teardown preventing dangling MySQL connections.

---

## Technology Stack

- **Backend**: Python 3.12+, Flask 3.0+
- **Database**: MySQL 8.0+ / MariaDB 10.4+
- **Connector**: `mysql-connector-python` with connection pooling
- **Security & Forms**: `Flask-WTF`, `Werkzeug`
- **Frontend**: HTML5, CSS3, Vanilla JavaScript (no heavy frontend frameworks required)
- **Icons**: Lucide Icons (CDN)
- **Visualizations**: Chart.js 4.4+ (CDN)
- **Testing**: `pytest`

---

## Project Architecture

```
employee_management_system/
│
├── app.py                     # Application factory, CLI commands, filter registrations
├── config.py                  # Environment-driven configuration classes
├── db.py                      # Connection pool manager, context managers, health checks
├── schema.sql                 # MySQL schema DDL (departments, employees, admins)
├── seed.py                    # Schema initialization and sample data seeder
├── requirements.txt           # Project package dependencies
├── .env.example               # Template environment configuration file
├── .env                       # Local secrets (ignored by Git)
├── .gitignore                 # Version control exclusions
├── README.md                  # Comprehensive documentation
│
├── routes/                    # Flask Blueprints (Controllers)
│   ├── __init__.py
│   ├── auth.py                # Admin login/logout & @login_required decorator
│   ├── dashboard.py           # Metrics and overview charts
│   ├── employees.py           # Employee CRUD, search, filter, pagination
│   ├── departments.py         # Department management and deletion guard
│   ├── reports.py             # Payroll analytics and CSV download
│   └── settings.py            # System health diagnostics & display options
│
├── services/                  # Business Logic & Database Layer
│   ├── __init__.py
│   ├── auth_service.py        # Password hashing & admin retrieval
│   ├── employee_service.py    # Parameterized SQL queries & validation
│   ├── department_service.py  # Department queries & integrity verification
│   └── report_service.py      # Aggregations, metrics, CSV formula sanitizer
│
├── templates/                 # Jinja2 HTML Templates
│   ├── base.html              # Core SaaS admin panel layout & navigation
│   ├── dashboard.html         # Live KPI dashboard & charts
│   ├── auth/
│   │   └── login.html         # Administrator login form
│   ├── employees/
│   │   ├── list.html          # Paginated roster with search & filters
│   │   ├── add.html           # New employee registration form
│   │   ├── edit.html          # Employee update form
│   │   └── detail.html        # Comprehensive profile card
│   ├── departments/
│   │   └── list.html          # Department cards & management modals
│   ├── reports/
│   │   └── index.html         # Payroll analytics & CSV export tools
│   ├── settings/
│   │   └── index.html         # Diagnostics & preferences
│   └── errors/
│       ├── 404.html           # Not found page
│       ├── 500.html           # Server error page
│       └── db_error.html      # MySQL offline setup guide
│
├── static/                    # Static Assets
│   ├── css/
│   │   └── style.css          # Modern SaaS CSS design system
│   └── js/
│       ├── app.js             # Mobile drawer, modal handling, alerts
│       └── charts.js          # Chart.js initialization
│
└── tests/                     # Automated Test Suite (pytest)
    ├── __init__.py
    ├── conftest.py            # Pytest fixtures and test clients
    ├── test_validation.py     # Validation rules and CSV sanitizer tests
    ├── test_services.py       # Department rules and allowlist tests
    └── test_routes.py         # Route guards and HTTP status code tests
```

---

## Database Schema

```
departments
├── id (INT, PK, AUTO_INCREMENT)
├── name (VARCHAR 100, UNIQUE, NOT NULL)
├── description (VARCHAR 255)
└── created_at (TIMESTAMP)

employees
├── id (INT, PK, AUTO_INCREMENT)
├── full_name (VARCHAR 100, NOT NULL)
├── email (VARCHAR 150, UNIQUE, NOT NULL)
├── phone (VARCHAR 20)
├── department_id (INT, FK -> departments.id, ON DELETE RESTRICT)
├── job_title (VARCHAR 100, NOT NULL)
├── joining_date (DATE, NOT NULL)
├── salary (DECIMAL 12,2, NOT NULL)
├── status (ENUM 'Active', 'Inactive', DEFAULT 'Active')
├── address (VARCHAR 500)
├── created_at (TIMESTAMP)
└── updated_at (TIMESTAMP)

admins
├── id (INT, PK, AUTO_INCREMENT)
├── username (VARCHAR 50, UNIQUE, NOT NULL)
├── email (VARCHAR 150, UNIQUE, NOT NULL)
├── password_hash (VARCHAR 255, NOT NULL)
├── full_name (VARCHAR 100, NOT NULL)
└── created_at (TIMESTAMP)
```

---

## Step-by-Step Windows & VS Code Setup Guide

### 1. Prerequisites
- **Python 3.10+**: Download from [python.org](https://www.python.org/downloads/) (ensure **"Add Python to PATH"** is checked during installation).
- **MySQL Server**: You can use either:
  - Official **MySQL Community Server & Workbench**: [mysql.com/downloads/](https://dev.mysql.com/downloads/installer/)
  - Or **XAMPP** (includes MySQL / MariaDB with a 1-click start button): [apachefriends.org](https://www.apachefriends.org/)

### 2. Open the Project in VS Code
1. Open Visual Studio Code.
2. Select **File > Open Folder...** and navigate to:
   ```
   C:\Users\claks\.gemini\antigravity\scratch\employee_management_system
   ```
3. Open the integrated terminal (**Terminal > New Terminal** or press ``Ctrl + ` ``).

### 3. Create and Activate a Python Virtual Environment
Run the following in PowerShell:
```powershell
python -m venv .venv
```

Activate the virtual environment:
```powershell
.venv\Scripts\Activate.ps1
```
*(If PowerShell displays an execution policy error, see the [Troubleshooting](#troubleshooting-common-issues-on-windows) section).*

### 4. Install Required Packages
```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 5. Setup and Configure MySQL
1. Ensure your MySQL server is running (via MySQL Windows Service, MySQL Workbench, or the XAMPP Control Panel).
2. Note your MySQL port (default is `3306`), username (typically `root`), and password.

### 6. Configure Environment Variables (.env)
A default `.env` file is included. Open `.env` in VS Code and adjust your database password if necessary:
```ini
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_actual_mysql_password
DB_NAME=employee_db

SECRET_KEY=enter-a-random-secure-string-here
FLASK_APP=app.py
FLASK_ENV=development
FLASK_DEBUG=1

ITEMS_PER_PAGE=10
CURRENCY_SYMBOL=$
```

### 7. Seed Starter Departments and Sample Employees
Run the automated seeder script:
```powershell
python seed.py
```
This script will:
- Create the `employee_db` database and all required tables.
- Seed the default administrator account:
  - **Username**: `admin`
  - **Password**: `Admin@Password123`
- Seed 6 starter departments (Engineering, HR, Marketing, Finance, Sales, Operations).
- Seed 13 realistic employee records with varied dates, salaries, and statuses.

### 8. Launch the Flask Server
Start the local development server:
```powershell
python app.py
```
Or via the Flask CLI:
```powershell
flask run
```

### 9. Access the Application
Open your web browser and navigate to:
```
http://127.0.0.1:5000
```
Log in using:
- **Username**: `admin`
- **Password**: `Admin@Password123`

---

## Running Automated Tests

The application includes comprehensive automated unit and integration tests using `pytest`:

```powershell
python -m pytest tests/ -v
```

All **56 automated unit and integration tests** run in under 1 second, validating:
- **Employee CRUD Operations**: Full Create, Read, Update, and Delete endpoints and service operations.
- **Form Data Validation**: Server-side checks for required fields, email format, phone numbers, date boundaries, status enums, non-negative/maximum salary bounds, and text length limits.
- **Duplicate Email Prevention**: Blocks duplicate emails on creation and updates while permitting employees to retain their own email when updating other attributes.
- **Search & Filtering**: Keyword search across name, email, job title, and numeric ID; filtering by department, status, and date range.
- **Missing Records & Error Handling**: Graceful 404 responses for non-existent employee detail and edit views, and safe flash redirects when deleting missing records.
- **Department Management**: Department creation, renaming, and referential deletion protection preventing removal of departments with active staff.
- **Security & Data Protection**: CSV Formula Injection sanitization, sorting allowlist protection, CSRF token verification, and session authentication guards.
- **Dashboard & Analytics**: Dynamic calculations for metrics and Chart.js datasets, with robust empty-database resilience.

---

## Security and Data Protection

- **Parameterized Queries**: All database queries use parameterized placeholders (`%s`) to prevent SQL Injection.
- **Sorting Allowlist**: Sorting columns and directions are validated against strict Python allowlists before constructing queries.
- **CSRF Tokens**: All state-changing forms (`POST`) require valid CSRF tokens provided by `Flask-WTF`.
- **Password Hashing**: Passwords are never stored in plaintext; they are hashed using Werkzeug's `scrypt` implementation.
- **Session Protection**: Cookies are configured with `HttpOnly` and `SameSite='Lax'` flags.
- **CSV Formula Sanitization**: Prepends single quotes to user-controlled values starting with `=`, `+`, `-`, or `@` to neutralize spreadsheet execution vulnerabilities.

---

## Troubleshooting Common Issues on Windows

### 1. PowerShell Script Execution Policy Error
**Symptom**: `.venv\Scripts\Activate.ps1 cannot be loaded because running scripts is disabled on this system.`
**Solution**: Run this command in PowerShell to permit script activation for the current session:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

### 2. MySQL Connection Refused (Error 2003 / 10061)
**Symptom**: `Can't connect to MySQL server on 'localhost:3306' (10061)`
**Solution**:
1. Check that MySQL service is running:
   - Press `Win + R`, type `services.msc`, and look for `MySQL` or `MySQL80`. Click **Start**.
   - If using XAMPP, open the XAMPP Control Panel and click **Start** next to MySQL.
2. Verify that port 3306 is not blocked by Windows Firewall or another application.

### 3. Access Denied for User 'root'@'localhost' (Error 1045)
**Symptom**: `Access denied for user 'root'@'localhost' (using password: YES)`
**Solution**:
1. Open `.env` and verify that `DB_PASSWORD` matches the password set when MySQL was installed.
2. If your local MySQL `root` account has no password, set `DB_PASSWORD=` (leave it blank).

### 4. Port 5000 is Already in Use
**Symptom**: `OSError: [WinError 10048] Only one usage of each socket address is normally permitted`
**Solution**: Launch the Flask application on an alternative port:
```powershell
$env:PORT="5001"
python app.py
```
Then visit `http://127.0.0.1:5001`.

---

## Portfolio & Demonstration Checklist

- [x] Full End-to-End Application (No static mockups).
- [x] Real MySQL Schema with Foreign Keys, Constraints, and Indexes.
- [x] Connection Pooling and Context Managers.
- [x] Clean Service-Oriented Backend Architecture.
- [x] Responsive SaaS Dashboard with Chart.js.
- [x] Full CRUD on Employees with Server-Side Search, Filter, Sort, & Pagination.
- [x] Department Management with Business Rule Protection against Orphaned Records.
- [x] CSV Reporting with Formula Injection Sanitization.
- [x] Automated Test Suite passing 100% of tests.
