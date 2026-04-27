import requests
from pathlib import Path
import json

# Configuration
API_URL = "http://localhost:8000"
TEST_IMAGE_PATH = "test_image.jpg"  # Replace with your test image

def test_health():
    """Test if API is running"""
    try:
        response = requests.get(f"{API_URL}/")
        print("✓ Health Check:")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.json()}\n")
        return response.status_code == 200
    except Exception as e:
        print(f"✗ Health Check Failed: {e}\n")
        return False

def test_prediction(image_path=TEST_IMAGE_PATH):
    """Test prediction with an image"""
    if not Path(image_path).exists():
        print(f"✗ Test image not found: {image_path}")
        print(f"  Please provide a test image at {image_path}\n")
        return False

    try:
        with open(image_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{API_URL}/predict/", files=files)

        print("✓ Prediction Test:")
        print(f"  Status: {response.status_code}")
        result = response.json()
        print(f"  Result: {json.dumps(result, indent=2)}\n")
        return response.status_code == 200
    except Exception as e:
        print(f"✗ Prediction Test Failed: {e}\n")
        return False

def test_invalid_file():
    """Test error handling with invalid file"""
    try:
        files = {'file': ('test.txt', b'not an image')}
        response = requests.post(f"{API_URL}/predict/", files=files)

        print("✓ Invalid File Test:")
        print(f"  Status: {response.status_code}")
        if response.status_code >= 400:
            print(f"  Correctly rejected invalid file: {response.json()['detail']}\n")
            return True
    except Exception as e:
        print(f"✗ Invalid File Test Failed: {e}\n")
    return False

if __name__ == "__main__":
    print("=" * 50)
    print("Oil Spill Detection API - Test Suite")
    print("=" * 50 + "\n")

    # Run tests
    test_health()
    test_prediction(TEST_IMAGE_PATH)
    test_invalid_file()

    print("=" * 50)
    print("Testing complete!")
    print("=" * 50)
