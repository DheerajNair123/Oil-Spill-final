from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import uuid

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication and tracking"""
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='coast_guard')  # 'coast_guard', 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    predictions = db.relationship('Prediction', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password"""
        return check_password_hash(self.password_hash, password)
    
    def get_accuracy(self):
        """Calculate user's prediction accuracy"""
        predictions = self.predictions
        if not predictions:
            return None
        
        total = len(predictions)
        correct = sum(1 for p in predictions if p.feedback is True)
        return round((correct / total) * 100, 2) if total > 0 else 0

    def is_admin(self):
        return self.role == 'admin'

    def is_coast_guard(self):
        return self.role in ('coast_guard', 'user')
    
    def __repr__(self):
        return f'<User {self.username}>'


class Prediction(db.Model):
    """Model to store prediction records"""
    __tablename__ = 'predictions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    image_filename = db.Column(db.String(255), nullable=False)
    image_path = db.Column(db.String(500), nullable=False)
    prediction_label = db.Column(db.String(50), nullable=False)  # 'Oil Spill' or 'No Oil Spill'
    confidence_score = db.Column(db.Float, nullable=False)
    raw_prediction_value = db.Column(db.Float, nullable=False)  # 0-1 value from model
    feedback = db.Column(db.Boolean, nullable=True)  # True=correct, False=incorrect, None=no feedback
    feedback_timestamp = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    processed = db.Column(db.Boolean, default=False)
    processing_time = db.Column(db.Float, nullable=True)  # in seconds
    
    def __repr__(self):
        return f'<Prediction {self.id}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'username': self.user.username,
            'image_filename': self.image_filename,
            'prediction': self.prediction_label,
            'confidence': self.confidence_score,
            'feedback': self.feedback,
            'created_at': self.created_at.isoformat(),
            'processing_time': self.processing_time
        }


class Alert(db.Model):
    """Incident alert generated when the model detects an oil spill"""
    __tablename__ = 'alerts'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    prediction_id = db.Column(db.String(36), db.ForeignKey('predictions.id'), nullable=True, unique=True)
    location_label = db.Column(db.String(255), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    severity = db.Column(db.String(20), nullable=False, default='medium')
    status = db.Column(db.String(30), nullable=False, default='New')
    image_snapshot = db.Column(db.String(500), nullable=True)
    detection_time = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    acknowledged_at = db.Column(db.DateTime, nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    prediction = db.relationship('Prediction', backref=db.backref('alert', uselist=False), lazy=True)
    actions = db.relationship('AlertAction', backref='alert', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'prediction_id': self.prediction_id,
            'location_label': self.location_label,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'severity': self.severity,
            'status': self.status,
            'image_snapshot': self.image_snapshot,
            'detection_time': self.detection_time.isoformat() if self.detection_time else None,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'actions': [action.to_dict() for action in self.actions]
        }


class AlertAction(db.Model):
    """Actions taken by coast guard personnel or admins"""
    __tablename__ = 'alert_actions'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_id = db.Column(db.String(36), db.ForeignKey('alerts.id'), nullable=False, index=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    action_taken = db.Column(db.String(120), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('User', backref=db.backref('alert_actions', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'alert_id': self.alert_id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'action_taken': self.action_taken,
            'notes': self.notes,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
        }


class ModelMetrics(db.Model):
    """Track model performance metrics"""
    __tablename__ = 'model_metrics'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_version = db.Column(db.String(50), nullable=False)
    model_accuracy = db.Column(db.Float, nullable=True)
    total_predictions = db.Column(db.Integer, default=0)
    oil_spill_count = db.Column(db.Integer, default=0)
    no_oil_spill_count = db.Column(db.Integer, default=0)
    average_confidence = db.Column(db.Float, nullable=True)
    user_feedback_accuracy = db.Column(db.Float, nullable=True)
    feedback_count = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ModelMetrics {self.model_version}>'


class APIKey(db.Model):
    """API keys for programmatic access"""
    __tablename__ = 'api_keys'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    key = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    last_used = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    
    def is_valid(self):
        """Check if API key is still valid"""
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        return True
    
    def __repr__(self):
        return f'<APIKey {self.name}>'


class AuditLog(db.Model):
    """Audit trail for important actions"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(50), nullable=False)
    resource_id = db.Column(db.String(36), nullable=True)
    details = db.Column(db.JSON, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<AuditLog {self.action}>'
