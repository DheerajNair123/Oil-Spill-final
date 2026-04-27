#!/usr/bin/env python
"""
Database initialization script
Run this before starting the application for the first time
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from models import db, User

def init_database():
    """Initialize the database and create an admin user"""
    app, _ = create_app('development')
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print("✓ Database tables created")
        
        # Check if admin user exists
        admin_user = User.query.filter_by(email='admin@example.com').first()
        
        if not admin_user:
            # Create admin user
            admin_user = User(
                username='admin',
                email='admin@example.com',
                role='admin',
                is_active=True
            )
            admin_user.set_password('admin123')
            
            db.session.add(admin_user)
            db.session.commit()
            print("✓ Admin user created (email: admin@example.com, password: admin123)")
            print("  ⚠️  IMPORTANT: Change the admin password immediately!")
        else:
            print("✓ Admin user already exists")
        
        # Create a coast guard user
        coast_guard_user = User.query.filter_by(email='coastguard@example.com').first()
        
        if not coast_guard_user:
            coast_guard_user = User(
                username='coastguard',
                email='coastguard@example.com',
                role='coast_guard',
                is_active=True
            )
            coast_guard_user.set_password('coast123')
            
            db.session.add(coast_guard_user)
            db.session.commit()
            print("✓ Coast guard user created (email: coastguard@example.com, password: coast123)")
        else:
            print("✓ Coast guard user already exists")

        # Backward-compatible demo user remains as a coast guard account
        demo_user = User.query.filter_by(email='demo@example.com').first()
        
        if not demo_user:
            demo_user = User(
                username='demo',
                email='demo@example.com',
                role='coast_guard',
                is_active=True
            )
            demo_user.set_password('demo123')
            
            db.session.add(demo_user)
            db.session.commit()
            print("✓ Demo user created (email: demo@example.com, password: demo123)")
        else:
            print("✓ Demo user already exists")
        
        print("\n" + "="*50)
        print("DATABASE INITIALIZATION COMPLETE")
        print("="*50)
        print("\nYou can now run: python app.py")

if __name__ == '__main__':
    init_database()
