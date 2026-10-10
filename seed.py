"""
Database Seeding Script
Initializes tables and seeds starter departments, realistic sample employees,
and an administrator account for local development and demonstration.

Usage:
    python seed.py
    python seed.py --admin-only
    python seed.py --reset
"""
import sys
import argparse
from datetime import date, timedelta
from decimal import Decimal
from config import get_config
from db import init_db, get_db_cursor, check_db_connection, DatabaseError
from services.auth_service import create_admin

SAMPLE_DEPARTMENTS = [
    ("Engineering", "Software development, architecture, DevOps, and QA engineering."),
    ("Human Resources", "Talent acquisition, benefits, onboarding, and employee relations."),
    ("Marketing", "Brand management, digital marketing, content, and public relations."),
    ("Finance", "Financial planning, accounting, payroll, and corporate compliance."),
    ("Sales", "Account management, business development, and client partnerships."),
    ("Operations", "Office management, IT infrastructure, and facilities operations.")
]

SAMPLE_EMPLOYEES = [
    {
        "full_name": "Sarah Connor",
        "email": "sarah.connor@example.com",
        "phone": "+1 (555) 234-5678",
        "dept_name": "Engineering",
        "job_title": "Lead Software Architect",
        "joining_date": date.today() - timedelta(days=520),
        "salary": Decimal("115000.00"),
        "status": "Active",
        "address": "104 Tech Boulevard, Suite 300, Austin, TX"
    },
    {
        "full_name": "Alex Mercer",
        "email": "alex.mercer@example.com",
        "phone": "+1 (555) 345-6789",
        "dept_name": "Engineering",
        "job_title": "Senior Backend Developer",
        "joining_date": date.today() - timedelta(days=340),
        "salary": Decimal("95000.00"),
        "status": "Active",
        "address": "742 Evergreen Terrace, Seattle, WA"
    },
    {
        "full_name": "Elena Rostova",
        "email": "elena.rostova@example.com",
        "phone": "+1 (555) 456-7890",
        "dept_name": "Engineering",
        "job_title": "Frontend Engineer",
        "joining_date": date.today() - timedelta(days=120),
        "salary": Decimal("82000.00"),
        "status": "Active",
        "address": "12 Market Street, Apt 4B, San Francisco, CA"
    },
    {
        "full_name": "Marcus Vance",
        "email": "marcus.vance@example.com",
        "phone": "+1 (555) 567-8901",
        "dept_name": "Human Resources",
        "job_title": "HR Director",
        "joining_date": date.today() - timedelta(days=600),
        "salary": Decimal("105000.00"),
        "status": "Active",
        "address": "55 Magnolia Ave, Chicago, IL"
    },
    {
        "full_name": "Chloe Bennett",
        "email": "chloe.bennett@example.com",
        "phone": "+1 (555) 678-9012",
        "dept_name": "Human Resources",
        "job_title": "Talent Acquisition Specialist",
        "joining_date": date.today() - timedelta(days=90),
        "salary": Decimal("68000.00"),
        "status": "Active",
        "address": "890 Pinecrest Way, Denver, CO"
    },
    {
        "full_name": "David Sterling",
        "email": "david.sterling@example.com",
        "phone": "+1 (555) 789-0123",
        "dept_name": "Finance",
        "job_title": "Chief Financial Officer",
        "joining_date": date.today() - timedelta(days=750),
        "salary": Decimal("145000.00"),
        "status": "Active",
        "address": "300 Wall Street, New York, NY"
    },
    {
        "full_name": "Jessica Pearson",
        "email": "jessica.pearson@example.com",
        "phone": "+1 (555) 890-1234",
        "dept_name": "Finance",
        "job_title": "Senior Financial Analyst",
        "joining_date": date.today() - timedelta(days=210),
        "salary": Decimal("88000.00"),
        "status": "Active",
        "address": "45 Liberty Plaza, Boston, MA"
    },
    {
        "full_name": "Liam Gallagher",
        "email": "liam.gallagher@example.com",
        "phone": "+1 (555) 901-2345",
        "dept_name": "Marketing",
        "job_title": "VP of Marketing",
        "joining_date": date.today() - timedelta(days=410),
        "salary": Decimal("112000.00"),
        "status": "Active",
        "address": "21 Beacon Hill Road, Atlanta, GA"
    },
    {
        "full_name": "Maya Lin",
        "email": "maya.lin@example.com",
        "phone": "+1 (555) 012-3456",
        "dept_name": "Marketing",
        "job_title": "Content & SEO Manager",
        "joining_date": date.today() - timedelta(days=160),
        "salary": Decimal("72000.00"),
        "status": "Active",
        "address": "77 Sunset Strip, Los Angeles, CA"
    },
    {
        "full_name": "James Holden",
        "email": "james.holden@example.com",
        "phone": "+1 (555) 123-4567",
        "dept_name": "Sales",
        "job_title": "Enterprise Account Executive",
        "joining_date": date.today() - timedelta(days=300),
        "salary": Decimal("92000.00"),
        "status": "Active",
        "address": "404 Prairie Lane, Dallas, TX"
    },
    {
        "full_name": "Rachel Zane",
        "email": "rachel.zane@example.com",
        "phone": "+1 (555) 234-0987",
        "dept_name": "Sales",
        "job_title": "Sales Development Rep",
        "joining_date": date.today() - timedelta(days=45),
        "salary": Decimal("58000.00"),
        "status": "Active",
        "address": "500 Michigan Ave, Chicago, IL"
    },
    {
        "full_name": "Arthur Pendelton",
        "email": "arthur.pendelton@example.com",
        "phone": "+1 (555) 345-9876",
        "dept_name": "Operations",
        "job_title": "Operations Manager",
        "joining_date": date.today() - timedelta(days=680),
        "salary": Decimal("84000.00"),
        "status": "Active",
        "address": "16 Oakwood Court, Minneapolis, MN"
    },
    {
        "full_name": "Victor Creed",
        "email": "victor.creed@example.com",
        "phone": "+1 (555) 456-8765",
        "dept_name": "Engineering",
        "job_title": "Contract DevOps Engineer",
        "joining_date": date.today() - timedelta(days=400),
        "salary": Decimal("80000.00"),
        "status": "Inactive",
        "address": "12 Elm Street, Portland, OR"
    }
]


def seed_departments():
    """Seeds starter departments if not present."""
    print("-> Seeding departments...")
    created_count = 0
    with get_db_cursor(commit=True) as cursor:
        for name, desc in SAMPLE_DEPARTMENTS:
            cursor.execute("SELECT id FROM departments WHERE name = %s", [name])
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO departments (name, description) VALUES (%s, %s)",
                    [name, desc]
                )
                created_count += 1
    print(f"   Done. Added {created_count} new departments.")


def seed_employees():
    """Seeds sample employee records."""
    print("-> Seeding sample employees...")
    created_count = 0
    with get_db_cursor(commit=True) as cursor:
        # Load department name -> id mapping
        cursor.execute("SELECT id, name FROM departments")
        dept_map = {row['name']: row['id'] for row in cursor.fetchall()}

        for emp in SAMPLE_EMPLOYEES:
            cursor.execute("SELECT id FROM employees WHERE email = %s", [emp['email']])
            if not cursor.fetchone():
                dept_id = dept_map.get(emp['dept_name'])
                cursor.execute("""
                    INSERT INTO employees (full_name, email, phone, department_id,
                                           job_title, joining_date, salary, status, address)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, [
                    emp['full_name'],
                    emp['email'],
                    emp['phone'],
                    dept_id,
                    emp['job_title'],
                    emp['joining_date'],
                    emp['salary'],
                    emp['status'],
                    emp['address']
                ])
                created_count += 1
    print(f"   Done. Added {created_count} sample employees.")


def seed_admin(username="admin", email="admin@ems.local", password="Admin@Password123", full_name="System Administrator"):
    """Seeds a starter administrator account."""
    print(f"-> Seeding administrator account '{username}'...")
    with get_db_cursor() as cursor:
        cursor.execute("SELECT id FROM admins WHERE username = %s OR email = %s", [username, email])
        if cursor.fetchone():
            print(f"   Admin '{username}' already exists. Skipping.")
            return

    success, admin_id, err = create_admin(username, email, password, full_name)
    if success:
        print(f"   Admin '{username}' created successfully!")
        print(f"   Default Login: Username: {username} | Password: {password}")
    else:
        print(f"   Failed to create admin: {err}")


def main():
    parser = argparse.ArgumentParser(description="EMS Database Initializer and Seeder")
    parser.add_argument("--admin-only", action="store_true", help="Only seed the admin user")
    parser.add_argument("--username", default="admin", help="Admin username")
    parser.add_argument("--password", default="Admin@Password123", help="Admin password")
    args = parser.parse_args()

    print("==================================================")
    print("  Employee Management System - Database Seeder   ")
    print("==================================================")

    # 1. Initialize DB Schema
    print("-> Checking and applying database schema...")
    try:
        init_db()
        print("   Database schema verified and up to date.")
    except Exception as e:
        print(f"ERROR: Could not initialize database schema:\n{e}")
        print("\nPlease ensure MySQL is running and your .env file is properly configured.")
        sys.exit(1)

    # 2. Seed Admin
    seed_admin(username=args.username, password=args.password)

    if not args.admin_only:
        # 3. Seed Departments & Employees
        seed_departments()
        seed_employees()

    print("\n[SUCCESS] Seeding completed successfully!")
    print("You can now start the application with: python app.py")


if __name__ == '__main__':
    main()
