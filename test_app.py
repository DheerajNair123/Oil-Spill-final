import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from models import db, User, Prediction

@pytest.fixture
def app():
    """Create and configure a test app instance"""
    app, _ = create_app('testing')
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """A test client for the app"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test CLI runner for the app's CLI commands"""
    return app.test_cli_runner()

class TestAuthentication:
    """Test user authentication"""
    
    def test_register_user(self, client):
        """Test user registration"""
        response = client.post('/register', data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Sign in here' in response.data
    
    def test_login_user(self, client, app):
        """Test user login"""
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
        
        response = client.post('/login', data={
            'email': 'test@example.com',
            'password': 'password123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Dashboard' in response.data
    
    def test_logout_user(self, client, app):
        """Test user logout"""
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
        
        # Login first
        client.post('/login', data={
            'email': 'test@example.com',
            'password': 'password123'
        })
        
        # Then logout
        response = client.get('/logout', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'logged out' in response.data

class TestDashboard:
    """Test dashboard functionality"""
    
    def test_dashboard_requires_login(self, client):
        """Test that dashboard requires login"""
        response = client.get('/dashboard')
        assert response.status_code == 302  # Redirect to login
    
    def test_dashboard_access(self, client, app):
        """Test accessing dashboard when logged in"""
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
        
        client.post('/login', data={
            'email': 'test@example.com',
            'password': 'password123'
        })
        
        response = client.get('/dashboard')
        assert response.status_code == 200
        assert b'Dashboard' in response.data

class TestUserProfile:
    """Test user profile"""
    
    def test_view_profile(self, client, app):
        """Test viewing user profile"""
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
        
        client.post('/login', data={
            'email': 'test@example.com',
            'password': 'password123'
        })
        
        response = client.get('/profile')
        assert response.status_code == 200
        assert b'testuser' in response.data

class TestAPIs:
    """Test API endpoints"""
    
    def test_model_stats_api(self, client):
        """Test model stats API"""
        response = client.get('/api/model-stats')
        assert response.status_code == 200
        data = response.get_json()
        assert 'total_predictions' in data
        assert 'accuracy' in data
    
    def test_api_predict_no_auth(self, client):
        """Test that API predict requires authentication"""
        response = client.post('/api/predict')
        assert response.status_code == 401

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
