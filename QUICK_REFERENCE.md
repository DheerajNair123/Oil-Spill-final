# Quick Reference - Live Image Sending

## Installation

```bash
pip install requests
```

## Common Commands

### Test API Connection
```bash
python test_sender.py --url http://localhost:5000 --key YOUR_API_KEY
```

### Send Single Image
```bash
python image_sender.py \
  --url http://localhost:5000 \
  --key YOUR_API_KEY \
  /path/to/image.jpg
```

### Send with Location
```bash
python image_sender.py \
  --url http://localhost:5000 \
  --key YOUR_API_KEY \
  --location "Station A" \
  --latitude 18.52 \
  --longitude 73.86 \
  /path/to/image.jpg
```

### Monitor Directory
```bash
python image_sender.py \
  --url http://localhost:5000 \
  --key YOUR_API_KEY \
  --watch /path/to/image_folder \
  --poll-interval 5
```

### Get Help
```bash
python image_sender.py --help
python test_sender.py --help
```

## Response Indicators

| Status | Meaning | Action |
|--------|---------|--------|
| `âœ“ Prediction successful` | Oil classification done | Check result |
| `âš ï¸ ALERT CREATED` | Oil spill detected | Check alert ID and severity |
| `âœ— Connection failed` | Can't reach server | Verify URL and network |
| `âœ— API Error` | Server returned error | Check API key and logs |

## Logging

View real-time logs:
```bash
tail -f image_sender.log
```

View with alerts only:
```bash
grep -i "alert\|error" image_sender.log
```

## API Key Management

**Create new API key (Admin):**
1. Login as Admin
2. Dashboard â†’ Manage Users â†’ Select User
3. Generate API Key
4. Copy full key

**Note:** Key format is a long alphanumeric string (not "Bearer ..." part)

## Typical Workflow

```
1. Get API key from admin
2. Test connection:
   python test_sender.py --url http://server:5000 --key KEY
   
3. Single image test:
   python image_sender.py --url http://server:5000 --key KEY image.jpg
   
4. If working, monitor directory:
   python image_sender.py --url http://server:5000 --key KEY --watch captures
   
5. Check dashboard for alerts:
   http://server:5000/dashboard
```

## Environment Variables (Optional)

```bash
# Set environment variables to avoid typing
export OIL_DETECTOR_URL="http://localhost:5000"
export OIL_DETECTOR_KEY="your-api-key"

# Then use shorter commands
python image_sender.py $OIL_DETECTOR_URL $OIL_DETECTOR_KEY image.jpg
```

## Docker Integration

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY image_sender.py requirements.txt ./
RUN pip install requests

ENTRYPOINT ["python", "image_sender.py"]
```

Build and run:
```bash
docker build -t oil-detector-sender .
docker run -v /data/captures:/captures oil-detector-sender \
  --url http://detector:5000 \
  --key YOUR_KEY \
  --watch /captures
```

## Systemd Service (Linux)

Create `/etc/systemd/system/oil-sender.service`:

```ini
[Unit]
Description=Oil Spill Detector Image Sender
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=oil-sender
WorkingDirectory=/opt/oil-sender
ExecStart=/usr/bin/python3 image_sender.py \
  --url http://detector.local:5000 \
  --key YOUR_API_KEY \
  --location "Patrol Zone 7" \
  --watch /mnt/camera/captures

Restart=on-failure
RestartSec=30s

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable oil-sender
sudo systemctl start oil-sender
sudo systemctl status oil-sender
```

## Cron Job (Periodic Submission)

```bash
# Submit images hourly (run from /opt/oil-sender/)
0 * * * * /usr/bin/python3 /opt/oil-sender/image_sender.py \
  --url http://detector:5000 \
  --key YOUR_KEY \
  --watch /data/hourly_captures >> /var/log/oil-sender.log 2>&1
```

## Monitoring Health

```bash
# Check if sender is running
ps aux | grep image_sender

# Check recent predictions
tail -20 image_sender.log | grep "Prediction\|ALERT"

# Count alerts in last hour
grep "$(date +%Y-%m-%d\ %H:)" image_sender.log | grep -i alert | wc -l

# Test connectivity
curl -I http://localhost:5000/api/predict
```

## Troubleshooting Commands

```bash
# Test API availability
curl http://localhost:5000/

# Check with API key
curl -H "Authorization: Bearer YOUR_KEY" \
  -F "image=@test_image.jpg" \
  http://localhost:5000/api/predict

# Verbose test
python test_sender.py --url http://localhost:5000 --key YOUR_KEY -v

# Check Python dependencies
python -c "import requests; print('âœ“ requests installed')"

# Verify image file
file test_image.jpg
identify test_image.jpg  # (requires ImageMagick)
```

## Performance Tuning

```bash
# Increase timeout for slow networks
python image_sender.py --url http://server:5000 --key KEY --timeout 60 image.jpg

# Monitor system resources
while true; do free -h; sleep 5; done

# Check network latency
ping -c 4 server.local
```

## Integration Checklist

- [ ] API key obtained and tested
- [ ] Test script passes: `test_sender.py`
- [ ] Single image upload works
- [ ] Directory monitoring works
- [ ] Location tagging verified
- [ ] Dashboard shows alerts automatically
- [ ] Logs being written to `image_sender.log`
- [ ] Retry logic tested (disconnect test)
- [ ] Device ready for deployment

## Quick Stats

| Operation | Time |
|-----------|------|
| API prediction | ~250ms |
| Upload (1-5 Mbps) | 0.5-2s |
| Alert notification | <1s |
| Dashboard refresh | 5-10s |

---

**For detailed documentation, see:** `LIVE_IMAGE_SENDING.md`

