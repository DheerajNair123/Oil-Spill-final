# Live Image Sending System - Integration Guide

## Overview

This system enables drones, cameras, and edge devices to capture and send live ocean images to the Oil Spill Detector for real-time analysis and alert generation.

**Key Components:**
- `image_sender.py` â€” Client-side Python script for image capture and transmission
- `test_sender.py` â€” Test script to validate API connectivity
- Backend `/api/predict` endpoint â€” Handles image classification and alert creation
- Dashboard alert polling â€” Automatically displays new detections

## Architecture

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ Device/Drone/Camera                                             â”‚
â”‚ â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                                         â”‚
â”‚ â”‚  Image Source       â”‚ (webcam, file, or edge device API)     â”‚
â”‚ â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                                         â”‚
â”‚            â”‚ (image frames)                                     â”‚
â”‚ â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”â”‚
â”‚ â”‚ image_sender.py                                            â”‚â”‚
â”‚ â”‚ - Capture image                                            â”‚â”‚
â”‚ â”‚ - Build multipart form data (image + location)            â”‚â”‚
â”‚ â”‚ - POST to /api/predict with API key                       â”‚â”‚
â”‚ â”‚ - Handle response & log alerts                            â”‚â”‚
â”‚ â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”˜â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”˜
            â”‚ HTTPS POST                                     â”‚
            â”‚ (multipart/form-data + Bearer Token)          â”‚
            â–¼                                                 â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ Flask Backend (app.py)                                          â”‚
â”‚ â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ â”‚ /api/predict endpoint                                        â”‚
â”‚ â”‚ - Validate API key                                           â”‚
â”‚ â”‚ - Save image to /uploads                                     â”‚
â”‚ â”‚ - Run ML prediction                                          â”‚
â”‚ â”‚ - Create alert if Oil Spill detected                         â”‚
â”‚ â”‚ - Return: {prediction, confidence, image_url, alert}        â”‚
â”‚ â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
â”‚ â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ â”‚ Database                                                     â”‚
â”‚ â”‚ - Prediction record                                          â”‚
â”‚ â”‚ - Alert record (if oil spill)                                â”‚
â”‚ â”‚ - AlertAction record (audit trail)                           â”‚
â”‚ â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
            â–²
            â”‚ Alert polling
            â”‚ (GET /api/alerts)
            â”‚
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ Web Dashboard / Mobile App                                       â”‚
â”‚ - Live alert display                                             â”‚
â”‚ - Alert management                                               â”‚
â”‚ - Image preview                                                  â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

## Quick Start

### 1. Prerequisites

**On Flask Server:**
- Flask app running and accessible (e.g., `http://localhost:5000`)
- API key created for device user in admin panel
- ML model loaded successfully

**On Device/Client:**
```bash
pip install requests
```

### 2. Get an API Key

1. Login to Dashboard as **Admin**
2. Go to **Manage Users**
3. Create a new user with role "coast_guard"
4. Generate API key for that user (or use existing key)
5. Copy the key for use in sender

### 3. Test API Connection

```bash
python test_sender.py --url http://YOUR_SERVER:5000 --key YOUR_API_KEY
```

This will:
- Auto-detect an image from `test/` directory
- Send it to `/api/predict`
- Display prediction results
- Show alert if oil spill detected

**Expected output:**
```
============================================================
Oil Spill Detector - API Test
============================================================

Searching for test images...

Testing /api/predict endpoint...
  Image: sample_oil_spill.jpg
  API URL: http://localhost:5000/api/predict

âœ“ Prediction successful!
  Prediction: Oil Spill
  Confidence: 95.23%
  Image URL: http://localhost:5000/uploads/20260505_143022_sample.jpg
  Processing Time: 245ms
  Alert Created: True

âš ï¸  ALERT DETECTED:
  Alert ID: 42
  Severity: high
  Status: New

============================================================
âœ“ API test passed!
```

### 4. Send Live Images

#### Option A: Single Image Upload

```bash
python image_sender.py \
  --url http://YOUR_SERVER:5000 \
  --key YOUR_API_KEY \
  --location "Arabian Sea - Station A" \
  --latitude 18.520430 \
  --longitude 73.856743 \
  /path/to/captured_image.jpg
```

#### Option B: Directory Monitoring (Auto-Send New Images)

```bash
python image_sender.py \
  --url http://YOUR_SERVER:5000 \
  --key YOUR_API_KEY \
  --location "Drone Flight A" \
  --watch /path/to/capture_directory \
  --poll-interval 5
```

The script will:
- Monitor `/path/to/capture_directory` every 5 seconds
- Send new images as they appear
- Log all predictions and alerts to `image_sender.log`
- Retry failed uploads automatically

## API Endpoint Reference

### POST /api/predict

Send an image for oil spill detection.

**Request:**
```
POST /api/predict HTTP/1.1
Authorization: Bearer YOUR_API_KEY
Content-Type: multipart/form-data

image: <binary image file>
location_label: (optional) "Arabian Sea - Station A"
latitude: (optional) 18.520430
longitude: (optional) 73.856743
```

**Response (200):**
```json
{
  "id": 123,
  "prediction": "Oil Spill",
  "confidence": 0.9523,
  "processing_time": 245,
  "image_url": "http://server:5000/uploads/20260505_143022_image.jpg",
  "alert_created": true,
  "alert": {
    "id": 42,
    "prediction_id": 123,
    "location_label": "Arabian Sea - Station A",
    "latitude": 18.520430,
    "longitude": 73.856743,
    "severity": "high",
    "status": "New",
    "detection_time": "2026-05-05T14:30:22",
    "acknowledged_at": null,
    "resolved_at": null
  }
}
```

**Error Responses:**
- `401` â€” Missing or invalid API key
- `400` â€” No image provided
- `500` â€” ML prediction error

## Integration Examples

### Example 1: Raspberry Pi with USB Camera

```bash
#!/bin/bash
# Capture images every 30 seconds and send to server

API_URL="http://192.168.1.100:5000"
API_KEY="your-api-key-here"
CAPTURE_DIR="/tmp/captures"

mkdir -p $CAPTURE_DIR

# Start image capture in background
while true; do
  timestamp=$(date +%Y%m%d_%H%M%S)
  fswebcam -r 1024x768 "$CAPTURE_DIR/${timestamp}.jpg"
  sleep 30
done &

# Start image sender
python3 image_sender.py \
  --url $API_URL \
  --key $API_KEY \
  --location "Coastal Patrol Point 7" \
  --latitude 18.520430 \
  --longitude 73.856743 \
  --watch $CAPTURE_DIR
```

### Example 2: Drone API Integration

```python
# Integrate image_sender into drone control system
from image_sender import ImageSender
from drone_api import get_drone_image, get_drone_location

sender = ImageSender(
    api_url="http://command-center:5000",
    api_key="drone-key-xyz"
)

while drone.is_flying():
    # Capture from drone
    image_data = get_drone_image()
    image_path = "/tmp/drone_frame.jpg"
    image_data.save(image_path)
    
    # Get drone location
    gps = get_drone_location()
    
    # Send to detector
    result = sender.send_image(
        image_path,
        location_label=f"Drone {drone.id}",
        latitude=gps['lat'],
        longitude=gps['lon']
    )
    
    # Handle alert
    if result.get('alert_created'):
        drone.log_alert(result['alert']['id'])
        # Trigger RTK (return to home) or hover
        drone.hover()
```

### Example 3: Scheduled Cloud Submission

```python
# Send images from edge device to cloud server periodically

import schedule
import time
from image_sender import ImageSender

sender = ImageSender(
    api_url="https://detector.example.com",
    api_key="device-key-abc123"
)

def submit_daily_batch():
    """Send accumulated images from last 24 hours"""
    images = Path('/data/daily_images').glob('*.jpg')
    for img in images:
        result = sender.send_image(
            str(img),
            location_label="Station 5"
        )
        if result.get('alert_created'):
            notify_admin(f"Alert: {result['alert']['id']}")

# Run every day at 2 AM
schedule.every().day.at("02:00").do(submit_daily_batch)

while True:
    schedule.run_pending()
    time.sleep(60)
```

## Dashboard Integration

The existing dashboard automatically displays new alerts via polling (`/api/alerts`).

**No changes needed!** The alert creation happens automatically when `/api/predict` detects oil spill.

**Dashboard features:**
- Real-time alert list with image preview
- Alert status tracking (New â†’ Acknowledged â†’ In Progress â†’ Resolved)
- Location and severity display
- Action audit trail

## Monitoring & Logging

### image_sender.py logs to:
- **Console:** Real-time progress and errors
- **File:** `image_sender.log` â€” Complete audit trail

### Example log output:
```
2026-05-05 14:30:22,145 - INFO - Monitoring directory: /mnt/captures
2026-05-05 14:30:22,146 - INFO - Poll interval: 5s, extensions: ('.jpg', '.jpeg', '.png', '.bmp')
2026-05-05 14:30:27,230 - INFO - Sending image: drone_20260505_143022.jpg
2026-05-05 14:30:28,512 - INFO - âœ“ Prediction: Oil Spill (confidence: 0.9523)
2026-05-05 14:30:28,513 - WARNING - âš ï¸  ALERT CREATED! ID: 42
2026-05-05 14:30:33,102 - INFO - Sending image: drone_20260505_143033.jpg
2026-05-05 14:30:34,221 - INFO - âœ“ Prediction: No Oil Spill (confidence: 0.8821)
```

## Troubleshooting

### "Missing or invalid API key" (401)

**Cause:** API key not found or invalid format

**Solution:**
1. Verify key is copied correctly (no extra spaces)
2. Verify key exists in database (admin panel)
3. Ensure format is: `Bearer YOUR_KEY` (not just key)

### "Connection failed" 

**Cause:** Can't reach Flask server

**Solution:**
```bash
# Test connectivity
curl http://YOUR_SERVER:5000/
python test_sender.py --url http://YOUR_SERVER:5000 --key TEST
```

### "No image provided" (400)

**Cause:** Image file not found or not readable

**Solution:**
- Verify image path is correct: `ls -la /path/to/image.jpg`
- Check file permissions: `chmod 644 /path/to/image.jpg`

### Slow predictions

**Cause:** Large image files or slow network

**Solution:**
- Resize images before sending (e.g., max 1920x1080)
- Increase timeout: `--timeout 60`
- Check network bandwidth

### "Directory polling mode" not picking up images

**Cause:** Wrong file extensions or path

**Solution:**
```bash
# Verify images exist
ls -la /watch/directory/*.jpg

# Check for case sensitivity
python image_sender.py --watch /path --url ... --key ...
```

## Testing Plan

### Phase 1: API Validation âœ“
```bash
python test_sender.py --url http://localhost:5000 --key YOUR_KEY
```
Expected: Successful prediction with alert (if test image contains oil spill)

### Phase 2: Single Image Upload
```bash
python image_sender.py \
  --url http://localhost:5000 \
  --key YOUR_KEY \
  test/oil_spill/sample.jpg
```
Expected: Upload succeeds, alert created, image URL in response

### Phase 3: Directory Monitoring
```bash
# Terminal 1: Start image_sender
python image_sender.py \
  --url http://localhost:5000 \
  --key YOUR_KEY \
  --watch ./test/oil_spill

# Terminal 2: Copy images to monitored directory
cp test/oil_spill/* ./test/oil_spill/copies/
```
Expected: New images detected and sent automatically

### Phase 4: Location Tagging
```bash
python image_sender.py \
  --url http://localhost:5000 \
  --key YOUR_KEY \
  --location "Arabian Sea" \
  --latitude 18.52 \
  --longitude 73.86 \
  test/oil_spill/sample.jpg
```
Expected: Alert includes location data

### Phase 5: Hardware Device
Deploy image_sender.py to:
- Raspberry Pi + USB camera
- Or integrate into drone software
- Or edge device with API

## Performance Notes

| Metric | Value |
|--------|-------|
| Avg prediction time | 200-300ms |
| Image upload time | 0.5-2s (network dependent) |
| Alert creation | <100ms |
| Dashboard refresh | 5-10s (polling interval) |
| Max concurrent uploads | Limited by Flask workers |

## Security Considerations

âœ“ API key authentication required
âœ“ HTTPS recommended for production
âœ“ Image files stored on server
âœ“ Audit trail of all predictions
âœ“ User-based access control

**Recommendations:**
1. Use HTTPS in production (TLS)
2. Rotate API keys periodically
3. Monitor image_sender.log for errors
4. Set up firewall rules to limit API access
5. Use VPN for remote devices

## Files Reference

| File | Purpose |
|------|---------|
| `image_sender.py` | Main client-side sender (single + batch) |
| `test_sender.py` | API test/validation script |
| `app.py` | Flask backend (modified: added image_url to response) |
| `image_sender.log` | Client-side logs |

## Support

For issues or questions:
1. Check `image_sender.log` for error details
2. Run `test_sender.py --url ... --key ... -v` for verbose output
3. Verify API key and URL are correct
4. Check Flask app logs on server
5. Verify ML model is loaded (`âœ“ ML Model loaded successfully`)

