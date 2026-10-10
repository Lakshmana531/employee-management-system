"""
Application Configuration Module
Loads configuration settings from environment variables with safe defaults.
"""
import os
from pathlib import Path
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


class Config:
    """Base Configuration Class."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-insecure-secret-key-change-me')
    
    # Database Settings
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = int(os.environ.get('DB_PORT', 3306))
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
    DB_NAME = os.environ.get('DB_NAME', 'employee_db')
    
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
    def validate_production(cls):
        """
        Validates that critical production environment variables are properly configured.
        Raises ValueError if SECRET_KEY is missing, insecure, or too short.
        """
        secret = os.environ.get('SECRET_KEY', '').strip()
        if not secret or secret in INSECURE_SECRET_KEYS or len(secret) < 16:
            raise ValueError(
                "Production security violation: FLASK_ENV=production requires a strong, random SECRET_KEY "
                "set via the SECRET_KEY environment variable (minimum 16 characters). "
                "The development fallback key is strictly disallowed in production. "
                "Generate a cryptographically secure key with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        cls.SECRET_KEY = secret
        return secret


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}


def get_config():
    """Retrieve the active configuration based on FLASK_ENV or FLASK_CONFIG."""
    env_name = os.environ.get('FLASK_ENV', os.environ.get('FLASK_CONFIG', 'development')).lower()
    config_cls = config_by_name.get(env_name, DevelopmentConfig)
    if issubclass(config_cls, ProductionConfig):
        config_cls.validate_production()
    return config_cls

