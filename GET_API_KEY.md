# ðŸ”‘ HOW TO GET YOUR API KEY - Visual Guide

## The Simplest Way: Use the Python Script

### Step 1: Open Terminal
```
cd C:\Users\dheer\Documents\ChromebookFiles\Dheeraj\windows\Downloads\college\semVII\MPTRIAL
```

### Step 2: Run This Command
```bash
python generate_api_key.py drone@maritime.local
```

### Step 3: You'll See This Output
```
============================================================
Generating API Key for: drone_device_1
Email: drone@maritime.local
Role: coast_guard
============================================================

âœ“ API Key Generated Successfully!

API Key Details:
  ID:       45a4c232-16a8-4aa2-85d4-801ce5d4c53c
  Name:     Default API Key
  Created:  2026-05-05 05:08:16.432119
  Status:   Active

============================================================
YOUR API KEY:
============================================================

YOUR_API_KEY_HERE

============================================================

âš ï¸  IMPORTANT: Copy and save this key in a safe place!
   It won't be shown again.
```

### Step 4: Copy Your Key
```
YOUR_API_KEY_HERE
```

### Step 5: Use It!
```bash
python image_sender.py \
  --url http://localhost:5000 \
  --key YOUR_API_KEY_HERE \
  image.jpg
```

---

## OR: Use the Admin Dashboard (GUI Method)

### Step 1: Login as Admin
```
URL: http://localhost:5000/login
Email: admin@example.com
Password: admin123
```

### Step 2: Navigate to Users
```
Dashboard â†’ Admin Users Management
```

### Step 3: Create a New User
```
Username: drone_device_1
Email: drone@maritime.local
Password: TempPass123!
Role: Coast Guard
```

### Step 4: Click "Create User"
The user will be created and added to the system.

### Step 5: Find the User in List
Look for "drone_device_1" in the Users table.

### Step 6: Generate API Key
Click on the user â†’ "Generate API Key" button.

### Step 7: Copy the Key
The key will appear in a popup. Copy it immediately!

---

## Already Have a User? Here's How to Generate a Key

If you already have a user account (e.g., `coastguard@example.com`):

### Command Format
```bash
python generate_api_key.py your_user_email@example.com
```

### Example
```bash
python generate_api_key.py coastguard@example.com
```

### Output
```
============================================================
Generating API Key for: coastguard
Email: coastguard@example.com
Role: coast_guard
============================================================

âœ“ API Key Generated Successfully!
...
YOUR API KEY:
YOUR_API_KEY_HERE
============================================================
```

---

## For Each User: One Python Command

| User | Command |
|------|---------|
| drone_device_1 | `python generate_api_key.py drone@maritime.local` |
| demo | `python generate_api_key.py demo@example.com` |
| cg_officer1 | `python generate_api_key.py officer1@coastguard.local` |
| Any new user | `python generate_api_key.py their_email@domain.com` |

---

## What Each Part Means

```
YOUR_API_KEY_HERE
â”‚         â”‚
â”‚         â””â”€ Random hex string (unique for this key)
â”‚            (48 characters long)
â”‚
â””â”€ Prefix indicating:
   "sk" = Secret Key
   "live" = Production/Live environment
```

---

## Safety Tips

### âœ… DO:
- Copy key immediately after generation
- Save it securely (password manager, vault)
- Share with trusted users only
- Rotate keys periodically

### âŒ DON'T:
- Share key via email or chat
- Commit key to GitHub
- Use in logs or debugging output
- Share with untrusted devices

---

## The Keys Used in This Demo

| User | Email | Key | Generated | Status |
|------|-------|-----|-----------|--------|
| drone_device_1 | drone@maritime.local | `YOUR_API_KEY_HERE` | 2026-05-05 | âœ… Active |
| demo | demo@example.com | (already exists) | 2026-04-21 | âœ… Active |

---

## Quick Start With Your Key

Once you have your key, it's easy:

### Test
```bash
python test_sender.py \
  --url http://localhost:5000 \
  --key YOUR_API_KEY_HERE
```

### Send Image
```bash
python image_sender.py \
  --url http://localhost:5000 \
  --key YOUR_API_KEY_HERE \
  image.jpg
```

### Monitor Folder
```bash
python image_sender.py \
  --url http://localhost:5000 \
  --key YOUR_API_KEY_HERE \
  --watch /folder/with/images
```

---

## Troubleshooting

### "Key not found" error?
```
Step 1: Verify email address is correct
Step 2: Make sure user exists in database
Step 3: Check user is active (not disabled)
```

### "Invalid API key" when using key?
```
Step 1: Copy key exactly (no spaces)
Step 2: Verify key is still active
Step 3: Try generating a new key
```

### Lost your key?
```
Generate a new one:
python generate_api_key.py your_email@example.com

Old keys don't work anymore (safely invalidated)
```

---

## Summary

### Easiest Way to Get a Key:
```bash
python generate_api_key.py user_email@example.com
```

### Then Use It Like This:
```bash
python image_sender.py \
  --url http://localhost:5000 \
  --key YOUR_API_KEY_HERE \
  image.jpg
```

### You'll See:
```
âœ“ Success!
  Prediction: Oil Spill
  Confidence: 99%
  Alert ID: xxx-xxx-xxx
```

---

## Need More Keys?

Each user can have multiple keys (for different devices):

```bash
# Generate first key for drone_device_1
python generate_api_key.py drone@maritime.local

# Generate second key for same user (different device)
python generate_api_key.py drone@maritime.local

# Both keys work! Can use on different devices/locations
```

---

## For Admin: Creating Keys for Others

If you're the admin creating keys for your team:

### For a drone operator:
```bash
# 1. Create user (via admin dashboard or script)
# 2. Generate key
python generate_api_key.py drone_operator@company.com

# 3. Send them: 
#    - Email to use for login
#    - Temporary password
#    - API key for image_sender.py
```

### For a mobile app user:
```bash
# Generate the same way
python generate_api_key.py mobile_user@company.com

# They can then use key with:
# - Mobile app API calls
# - Python image_sender.py
# - Any HTTP client
```

---

## That's It!

**You now know how to:**
1. âœ… Get an API key
2. âœ… Use it with image_sender.py
3. âœ… Send images to the detector
4. âœ… See alerts on dashboard

**Start with:**
```bash
python generate_api_key.py your_email@example.com
```

**Then use:**
```bash
python image_sender.py --url http://localhost:5000 --key YOUR_KEY image.jpg
```

**Done! ðŸŽ‰**



