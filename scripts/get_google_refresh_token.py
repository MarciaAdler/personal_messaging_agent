"""
Run this ONCE on your own laptop (not on Railway) to generate a Google OAuth
refresh token for read-only Calendar access.

Prerequisites:
1. Go to https://console.cloud.google.com/ and create a project (or use an existing one).
2. Enable the "Google Calendar API" for that project.
3. Go to "APIs & Services" > "Credentials" > "Create Credentials" > "OAuth client ID".
   - Application type: "Desktop app"
   - Download the resulting client_secret.json and place it in this scripts/ folder.
4. Go to "OAuth consent screen" and add your own Google account as a "Test user"
   (this app will stay in "Testing" mode, which is fine for personal use).
5. pip install google-auth-oauthlib
6. Run: python get_google_refresh_token.py

This will open a browser window for you to log in and approve read-only Calendar
access, then print out GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REFRESH_TOKEN
for you to paste into your Railway environment variables.
"""

import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
CLIENT_SECRET_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "client_secret.json")

def main():
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_PATH, SCOPES)
    creds = flow.run_local_server(port=0)

    print("\n--- Copy these into your Railway environment variables ---\n")
    print(f"GOOGLE_CLIENT_ID={creds.client_id}")
    print(f"GOOGLE_CLIENT_SECRET={creds.client_secret}")
    print(f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}")
    print("\n------------------------------------------------------------\n")

if __name__ == "__main__":
    main()
