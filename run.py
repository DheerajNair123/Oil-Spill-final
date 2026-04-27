#!/usr/bin/env python
"""
Run script for Oil Spill Detector application
Handles initialization and startup
"""

import os
import sys
from app import create_app
from models import db

def main():
    """
    Initialize and run the Flask application
    """
    # Get the config from environment or default to development
    config_name = os.environ.get('FLASK_ENV', 'development')
    
    # Create the Flask app
    app, prediction_service = create_app(config_name)
    
    # Create database if it doesn't exist
    with app.app_context():
        db.create_all()
    
    # Print startup information
    print("\n" + "="*70)
    print(" " * 15 + "🌊 OIL SPILL DETECTOR SYSTEM")
    print("="*70)
    print(f"\nConfiguration: {config_name.upper()}")
    print(f"Debug Mode: {app.debug}")
    print(f"Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"Upload Folder: {app.config['UPLOAD_FOLDER']}")
    print(f"Model: {app.config['MODEL_PATH']}")
    
    if prediction_service:
        print("✓ ML Model: Loaded successfully")
    else:
        print("✗ ML Model: Failed to load - using dummy predictions")
    
    print("\n" + "-"*70)
    print("Starting server...")
    print("-"*70)
    print("\n🚀 Server running on: http://localhost:5000")
    print("\nDefault Credentials (change immediately in production):")
    print("  Admin    - Email: admin@example.com  | Password: admin123")
    print("  Coast Guard - Email: coastguard@example.com | Password: coast123")
    print("  Demo        - Email: demo@example.com       | Password: demo123")
    print("\nAPI Documentation: http://localhost:5000/apidocs/")
    print("\nPress CTRL+C to stop the server\n")
    
    # Run the application
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=app.debug,
        use_reloader=True
    )

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nServer stopped.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
