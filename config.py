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


class Config:
    """Base Configuration Class."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-insecure-secret-key-change-me')
    
    # Database Settings
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = int(os.environ.get('DB_PORT', 3306))
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
    DB_NAME = os.environ.get('DB_NAME', 'employee_db')
    
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


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}


def get_config():
    """Retrieve the active configuration based on FLASK_ENV or FLASK_CONFIG."""
    env_name = os.environ.get('FLASK_ENV', os.environ.get('FLASK_CONFIG', 'development')).lower()
    return config_by_name.get(env_name, DevelopmentConfig)
