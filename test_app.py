import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from models import db, User, Prediction, Alert

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


class TestAlertStatusLock:
    """Ensure resolved alerts are immutable"""

    def test_resolved_alert_cannot_change_status(self, client, app):
        """Resolved alerts should not transition to another status"""
        with app.app_context():
            user = User(username='cguser', email='cg@example.com', role='coast_guard')
            user.set_password('password123')
            db.session.add(user)
            db.session.flush()

            prediction = Prediction(
                user_id=user.id,
                image_filename='sample.jpg',
                image_path='uploads/sample.jpg',
                prediction_label='Oil Spill',
                confidence_score=0.91,
                raw_prediction_value=0.91,
                processing_time=0.1
            )
            db.session.add(prediction)
            db.session.flush()

            alert = Alert(
                prediction_id=prediction.id,
                location_label='Test Zone',
                severity='high',
                status='Resolved'
            )
            db.session.add(alert)
            db.session.commit()
            alert_id = alert.id

        client.post('/login', data={
            'email': 'cg@example.com',
            'password': 'password123'
        })

        response = client.post(
            f'/api/alerts/{alert_id}/status',
            json={'status': 'In Progress'}
        )
        assert response.status_code == 409

        response = client.post(
            f'/api/alerts/{alert_id}/acknowledge',
            json={'notes': 'Trying to acknowledge again'}
        )
        assert response.status_code == 409

        with app.app_context():
            persisted_alert = Alert.query.get(alert_id)
            assert persisted_alert.status == 'Resolved'

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
