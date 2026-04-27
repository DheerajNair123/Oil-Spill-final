# 🌊 Oil Spill Detection System - Complete Project

A comprehensive, production-ready oil spill detection system with machine learning, user authentication, analytics dashboard, and RESTful API.

## 📋 Features

### Phase 1: Core Features ✅
- ✓ User authentication & registration with role-based access
- ✓ SQLAlchemy database integration with multiple models
- ✓ Prediction system with confidence scoring
- ✓ User feedback mechanism for model improvement
- ✓ Comprehensive analytics dashboard with charts
- ✓ Prediction history with pagination
- ✓ User profiles with statistics

### Phase 2: Advanced Features 🚧
- 🔄 REST API with Swagger documentation
- 🔄 Image preprocessing (contrast enhancement, denoising)
- 🔄 Batch image processing
- 🔄 Admin panel with user management
- 🔄 API key management for programmatic access
- 🔄 Audit logging for security

### Phase 3: ML & Optimization
- ⭕ Grad-CAM model explainability
- ⭕ Fine-tuning with user feedback
- ⭕ Performance monitoring & alerts
- ⭕ Model versioning

### Phase 4: Production Deployment
- ⭕ Docker containerization
- ⭕ CI/CD pipeline (GitHub Actions)
- ⭕ Cloud deployment (AWS/Google Cloud)
- ⭕ Comprehensive test suite

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- TensorFlow/Keras (pre-installed in venv)
- Virtual environment setup

### Installation

1. **Navigate to project directory**
   ```bash
   cd path/to/MPTRIAL
   ```

2. **Activate virtual environment**
   ```bash
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the database**
   ```bash
   python init_db.py
   ```
   This creates:
   - SQLite database (oil_spill.db)
   - Admin user: `admin@example.com` / `admin123`
   - Demo user: `demo@example.com` / `demo123`

5. **Run the application**
   ```bash
   python run.py
   ```

6. **Access the application**
   - Application: http://localhost:5000
   - API Docs: http://localhost:5000/apidocs/
   - Admin Panel: http://localhost:5000/admin

## 📁 Project Structure

```
MPTRIAL/
├── app.py                  # Main Flask application
├── models.py               # SQLAlchemy models
├── config.py               # Configuration management
├── forms.py                # WTForms for validation
├── utils.py                # Utility functions & services
├── run.py                  # Application runner
├── init_db.py              # Database initialization
├── test_app.py             # Unit & integration tests
├── requirements.txt        # Python dependencies
├── model.h5                # Pre-trained ML model
├── uploads/                # Uploaded images
├── static/                 # Static files
└── README.md               # This file
```

## 🔐 User Roles

| Role | Permissions |
|------|------------|
| **Admin** | Full system access, user management, analytics |
| **User** | Make predictions, view history, manage profile |
| **Supervisor** | View all predictions, system statistics |

## 🔌 API Endpoints

### Authentication
- `POST /register` - User registration
- `POST /login` - User login
- `GET /logout` - User logout

### Predictions
- `GET /` - Main prediction page
- `POST /` - Submit image for prediction
- `GET /history` - View prediction history
- `POST /feedback/<id>` - Submit feedback

### Analytics
- `GET /dashboard` - User dashboard
- `GET /api/accuracy` - User accuracy stats
- `GET /api/model-stats` - Model statistics

### Admin
- `GET /admin` - Admin dashboard
- `GET /admin/users` - Manage users

### API (Programmatic)
- `POST /api/predict` - API prediction endpoint (requires Bearer token)

## 📊 Database Models

### User
- Username, email, password hash
- Role-based access control
- Account status tracking

### Prediction
- User reference
- Image metadata
- Prediction result with confidence
- User feedback tracking
- Processing timestamp & time

### APIKey
- Secure API key management
- Usage tracking
- Expiration support

### AuditLog
- Security event logging
- User action tracking

### ModelMetrics
- Performance statistics
- Accuracy tracking

## 🎯 Configuration

Environment variables (create `.env` file):
```env
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///oil_spill.db
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=16777216
```

## 🧪 Testing

Run unit and integration tests:
```bash
pytest test_app.py -v
```

## 📈 Usage Examples

### Registration & Login
1. Visit http://localhost:5000/register
2. Create account with username, email, password
3. Login with credentials

### Making Predictions
1. Login to your account
2. Go to "Predict" tab
3. Upload satellite image
4. View prediction result
5. Provide feedback (correct/incorrect)

### Viewing Analytics
1. Go to "Dashboard"
2. View personal statistics
3. See model accuracy metrics
4. Review prediction distribution

### API Usage
```python
import requests

headers = {'Authorization': 'Bearer YOUR_API_KEY'}
files = {'image': open('satellite_image.jpg', 'rb')}

response = requests.post(
    'http://localhost:5000/api/predict',
    headers=headers,
    files=files
)

result = response.json()
print(f"Prediction: {result['prediction']}")
print(f"Confidence: {result['confidence']}")
```

## 🔒 Security Features

- ✓ Password hashing with Werkzeug
- ✓ CSRF protection with Flask-WTF
- ✓ SQL injection prevention with ORM
- ✓ Session management
- ✓ API key authentication
- ✓ Audit logging
- ✓ Role-based access control

## 📚 Additional Resources

### Model Explainability (Phase 3)
- Grad-CAM visualizations
- Feature importance analysis
- Model confidence reasoning

### Batch Processing (Phase 2)
- Process multiple images at once
- Batch API endpoints
- Progress tracking

### Advanced Analytics (Phase 3)
- Time-series predictions
- Performance trends
- Model comparison

## 🐛 Troubleshooting

### Model Loading Error
```
Error loading model: No such file or directory: 'model.h5'
```
Solution: Ensure model.h5 exists in project root. Download pre-trained model if missing.

### Database Locked
```
sqlite3.OperationalError: database is locked
```
Solution: Delete `oil_spill.db` and run `python init_db.py` again.

### Port Already in Use
```
OSError: [Errno 48] Address already in use
```
Solution: Change port in `run.py` or kill process using port 5000.

## 🚀 Deployment

### Docker Deployment
```bash
docker build -t oil-spill-detector .
docker run -p 5000:5000 oil-spill-detector
```

### Cloud Deployment (AWS)
- Upload to AWS S3
- Deploy on EC2 or Elastic Beanstalk
- Use RDS for PostgreSQL database

### Heroku Deployment
```bash
heroku create your-app-name
git push heroku main
heroku run python init_db.py
```

## 📝 Development Roadmap

- [x] Phase 1: Core features (users, predictions, analytics)
- [ ] Phase 2: API, batch processing, admin panel
- [ ] Phase 3: Model explainability, fine-tuning, monitoring
- [ ] Phase 4: Docker, CI/CD, cloud deployment

## 📄 License

This project is created for educational purposes.

## 👥 Contributors

- Dheeraj (Project Lead & Developer)

## 📧 Support

For issues and feature requests, create a GitHub issue or contact the development team.

---

**Last Updated**: April 21, 2026
**Status**: Production Ready (Phase 1) | In Development (Phases 2-4)
