#!/usr/bin/env python3
"""
Test script for Oil Spill Detector API
======================================
Quick validation of API endpoints and image upload functionality.
"""

import os
import sys
import json
import argparse
from pathlib import Path

import requests


def test_api_predict(api_url: str, api_key: str, image_path: str, verbose: bool = False) -> bool:
    """Test /api/predict endpoint with an image file."""
    
    if not os.path.exists(image_path):
        print(f"✗ Image file not found: {image_path}")
        return False
    
    try:
        with open(image_path, 'rb') as f:
            files = {'image': f}
            headers = {'Authorization': f'Bearer {api_key}'}
            
            print(f"\nTesting /api/predict endpoint...")
            print(f"  Image: {os.path.basename(image_path)}")
            print(f"  API URL: {api_url}/api/predict")
            
            response = requests.post(
                f"{api_url}/api/predict",
                files=files,
                headers=headers,
                timeout=30
            )
            
            if verbose:
                print(f"  Status Code: {response.status_code}")
            
            response.raise_for_status()
            result = response.json()
            
            if 'error' in result:
                print(f"✗ API Error: {result['error']}")
                return False
            
            print(f"✓ Prediction successful!")
            print(f"  Prediction: {result.get('prediction')}")
            print(f"  Confidence: {result.get('confidence', 'N/A'):.2%}")
            print(f"  Image URL: {result.get('image_url')}")
            print(f"  Processing Time: {result.get('processing_time', 'N/A')}ms")
            print(f"  Alert Created: {result.get('alert_created')}")
            
            if result.get('alert_created'):
                alert = result.get('alert', {})
                print(f"\n⚠️  ALERT DETECTED:")
                print(f"  Alert ID: {alert.get('id')}")
                print(f"  Severity: {alert.get('severity')}")
                print(f"  Status: {alert.get('status')}")
            
            if verbose:
                print(f"\nFull Response:\n{json.dumps(result, indent=2)}")
            
            return True
            
    except requests.exceptions.ConnectionError:
        print(f"✗ Connection error - check API URL: {api_url}")
        return False
    except requests.exceptions.Timeout:
        print(f"✗ Request timeout")
        return False
    except requests.exceptions.HTTPError as e:
        print(f"✗ HTTP Error: {e.response.status_code}")
        try:
            print(f"  Response: {e.response.json()}")
        except:
            print(f"  Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_with_sample_image(api_url: str, api_key: str) -> bool:
    """Test with first available image from test/ directory."""
    test_dir = Path('test')
    
    if not test_dir.exists():
        print("⚠️  test/ directory not found")
        return False
    
    # Find first image
    for ext in ['.jpg', '.jpeg', '.png', '.bmp']:
        images = list(test_dir.glob(f'**/*{ext}'))
        images += list(test_dir.glob(f'**/*{ext.upper()}'))
        
        if images:
            return test_api_predict(api_url, api_key, str(images[0]))
    
    print("⚠️  No test images found in test/ directory")
    print("   Checked: test/no_oil_spill/ and test/oil_spill/")
    return False


def main():
    parser = argparse.ArgumentParser(
        description='Test Oil Spill Detector API',
        epilog="""
Examples:
  # Test with auto-detected image from test/ directory
  python test_api.py --url http://localhost:5000 --key YOUR_API_KEY
  
  # Test with specific image
  python test_api.py --url http://localhost:5000 --key YOUR_API_KEY \\
    --image test/oil_spill/sample.jpg
  
  # Verbose output
  python test_api.py --url http://localhost:5000 --key YOUR_API_KEY -v
        """
    )
    
    parser.add_argument('--url', required=True, help='API base URL (e.g., http://localhost:5000)')
    parser.add_argument('--key', required=True, help='API Key')
    parser.add_argument('--image', help='Image file to test (auto-finds from test/ if not provided)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Oil Spill Detector - API Test")
    print("=" * 60)
    
    if args.image:
        success = test_api_predict(args.url, args.key, args.image, args.verbose)
    else:
        print("\nSearching for test images...")
        success = test_with_sample_image(args.url, args.key)
    
    print("\n" + "=" * 60)
    if success:
        print("✓ API test passed!")
        sys.exit(0)
    else:
        print("✗ API test failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
