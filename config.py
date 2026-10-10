"""
Application Configuration Module
Loads configuration settings from environment variables with safe defaults.
"""
import os
from pathlib import Path
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv

# Base directory of the application
BASE_DIR = Path(__file__).resolve().parent

# Load .env file from the project root if it exists
dotenv_path = BASE_DIR / '.env'
if dotenv_path.exists():
    load_dotenv(dotenv_path)


INSECURE_SECRET_KEYS = {
    'dev-insecure-secret-key-change-me',
    'change-this-to-a-secure-random-secret-key-in-production',
    'enter-a-random-secure-string-here',
    'secret',
    'password',
    'default',
    'your-secret-key-here',
}


def _clean_env(val):
    """Strips leading/trailing whitespace and surrounding quotes from environment variables."""
    if val is None:
        return None
    s = str(val).strip().strip("'\"")
    return s if s else None


def is_production_environment():
    """
    Detects whether the application is running in a cloud or production environment.
    Automatically identifies Render, Railway, Heroku, or explicit production flags.
    """
    env = (_clean_env(os.environ.get('FLASK_ENV')) or _clean_env(os.environ.get('FLASK_CONFIG')) or '').lower()
    if env == 'production':
        return True
    if (_clean_env(os.environ.get('ENVIRONMENT')) or '').lower() == 'production':
        return True
    # Render cloud platform automatically sets RENDER=true
    if (_clean_env(os.environ.get('RENDER')) or '').lower() == 'true':
        return True
    return False


def _resolve_database_config(is_production=None):
    """
    Resolves MySQL connection settings from either individual environment variables
    (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, or common cloud provider names like MYSQLHOST)
    or a unified connection URL (DATABASE_URL, MYSQL_URL, JAWSDB_URL, CLEARDB_DATABASE_URL).
    
    In local development (is_production=False), missing values safely fall back to local defaults:
    localhost:3306, user 'root', database 'employee_db'.
    In production (is_production=True), missing values remain None so they can be explicitly validated.
    """
    if is_production is None:
        is_production = is_production_environment()

    db_url = _clean_env(
        os.environ.get('DATABASE_URL')
        or os.environ.get('MYSQL_URL')
        or os.environ.get('JAWSDB_URL')
        or os.environ.get('CLEARDB_DATABASE_URL')
    )
    _p = None
    if db_url:
        try:
            _p = urlparse(db_url)
        except Exception:
            _p = None

    raw_host = _clean_env(
        os.environ.get('DB_HOST')
        or os.environ.get('MYSQLHOST')
        or os.environ.get('MYSQL_HOST')
        or (_p.hostname if _p and _p.hostname else None)
    )

    raw_port = _clean_env(
        os.environ.get('DB_PORT')
        or os.environ.get('MYSQLPORT')
        or os.environ.get('MYSQL_PORT')
        or (str(_p.port) if _p and _p.port else None)
    )

    raw_user = _clean_env(
        os.environ.get('DB_USER')
        or os.environ.get('MYSQLUSER')
        or os.environ.get('MYSQL_USER')
        or (_p.username if _p and _p.username else None)
    )

    raw_pass = _clean_env(
        os.environ.get('DB_PASSWORD')
        or os.environ.get('MYSQLPASSWORD')
        or os.environ.get('MYSQL_PASSWORD')
        or (unquote(_p.password) if _p and _p.password else None)
    )

    raw_name = _clean_env(
        os.environ.get('DB_NAME')
        or os.environ.get('MYSQLDATABASE')
        or os.environ.get('MYSQL_DATABASE')
        or (_p.path.lstrip('/') if _p and _p.path else None)
    )

    if is_production:
        # In production, do not fall back to localhost
        host = raw_host
        port = int(raw_port) if raw_port and raw_port.isdigit() else 3306
        user = raw_user
        password = raw_pass or ''
        dbname = raw_name
    else:
        # In local development / testing, use safe local defaults
        host = raw_host or 'localhost'
        port = int(raw_port) if raw_port and raw_port.isdigit() else 3306
        user = raw_user or 'root'
        password = raw_pass or ''
        dbname = raw_name or 'employee_db'

    return host, port, user, password, dbname


class Config:
    """Base Configuration Class."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-insecure-secret-key-change-me')
    
    # Database Settings (supports DB_* vars or DATABASE_URL / MYSQL_URL)
    _host, _port, _user, _pass, _name = _resolve_database_config(is_production=False)
    DB_HOST = _host
    DB_PORT = _port
    DB_USER = _user
    DB_PASSWORD = _pass
    DB_NAME = _name
    
    # SSL/TLS Database Settings (for managed cloud databases e.g., Aiven, AWS RDS)
    DB_SSL_CA = os.environ.get('DB_SSL_CA', None)
    DB_SSL_DISABLED = os.environ.get('DB_SSL_DISABLED', 'false').lower() in ('true', '1', 'yes')

    # Connection Pool Settings
    DB_POOL_NAME = 'ems_pool'
    DB_POOL_SIZE = int(os.environ.get('DB_POOL_SIZE', 5))
    
    # Application Preferences
    ITEMS_PER_PAGE = int(os.environ.get('ITEMS_PER_PAGE', 10))
    CURRENCY_SYMBOL = os.environ.get('CURRENCY_SYMBOL', '$')
    
    # Security & Sessions
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600 * 4  # 4 hours
    WTF_CSRF_ENABLED = True


class DevelopmentConfig(Config):
    """Development Configuration."""
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    """Testing Configuration."""
    DEBUG = False
    TESTING = True
    WTF_CSRF_ENABLED = False
    DB_NAME = os.environ.get('TEST_DB_NAME', 'employee_db_test')


class ProductionConfig(Config):
    """Production Configuration."""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    
    # In production, fallback keys are rejected; SECRET_KEY must be provided via environment
    SECRET_KEY = os.environ.get('SECRET_KEY', '')

    @classmethod
    def get_database_settings(cls):
        """Resolves database settings specifically for production mode."""
        return _resolve_database_config(is_production=True)

    @classmethod
    def validate_production(cls, raise_for_db=True):
        """
        Validates that critical production environment variables are properly configured.
        Raises ValueError with clear, safe explanations if SECRET_KEY or hosted DB variables are missing.
        Never discloses passwords or secrets.
        """
        # 1. Validate SECRET_KEY
        secret = os.environ.get('SECRET_KEY', '').strip()
        if not secret or secret in INSECURE_SECRET_KEYS or len(secret) < 16:
            raise ValueError(
                "Production security violation: FLASK_ENV=production requires a strong, random SECRET_KEY "
                "set via the SECRET_KEY environment variable (minimum 16 characters). "
                "The development fallback key is strictly disallowed in production. "
                "Generate a cryptographically secure key with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        cls.SECRET_KEY = secret

        # 2. Validate Hosted Database Settings
        db_host, db_port, db_user, db_pass, db_name = cls.get_database_settings()
        missing = []
        if not db_host or db_host.lower() in ('localhost', '127.0.0.1', '::1'):
            missing.append("DB_HOST (cannot be 'localhost' in production)")
        if not db_user:
            missing.append("DB_USER")
        if not db_name:
            missing.append("DB_NAME")

        if missing and raise_for_db:
            raise ValueError(
                f"Production database configuration error: Missing required hosted database setting(s): {', '.join(missing)}. "
                "In cloud production (such as Render), MySQL runs externally. "
                "Please configure DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, and DB_NAME "
                "(or provide a complete connection URI in DATABASE_URL / MYSQL_URL) "
                "in your Render service Environment tab."
            )

        if db_host:
            cls.DB_HOST = db_host
            cls.DB_PORT = db_port
            cls.DB_USER = db_user or ''
            cls.DB_PASSWORD = db_pass or ''
            cls.DB_NAME = db_name or ''
        return True


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}


def get_config():
    """Retrieve the active configuration based on FLASK_ENV, FLASK_CONFIG, or cloud environment."""
    env_name = _clean_env(os.environ.get('FLASK_ENV') or os.environ.get('FLASK_CONFIG'))
    if env_name:
        env_name = env_name.lower()
    else:
        # Automatic platform detection: if on Render or production environment, use production config
        env_name = 'production' if is_production_environment() else 'development'

    config_cls = config_by_name.get(env_name, DevelopmentConfig)
    if issubclass(config_cls, ProductionConfig):
        # Validate SECRET_KEY (non-fatal for DB at factory time so web UI can render friendly diagnostic)
        config_cls.validate_production(raise_for_db=False)
    return config_cls


