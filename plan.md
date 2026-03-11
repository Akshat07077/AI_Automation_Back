You are helping extend an existing SaaS product.

Current product:

This is an AI-powered lead generation and outreach automation platform.

Tech stack:
Frontend: Next.js
Backend: FastAPI (Python)
Database: PostgreSQL (Neon)

Current system capabilities:

- Users maintain leads inside a Google Sheet
- Backend reads the sheet
- AI generates personalized outreach emails
- Emails are sent through Gmail
- There is a dashboard where users can:
  - Import leads from Google Sheet
  - Run outreach batch
  - View basic statistics

Google Sheet structure:

Lead_ID
Founder_Name
Startup_Name
Email
Hiring_Role
Startup_Stage
Tech_Stack
Website
LinkedIn
Observation
Campaign
Status
Last_Contacted
Subject_Variant
Notes
Created_Date

The system currently accesses the sheet using a Google Service Account JSON file.

This works for internal usage but is NOT suitable for a SaaS product.

We need to replace the service account setup with Google OAuth so that each user can connect their Google account.

DO NOT rebuild the existing system.
Instead extend it.

--------------------------------

GOAL

Convert the current internal tool into a multi-user SaaS product.

Users must be able to:

1. Sign in to the dashboard
2. Connect their Google account
3. Select which Google Sheet contains their leads
4. Run outreach automation using that sheet

The system should not require users to download JSON files or configure Google Cloud.

--------------------------------

GOOGLE OAUTH IMPLEMENTATION

Replace service account access with Google OAuth.

Scopes required:

https://www.googleapis.com/auth/spreadsheets.readonly
https://www.googleapis.com/auth/drive.metadata.readonly

OAuth flow:

1. User clicks "Connect Google" in Settings page
2. Redirect to Google OAuth login
3. User grants permission
4. Google redirects to backend callback
5. Backend receives authorization code
6. Exchange code for:
   - access_token
   - refresh_token
   - expiry

Store tokens in database.

Database fields:

google_access_token
google_refresh_token
token_expiry
google_email

--------------------------------

SHEET SELECTION

After OAuth connection:

Use Google Drive API to fetch the user's spreadsheets.

Return list:

[
  { "id": "sheet_id_1", "name": "Startup Leads" },
  { "id": "sheet_id_2", "name": "AI Outreach Leads" }
]

Frontend displays a dropdown where user selects which sheet to use.

Store selected sheet_id in database.

--------------------------------

SHEET READING

Modify the current lead import logic to use the user's OAuth credentials.

Use Google Sheets API:

spreadsheets.values.get

Read rows and convert them to lead objects.

--------------------------------

TOKEN REFRESH

Access tokens expire.

When expired:

Use refresh_token to obtain a new access_token automatically.

--------------------------------

SETTINGS PAGE UI

Add a new section:

Integrations → Google

Display:

Google Account Status: Connected / Not Connected
Connected Email
Lead Source Sheet

Buttons:

Connect Google
Reconnect Google
Change Sheet

--------------------------------

BACKEND ENDPOINTS

Implement the following:

GET /auth/google
Redirect user to Google OAuth

GET /auth/google/callback
Handle OAuth response and store tokens

GET /google/sheets
Return list of spreadsheets

POST /google/select-sheet
Store selected sheet id

GET /google/read-sheet
Fetch leads from sheet

--------------------------------

FRONTEND CHANGES

Settings Page:

Add Google integration section.

Show connection status.

If connected:

Allow selecting sheet.

--------------------------------

IMPORTANT REQUIREMENTS

Do NOT use service account JSON anymore.

Use OAuth per user.

Tokens must be stored securely.

The existing outreach pipeline should continue working using the selected sheet.

--------------------------------

FINAL RESULT

User flow should be:

Login
→ Connect Google
→ Select Sheet
→ Import Leads
→ Run Outreach

No manual Google Cloud configuration required.

--------------------------------

Write production-ready backend and frontend integration code.