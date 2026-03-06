# Quick Fix: Import Leads 400 Error

## The Problem

You're getting a 400 Bad Request error when trying to import leads locally.

## Most Likely Cause

The service account is not configured. You need to set **either**:
- `GOOGLE_SERVICE_ACCOUNT_JSON` (recommended)
- `GOOGLE_SERVICE_ACCOUNT_FILE` (file path)

## Quick Fix

### Option 1: Use JSON from Environment Variable (Recommended)

1. **Get your service account JSON:**
   - Open `service_account.json` (if you have it)
   - Or download it from Google Cloud Console

2. **Convert to single-line string:**
   ```python
   import json
   with open('service_account.json', 'r') as f:
       data = json.load(f)
       print(json.dumps(data))  # Copy this output
   ```

3. **Add to your `.env` file:**
   ```env
   GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"...","private_key":"..."}
   ```

### Option 2: Use File Path

1. **Make sure `service_account.json` exists** in your project root

2. **Add to your `.env` file:**
   ```env
   GOOGLE_SERVICE_ACCOUNT_FILE=./service_account.json
   ```

## Check Your Current Setup

Run this to see what's configured:
```python
from app.core.config import get_settings
settings = get_settings()
print(f"JSON set: {settings.google_service_account_json is not None}")
print(f"File set: {settings.google_service_account_file}")
```

## Common 400 Errors

### Error: "Either GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_SERVICE_ACCOUNT_FILE must be set"
**Fix:** Set one of these in your `.env` file

### Error: "Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON"
**Fix:** Make sure JSON is valid and properly escaped (single line)

### Error: "Google Sheet not found"
**Fix:** Check `GOOGLE_SHEETS_ID` is correct

### Error: "Permission denied"
**Fix:** Share the Google Sheet with the service account email

## Test After Fix

1. Restart your backend server
2. Try importing leads again
3. Check the terminal output for detailed error messages

---

**Need Help?** Check the terminal output - it now shows detailed error information!
