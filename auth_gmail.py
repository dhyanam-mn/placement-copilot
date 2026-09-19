import os
import sys
from google_auth_oauthlib.flow import InstalledAppFlow

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def main():
    if not os.path.exists("credentials.json"):
        print("Error: credentials.json not found in root directory!", flush=True)
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", GMAIL_SCOPES)
    print("\nStarting local OAuth authorization server on http://localhost:8090/ ...", flush=True)
    print("Opening your default browser for Google account authorization...\n", flush=True)
    try:
        creds = flow.run_local_server(port=8090, prompt="consent", open_browser=True)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
        print("\n[SUCCESS] Authorized Gmail read-only access! Saved tokens to token.json.", flush=True)
    except Exception as e:
        print(f"\nAuthorization failed or canceled: {e}", flush=True)

if __name__ == "__main__":
    main()
