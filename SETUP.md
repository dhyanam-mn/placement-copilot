# Placement Copilot — Setup & Gmail OAuth Guide

This document provides setup instructions for Placement Copilot, including setting up Google OAuth 2.0 credentials for the **Gmail Tracker Agent**.

---

## 1. Prerequisites

- Python 3.11+
- PostgreSQL database
- Required Python packages:
  ```bash
  pip install -r requirements.txt
  ```

---

## 2. Setting Up Gmail OAuth 2.0 Credentials (Gmail Tracker Agent)

The Gmail Tracker Agent requires **read-only access** to your Gmail inbox (`https://www.googleapis.com/auth/gmail.readonly`).

### Step-by-Step Google Cloud Console Setup

1. **Create a Google Cloud Project**:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/).
   - Click the project dropdown at the top and select **New Project**.
   - Name your project (e.g., `Placement-Copilot-Tracker`) and click **Create**.

2. **Enable the Gmail API**:
   - In the Cloud Console sidebar, go to **APIs & Services** > **Library**.
   - Search for **Gmail API**.
   - Click **Gmail API** and click **Enable**.

3. **Configure OAuth Consent Screen**:
   - Go to **APIs & Services** > **OAuth consent screen**.
   - Choose **User Type**: **External** (or Internal if using Workspace). Click **Create**.
   - Fill in required fields: App Name (`Placement Copilot`), User support email, and Developer contact information.
   - Click **Save and Continue**.
   - Under **Scopes**, click **Add or Remove Scopes**, search for `gmail.readonly`, check `https://www.googleapis.com/auth/gmail.readonly`, and click **Update**.
   - Click **Save and Continue**.
   - Under **Test users**, click **Add Users** and enter the Gmail address you will connect. Click **Save**.

4. **Create OAuth 2.0 Credentials**:
   - Go to **APIs & Services** > **Credentials**.
   - Click **+ Create Credentials** > **OAuth client ID**.
   - Select **Application type**: **Desktop app**.
   - Name the client (e.g., `Placement Copilot Desktop`).
   - Click **Create**.
   - Click **Download JSON** on the created OAuth client.
   - Rename the downloaded file to **`credentials.json`** and place it in the root directory of this repository (`Placement-Copilot/credentials.json`).

5. **First-Time Authorization**:
   - When the backend runs a sync or when calling `POST /tracker/gmail/sync`, an authorization URL / browser prompt will pop up once.
   - Grant read-only access to your inbox.
   - A `token.json` file will be generated automatically in the root folder, saving refresh tokens for automated background polling.

---

## 3. Running Without Live Gmail Credentials (Mock Mode)

If `credentials.json` is not configured, Placement Copilot automatically operates in **Mock / Test Mode**:
- `POST /tracker/gmail/sync` accepts optional mock email fixtures in the JSON body:
  ```json
  {
    "mock_messages": [
      {
        "id": "msg_001",
        "sender": "recruiter@razorpay.com",
        "subject": "Invitation to Online Assessment - Razorpay SDE Intern",
        "body": "Hi, please complete your online assessment on HackerRank within 48 hours."
      }
    ]
  }
  ```
- Smoke tests and automated test suites (`smoke_test_gmail.sh`, `pytest`) run completely offline using mock fixtures without requiring live Google credentials.
