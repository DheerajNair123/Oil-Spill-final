from flask import Flask, request, render_template_string, url_for, jsonify, redirect, flash, session, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_cors import CORS
from functools import wraps
import os
import json
from datetime import datetime

# Try to import TensorFlow, but don't fail if it's not available
try:
    from tensorflow.keras.models import load_model
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    print("⚠️  TensorFlow not available - predictions will not work")

from config import config
from models import db, User, Prediction, Alert, AlertAction, APIKey, AuditLog
from forms import RegistrationForm, LoginForm, UpdateProfileForm, ChangePasswordForm, AdminCreateUserForm
from utils import PredictionService, ImageProcessing, AnalyticsService, log_audit_action, generate_api_key
from flasgger import Swagger

# Initialize Flask app
def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    login_manager = LoginManager(app)
    CORS(app)
    swagger = Swagger(app)
    
    # Create upload folder
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Load ML model
    model = None
    prediction_service = None
    
    if TENSORFLOW_AVAILABLE:
        try:
            model = load_model(app.config['MODEL_PATH'])
            prediction_service = PredictionService(model)
            print("✓ ML Model loaded successfully")
        except Exception as e:
            print(f"⚠️  Error loading model: {e}")
    else:
        print("⚠️  TensorFlow not available - running without ML model")
    
    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)
    
    @login_manager.unauthorized_handler
    def unauthorized():
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('login'))

    def role_required(*allowed_roles, api=False):
        def decorator(view_func):
            @wraps(view_func)
            def wrapped(*args, **kwargs):
                if not current_user.is_authenticated:
                    if api:
                        return jsonify({'error': 'Authentication required'}), 401
                    return redirect(url_for('login'))

                user_role = getattr(current_user, 'role', 'coast_guard')
                normalized_role = 'coast_guard' if user_role == 'user' else user_role
                if normalized_role not in allowed_roles:
                    if api:
                        return jsonify({'error': 'Forbidden'}), 403
                    flash('You do not have permission to access this page.', 'danger')
                    return redirect(url_for('dashboard'))

                return view_func(*args, **kwargs)

            return wrapped

        return decorator

    def severity_for_prediction(label, confidence):
        if label != 'Oil Spill':
            return 'low'
        if confidence >= 0.85:
            return 'high'
        if confidence >= 0.65:
            return 'medium'
        return 'low'

    def serialize_alert(alert):
        data = alert.to_dict()
        data['prediction_label'] = alert.prediction.prediction_label if alert.prediction else None
        data['confidence_score'] = alert.prediction.confidence_score if alert.prediction else None
        return data

    def create_alert_from_prediction(prediction, pred_result, location_label=None, latitude=None, longitude=None):
        if prediction.prediction_label != 'Oil Spill':
            return None

        existing_alert = Alert.query.filter_by(prediction_id=prediction.id).first()
        if existing_alert:
            return existing_alert

        alert = Alert(
            prediction_id=prediction.id,
            location_label=location_label or 'Unknown location',
            latitude=latitude,
            longitude=longitude,
            severity=severity_for_prediction(prediction.prediction_label, pred_result['confidence']),
            status='New',
            image_snapshot=prediction.image_path,
            detection_time=datetime.utcnow()
        )
        db.session.add(alert)
        db.session.flush()

        first_action = AlertAction(
            alert_id=alert.id,
            user_id=prediction.user_id,
            action_taken='Alert generated',
            notes='Oil spill detected by the ML pipeline.'
        )
        db.session.add(first_action)
        db.session.commit()
        return alert

    def compute_alert_statistics():
        alerts = Alert.query.all()
        resolved = [alert for alert in alerts if alert.status == 'Resolved']
        acknowledged = [alert for alert in alerts if alert.acknowledged_at]

        response_minutes = []
        for alert in alerts:
            first_response = None
            for action in sorted(alert.actions, key=lambda action: action.timestamp):
                if action.action_taken and action.action_taken != 'Alert generated':
                    first_response = action.timestamp
                    break
            if first_response:
                response_minutes.append((first_response - alert.detection_time).total_seconds() / 60)

        severity_counts = {'low': 0, 'medium': 0, 'high': 0}
        for alert in alerts:
            severity_counts[alert.severity] = severity_counts.get(alert.severity, 0) + 1

        average_response_time = round(sum(response_minutes) / len(response_minutes), 2) if response_minutes else 0

        return {
            'total_alerts': len(alerts),
            'open_alerts': sum(1 for alert in alerts if alert.status not in ('Resolved', 'Closed')),
            'acknowledged_alerts': len(acknowledged),
            'resolved_alerts': len(resolved),
            'average_response_time_minutes': average_response_time,
            'severity_counts': severity_counts,
        }
    
    # ======================== AUTHENTICATION ROUTES ========================
    
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """User registration or admin-controlled onboarding"""
        admin_exists = User.query.filter_by(role='admin').first() is not None
        if current_user.is_authenticated and getattr(current_user, 'role', 'coast_guard') != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))

        form = AdminCreateUserForm() if current_user.is_authenticated and current_user.role == 'admin' else RegistrationForm()
        if form.validate_on_submit():
            if isinstance(form, AdminCreateUserForm):
                user = User(
                    username=form.username.data,
                    email=form.email.data,
                    role=form.role.data
                )
            else:
                if admin_exists:
                    flash('Registration is managed by an admin.', 'warning')
                    return redirect(url_for('login'))
                user = User(
                    username=form.username.data,
                    email=form.email.data,
                    role='coast_guard'
                )
            user.set_password(form.password.data)
            
            db.session.add(user)
            db.session.commit()
            
            log_audit_action(user.id, 'REGISTER', 'USER', user.id, 
                           {'email': user.email, 'username': user.username}, 
                           request.remote_addr)
            
            flash('User created successfully.', 'success')
            if current_user.is_authenticated and current_user.role == 'admin':
                return redirect(url_for('manage_users'))
            return redirect(url_for('register'))
        
        return render_template_string(get_registration_template(), form=form)
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """User login"""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            
            if user is None or not user.check_password(form.password.data):
                flash('Invalid email or password.', 'danger')
                return redirect(url_for('login'))
            
            if not user.is_active:
                flash('Your account has been disabled.', 'danger')
                return redirect(url_for('login'))
            
            login_user(user, remember=form.remember_me.data)
            log_audit_action(user.id, 'LOGIN', 'USER', user.id, {}, request.remote_addr)
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        
        return render_template_string(get_login_template(), form=form)

    @app.route('/api/login', methods=['POST'])
    def api_login():
        payload = request.get_json(silent=True) or request.form
        email = payload.get('email')
        password = payload.get('password')

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        user = User.query.filter_by(email=email).first()
        if user is None or not user.check_password(password):
            return jsonify({'error': 'Invalid email or password'}), 401

        if not user.is_active:
            return jsonify({'error': 'Account is disabled'}), 403

        login_user(user, remember=bool(payload.get('remember_me')))
        log_audit_action(user.id, 'LOGIN', 'USER', user.id, {}, request.remote_addr)
        return jsonify({'message': 'Login successful', 'role': user.role, 'redirect': url_for('admin_panel') if user.role == 'admin' else url_for('coast_guard_dashboard')})

    @app.route('/api/logout', methods=['POST'])
    @login_required
    def api_logout():
        user_id = current_user.id
        logout_user()
        log_audit_action(user_id, 'LOGOUT', 'USER', user_id, {}, request.remote_addr)
        return jsonify({'message': 'Logout successful'})
    
    @app.route('/logout')
    @login_required
    def logout():
        """User logout"""
        user_id = current_user.id
        logout_user()
        log_audit_action(user_id, 'LOGOUT', 'USER', user_id, {}, request.remote_addr)
        flash('You have been logged out.', 'info')
        return redirect(url_for('login'))

    @app.route('/uploads/<path:filename>')
    @login_required
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    
    # ======================== PREDICTION ROUTES ========================
    
    @app.route('/', methods=['GET', 'POST'])
    @login_required
    def index():
        """Main prediction page"""
        if model is None:
            return "Error: Model not loaded", 500
        
        result = None
        if request.method == 'POST':
            file = request.files.get('image')
            if file and file.filename:
                try:
                    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    location_label = request.form.get('location_label') or request.form.get('location')
                    latitude = request.form.get('latitude', type=float)
                    longitude = request.form.get('longitude', type=float)
                    
                    # Make prediction
                    pred_result = prediction_service.predict_image(filepath)
                    
                    if pred_result['success']:
                        # Save to database
                        prediction = prediction_service.save_prediction(
                            current_user.id,
                            filename,
                            filepath,
                            pred_result['label'],
                            pred_result['confidence'],
                            pred_result['raw_value'],
                            pred_result['processing_time']
                        )

                        alert = create_alert_from_prediction(
                            prediction,
                            pred_result,
                            location_label=location_label,
                            latitude=latitude,
                            longitude=longitude
                        )
                        
                        log_audit_action(current_user.id, 'PREDICT', 'PREDICTION', prediction.id,
                                       {'label': pred_result['label'], 'confidence': pred_result['confidence']},
                                       request.remote_addr)
                        
                        result = {
                            'label': pred_result['label'],
                            'confidence': f"{pred_result['confidence'] * 100:.2f}%",
                            'filename': filename,
                            'prediction_id': prediction.id,
                            'alert_created': alert is not None
                        }
                    else:
                        flash(f'Error making prediction: {pred_result["error"]}', 'danger')
                
                except Exception as e:
                    flash(f'Error processing image: {str(e)}', 'danger')
        
        return render_template_string(get_main_template(), result=result)
    
    @app.route('/history')
    @login_required
    def history():
        """User prediction history"""
        page = request.args.get('page', 1, type=int)
        predictions = Prediction.query.filter_by(user_id=current_user.id)\
            .order_by(Prediction.created_at.desc())\
            .paginate(page=page, per_page=10)
        
        return render_template_string(get_history_template(), predictions=predictions)
    
    @app.route('/feedback/<prediction_id>', methods=['POST'])
    @login_required
    def submit_feedback(prediction_id):
        """Submit feedback on prediction"""
        try:
            data = request.get_json()
            is_correct = data.get('is_correct')
            
            prediction = Prediction.query.get(prediction_id)
            if not prediction:
                return jsonify({'error': 'Prediction not found'}), 404
            
            if prediction.user_id != current_user.id:
                return jsonify({'error': 'Unauthorized'}), 403
            
            prediction.feedback = is_correct
            prediction.feedback_timestamp = datetime.utcnow()
            db.session.commit()
            
            log_audit_action(current_user.id, 'FEEDBACK', 'PREDICTION', prediction_id,
                           {'feedback': is_correct}, request.remote_addr)
            
            return jsonify({'status': 'success'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    # ======================== ANALYTICS ROUTES ========================
    
    @app.route('/api/accuracy')
    @login_required
    def get_accuracy():
        """Get accuracy statistics"""
        user_accuracy = AnalyticsService.get_user_accuracy(current_user.id) or 0
        predictions = Prediction.query.filter_by(user_id=current_user.id).all()
        feedback_predictions = [p for p in predictions if p.feedback is not None]
        
        return jsonify({
            'total_predictions': len(predictions),
            'feedback_count': len(feedback_predictions),
            'correct_predictions': sum(1 for p in feedback_predictions if p.feedback is True),
            'accuracy': user_accuracy
        })
    
    @app.route('/api/model-stats')
    def get_model_stats():
        """Get model statistics"""
        stats = AnalyticsService.get_model_statistics()
        return jsonify(stats)
    
    # ======================== ADMIN ROUTES ========================
    
    def admin_required(f):
        """Decorator for admin-only routes"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if getattr(current_user, 'role', 'coast_guard') != 'admin':
                flash('Admin access required.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function

    @app.route('/dashboard')
    @login_required
    def dashboard():
        if getattr(current_user, 'role', 'coast_guard') == 'admin':
            total_users = User.query.count()
            total_predictions = Prediction.query.count()
            model_stats = AnalyticsService.get_model_statistics()
            audit_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(50).all()
            alert_stats = compute_alert_statistics()
            alerts = Alert.query.order_by(Alert.detection_time.desc()).limit(50).all()
            create_user_form = AdminCreateUserForm()

            return render_template_string(get_admin_template(),
                                         total_users=total_users,
                                         total_predictions=total_predictions,
                                         model_stats=model_stats,
                                         audit_logs=audit_logs,
                                         alert_stats=alert_stats,
                                         alerts=alerts,
                                         create_user_form=create_user_form)

        alerts = Alert.query.order_by(Alert.detection_time.desc()).limit(25).all()
        recent_actions = AlertAction.query.join(Alert).order_by(AlertAction.timestamp.desc()).limit(10).all()
        open_alerts = [alert for alert in alerts if alert.status not in ('Resolved', 'Closed')]
        user_predictions = Prediction.query.filter_by(user_id=current_user.id).all()
        model_stats = AnalyticsService.get_model_statistics()
        user_accuracy = AnalyticsService.get_user_accuracy(current_user.id)

        return render_template_string(
            get_dashboard_template(),
            current_role=getattr(current_user, 'role', 'coast_guard'),
            alerts=alerts,
            open_alerts=open_alerts,
            recent_actions=recent_actions,
            total_predictions=len(user_predictions),
            user_accuracy=user_accuracy,
            model_stats=model_stats,
        )

    @app.route('/coast-guard/dashboard')
    @login_required
    @role_required('coast_guard', 'admin')
    def coast_guard_dashboard():
        return dashboard()
    
    @app.route('/admin')
    @login_required
    @admin_required
    def admin_panel():
        """Admin panel"""
        total_users = User.query.count()
        total_predictions = Prediction.query.count()
        model_stats = AnalyticsService.get_model_statistics()
        audit_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(50).all()
        alert_stats = compute_alert_statistics()
        alerts = Alert.query.order_by(Alert.detection_time.desc()).limit(50).all()
        create_user_form = AdminCreateUserForm()
        
        return render_template_string(get_admin_template(),
                                     total_users=total_users,
                                     total_predictions=total_predictions,
                                     model_stats=model_stats,
                                     audit_logs=audit_logs,
                                     alert_stats=alert_stats,
                                     alerts=alerts,
                                     create_user_form=create_user_form)

    @app.route('/admin/users/new', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def create_user():
        form = AdminCreateUserForm()
        if form.validate_on_submit():
            try:
                user = User(
                    username=form.username.data,
                    email=form.email.data,
                    role=form.role.data,
                )
                user.set_password(form.password.data)
                db.session.add(user)
                db.session.commit()
                log_audit_action(current_user.id, 'CREATE_USER', 'USER', user.id, {'email': user.email, 'role': user.role}, request.remote_addr)
                flash('User created successfully.', 'success')
                return redirect(url_for('manage_users'))
            except Exception:
                db.session.rollback()
                flash('Unable to create user. Please check details and try again.', 'danger')
        elif request.method == 'POST':
            for field_name, errors in form.errors.items():
                field_label = getattr(form, field_name).label.text if hasattr(form, field_name) else field_name
                for error in errors:
                    flash(f'{field_label}: {error}', 'danger')
        return render_template_string(get_registration_template(), form=form)
    
    @app.route('/admin/users')
    @login_required
    @admin_required
    def manage_users():
        """Manage users"""
        page = request.args.get('page', 1, type=int)
        users = User.query.paginate(page=page, per_page=20)
        
        return render_template_string(get_users_management_template(), users=users, create_user_form=AdminCreateUserForm())

    @app.route('/api/users', methods=['POST'])
    @login_required
    @role_required('admin', api=True)
    def api_create_user():
        payload = request.get_json(silent=True) or {}
        required_fields = ['username', 'email', 'password', 'role']
        missing = [field for field in required_fields if not payload.get(field)]
        if missing:
            return jsonify({'error': f"Missing fields: {', '.join(missing)}"}), 400

        if payload['role'] not in ('coast_guard', 'admin'):
            return jsonify({'error': 'Invalid role. Use coast_guard or admin.'}), 400

        if User.query.filter((User.email == payload['email']) | (User.username == payload['username'])).first():
            return jsonify({'error': 'User already exists'}), 409

        try:
            user = User(username=payload['username'], email=payload['email'], role=payload['role'])
            user.set_password(payload['password'])
            db.session.add(user)
            db.session.commit()
            log_audit_action(current_user.id, 'CREATE_USER', 'USER', user.id, {'email': user.email, 'role': user.role}, request.remote_addr)
            return jsonify({'message': 'User created', 'user': {'id': user.id, 'username': user.username, 'email': user.email, 'role': user.role}}), 201
        except Exception:
            db.session.rollback()
            return jsonify({'error': 'Unable to create user'}), 500

    @app.route('/api/alerts', methods=['GET'])
    @login_required
    @role_required('admin', 'coast_guard', api=True)
    def api_fetch_alerts():
        query = Alert.query.order_by(Alert.detection_time.desc())
        if getattr(current_user, 'role', 'coast_guard') != 'admin':
            query = query.filter(Alert.status.in_(['New', 'Acknowledged', 'In Progress', 'Resolved']))
        alerts = query.all()
        return jsonify({'alerts': [serialize_alert(alert) for alert in alerts], 'count': len(alerts)})

    @app.route('/api/alerts/<alert_id>', methods=['GET'])
    @login_required
    @role_required('admin', 'coast_guard', api=True)
    def api_get_alert(alert_id):
        alert = Alert.query.get_or_404(alert_id)
        return jsonify(serialize_alert(alert))

    @app.route('/api/alerts/<alert_id>/status', methods=['POST'])
    @login_required
    @role_required('admin', 'coast_guard', api=True)
    def api_update_alert_status(alert_id):
        alert = Alert.query.get_or_404(alert_id)
        payload = request.get_json(silent=True) or {}
        new_status = payload.get('status')
        notes = payload.get('notes')

        if not new_status:
            return jsonify({'error': 'status is required'}), 400

        if alert.status == 'Resolved' and new_status != 'Resolved':
            return jsonify({'error': 'Resolved alerts cannot be updated'}), 409

        alert.status = new_status
        if new_status == 'Acknowledged' and not alert.acknowledged_at:
            alert.acknowledged_at = datetime.utcnow()
        if new_status == 'Resolved':
            alert.resolved_at = datetime.utcnow()

        action = AlertAction(
            alert_id=alert.id,
            user_id=current_user.id,
            action_taken=f'Status updated to {new_status}',
            notes=notes
        )
        db.session.add(action)
        db.session.commit()
        log_audit_action(current_user.id, 'UPDATE_ALERT_STATUS', 'ALERT', alert.id, {'status': new_status, 'notes': notes}, request.remote_addr)
        return jsonify({'message': 'Alert updated', 'alert': serialize_alert(alert)})

    @app.route('/api/alerts/<alert_id>/acknowledge', methods=['POST'])
    @login_required
    @role_required('admin', 'coast_guard', api=True)
    def api_acknowledge_alert(alert_id):
        alert = Alert.query.get_or_404(alert_id)
        if alert.status == 'Resolved':
            return jsonify({'error': 'Resolved alerts cannot be updated'}), 409
        alert.status = 'Acknowledged'
        if not alert.acknowledged_at:
            alert.acknowledged_at = datetime.utcnow()
        action = AlertAction(
            alert_id=alert.id,
            user_id=current_user.id,
            action_taken='Alert acknowledged',
            notes=request.get_json(silent=True).get('notes') if request.get_json(silent=True) else None
        )
        db.session.add(action)
        db.session.commit()
        log_audit_action(current_user.id, 'ACKNOWLEDGE_ALERT', 'ALERT', alert.id, {}, request.remote_addr)
        return jsonify({'message': 'Alert acknowledged', 'alert': serialize_alert(alert)})

    @app.route('/api/alerts/<alert_id>/actions', methods=['GET'])
    @login_required
    @role_required('admin', 'coast_guard', api=True)
    def api_alert_actions(alert_id):
        alert = Alert.query.get_or_404(alert_id)
        return jsonify({'actions': [action.to_dict() for action in alert.actions]})
    
    # ======================== API ROUTES ========================
    
    @app.route('/api/predict', methods=['POST'])
    def api_predict():
        """
        API endpoint for predictions
        ---
        parameters:
          - name: Authorization
            in: header
            type: string
            required: true
            description: API Key (Bearer token)
        responses:
          200:
            description: Prediction response
          401:
            description: Unauthorized
        """
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid API key'}), 401
        
        api_key_str = auth_header[7:]
        api_key = APIKey.query.filter_by(key=api_key_str).first()
        
        if not api_key or not api_key.is_valid():
            return jsonify({'error': 'Invalid API key'}), 401
        
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        file = request.files['image']
        if not file or file.filename == '':
            return jsonify({'error': 'No image selected'}), 400
        
        try:
            filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            payload = request.form if request.form else (request.get_json(silent=True) or {})
            location_label = payload.get('location_label') or payload.get('location')
            latitude = payload.get('latitude')
            longitude = payload.get('longitude')
            latitude = float(latitude) if latitude not in (None, '') else None
            longitude = float(longitude) if longitude not in (None, '') else None
            
            pred_result = prediction_service.predict_image(filepath)
            
            if pred_result['success']:
                prediction = prediction_service.save_prediction(
                    api_key.user_id,
                    filename,
                    filepath,
                    pred_result['label'],
                    pred_result['confidence'],
                    pred_result['raw_value'],
                    pred_result['processing_time']
                )

                alert = create_alert_from_prediction(
                    prediction,
                    pred_result,
                    location_label=location_label,
                    latitude=latitude,
                    longitude=longitude
                )
                
                api_key.last_used = datetime.utcnow()
                db.session.commit()
                
                return jsonify({
                    'id': prediction.id,
                    'prediction': prediction.prediction_label,
                    'confidence': prediction.confidence_score,
                    'processing_time': prediction.processing_time,
                    'alert_created': alert is not None,
                    'alert': serialize_alert(alert) if alert else None
                })
            else:
                return jsonify({'error': pred_result['error']}), 500
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    # ======================== PROFILE ROUTES ========================
    
    @app.route('/profile')
    @login_required
    def profile():
        """User profile page"""
        user_accuracy = AnalyticsService.get_user_accuracy(current_user.id)
        predictions_count = Prediction.query.filter_by(user_id=current_user.id).count()
        
        return render_template_string(get_profile_template(),
                                     user_accuracy=user_accuracy,
                                     predictions_count=predictions_count)
    
    @app.route('/profile/update', methods=['GET', 'POST'])
    @login_required
    def update_profile():
        """Update user profile"""
        form = UpdateProfileForm(current_user.username, current_user.email)
        if form.validate_on_submit():
            current_user.username = form.username.data
            current_user.email = form.email.data
            db.session.commit()
            flash('Your profile has been updated.', 'success')
            return redirect(url_for('profile'))
        elif request.method == 'GET':
            form.username.data = current_user.username
            form.email.data = current_user.email
        
        return render_template_string(get_update_profile_template(), form=form)
    
    # ======================== DATABASE INITIALIZATION ========================
    
    with app.app_context():
        db.create_all()
    
    return app, prediction_service


# ======================== HTML TEMPLATES ========================

def get_login_template():
    return '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Oil Spill Detector - Login</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
            background-attachment: fixed;
            font-family: 'Segoe UI', sans-serif;
            color: white;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        .glass-card {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.18);
            width: 100%;
            max-width: 400px;
        }
        h2 {
            font-size: 2rem;
            font-weight: 600;
            margin-bottom: 30px;
            text-align: center;
        }
        .form-control {
            background: rgba(255, 255, 255, 0.2);
            border: none;
            color: white;
            margin-bottom: 15px;
        }
        .form-control::placeholder {
            color: rgba(255, 255, 255, 0.7);
        }
        .btn-login {
            background-color: #6c5ce7;
            border: none;
            color: white;
            width: 100%;
            padding: 12px;
            border-radius: 8px;
            font-weight: 600;
            margin-top: 10px;
        }
        .btn-login:hover {
            background-color: #a29bfe;
            color: black;
        }
        .signup-link {
            text-align: center;
            margin-top: 20px;
        }
        .signup-link a {
            color: #00b894;
            text-decoration: none;
            font-weight: 600;
        }
        .signup-link a:hover {
            text-decoration: underline;
        }
        .alert {
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="glass-card">
        <h2>🌊 Oil Spill Detector</h2>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <form method="POST" novalidate>
            {{ form.hidden_tag() }}
            
            <div class="mb-3">
                {{ form.email(class="form-control", placeholder="Email", autofocus=true) }}
                {% if form.email.errors %}
                    <small class="text-danger">{{ form.email.errors[0] }}</small>
                {% endif %}
            </div>
            
            <div class="mb-3">
                {{ form.password(class="form-control", placeholder="Password") }}
                {% if form.password.errors %}
                    <small class="text-danger">{{ form.password.errors[0] }}</small>
                {% endif %}
            </div>
            
            <div class="form-check mb-3">
                {{ form.remember_me(class="form-check-input") }}
                {{ form.remember_me.label(class="form-check-label") }}
            </div>
            
            {{ form.submit(class="btn btn-login") }}
        </form>
        
        <div class="signup-link">
            Accounts are created by an admin. Contact the manager if you need access.
        </div>
    </div>
</body>
</html>
    '''

def get_registration_template():
    return '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Register - Oil Spill Detector</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
            background-attachment: fixed;
            font-family: 'Segoe UI', sans-serif;
            color: white;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        .glass-card {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.18);
            width: 100%;
            max-width: 450px;
        }
        h2 {
            font-size: 2rem;
            font-weight: 600;
            margin-bottom: 30px;
            text-align: center;
        }
        .form-control {
            background: rgba(255, 255, 255, 0.2);
            border: none;
            color: white;
            margin-bottom: 15px;
        }
        .form-control::placeholder {
            color: rgba(255, 255, 255, 0.7);
        }
        .btn-register {
            background-color: #6c5ce7;
            border: none;
            color: white;
            width: 100%;
            padding: 12px;
            border-radius: 8px;
            font-weight: 600;
            margin-top: 10px;
        }
        .btn-register:hover {
            background-color: #a29bfe;
            color: black;
        }
        .login-link {
            text-align: center;
            margin-top: 20px;
        }
        .login-link a {
            color: #00b894;
            text-decoration: none;
            font-weight: 600;
        }
        .login-link a:hover {
            text-decoration: underline;
        }
        .alert {
            margin-bottom: 20px;
        }
        .form-text {
            color: rgba(255, 255, 255, 0.7);
            font-size: 0.85rem;
        }
    </style>
</head>
<body>
    <div class="glass-card">
        <h2>Create Account</h2>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <form method="POST" novalidate>
            {{ form.hidden_tag() }}
            
            <div class="mb-3">
                {{ form.username(class="form-control", placeholder="Username", autofocus=true) }}
                {% if form.username.errors %}
                    <small class="text-danger">{{ form.username.errors[0] }}</small>
                {% endif %}
            </div>
            
            <div class="mb-3">
                {{ form.email(class="form-control", placeholder="Email") }}
                {% if form.email.errors %}
                    <small class="text-danger">{{ form.email.errors[0] }}</small>
                {% endif %}
            </div>
            
            <div class="mb-3">
                {{ form.password(class="form-control", placeholder="Password") }}
                <small class="form-text">At least 6 characters</small>
                {% if form.password.errors %}
                    <small class="text-danger">{{ form.password.errors[0] }}</small>
                {% endif %}
            </div>
            
            {% if form.confirm_password is defined %}
            <div class="mb-3">
                {{ form.confirm_password(class="form-control", placeholder="Confirm Password") }}
                {% if form.confirm_password.errors %}
                    <small class="text-danger">{{ form.confirm_password.errors[0] }}</small>
                {% endif %}
            </div>
            {% endif %}

            {% if form.role is defined %}
            <div class="mb-3">
                {{ form.role(class="form-control") }}
                {% if form.role.errors %}
                    <small class="text-danger">{{ form.role.errors[0] }}</small>
                {% endif %}
            </div>
            {% endif %}
            
            {{ form.submit(class="btn btn-register") }}
        </form>
        
        <div class="login-link">
            Already have an account? <a href="{{ url_for('login') }}">Sign in here</a>
        </div>
    </div>
</body>
</html>
    '''

def get_main_template():
    return '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Oil Spill Detector</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    <style>
        body {
            background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
            background-attachment: fixed;
            font-family: 'Segoe UI', sans-serif;
            color: white;
            min-height: 100vh;
        }
        .navbar {
            background: rgba(0, 0, 0, 0.3) !important;
            backdrop-filter: blur(10px);
        }
        .navbar-brand {
            font-weight: 700;
            font-size: 1.5rem;
        }
        .container-main {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: calc(100vh - 60px);
            padding: 20px;
        }
        .glass-card {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.18);
            width: 100%;
            max-width: 600px;
        }
        h1 {
            font-size: 2.5rem;
            font-weight: 600;
            text-align: center;
            margin-bottom: 30px;
        }
        .form-control {
            background: rgba(255, 255, 255, 0.2);
            border: none;
            color: white;
        }
        .form-control::file-selector-button {
            background-color: #00b894;
            color: white;
            padding: 10px 16px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: background 0.3s ease;
        }
        .form-control::file-selector-button:hover {
            background-color: #019875;
        }
        .btn-custom {
            background-color: #6c5ce7;
            border: none;
            padding: 12px 24px;
            border-radius: 12px;
            color: white;
            font-size: 1rem;
            transition: 0.3s ease;
            width: 100%;
        }
        .btn-custom:hover {
            background-color: #a29bfe;
            color: black;
        }
        img {
            margin-top: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.5);
            max-width: 100%;
        }
        .result-text {
            margin-top: 20px;
            font-size: 1.2rem;
            animation: fadeIn 0.5s ease-in;
        }
        .feedback-buttons {
            margin: 20px 0;
        }
        .feedback-buttons button {
            margin: 5px;
        }
        @keyframes fadeIn {
            0% { opacity: 0; transform: translateY(10px); }
            100% { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="{{ url_for('index') }}">🌊 Oil Spill Detector</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item"><a class="nav-link" href="{{ url_for('index') }}">Predict</a></li>
                    <li class="nav-item"><a class="nav-link" href="{{ url_for('dashboard') }}">Dashboard</a></li>
                    <li class="nav-item"><a class="nav-link" href="{{ url_for('history') }}">History</a></li>
                    <li class="nav-item"><a class="nav-link" href="{{ url_for('profile') }}">Profile</a></li>
                    <li class="nav-item"><a class="nav-link" href="{{ url_for('logout') }}">Logout</a></li>
                </ul>
            </div>
        </div>
    </nav>
    
    <div class="container-main">
        <div class="glass-card text-center">
            <h1><i class="fa-solid fa-water"></i> Oil Spill Detector</h1>
            
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                            {{ message }}
                            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                        </div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            
            <form method="POST" enctype="multipart/form-data" class="mt-4">
                <input class="form-control mb-3" type="file" name="image" accept="image/*" required>
                <input class="form-control mb-3" type="text" name="location_label" placeholder="Location label (optional)">
                <div class="row g-2 mb-3">
                    <div class="col-md-6">
                        <input class="form-control" type="number" step="any" name="latitude" placeholder="Latitude (optional)">
                    </div>
                    <div class="col-md-6">
                        <input class="form-control" type="number" step="any" name="longitude" placeholder="Longitude (optional)">
                    </div>
                </div>
                <button type="submit" class="btn btn-custom">
                    <i class="fa-solid fa-magnifying-glass"></i> Detect
                </button>
            </form>

            {% if result %}
                <div class="result-text">
                    <strong>Prediction:</strong> {{ result.label }}<br>
                    <strong>Confidence:</strong> {{ result.confidence }}
                </div>
                <img src="{{ url_for('uploaded_file', filename=result.filename) }}" alt="Uploaded Image">
                
                <div class="feedback-buttons">
                    <p><strong>Was this prediction correct?</strong></p>
                    <button class="btn btn-success" onclick="submitFeedback('{{ result.prediction_id }}', true)">
                        <i class="fa-solid fa-check"></i> Correct
                    </button>
                    <button class="btn btn-danger" onclick="submitFeedback('{{ result.prediction_id }}', false)">
                        <i class="fa-solid fa-times"></i> Incorrect
                    </button>
                </div>
                <div id="feedback-message" class="mt-2"></div>
            {% endif %}
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        function submitFeedback(predictionId, isCorrect) {
            fetch('/feedback/' + predictionId, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({is_correct: isCorrect})
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('feedback-message').innerHTML = 
                    '<div class="alert alert-success">Thank you for your feedback!</div>';
            })
            .catch(error => {
                document.getElementById('feedback-message').innerHTML = 
                    '<div class="alert alert-danger">Error submitting feedback</div>';
            });
        }
    </script>
</body>
</html>
    '''

def get_dashboard_template():
    return '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Dashboard - Oil Spill Detector</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {
            background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
            background-attachment: fixed;
            font-family: 'Segoe UI', sans-serif;
            color: white;
            min-height: 100vh;
            padding: 20px 0;
        }
        .navbar {
            background: rgba(0, 0, 0, 0.3) !important;
            backdrop-filter: blur(10px);
            margin-bottom: 30px;
        }
        .stat-card {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 25px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.18);
            margin-bottom: 20px;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        }
        .stat-number {
            font-size: 2.5rem;
            font-weight: 700;
            color: #00b894;
        }
        .stat-label {
            font-size: 1rem;
            color: rgba(255, 255, 255, 0.7);
            margin-top: 10px;
        }
        .chart-container {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 25px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.18);
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="{{ url_for('index') }}">🌊 Oil Spill Detector</a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="{{ url_for('index') }}">Predict</a>
                <a class="nav-link active" href="{{ url_for('dashboard') }}">Dashboard</a>
                <a class="nav-link" href="{{ url_for('history') }}">History</a>
                <a class="nav-link" href="{{ url_for('profile') }}">Profile</a>
                <a class="nav-link" href="{{ url_for('logout') }}">Logout</a>
            </div>
        </div>
    </nav>
    
    <div class="container">
        <h2 class="mb-4">{% if current_role == 'admin' %}📊 Manager Dashboard{% else %}🛟 Coast Guard Dashboard{% endif %}</h2>
        
        <div class="row">
            <div class="col-md-4">
                <div class="stat-card">
                    <div class="stat-number">{{ total_predictions }}</div>
                    <div class="stat-label">Your Predictions</div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="stat-card">
                    <div class="stat-number">{{ user_accuracy if user_accuracy else 'N/A' }}%</div>
                    <div class="stat-label">Your Accuracy</div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="stat-card">
                    <div class="stat-number">{{ model_stats.accuracy }}%</div>
                    <div class="stat-label">Model Accuracy</div>
                </div>
            </div>
        </div>
        
        <div class="row mt-4">
            <div class="col-md-6">
                <div class="stat-card">
                    <h5>Prediction Distribution</h5>
                    <div id="distributionChart"></div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="stat-card">
                    <h5>Model Statistics</h5>
                    <p><strong>Total Predictions:</strong> {{ model_stats.total_predictions }}</p>
                    <p><strong>Oil Spills Detected:</strong> {{ model_stats.oil_spill_count }}</p>
                    <p><strong>No Oil Spills:</strong> {{ model_stats.no_oil_spill_count }}</p>
                    <p><strong>Avg. Confidence:</strong> {{ "%.2f"|format(model_stats.average_confidence * 100) }}%</p>
                </div>
            </div>
        </div>

        <div class="row mt-4">
            <div class="col-12">
                <div class="stat-card">
                    <h5 class="mb-3">Live Alerts</h5>
                    {% if alerts %}
                        <div class="table-responsive">
                            <table class="table table-dark table-striped align-middle mb-0">
                                <thead>
                                    <tr>
                                        <th>Time</th>
                                        <th>Location</th>
                                        <th>Severity</th>
                                        <th>Status</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {% for alert in alerts %}
                                    <tr>
                                        <td>{{ alert.detection_time.strftime('%Y-%m-%d %H:%M') if alert.detection_time else '-' }}</td>
                                        <td>
                                            {{ alert.location_label or 'Unknown' }}
                                            {% if alert.latitude is not none and alert.longitude is not none %}
                                                <br><small><a href="https://www.openstreetmap.org/?mlat={{ alert.latitude }}&mlon={{ alert.longitude }}#map=12/{{ alert.latitude }}/{{ alert.longitude }}" target="_blank">View map</a></small>
                                            {% endif %}
                                        </td>
                                        <td><span class="badge bg-warning text-dark">{{ alert.severity }}</span></td>
                                        <td><span class="badge bg-info text-dark">{{ alert.status }}</span></td>
                                        <td>
                                            {% set is_resolved = alert.status == 'Resolved' %}
                                            <button class="btn btn-sm btn-success" onclick="updateAlert('{{ alert.id }}', 'Acknowledged')" {% if is_resolved %}disabled{% endif %}>Acknowledge</button>
                                            <button class="btn btn-sm btn-primary" onclick="updateAlert('{{ alert.id }}', 'In Progress')" {% if is_resolved %}disabled{% endif %}>In Progress</button>
                                            <button class="btn btn-sm btn-danger" onclick="updateAlert('{{ alert.id }}', 'Resolved')" {% if is_resolved %}disabled{% endif %}>Resolved</button>
                                        </td>
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    {% else %}
                        <p class="text-muted mb-0">No alerts have been generated yet.</p>
                    {% endif %}
                </div>
            </div>
        </div>

        <div class="row mt-4">
            <div class="col-md-6">
                <div class="stat-card">
                    <h5>Recent Response Actions</h5>
                    {% if recent_actions %}
                        <ul class="list-group list-group-flush">
                            {% for action in recent_actions %}
                                <li class="list-group-item bg-transparent text-white border-light">
                                    <strong>{{ action.action_taken }}</strong><br>
                                    <small>{{ action.timestamp.strftime('%Y-%m-%d %H:%M') if action.timestamp else '' }}</small>
                                </li>
                            {% endfor %}
                        </ul>
                    {% else %}
                        <p class="text-muted mb-0">No response actions yet.</p>
                    {% endif %}
                </div>
            </div>
            <div class="col-md-6">
                <div class="stat-card">
                    <h5>Operational Status</h5>
                    <p><strong>Open Alerts:</strong> {{ open_alerts|length if open_alerts else 0 }}</p>
                    <p><strong>Current Role:</strong> {{ current_role|replace('_', ' ')|title }}</p>
                    <p class="text-muted mb-0">Use the status buttons to coordinate response directly from the dashboard.</p>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        const data = [{
            values: [{{ model_stats.oil_spill_count }}, {{ model_stats.no_oil_spill_count }}],
            labels: ['Oil Spill', 'No Oil Spill'],
            type: 'pie',
            marker: {colors: ['#ff6b6b', '#00b894']}
        }];
        const layout = {
            template: 'plotly_dark',
            margin: {l: 0, r: 0, b: 0, t: 0}
        };
        Plotly.newPlot('distributionChart', data, layout, {responsive: true});

        function updateAlert(alertId, status) {
            fetch('/api/alerts/' + alertId + '/status', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status: status})
            }).then(() => window.location.reload());
        }
    </script>
</body>
</html>
    '''

def get_history_template():
    return '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Prediction History - Oil Spill Detector</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    <style>
        body {
            background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
            background-attachment: fixed;
            font-family: 'Segoe UI', sans-serif;
            color: white;
            min-height: 100vh;
            padding: 20px 0;
        }
        .navbar {
            background: rgba(0, 0, 0, 0.3) !important;
            backdrop-filter: blur(10px);
            margin-bottom: 30px;
        }
        .table-container {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 25px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.18);
            overflow-x: auto;
        }
        table {
            margin: 0;
        }
        th {
            border-bottom: 2px solid rgba(255, 255, 255, 0.2);
            color: #00b894;
        }
        td {
            padding: 15px !important;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="{{ url_for('index') }}">🌊 Oil Spill Detector</a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="{{ url_for('index') }}">Predict</a>
                <a class="nav-link" href="{{ url_for('dashboard') }}">Dashboard</a>
                <a class="nav-link active" href="{{ url_for('history') }}">History</a>
                <a class="nav-link" href="{{ url_for('profile') }}">Profile</a>
                <a class="nav-link" href="{{ url_for('logout') }}">Logout</a>
            </div>
        </div>
    </nav>
    
    <div class="container">
        <h2 class="mb-4">📋 Prediction History</h2>
        
        <div class="table-container">
            <table class="table table-hover mb-0">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Image</th>
                        <th>Prediction</th>
                        <th>Confidence</th>
                        <th>Feedback</th>
                    </tr>
                </thead>
                <tbody>
                    {% if predictions.items %}
                        {% for pred in predictions.items %}
                        <tr>
                            <td>{{ pred.created_at.strftime('%Y-%m-%d %H:%M') }}</td>
                            <td>{{ pred.image_filename[:30] }}...</td>
                            <td>
                                {% if pred.prediction_label == 'Oil Spill' %}
                                    <span class="badge bg-danger">Oil Spill</span>
                                {% else %}
                                    <span class="badge bg-success">No Oil Spill</span>
                                {% endif %}
                            </td>
                            <td>{{ "%.2f"|format(pred.confidence_score * 100) }}%</td>
                            <td>
                                {% if pred.feedback is None %}
                                    <span class="text-warning">⏳ Pending</span>
                                {% elif pred.feedback %}
                                    <span class="text-success">✓ Correct</span>
                                {% else %}
                                    <span class="text-danger">✗ Incorrect</span>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    {% else %}
                        <tr>
                            <td colspan="5" class="text-center text-muted">No predictions yet</td>
                        </tr>
                    {% endif %}
                </tbody>
            </table>
        </div>
        
        {% if predictions.pages > 1 %}
        <nav class="mt-4">
            <ul class="pagination justify-content-center">
                {% if predictions.has_prev %}
                    <li class="page-item"><a class="page-link" href="{{ url_for('history', page=predictions.prev_num) }}">Previous</a></li>
                {% endif %}
                
                {% for page_num in predictions.iter_pages() %}
                    {% if page_num %}
                        {% if page_num == predictions.page %}
                            <li class="page-item active"><span class="page-link">{{ page_num }}</span></li>
                        {% else %}
                            <li class="page-item"><a class="page-link" href="{{ url_for('history', page=page_num) }}">{{ page_num }}</a></li>
                        {% endif %}
                    {% endif %}
                {% endfor %}
                
                {% if predictions.has_next %}
                    <li class="page-item"><a class="page-link" href="{{ url_for('history', page=predictions.next_num) }}">Next</a></li>
                {% endif %}
            </ul>
        </nav>
        {% endif %}
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
    '''

def get_profile_template():
    return '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Profile - Oil Spill Detector</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    <style>
        body {
            background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
            background-attachment: fixed;
            font-family: 'Segoe UI', sans-serif;
            color: white;
            min-height: 100vh;
            padding: 20px 0;
        }
        .navbar {
            background: rgba(0, 0, 0, 0.3) !important;
            backdrop-filter: blur(10px);
            margin-bottom: 30px;
        }
        .profile-card {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 30px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.18);
        }
        .btn-action {
            margin: 10px 5px;
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="{{ url_for('index') }}">🌊 Oil Spill Detector</a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="{{ url_for('index') }}">Predict</a>
                <a class="nav-link" href="{{ url_for('dashboard') }}">Dashboard</a>
                <a class="nav-link" href="{{ url_for('history') }}">History</a>
                <a class="nav-link active" href="{{ url_for('profile') }}">Profile</a>
                <a class="nav-link" href="{{ url_for('logout') }}">Logout</a>
            </div>
        </div>
    </nav>
    
    <div class="container">
        <div class="row">
            <div class="col-md-8 offset-md-2">
                <div class="profile-card">
                    <h2 class="mb-4">👤 My Profile</h2>
                    
                    <p><strong>Username:</strong> {{ current_user.username }}</p>
                    <p><strong>Email:</strong> {{ current_user.email }}</p>
                    <p><strong>Member Since:</strong> {{ current_user.created_at.strftime('%B %d, %Y') }}</p>
                    <hr>
                    
                    <h5>📊 Statistics</h5>
                    <p><strong>Total Predictions:</strong> {{ predictions_count }}</p>
                    <p><strong>Accuracy:</strong> {{ user_accuracy if user_accuracy else 'No feedback yet' }}%</p>
                    <hr>
                    
                    <a href="{{ url_for('update_profile') }}" class="btn btn-primary btn-action">
                        <i class="fa-solid fa-edit"></i> Edit Profile
                    </a>
                    <a href="{{ url_for('logout') }}" class="btn btn-danger btn-action">
                        <i class="fa-solid fa-sign-out-alt"></i> Logout
                    </a>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
    '''

def get_update_profile_template():
    return '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Edit Profile - Oil Spill Detector</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
            background-attachment: fixed;
            font-family: 'Segoe UI', sans-serif;
            color: white;
            min-height: 100vh;
            padding: 20px 0;
        }
        .form-card {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 30px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.18);
            max-width: 500px;
            margin: 50px auto;
        }
        .form-control {
            background: rgba(255, 255, 255, 0.2);
            border: none;
            color: white;
        }
        .form-control::placeholder {
            color: rgba(255, 255, 255, 0.7);
        }
        .btn-submit {
            background-color: #6c5ce7;
            border: none;
            color: white;
            width: 100%;
            padding: 12px;
            border-radius: 8px;
            font-weight: 600;
            margin-top: 10px;
        }
        .btn-submit:hover {
            background-color: #a29bfe;
            color: black;
        }
    </style>
</head>
<body>
    <div class="form-card">
        <h2 class="text-center mb-4">Edit Profile</h2>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <form method="POST" novalidate>
            {{ form.hidden_tag() }}
            
            <div class="mb-3">
                {{ form.username(class="form-control", placeholder="Username") }}
                {% if form.username.errors %}
                    <small class="text-danger">{{ form.username.errors[0] }}</small>
                {% endif %}
            </div>
            
            <div class="mb-3">
                {{ form.email(class="form-control", placeholder="Email") }}
                {% if form.email.errors %}
                    <small class="text-danger">{{ form.email.errors[0] }}</small>
                {% endif %}
            </div>
            
            {{ form.submit(class="btn btn-submit") }}
        </form>
        
        <a href="{{ url_for('profile') }}" class="btn btn-secondary mt-3" style="width: 100%;">Back to Profile</a>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
    '''

def get_admin_template():
    return '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Admin Panel - Oil Spill Detector</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    <style>
        :root {
            --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --dark-gradient: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
            --success-color: #00b894;
            --warning-color: #fdcb6e;
            --danger-color: #e74c3c;
            --info-color: #3498db;
        }

        * {
            transition: all 0.3s ease;
        }

        body {
            background: var(--dark-gradient);
            background-attachment: fixed;
            font-family: 'Segoe UI', sans-serif;
            color: white;
            min-height: 100vh;
            padding: 20px 0;
        }

        .navbar {
            background: rgba(0, 0, 0, 0.4) !important;
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            margin-bottom: 40px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }

        .navbar-brand {
            font-weight: 700;
            font-size: 1.3rem;
            letter-spacing: 0.5px;
        }

        .nav-link {
            font-weight: 500;
            margin: 0 10px;
            position: relative;
        }

        .nav-link:hover {
            color: var(--success-color) !important;
        }

        .nav-link::after {
            content: '';
            position: absolute;
            width: 0;
            height: 2px;
            bottom: -5px;
            left: 50%;
            background-color: var(--success-color);
            transition: all 0.3s ease;
            transform: translateX(-50%);
        }

        .nav-link:hover::after {
            width: 30px;
        }

        /* Stat Card Styling */
        .stat-card {
            background: rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            padding: 30px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.15);
            margin-bottom: 25px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            overflow: hidden;
            position: relative;
            cursor: hover;
        }

        .stat-card::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -50%;
            width: 200px;
            height: 200px;
            background: radial-gradient(circle, rgba(102, 126, 234, 0.1) 0%, transparent 70%);
            border-radius: 50%;
            pointer-events: none;
        }

        .stat-card:hover {
            background: rgba(255, 255, 255, 0.12);
            border-color: rgba(255, 255, 255, 0.25);
            box-shadow: 0 12px 48px rgba(102, 126, 234, 0.15);
            transform: translateY(-5px);
        }

        .stat-card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 15px;
        }

        .stat-icon {
            font-size: 2.5rem;
            background: var(--primary-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            opacity: 0.8;
        }

        .stat-number {
            font-size: 3rem;
            font-weight: 800;
            background: linear-gradient(135deg, var(--success-color) 0%, #00d2d3 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 8px;
        }

        .stat-label {
            font-size: 0.95rem;
            color: rgba(255, 255, 255, 0.7);
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        /* Main Title */
        .page-title {
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 40px;
            background: linear-gradient(135deg, #fff 0%, var(--success-color) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        /* Section Card */
        .section-card {
            background: rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            padding: 35px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.15);
            margin-bottom: 25px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }

        .section-card:hover {
            background: rgba(255, 255, 255, 0.11);
            border-color: rgba(255, 255, 255, 0.25);
            box-shadow: 0 12px 48px rgba(102, 126, 234, 0.15);
        }

        .section-title {
            font-size: 1.4rem;
            font-weight: 700;
            margin-bottom: 25px;
            display: flex;
            align-items: center;
            gap: 12px;
            padding-bottom: 15px;
            border-bottom: 2px solid rgba(255, 255, 255, 0.1);
        }

        .section-title i {
            background: var(--primary-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            font-size: 1.5rem;
        }

        /* Stat Details */
        .stat-detail {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            font-size: 0.95rem;
        }

        .stat-detail:last-child {
            border-bottom: none;
        }

        .stat-detail-label {
            color: rgba(255, 255, 255, 0.7);
            font-weight: 500;
        }

        .stat-detail-value {
            font-weight: 700;
            color: var(--success-color);
            font-size: 1.1rem;
        }

        /* Table Styling */
        .table-responsive {
            border-radius: 12px;
            overflow: hidden;
        }

        .table {
            margin-bottom: 0;
        }

        .table thead th {
            background: rgba(102, 126, 234, 0.15);
            border: none;
            border-bottom: 2px solid rgba(255, 255, 255, 0.1);
            color: var(--success-color);
            font-weight: 700;
            text-transform: uppercase;
            font-size: 0.85rem;
            letter-spacing: 0.5px;
            padding: 15px;
        }

        .table tbody td {
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            padding: 15px;
            color: rgba(255, 255, 255, 0.9);
        }

        .table tbody tr:hover {
            background: rgba(102, 126, 234, 0.1);
        }

        /* Severity Badge */
        .badge-severity-low {
            background: rgba(52, 152, 219, 0.3);
            color: #3498db;
            border: 1px solid rgba(52, 152, 219, 0.5);
            font-weight: 600;
            padding: 6px 12px;
            border-radius: 20px;
        }

        .badge-severity-medium {
            background: rgba(241, 196, 15, 0.3);
            color: #f1c40f;
            border: 1px solid rgba(241, 196, 15, 0.5);
            font-weight: 600;
            padding: 6px 12px;
            border-radius: 20px;
        }

        .badge-severity-high {
            background: rgba(231, 76, 60, 0.3);
            color: #e74c3c;
            border: 1px solid rgba(231, 76, 60, 0.5);
            font-weight: 600;
            padding: 6px 12px;
            border-radius: 20px;
        }

        /* Form Styling */
        .form-control {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 12px;
            color: white;
            padding: 12px 16px;
            font-size: 0.95rem;
        }

        .form-control:focus {
            background: rgba(255, 255, 255, 0.12);
            border-color: var(--success-color);
            color: white;
            box-shadow: 0 0 0 0.2rem rgba(0, 184, 148, 0.25);
        }

        .form-control::placeholder {
            color: rgba(255, 255, 255, 0.5);
        }

        /* Button Styling */
        .btn-success {
            background: var(--primary-gradient);
            border: none;
            border-radius: 12px;
            font-weight: 700;
            padding: 12px 24px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }

        .btn-success:hover {
            background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
            box-shadow: 0 6px 25px rgba(102, 126, 234, 0.4);
            transform: translateY(-2px);
        }

        /* No Data Message */
        .no-data {
            text-align: center;
            padding: 40px 20px;
            color: rgba(255, 255, 255, 0.5);
            font-style: italic;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .page-title {
                font-size: 1.8rem;
                margin-bottom: 30px;
            }

            .stat-number {
                font-size: 2rem;
            }

            .stat-card {
                padding: 20px;
            }

            .section-card {
                padding: 20px;
            }
        }

        /* Animation */
        @keyframes slideInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .stat-card, .section-card {
            animation: slideInUp 0.6s ease forwards;
        }

        .stat-card:nth-child(1) { animation-delay: 0.1s; }
        .stat-card:nth-child(2) { animation-delay: 0.2s; }
        .stat-card:nth-child(3) { animation-delay: 0.3s; }
        /* Incident Cards */
.incident-card {
    background: rgba(37, 150, 190, 0.15);
    border-radius: 16px;
    padding: 20px;
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.2);
    transition: all 0.3s ease;
    color: white;
}

.incident-card:hover {
    transform: translateY(-6px);
    box-shadow: 0 12px 30px rgba(0,0,0,0.4);
}

.status-badge {
    background: rgba(255,255,255,0.2);
    padding: 6px 10px;
    border-radius: 8px;
    font-size: 0.75rem;
    text-transform: uppercase;
}

.badge-severity-high {
    background: #e74c3c;
    color: white;
    padding: 6px 12px;
    border-radius: 10px;
}

.badge-severity-medium {
    background: #f39c12;
    color: black;
    padding: 6px 12px;
    border-radius: 10px;
}

.badge-severity-low {
    background: #2ecc71;
    color: white;
    padding: 6px 12px;
    border-radius: 10px;
}
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="{{ url_for('index') }}">
                <i class="fas fa-water"></i> Oil Spill Detector
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <div class="navbar-nav ms-auto">
                    <a class="nav-link active" href="{{ url_for('admin_panel') }}">
                        <i class="fas fa-chart-line"></i> Dashboard
                    </a>
                    <a class="nav-link" href="{{ url_for('manage_users') }}">
                        <i class="fas fa-users"></i> Users
                    </a>
                    <a class="nav-link" href="{{ url_for('logout') }}">
                        <i class="fas fa-sign-out-alt"></i> Logout
                    </a>
                </div>
            </div>
        </div>
    </nav>
    
    <div class="container">
        <h1 class="page-title"><i class="fas fa-cogs"></i> Admin Dashboard</h1>
        
        <!-- Key Metrics -->
        <div class="row mb-4">
            <div class="col-md-4">
                <div class="stat-card">
                    <div class="stat-card-header">
                        <div>
                            <div class="stat-number">{{ total_users }}</div>
                            <div class="stat-label">Total Users</div>
                        </div>
                        <div class="stat-icon">
                            <i class="fas fa-users-cog"></i>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="stat-card">
                    <div class="stat-card-header">
                        <div>
                            <div class="stat-number">{{ total_predictions }}</div>
                            <div class="stat-label">Total Predictions</div>
                        </div>
                        <div class="stat-icon">
                            <i class="fas fa-microscope"></i>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="stat-card">
                    <div class="stat-card-header">
                        <div>
                            <div class="stat-number">{{ model_stats.accuracy }}%</div>
                            <div class="stat-label">Model Accuracy</div>
                        </div>
                        <div class="stat-icon">
                            <i class="fas fa-brain"></i>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Statistics Sections -->
        <div class="row mt-5">
            <div class="col-lg-6">
                <div class="section-card">
                    <h3 class="section-title">
                        <i class="fas fa-chart-pie"></i> Model Statistics
                    </h3>
                    <div class="stat-detail">
                        <span class="stat-detail-label"><i class="fas fa-exclamation-triangle"></i> Oil Spills Detected</span>
                        <span class="stat-detail-value">{{ model_stats.oil_spill_count }}</span>
                    </div>
                    <div class="stat-detail">
                        <span class="stat-detail-label"><i class="fas fa-check-circle"></i> No Oil Spills</span>
                        <span class="stat-detail-value">{{ model_stats.no_oil_spill_count }}</span>
                    </div>
                    <div class="stat-detail">
                        <span class="stat-detail-label"><i class="fas fa-tachometer-alt"></i> Average Confidence</span>
                        <span class="stat-detail-value">{{ "%.2f"|format(model_stats.average_confidence * 100) }}%</span>
                    </div>
                </div>
            </div>
            <div class="col-lg-6">
                <div class="section-card">
                    <h3 class="section-title">
                        <i class="fas fa-bell"></i> Alert Analytics
                    </h3>
                    <div class="stat-detail">
                        <span class="stat-detail-label"><i class="fas fa-exclamation-circle"></i> Total Alerts</span>
                        <span class="stat-detail-value">{{ alert_stats.total_alerts }}</span>
                    </div>
                    <div class="stat-detail">
                        <span class="stat-detail-label"><i class="fas fa-lock-open"></i> Open Alerts</span>
                        <span class="stat-detail-value">{{ alert_stats.open_alerts }}</span>
                    </div>
                    <div class="stat-detail">
                        <span class="stat-detail-label"><i class="fas fa-hourglass-half"></i> Avg Response Time</span>
                        <span class="stat-detail-value">{{ alert_stats.average_response_time_minutes }} min</span>
                    </div>
                    <div class="stat-detail">
                        <span class="stat-detail-label"><i class="fas fa-layer-group"></i> Severity Mix</span>
                        <span class="stat-detail-value">
                            <span class="badge-severity-low">L{{ alert_stats.severity_counts.low }}</span>
                            <span class="badge-severity-medium">M{{ alert_stats.severity_counts.medium }}</span>
                            <span class="badge-severity-high">H{{ alert_stats.severity_counts.high }}</span>
                        </span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Recent Incidents & User Creation -->
        <div class="row mt-5">
    <div class="col-lg-8">
        <div class="section-card">
            <h3 class="section-title">
                <i class="fas fa-fire"></i> Recent Incidents
            </h3>

            {% if alerts %}
                <div class="row">
                    {% for alert in alerts %}
                        <div class="col-md-6 mb-4">
                            <div class="incident-card">

                                <!-- Header -->
                                <div class="d-flex justify-content-between align-items-center mb-2">
                                    <h5 class="mb-0">
                                        <i class="fas fa-map-marker-alt"></i>
                                        {{ alert.location_label or 'Unknown' }}
                                    </h5>

                                    <span class="status-badge">
                                        {{ alert.status }}
                                    </span>
                                </div>

                                <!-- Time -->
                                <p class="text-muted mb-3">
                                    <i class="fas fa-clock"></i>
                                    {{ alert.detection_time.strftime('%Y-%m-%d %H:%M') if alert.detection_time else '-' }}
                                </p>

                                <!-- Severity + Action -->
                                <div class="d-flex justify-content-between align-items-center">

                                    {% if alert.severity == 'high' %}
                                        <span class="badge-severity-high">HIGH</span>
                                    {% elif alert.severity == 'medium' %}
                                        <span class="badge-severity-medium">MEDIUM</span>
                                    {% else %}
                                        <span class="badge-severity-low">LOW</span>
                                    {% endif %}

                                    <button class="btn btn-sm btn-light"
                                            onclick="viewAlert('{{ alert.id }}')">
                                        <i class="fas fa-eye"></i> View
                                    </button>
                                </div>

                                <!-- Optional Map Link -->
                                {% if alert.latitude and alert.longitude %}
                                    <div class="mt-3">
                                        <a href="https://www.openstreetmap.org/?mlat={{ alert.latitude }}&mlon={{ alert.longitude }}"
                                           target="_blank"
                                           class="map-link">
                                            📍 View on Map
                                        </a>
                                    </div>
                                {% endif %}

                            </div>
                        </div>
                    {% endfor %}
                </div>

            {% else %}
                <div class="no-data text-center">
                    <i class="fas fa-inbox fa-3x mb-3" style="opacity: 0.3;"></i>
                    <p>No incidents logged yet.</p>
                </div>
            {% endif %}
        </div>
    </div>

    <!-- RIGHT SIDE (UNCHANGED) -->
    <div class="col-lg-4">
        <div class="section-card">
            <h3 class="section-title">
                <i class="fas fa-user-plus"></i> Create Account
            </h3>
            <form method="POST" action="{{ url_for('create_user') }}">
                {{ create_user_form.hidden_tag() }}

                <div class="mb-3">
                    {{ create_user_form.username(class="form-control", placeholder="Username") }}
                </div>

                <div class="mb-3">
                    {{ create_user_form.email(class="form-control", placeholder="Email") }}
                </div>

                <div class="mb-3">
                    {{ create_user_form.role(class="form-control") }}
                </div>

                <div class="mb-3">
                    {{ create_user_form.password(class="form-control", placeholder="Temporary Password") }}
                </div>

                {{ create_user_form.submit(class="btn btn-success w-100") }}
            </form>
        </div>
    </div>
</div>
</div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
    '''

def get_users_management_template():
    return '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Manage Users - Oil Spill Detector</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    <style>
        :root {
            --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --dark-gradient: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
            --success-color: #00b894;
            --warning-color: #fdcb6e;
            --danger-color: #e74c3c;
            --info-color: #3498db;
        }

        * {
            transition: all 0.3s ease;
        }

        body {
            background: var(--dark-gradient);
            background-attachment: fixed;
            font-family: 'Segoe UI', sans-serif;
            color: white;
            min-height: 100vh;
            padding: 20px 0;
        }

        .navbar {
            background: rgba(0, 0, 0, 0.4) !important;
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            margin-bottom: 40px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }

        .navbar-brand {
            font-weight: 700;
            font-size: 1.3rem;
            letter-spacing: 0.5px;
        }

        .nav-link {
            font-weight: 500;
            margin: 0 10px;
            position: relative;
        }

        .nav-link:hover {
            color: var(--success-color) !important;
        }

        .nav-link::after {
            content: '';
            position: absolute;
            width: 0;
            height: 2px;
            bottom: -5px;
            left: 50%;
            background-color: var(--success-color);
            transition: all 0.3s ease;
            transform: translateX(-50%);
        }

        .nav-link:hover::after {
            width: 30px;
        }

        /* Page Title */
        .page-title {
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 40px;
            background: linear-gradient(135deg, #fff 0%, var(--success-color) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        /* Table Container */
        .table-container {
            background: rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            padding: 35px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.15);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }

        .table-responsive {
            border-radius: 12px;
            overflow: hidden;
        }

        /* Table Styling */
        .table {
            margin-bottom: 0;
        }

        .table thead th {
            background: rgba(102, 126, 234, 0.15);
            border: none;
            border-bottom: 2px solid rgba(255, 255, 255, 0.1);
            color: var(--success-color);
            font-weight: 700;
            text-transform: uppercase;
            font-size: 0.85rem;
            letter-spacing: 0.5px;
            padding: 18px 15px;
        }

        .table tbody td {
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            padding: 18px 15px;
            color: rgba(255, 255, 255, 0.9);
            font-size: 0.95rem;
        }

        .table tbody tr {
            transition: all 0.3s ease;
        }

        .table tbody tr:hover {
            background: rgba(102, 126, 234, 0.1);
            transform: translateX(5px);
        }

        /* Role Badge */
        .badge-role {
            padding: 8px 14px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .badge-admin {
            background: rgba(231, 76, 60, 0.3);
            color: #e74c3c;
            border: 1px solid rgba(231, 76, 60, 0.5);
        }

        .badge-coast-guard {
            background: rgba(52, 152, 219, 0.3);
            color: #3498db;
            border: 1px solid rgba(52, 152, 219, 0.5);
        }

        /* Status Badge */
        .badge-status {
            padding: 6px 12px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .badge-active {
            background: rgba(0, 184, 148, 0.3);
            color: var(--success-color);
            border: 1px solid rgba(0, 184, 148, 0.5);
        }

        .badge-inactive {
            background: rgba(231, 76, 60, 0.3);
            color: #e74c3c;
            border: 1px solid rgba(231, 76, 60, 0.5);
        }

        /* Icon styling */
        .user-avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: var(--primary-gradient);
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 12px;
            font-weight: 700;
            color: white;
            font-size: 0.9rem;
        }

        .user-info {
            display: flex;
            align-items: center;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .page-title {
                font-size: 1.8rem;
                margin-bottom: 30px;
            }

            .table-container {
                padding: 20px;
            }

            .table thead th,
            .table tbody td {
                padding: 12px 8px;
                font-size: 0.85rem;
            }
        }

        /* Animation */
        @keyframes slideInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .table-container {
            animation: slideInUp 0.6s ease forwards;
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="{{ url_for('index') }}">
                <i class="fas fa-water"></i> Oil Spill Detector
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <div class="navbar-nav ms-auto">
                    <a class="nav-link" href="{{ url_for('admin_panel') }}">
                        <i class="fas fa-chart-line"></i> Dashboard
                    </a>
                    <a class="nav-link active" href="{{ url_for('manage_users') }}">
                        <i class="fas fa-users"></i> Users
                    </a>
                    <a class="nav-link" href="{{ url_for('logout') }}">
                        <i class="fas fa-sign-out-alt"></i> Logout
                    </a>
                </div>
            </div>
        </div>
    </nav>
    
    <div class="container">
        <h1 class="page-title"><i class="fas fa-users-cog"></i> User Management</h1>
        
        <div class="table-container">
            <div class="table-responsive">
                <table class="table">
                    <thead>
                        <tr>
                            <th><i class="fas fa-user"></i> Username</th>
                            <th><i class="fas fa-envelope"></i> Email</th>
                            <th><i class="fas fa-shield-alt"></i> Role</th>
                            <th><i class="fas fa-calendar"></i> Joined</th>
                            <th><i class="fas fa-check-circle"></i> Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for user in users.items %}
                        <tr>
                            <td>
                                <div class="user-info">
                                    <div class="user-avatar">{{ user.username[0].upper() }}</div>
                                    <span>{{ user.username }}</span>
                                </div>
                            </td>
                            <td>{{ user.email }}</td>
                            <td>
                                {% if user.role == 'admin' %}
                                    <span class="badge-role badge-admin">
                                        <i class="fas fa-crown"></i> Manager
                                    </span>
                                {% else %}
                                    <span class="badge-role badge-coast-guard">
                                        <i class="fas fa-life-ring"></i> Coast Guard
                                    </span>
                                {% endif %}
                            </td>
                            <td>{{ user.created_at.strftime('%Y-%m-%d') }}</td>
                            <td>
                                {% if user.is_active %}
                                    <span class="badge-status badge-active">
                                        <i class="fas fa-circle"></i> Active
                                    </span>
                                {% else %}
                                    <span class="badge-status badge-inactive">
                                        <i class="fas fa-circle"></i> Inactive
                                    </span>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            
            {% if not users.items %}
            <div style="text-align: center; padding: 60px 20px; color: rgba(255, 255, 255, 0.5);">
                <i class="fas fa-inbox fa-3x mb-3" style="opacity: 0.3;"></i>
                <p>No users found.</p>
            </div>
            {% endif %}
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
    '''


if __name__ == '__main__':
    app, prediction_service = create_app('development')
    app.run(debug=True, host='0.0.0.0', port=5000)
