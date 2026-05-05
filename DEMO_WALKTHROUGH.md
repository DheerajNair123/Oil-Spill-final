# ðŸš€ Live Image Sending - Complete Demonstration

## Part 1: Get Your API Key

### Step 1: Access the Flask Dashboard

**URL:** `http://localhost:5000` (or your server IP:5000)

The login page should greet you. If this is your first time:

1. **Create the first admin account**
   - Go to `http://localhost:5000/register`
   - Fill in:
     - Username: `admin`
     - Email: `admin@oildetector.local`
     - Password: `SecurePassword123!`
   - Click "Create Account"

2. **Login with admin credentials**
   - Go to `http://localhost:5000/login`
   - Email: `admin@oildetector.local`
   - Password: `SecurePassword123!`
   - Click "Sign In"

### Step 2: Create a Device User

Once logged in as admin, you'll see the Dashboard with "Manage Users" option.

**Path:** Admin Dashboard â†’ Users â†’ Create User

**Fill in:**
```
Username: drone-device-1
Email: drone@patrol.local
Role: coast_guard
Password: DronePassword456!
```

Click "Create User" âœ“

### Step 3: Generate API Key for Device

In the admin dashboard:
1. Navigate to **Admin Users Management**
2. Find the user "drone-device-1"
3. Click on user to view details
4. Click **"Generate API Key"** button

You'll see a long string that looks like:
```
YOUR_API_KEY_HERE
```

**âš ï¸ IMPORTANT:** Copy this key immediately! It won't be shown again.

---

## Part 2: Test the API

Open a terminal and run:

```bash
python test_sender.py --url http://localhost:5000 --key YOUR_API_KEY_HERE
```

### Expected Output:

```
============================================================
Oil Spill Detector - API Test
============================================================

Searching for test images...

Testing /api/predict endpoint...
  Image: oil_spill_sample.jpg
  API URL: http://localhost:5000/api/predict

âœ“ Prediction successful!
  Prediction: Oil Spill
  Confidence: 0.9523
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

If you see this âœ“, your API key works!

---

## Part 3: Send Your First Image

### Single Image Upload

```bash
python image_sender.py \
  --url http://localhost:5000 \
  --key YOUR_API_KEY_HERE \
  --location "Patrol Station A" \
  --latitude 18.520430 \
  --longitude 73.856743 \
  test/oil_spill/sample_image.jpg
```

### Expected Output:

```
2026-05-05 14:30:22,145 - INFO - Sending image: sample_image.jpg
2026-05-05 14:30:24,512 - INFO - âœ“ Prediction: Oil Spill (confidence: 0.9523)
2026-05-05 14:30:24,513 - WARNING - âš ï¸  ALERT CREATED! ID: 42
```

âœ“ Image sent successfully!

Check the dashboard â†’ you'll see new alert instantly

---

## Part 4: Monitor a Live Directory

This is the real powerâ€”automatically send images as they arrive:

### Terminal 1: Start Image Sender

```bash
python image_sender.py \
  --url http://localhost:5000 \
  --key YOUR_API_KEY_HERE \
  --location "Drone Flight 7" \
  --watch ./test/oil_spill \
  --poll-interval 3
```

**Output:**
```
2026-05-05 14:35:00,100 - INFO - Monitoring directory: ./test/oil_spill
2026-05-05 14:35:00,101 - INFO - Poll interval: 3s, extensions: ('.jpg', '.jpeg', '.png', '.bmp')
[waiting for images...]
```

### Terminal 2: Simulate Camera Capturing Images

```bash
cp test/oil_spill/sample1.jpg ./test/oil_spill/new_capture_1.jpg
cp test/oil_spill/sample2.jpg ./test/oil_spill/new_capture_2.jpg
```

### Watch Terminal 1 Automatically Detect & Send:

```
2026-05-05 14:35:05,234 - INFO - Sending image: new_capture_1.jpg
2026-05-05 14:35:07,512 - INFO - âœ“ Prediction: Oil Spill (confidence: 0.8934)
2026-05-05 14:35:07,513 - WARNING - âš ï¸  ALERT CREATED! ID: 43

[3 seconds pass...]

2026-05-05 14:35:10,456 - INFO - Sending image: new_capture_2.jpg
2026-05-05 14:35:12,789 - INFO - âœ“ Prediction: Oil Spill (confidence: 0.9234)
2026-05-05 14:35:12,790 - WARNING - âš ï¸  ALERT CREATED! ID: 44
```

---

## Part 5: View Alerts in Dashboard

While `image_sender.py` is running and sending images:

1. **Open Dashboard:** `http://localhost:5000/dashboard`
2. **See Real-Time Alerts** appearing automatically
3. **Click on Alert** to see:
   - Predicted image
   - Location (latitude/longitude)
   - Confidence score
   - Alert severity
   - Detection time

4. **Manage Alert:**
   - Mark as "Acknowledged" â†’ Acknowledged âœ“
   - Add notes about action taken
   - Update status to "In Progress" or "Resolved"

---

## Complete Example: Drone Integration

### Real-World Scenario

You have a drone that captures images every 5 seconds and stores them to a USB drive.

```bash
#!/bin/bash
# on_drone.sh - Run on drone's edge computer

# Configuration
API_URL="http://command-center.local:5000"
API_KEY="YOUR_API_KEY_HERE"
LOCATION="Indian Ocean - Patrol Route Alpha"
CAPTURE_DIR="/mnt/usb_drive/captures"
LATITUDE="18.520430"
LONGITUDE="73.856743"

# Start the image sender (monitors captures folder)
python3 /home/drone/image_sender.py \
  --url $API_URL \
  --key $API_KEY \
  --location "$LOCATION" \
  --latitude $LATITUDE \
  --longitude $LONGITUDE \
  --watch $CAPTURE_DIR \
  --poll-interval 5 &

SENDER_PID=$!

# Meanwhile, drone captures images
while drone.is_flying(); do
  timestamp=$(date +%Y%m%d_%H%M%S)
  drone.capture_image("/mnt/usb_drive/captures/${timestamp}.jpg")
  
  # Update location if available
  gps_data=$(drone.get_gps())
  # Could update coordinates here
  
  sleep 5
done

# Stop sender when drone lands
kill $SENDER_PID
```

### What Happens:

1. **Drone captures** image â†’ saves to USB folder
2. **image_sender.py** detects new file (every 5 seconds)
3. **Sends image** to Flask server with location
4. **Flask runs** ML prediction (200-300ms)
5. **If Oil Spill detected:**
   - Alert created in database
   - Severity assigned (low/medium/high)
   - Logged to audit trail
6. **Command center admin** sees alert on dashboard
   - Can view image
   - See exact GPS coordinates
   - Acknowledge/investigate

---

## Verification Checklist

### âœ“ API Key Setup
```
â–¡ Admin account created
â–¡ Device user created (drone-device-1)
â–¡ API key generated
â–¡ API key copied and stored safely
```

### âœ“ API Testing
```bash
python test_sender.py --url http://localhost:5000 --key YOUR_KEY

â–¡ Test passes with "âœ“ API test passed!"
â–¡ Sees sample prediction result
â–¡ Shows image URL in response
```

### âœ“ Single Image Upload
```bash
python image_sender.py --url http://localhost:5000 --key YOUR_KEY test/oil_spill/sample.jpg

â–¡ Image sent successfully
â–¡ Alert created if oil spill
â–¡ Alert visible in dashboard
â–¡ Processing time < 1 second
```

### âœ“ Directory Monitoring
```bash
python image_sender.py --url http://localhost:5000 --key YOUR_KEY --watch ./test/oil_spill

â–¡ Detects new images automatically
â–¡ Sends them without intervention
â–¡ Logs all activity to image_sender.log
â–¡ Can handle multiple images in sequence
```

### âœ“ Dashboard Integration
```
â–¡ Dashboard loads at http://localhost:5000/dashboard
â–¡ Alerts appear in real-time
â–¡ Can click alert to see details
â–¡ Can update alert status
â–¡ Location data visible (if provided)
```

---

## Troubleshooting During Demo

### "Invalid API key" error

**Problem:** Key doesn't work
```
âœ— API Error: Invalid API key
```

**Solution:**
1. Copy key again from admin panel (exactly as shown)
2. Verify no extra spaces: `--key "YOUR_API_KEY_HERE"` (use quotes)
3. Check key hasn't expired (admin can regenerate)

### "Connection failed"

**Problem:** Can't reach server
```
âœ— Connection failed - check API URL and network
```

**Solution:**
```bash
# Test if server is running
curl http://localhost:5000

# Test if port is open
netstat -an | grep 5000

# Check Flask is still running in other terminal
```

### "No image provided" error

**Problem:** Image file not found
```
âœ— Image file not found
```

**Solution:**
```bash
# Verify image exists
ls -la test/oil_spill/sample_image.jpg

# Use absolute path
python image_sender.py --url ... --key ... C:\path\to\image.jpg
```

---

## Performance During Demo

| Operation | Time | Status |
|-----------|------|--------|
| API key generation | ~1s | âœ“ Instant |
| Image upload | 0.5-2s | âœ“ Fast |
| ML prediction | 200-300ms | âœ“ Real-time |
| Alert creation | <100ms | âœ“ Immediate |
| Dashboard refresh | 5-10s | âœ“ Quick polling |
| Total end-to-end | ~2-3s | âœ“ Production-ready |

---

## Next: Deploy to Real Device

Once you've verified everything works locally:

1. **Raspberry Pi** â€” Copy `image_sender.py`, install Python + requests
2. **Drone** â€” Integrate with drone control software
3. **Cloud Server** â€” Update `--url` to server IP/domain
4. **Production** â€” Use HTTPS, firewall rules, VPN

All the same commands work!

---

## Quick Reference Commands

```bash
# Get help
python image_sender.py --help
python test_sender.py --help

# Test API
python test_sender.py --url http://localhost:5000 --key YOUR_KEY

# Single image
python image_sender.py --url http://localhost:5000 --key YOUR_KEY image.jpg

# With location
python image_sender.py --url http://localhost:5000 --key YOUR_KEY \
  --location "Station A" --latitude 18.52 --longitude 73.86 image.jpg

# Monitor folder
python image_sender.py --url http://localhost:5000 --key YOUR_KEY --watch /captures

# View logs
tail -f image_sender.log
```

---

**Ready to get started? Follow the steps above and you'll have live image sending working in minutes!**



