# Debugging Import Leads 500 Error on Render

## How to See the Actual Error

The error is being logged to Render's logs. Here's how to see it:

1. **Go to Render Dashboard**
2. **Click on your backend service**
3. **Click "Logs" tab**
4. **Look for lines starting with `=== IMPORT LEADS ERROR ===`**

The logs will show:
- Error Type
- Error Message  
- Whether JSON or file is being used
- Google Sheets ID
- Full traceback

## Most Common Issues on Render

### Issue 1: JSON Not Properly Escaped

**Problem:** The JSON in the environment variable has line breaks or unescaped quotes.

**Solution:**
1. Get your service account JSON
2. Convert to single-line:
   ```python
   import json
   with open('service_account.json', 'r') as f:
       data = json.load(f)
       print(json.dumps(data))  # Copy this - it's already single-line
   ```
3. In Render dashboard → Environment → `GOOGLE_SERVICE_ACCOUNT_JSON`
4. Paste the single-line JSON (no line breaks!)
5. Save and redeploy

### Issue 2: JSON Truncated

**Problem:** Render might truncate very long environment variables.

**Check:**
- Look at the JSON preview in the error message
- If it's cut off, the JSON might be too long
- Try using the file method instead

### Issue 3: Missing Required Fields

**Problem:** JSON is valid but missing required fields.

**Check the error message** - it will tell you which fields are missing:
- `type`
- `project_id`
- `private_key`
- `client_email`

### Issue 4: Invalid Credentials

**Problem:** Service account credentials are wrong or expired.

**Solution:**
1. Go to Google Cloud Console
2. Download a fresh service account JSON
3. Update `GOOGLE_SERVICE_ACCOUNT_JSON` in Render

### Issue 5: Google Sheets Not Shared

**Problem:** Sheet exists but service account doesn't have access.

**Solution:**
1. Open your Google Sheet
2. Click "Share"
3. Add: `ai-auto@robust-chess-427018-j2.iam.gserviceaccount.com`
4. Give it "Viewer" access
5. Click "Send"

## Quick Diagnostic Steps

### Step 1: Check Render Logs
- Look for the `=== IMPORT LEADS ERROR ===` section
- Copy the full error message

### Step 2: Verify Environment Variables
In Render dashboard, check:
- ✅ `GOOGLE_SERVICE_ACCOUNT_JSON` is set
- ✅ `GOOGLE_SHEETS_ID` is set
- ✅ `GOOGLE_SHEETS_WORKSHEET` is set (or defaults to "Leads")

### Step 3: Test JSON Format
The error message will show if JSON is invalid. Common issues:
- Line breaks in the value
- Unescaped quotes
- Missing commas
- Truncated JSON

### Step 4: Verify Service Account
- Check the `client_email` in your JSON matches the service account
- Verify the service account exists in Google Cloud Console
- Ensure the service account has proper permissions

## What the Error Messages Mean

### "Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON"
- JSON syntax is wrong
- Fix: Validate JSON, ensure single line, escape quotes

### "Service account JSON missing required fields"
- JSON is valid but incomplete
- Fix: Ensure all required fields are present

### "Failed to create credentials from JSON"
- Credentials are malformed
- Fix: Download fresh JSON from Google Cloud Console

### "Permission denied" or "403"
- Sheet not shared with service account
- Fix: Share sheet with service account email

### "Google Sheet not found" or "404"
- Sheet ID is wrong
- Fix: Check `GOOGLE_SHEETS_ID` is correct

## Still Not Working?

1. **Check Render logs** - The full error is there
2. **Test locally first** - If it works locally but not on Render, it's an env var issue
3. **Verify JSON format** - Use a JSON validator
4. **Try file method** - If JSON is too complex, upload file to Render

---

**The error logs in Render will tell you exactly what's wrong!**
