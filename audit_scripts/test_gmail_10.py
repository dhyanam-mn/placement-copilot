import os
import sys
import json

sys.path.insert(0, os.path.abspath("."))

from database import SessionLocal
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from services.gmail_tracker import match_email_to_application

def test_gmail():
    if not os.path.exists("token.json"):
        print("token.json not found")
        return

    creds = Credentials.from_authorized_user_file('token.json')
    service = build('gmail', 'v1', credentials=creds)
    
    # List top 10 messages
    res = service.users().messages().list(userId='me', maxResults=10).execute()
    messages = res.get('messages', [])
    
    db = SessionLocal()
    output = []
    
    for m in messages:
        msg = service.users().messages().get(userId='me', id=m['id'], format='full').execute()
        headers = msg.get('payload', {}).get('headers', [])
        
        sender = ""
        subject = ""
        for h in headers:
            name = h.get('name', '').lower()
            if name == 'from':
                sender = h.get('value', '')
            elif name == 'subject':
                subject = h.get('value', '')
                
        # Run matcher
        match = match_email_to_application(db, sender, subject, msg.get('snippet', ''))
        matched_company = match.company if match else "none"
        
        output.append({
            "sender": sender,
            "subject": subject,
            "matched_company": matched_company
        })
        
    db.close()
    
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    test_gmail()
