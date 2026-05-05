#!/usr/bin/env python3
"""
Generate an API Key for a user - Quick Script
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from models import db, User, APIKey
import uuid

def generate_api_key_for_user(email: str, key_name: str = "Default API Key"):
    """Generate and display an API key for a user"""
    app, _ = create_app('development')
    
    with app.app_context():
        # Find user
        user = User.query.filter_by(email=email).first()
        
        if not user:
            print(f"✗ User not found: {email}")
            return None
        
        print(f"\n{'='*60}")
        print(f"Generating API Key for: {user.username}")
        print(f"Email: {user.email}")
        print(f"Role: {user.role}")
        print(f"{'='*60}\n")
        
        # Generate API key
        api_key_value = f"sk_live_{uuid.uuid4().hex[:32]}"
        
        api_key = APIKey(
            user_id=user.id,
            key=api_key_value,
            name=key_name
        )
        
        db.session.add(api_key)
        db.session.commit()
        
        print(f"✓ API Key Generated Successfully!")
        print(f"\nAPI Key Details:")
        print(f"  ID:       {api_key.id}")
        print(f"  Name:     {api_key.name}")
        print(f"  Created:  {api_key.created_at}")
        print(f"  Status:   Active")
        
        print(f"\n{'='*60}")
        print(f"YOUR API KEY:")
        print(f"{'='*60}")
        print(f"\n{api_key_value}\n")
        print(f"{'='*60}")
        
        print(f"\n⚠️  IMPORTANT: Copy and save this key in a safe place!")
        print(f"   It won't be shown again.\n")
        
        print(f"Usage in image_sender.py:")
        print(f"\n  python image_sender.py \\")
        print(f"    --url http://localhost:5000 \\")
        print(f"    --key {api_key_value} \\")
        print(f"    --location \"Station A\" \\")
        print(f"    /path/to/image.jpg\n")
        
        return api_key_value


if __name__ == '__main__':
    if len(sys.argv) > 1:
        email = sys.argv[1]
    else:
        # Default to the drone_device_1 user we just created
        email = "drone@maritime.local"
    
    api_key = generate_api_key_for_user(email)
    
    if not api_key:
        sys.exit(1)
