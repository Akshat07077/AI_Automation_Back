"""
Test script to validate Google Service Account configuration.
Run this to check if your JSON is valid and can connect to Google Sheets.
"""
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=== Testing Google Service Account Configuration ===\n")

# Check if JSON is set
json_str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
file_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")

print(f"1. GOOGLE_SERVICE_ACCOUNT_JSON set: {json_str is not None}")
print(f"2. GOOGLE_SERVICE_ACCOUNT_FILE set: {file_path is not None}\n")

if json_str:
    print("Testing JSON format...")
    try:
        # Try to parse JSON
        data = json.loads(json_str)
        print("✅ JSON is valid!")
        print(f"   - Type: {data.get('type')}")
        print(f"   - Project ID: {data.get('project_id')}")
        print(f"   - Client Email: {data.get('client_email')}")
        
        # Check required fields
        required_fields = ['type', 'project_id', 'private_key', 'client_email']
        missing = [f for f in required_fields if f not in data]
        if missing:
            print(f"❌ Missing required fields: {missing}")
        else:
            print("✅ All required fields present")
            
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        print("\nCommon issues:")
        print("1. JSON has line breaks - must be single line")
        print("2. Quotes not escaped - use \\\" instead of \"")
        print("3. Missing commas or brackets")
        
elif file_path:
    print(f"Testing file: {file_path}")
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            print("✅ File exists and JSON is valid!")
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in file: {e}")
    else:
        print(f"❌ File not found at: {file_path}")
else:
    print("❌ Neither GOOGLE_SERVICE_ACCOUNT_JSON nor GOOGLE_SERVICE_ACCOUNT_FILE is set!")

# Check Google Sheets ID
sheets_id = os.getenv("GOOGLE_SHEETS_ID")
print(f"\n3. GOOGLE_SHEETS_ID: {sheets_id if sheets_id else 'NOT SET'}")

# Test actual connection
print("\n=== Testing Google Sheets Connection ===")
try:
    import gspread
    from google.oauth2.service_account import Credentials
    
    if json_str:
        creds = Credentials.from_service_account_info(
            json.loads(json_str),
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
    elif file_path and os.path.exists(file_path):
        creds = Credentials.from_service_account_file(
            file_path,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
    else:
        print("❌ Cannot test connection - no credentials configured")
        exit(1)
    
    client = gspread.authorize(creds)
    print("✅ Successfully authenticated with Google!")
    
    if sheets_id:
        try:
            sheet = client.open_by_key(sheets_id)
            print(f"✅ Successfully opened sheet: {sheet.title}")
            
            worksheet_name = os.getenv("GOOGLE_SHEETS_WORKSHEET", "Leads")
            try:
                worksheet = sheet.worksheet(worksheet_name)
                print(f"✅ Found worksheet: {worksheet_name}")
                
                # Try to read a row
                rows = worksheet.get_all_records()
                print(f"✅ Successfully read {len(rows)} rows from sheet")
                
            except gspread.exceptions.WorksheetNotFound:
                available = [ws.title for ws in sheet.worksheets()]
                print(f"❌ Worksheet '{worksheet_name}' not found!")
                print(f"   Available worksheets: {', '.join(available)}")
        except gspread.exceptions.SpreadsheetNotFound:
            print(f"❌ Sheet not found with ID: {sheets_id}")
            print("   Check: 1. Sheet ID is correct")
            print("         2. Sheet is shared with service account")
        except gspread.exceptions.APIError as e:
            if e.response.status_code == 403:
                print("❌ Permission denied!")
                print("   Share the sheet with the service account email")
            else:
                print(f"❌ API Error: {e}")
    else:
        print("⚠️  GOOGLE_SHEETS_ID not set - cannot test sheet access")
        
except ImportError:
    print("❌ gspread not installed. Run: pip install gspread google-auth")
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")
    import traceback
    print("\nFull traceback:")
    print(traceback.format_exc())

print("\n=== Test Complete ===")
