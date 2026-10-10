"""
Database Management Module
Handles MySQL connection pooling, context management, error wrapping,
and connection diagnostics using mysql-connector-python.
"""
import logging
from contextlib import contextmanager
from pathlib import Path
import mysql.connector
from mysql.connector import errorcode, pooling
from flask import g, current_app

logger = logging.getLogger(__name__)

# Global connection pool instance
_connection_pool = None


class DatabaseError(Exception):
    """Base exception for database operations."""
    pass


class DatabaseConnectionError(DatabaseError):
    """Raised when connecting to MySQL fails."""
    pass


def _get_setting(cfg, key, default=None):
    """Safely retrieves a configuration key from either Flask Config or Config class."""
    if hasattr(cfg, 'get') and callable(getattr(cfg, 'get')):
        return cfg.get(key, default)
    return getattr(cfg, key, default)


def _clean_sql_statements(sql_text, skip_db_commands=False):
    """
    Strips SQL comment lines (-- and empty lines) and splits by semicolon into valid runnable statements.
    If skip_db_commands is True, filters out CREATE DATABASE and USE statements.
    """
    lines = []
    for line in sql_text.splitlines():
        trimmed = line.strip()
        if not trimmed or trimmed.startswith('--'):
            continue
        lines.append(line)
    clean_sql = '\n'.join(lines)
    stmts = [s.strip() for s in clean_sql.split(';') if s.strip()]
    if skip_db_commands:
        stmts = [
            s for s in stmts
            if not (s.upper().startswith('CREATE DATABASE') or s.upper().startswith('USE '))
        ]
    return stmts


def _build_ssl_config(cfg):
    """Extracts SSL/TLS connection options from configuration for mysql-connector-python."""
    ssl_opts = {}
    ssl_ca = _get_setting(cfg, 'DB_SSL_CA', None)
    ssl_disabled = _get_setting(cfg, 'DB_SSL_DISABLED', False)
    if ssl_disabled:
        ssl_opts['ssl_disabled'] = True
    elif ssl_ca:
        ssl_opts['ssl_ca'] = ssl_ca
    return ssl_opts



def get_db_pool():
    """
    Initializes or returns the existing MySQL connection pool.
    Uses current Flask app config or default environment settings.
    """
    global _connection_pool
    if _connection_pool is not None:
        return _connection_pool

    from config import get_config
    cfg = current_app.config if current_app else get_config()

    try:
        pool_config = {
            'pool_name': _get_setting(cfg, 'DB_POOL_NAME', 'ems_pool'),
            'pool_size': int(_get_setting(cfg, 'DB_POOL_SIZE', 5)),
            'host': _get_setting(cfg, 'DB_HOST', 'localhost'),
            'port': int(_get_setting(cfg, 'DB_PORT', 3306)),
            'user': _get_setting(cfg, 'DB_USER', 'root'),
            'password': _get_setting(cfg, 'DB_PASSWORD', ''),
            'database': _get_setting(cfg, 'DB_NAME', 'employee_db'),
            'autocommit': False,
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci',
            'connect_timeout': 5,
        }
        pool_config.update(_build_ssl_config(cfg))
        _connection_pool = pooling.MySQLConnectionPool(**pool_config)
        logger.info("MySQL connection pool '%s' initialized.", pool_config['pool_name'])
        return _connection_pool
    except mysql.connector.Error as err:
        logger.error("Failed to initialize MySQL connection pool: %s", err)
        _connection_pool = None
        raise DatabaseConnectionError(f"Database connection failed: {err.msg}") from err


def get_db_connection():
    """
    Retrieves a connection from the pool.
    When running in a Flask request context, stores it in Flask's 'g' object
    for reuse and automatic teardown.
    """
    # Check if we are inside an active Flask request context
    if current_app:
        if 'db_conn' not in g or g.db_conn is None or not g.db_conn.is_connected():
            try:
                pool = get_db_pool()
                g.db_conn = pool.get_connection()
            except mysql.connector.Error as err:
                logger.error("Unable to get connection from pool: %s", err)
                raise DatabaseConnectionError(f"Could not connect to MySQL server: {err.msg}") from err
        return g.db_conn

    # Outside Flask application context (CLI, seed scripts, etc.)
    try:
        pool = get_db_pool()
        return pool.get_connection()
    except mysql.connector.Error as err:
        logger.error("Unable to get standalone connection: %s", err)
        raise DatabaseConnectionError(f"Could not connect to MySQL server: {err.msg}") from err


def close_db_connection(e=None):
    """Closes the current request's database connection (registered with teardown_appcontext)."""
    conn = g.pop('db_conn', None)
    if conn is not None and conn.is_connected():
        try:
            conn.close()
        except mysql.connector.Error as err:
            logger.warning("Error closing database connection: %s", err)


@contextmanager
def get_db_cursor(commit=False, dictionary=True):
    """
    Context manager that yields a cursor.
    Safely commits on success if commit=True, rolls back on error,
    and guarantees cursor cleanup.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=dictionary)
    try:
        yield cursor
        if commit:
            conn.commit()
    except mysql.connector.Error as err:
        conn.rollback()
        logger.error("Database query failed [%s]: %s", err.errno, err.msg)
        raise DatabaseError(f"Database error: {err.msg}") from err
    finally:
        cursor.close()
        # If not inside a Flask request, return connection to pool immediately
        if not current_app and conn.is_connected():
            conn.close()


def check_db_connection():
    """
    Tests whether the MySQL database is reachable and the required tables exist.
    Returns:
        tuple (bool is_healthy, dict details)
    """
    from config import get_config
    cfg = current_app.config if current_app else get_config()
    
    host = _get_setting(cfg, 'DB_HOST', 'localhost')
    port = _get_setting(cfg, 'DB_PORT', 3306)
    user = _get_setting(cfg, 'DB_USER', 'root')
    password = _get_setting(cfg, 'DB_PASSWORD', '')
    database = _get_setting(cfg, 'DB_NAME', 'employee_db')

    conn_params = {
        'host': host,
        'port': int(port),
        'user': user,
        'password': password,
        'database': database,
        'connect_timeout': 3,
    }
    conn_params.update(_build_ssl_config(cfg))

    try:
        conn = mysql.connector.connect(**conn_params)
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION();")
        version = cursor.fetchone()[0]
        
        cursor.execute("SHOW TABLES;")
        tables = [t[0] for t in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        return True, {
            'status': 'Connected',
            'version': version,
            'database': database,
            'host': f"{host}:{port}",
            'tables': tables,
            'tables_count': len(tables),
            'tables_ready': all(t in tables for t in ['employees', 'departments', 'admins'])
        }
    except mysql.connector.Error as err:
        return False, {
            'status': 'Disconnected',
            'error_code': getattr(err, 'errno', 'UNKNOWN'),
            'error_message': getattr(err, 'msg', str(err)),
            'host': f"{host}:{port}",
            'database': database,
            'troubleshooting': (
                "Ensure MySQL Server is running and reachable. "
                "Verify DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, and DB_NAME in your environment variables."
            )
        }


def init_db(schema_file=None):
    """
    Executes schema.sql against the configured database.
    Connects directly to the target database first to support cloud-hosted MySQL
    (such as Aiven, AWS RDS, or Render) without requiring root/super privileges.
    Falls back to creating the database only if missing in local environments.
    """
    from config import get_config
    cfg = current_app.config if current_app else get_config()

    host = _get_setting(cfg, 'DB_HOST', 'localhost')
    port = int(_get_setting(cfg, 'DB_PORT', 3306))
    user = _get_setting(cfg, 'DB_USER', 'root')
    password = _get_setting(cfg, 'DB_PASSWORD', '')
    db_name = _get_setting(cfg, 'DB_NAME', 'employee_db')
    
    if schema_file is None:
        schema_file = Path(__file__).resolve().parent / 'schema.sql'
    
    schema_path = Path(schema_file)
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found at {schema_path}")
    
    with open(schema_path, 'r', encoding='utf-8-sig') as f:
        schema_sql = f.read()

    # Filter out CREATE DATABASE and USE statements so execution is 100% portable
    statements = _clean_sql_statements(schema_sql, skip_db_commands=True)

    base_params = {
        'host': host,
        'port': port,
        'user': user,
        'password': password,
        'connect_timeout': 5,
    }
    base_params.update(_build_ssl_config(cfg))

    conn = None
    # Step 1: Connect directly to the specified database (preferred for cloud databases)
    try:
        conn = mysql.connector.connect(database=db_name, **base_params)
    except mysql.connector.Error as err:
        err_code = getattr(err, 'errno', None)
        # If database does not exist (1049 ER_BAD_DB_ERROR), attempt creation (local dev)
        if err_code == errorcode.ER_BAD_DB_ERROR:
            logger.info("Database '%s' does not exist yet. Attempting to create it...", db_name)
            try:
                server_conn = mysql.connector.connect(**base_params)
                server_cursor = server_conn.cursor()
                server_cursor.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
                )
                server_conn.commit()
                server_cursor.close()
                server_conn.close()
                conn = mysql.connector.connect(database=db_name, **base_params)
            except mysql.connector.Error as root_err:
                raise DatabaseConnectionError(
                    f"Could not connect to or create database '{db_name}'. "
                    f"For cloud databases (e.g., Aiven), ensure the database is created in your provider console: {root_err.msg}"
                ) from root_err
        else:
            raise DatabaseConnectionError(f"Could not connect to MySQL database '{db_name}': {err.msg}") from err

    # Step 2: Execute table creation statements (CREATE TABLE IF NOT EXISTS)
    try:
        cursor = conn.cursor()
        for stmt in statements:
            cursor.execute(stmt)
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Database '%s' schema initialized successfully with %d statements.", db_name, len(statements))
    except mysql.connector.Error as err:
        if conn and conn.is_connected():
            conn.close()
        raise DatabaseError(f"Error executing schema statements: {err.msg}") from err

