"""
Pytest Fixtures Configuration
Sets up testing application context, mock session, and Flask test client.
"""
import pytest
from app import create_app
from config import TestingConfig


@pytest.fixture
def app():
    """Provides test-configured Flask application."""
    test_app = create_app(TestingConfig)
    return test_app


@pytest.fixture
def client(app):
    """Provides unauthenticated test client."""
    return app.test_client()


@pytest.fixture
def auth_client(app):
    """Provides an authenticated test client with an active administrator session."""
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['username'] = 'admin'
        sess['full_name'] = 'Administrator'
        sess['email'] = 'admin@ems.local'
    return client
