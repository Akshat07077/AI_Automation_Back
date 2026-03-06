# Fix .env File for GOOGLE_SERVICE_ACCOUNT_JSON

## The Problem

Python-dotenv can't parse your JSON because it contains special characters (quotes, newlines, etc.).

## Solution: Use Single Quotes

In `.env` files, you need to wrap the JSON in **single quotes** so the double quotes inside don't break parsing.

### ❌ Wrong (breaks parsing):
```env
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"..."}
```

### ✅ Correct (use single quotes):
```env
GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account","project_id":"...","private_key":"..."}'
```

## Step-by-Step Fix

1. **Open your `.env` file**

2. **Find the line with `GOOGLE_SERVICE_ACCOUNT_JSON`**

3. **Wrap the entire JSON value in single quotes:**
   ```env
   GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account","project_id":"robust-chess-427018-j2","private_key_id":"...","private_key":"-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n","client_email":"ai-auto@robust-chess-427018-j2.iam.gserviceaccount.com",...}'
   ```

4. **Make sure it's all on ONE line** (no line breaks)

5. **Save the file**

6. **Restart your server**

## Alternative: Use Base64 Encoding

If single quotes don't work, you can encode the JSON as Base64:

1. **Encode your JSON:**
   ```python
   import json
   import base64
   
   with open('service_account.json', 'r') as f:
       data = json.load(f)
       json_str = json.dumps(data)
       encoded = base64.b64encode(json_str.encode()).decode()
       print(encoded)  # Copy this
   ```

2. **In your code, decode it:**
   ```python
   import base64
   json_str = base64.b64decode(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_B64")).decode()
   ```

   But this requires code changes, so single quotes are easier.

## Quick Test

After fixing, restart your server. The errors should disappear.

If you still get errors, check:
- No line breaks in the JSON value
- All quotes are properly escaped or use single quotes around the whole value
- JSON is valid (test with `json.loads()`)
