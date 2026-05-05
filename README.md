# ðŸ›¢ï¸ Oil Spill Detector System

A Flask-based web application and API for detecting oil spills in satellite imagery using a TensorFlow model. The app includes user login, role-based dashboards, prediction history, feedback capture, alert management, and a JSON API for external integrations.

## ðŸ” What It Does

The application lets a user upload a satellite image, runs it through the trained model, and stores the prediction in the database. If an oil spill is detected, the system creates an alert record that can be reviewed and managed from the dashboard or API.

## âœ¨ Features

- ðŸ” User authentication with Flask-Login
- ðŸ‘¥ Role-based access for admin, coast guard, and regular/demo users
- ðŸ–¼ï¸ Single-image prediction from the web UI
- ðŸ“œ Prediction history with feedback status tracking
- ðŸš¨ Alert creation, acknowledgement, and status updates when oil spills are detected
- ðŸ› ï¸ Admin dashboard with user management and summary metrics
- âš“ Coast guard dashboard for operational review
- ðŸŒ REST API with bearer API key support
- ðŸ“„ Swagger documentation at `/apidocs/`
- ðŸ—‚ï¸ Image serving for uploaded files

## ðŸ§° Tech Stack

- ðŸ Flask
- ðŸ”‘ Flask-Login
- ðŸ—„ï¸ Flask-SQLAlchemy
- ðŸŒ Flask-CORS
- ðŸ“‹ Flasgger / Swagger
- ðŸ¤– TensorFlow / Keras

## ðŸš€ Installation

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

## âš™ï¸ Configuration

The main settings live in `config.py` and can be overridden with environment variables.

- `SECRET_KEY`
- `DATABASE_URL`
- `UPLOAD_FOLDER`
- `MAX_CONTENT_LENGTH`
- `MODEL_PATH`
- `PREDICTION_THRESHOLD`
- `FLASK_ENV`

Default values are provided for local development, including a SQLite database at `sqlite:///oil_spill.db`.

## â–¶ï¸ Running the App

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

### ðŸ“– API documentation

Open `http://localhost:5000/apidocs/` for the Swagger UI.

## ðŸ‘¤ Default Accounts

The startup script prints demo credentials that are useful for local testing:

- ðŸ‘‘ Admin: `admin@example.com` / `admin123`
- âš“ Coast Guard: `coastguard@example.com` / `coast123`
- ðŸ§ª Demo: `demo@example.com` / `demo123`

> âš ï¸ Change these before using the app in a real environment.

## ðŸ—ºï¸ Main Web Routes

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

## ðŸ”Œ API Endpoints

### ðŸ§  Prediction

- `POST /api/predict`
- Requires a bearer API key for API usage
- Accepts an uploaded image and returns prediction details

### ðŸ“Š Metrics

- `GET /api/accuracy`
- `GET /api/model-stats`

### ðŸš¨ Alerts

- `GET /api/alerts`
- `GET /api/alerts/<alert_id>`
- `POST /api/alerts/<alert_id>/status`
- `POST /api/alerts/<alert_id>/acknowledge`
- `GET /api/alerts/<alert_id>/actions`

### ðŸ‘¥ User management API

- `POST /api/users`

## ðŸ§ª Testing

Run the available checks from the project root:

```bash
python test_app.py
python test_api.py
```

If you only want a quick verification of the model pipeline, use the helper scripts in the repo such as `quick_accuracy_check.py`.

## ðŸ“ Project Structure

```text
MPTRIAL/
â”œâ”€â”€ app.py
â”œâ”€â”€ run.py
â”œâ”€â”€ config.py
â”œâ”€â”€ models.py
â”œâ”€â”€ forms.py
â”œâ”€â”€ utils.py
â”œâ”€â”€ test_app.py
â”œâ”€â”€ test_api.py
â”œâ”€â”€ evaluate_model.py
â”œâ”€â”€ quick_accuracy_check.py
â”œâ”€â”€ model.h5
â”œâ”€â”€ instance/
â”œâ”€â”€ uploads/
â””â”€â”€ README.md
```

## ðŸ“ Notes

- âš ï¸ TensorFlow is optional at import time, but predictions require a valid model.
- ðŸ“‚ Uploaded images are stored under the configured upload folder.
- ðŸ“ The app uses a 224x224 input size and a default prediction threshold of 0.5.

## ðŸ“œ License

MIT 

## ðŸ‘¨â€ðŸ’» Author

Dheeraj
