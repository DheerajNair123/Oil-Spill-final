# Oil Spill Detector System

A Flask-based web application and API for detecting oil spills in satellite imagery using a TensorFlow model. The app includes user login, role-based dashboards, prediction history, feedback capture, alert management, and a JSON API for external integrations.

## What It Does

The application lets a user upload a satellite image, runs it through the trained model, and stores the prediction in the database. If an oil spill is detected, the system creates an alert record that can be reviewed and managed from the dashboard or API.

## Features

- User authentication with Flask-Login
- Role-based access for admin, coast guard, and regular/demo users
- Single-image prediction from the web UI
- Prediction history with feedback status tracking
- Alert creation, acknowledgement, and status updates when oil spills are detected
- Admin dashboard with user management and summary metrics
- Coast guard dashboard for operational review
- REST API with bearer API key support
- Swagger documentation at `/apidocs/`
- Image serving for uploaded files

## Tech Stack

- Flask
- Flask-Login
- Flask-SQLAlchemy
- Flask-CORS
- Flasgger / Swagger
- TensorFlow / Keras

## Installation

### 1. Clone or open the project
```bash
cd /path/to/MPTRIAL
```

### 2. Create a virtual environment
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Make sure the model is available

Place your trained model at `model.h5`, or set `MODEL_PATH` to point to a different file.

## Configuration

The main settings live in `config.py` and can be overridden with environment variables.

- `SECRET_KEY`
- `DATABASE_URL`
- `UPLOAD_FOLDER`
- `MAX_CONTENT_LENGTH`
- `MODEL_PATH`
- `PREDICTION_THRESHOLD`
- `FLASK_ENV`

Default values are provided for local development, including a SQLite database at `sqlite:///oil_spill.db`.

## Running the App

### Preferred startup command
```bash
python run.py
```

This initializes the database, loads the model, and starts the server at `http://localhost:5000`.

### Alternate startup command
```bash
python app.py
```

Use this if you want the application to start directly from the Flask app module.

### API documentation

Open `http://localhost:5000/apidocs/` for the Swagger UI.

## Default Accounts

The startup script prints demo credentials that are useful for local testing:

- Admin: `admin@example.com` / `admin123`
- Coast Guard: `coastguard@example.com` / `coast123`
- Demo: `demo@example.com` / `demo123`

Change these before using the app in a real environment.

## Main Web Routes

- `GET /` - landing page / home
- `GET, POST /register` - admin-controlled registration once an admin exists
- `GET, POST /login` - web login
- `POST /api/login` - API/session login
- `POST /api/logout` - API logout
- `GET /dashboard` - role-based dashboard
- `GET /admin` - admin dashboard
- `GET, POST /admin/users/new` - create users from the admin area
- `GET /admin/users` - user management list
- `GET /history` - prediction history
- `POST /feedback/<prediction_id>` - submit prediction feedback
- `GET /profile` - profile page
- `GET, POST /profile/update` - update profile
- `GET /uploads/<filename>` - access uploaded files

## API Endpoints

### Prediction

- `POST /api/predict`
- Requires a bearer API key for API usage
- Accepts an uploaded image and returns prediction details

### Metrics

- `GET /api/accuracy`
- `GET /api/model-stats`

### Alerts

- `GET /api/alerts`
- `GET /api/alerts/<alert_id>`
- `POST /api/alerts/<alert_id>/status`
- `POST /api/alerts/<alert_id>/acknowledge`
- `GET /api/alerts/<alert_id>/actions`

### User management API

- `POST /api/users`

## Testing

Run the available checks from the project root:

```bash
python test_app.py
python test_api.py
```

If you only want a quick verification of the model pipeline, use the helper scripts in the repo such as `quick_accuracy_check.py`.

## Project Structure

```text
MPTRIAL/
├── app.py
├── run.py
├── config.py
├── models.py
├── forms.py
├── utils.py
├── test_app.py
├── test_api.py
├── evaluate_model.py
├── quick_accuracy_check.py
├── model.h5
├── instance/
├── uploads/
└── README.md
```

## Notes

- TensorFlow is optional at import time, but predictions require a valid model.
- Uploaded images are stored under the configured upload folder.
- The app uses a 224x224 input size and a default prediction threshold of 0.5.

## License

College Mini Project (semVII)

## Author

Dheeraj
