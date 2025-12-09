import os
import toml
from google.oauth2 import service_account
from googleapiclient.discovery import build

SECRETS_PATH = ".streamlit/secrets.toml"

def debug_drive_auth():
    print(f"--- DIAGNOSIS: Google Drive Service Account ---")
    
    # 1. Check if secrets file exists
    if not os.path.exists(SECRETS_PATH):
        print(f"[ERROR] Secrets file not found at: {SECRETS_PATH}")
        return

    print(f"[OK] Found secrets file: {SECRETS_PATH}")

    # 2. Parse TOML
    try:
        data = toml.load(SECRETS_PATH)
        if "google_drive" not in data:
            print("[ERROR] 'google_drive' section missing in secrets.toml")
            return
        
        creds_info = data["google_drive"]
        client_email = creds_info.get("client_email", "UNKNOWN")
        print(f"[INFO] Service Account Email: {client_email}")
        
    except Exception as e:
        print(f"[ERROR] Failed to parse secrets.toml: {e}")
        return

    # 3. Authenticate
    try:
        print("[INFO] Attempting authentication...")
        # Fix for newlines in private key
        if 'private_key' in creds_info:
             creds_info['private_key'] = creds_info['private_key'].replace('\\n', '\n')

        creds = service_account.Credentials.from_service_account_info(
            creds_info, scopes=['https://www.googleapis.com/auth/drive']
        )
        service = build('drive', 'v3', credentials=creds)
        print("[OK] Service object built successfully.")

    except Exception as e:
        print(f"[ERROR] Authentication failed: {e}")
        return

    # 4. Test API Call (List Files)
    try:
        print("[INFO] Testing API call (files().list)...")
        results = service.files().list(
            pageSize=5,
            fields="nextPageToken, files(id, name)"
        ).execute()
        items = results.get('files', [])
        
        if not items:
            print("[OK] API Call Successful (No files found, but auth worked).")
        else:
            print("[OK] API Call Successful. Found files:")
            for item in items:
                print(f" - {item['name']} ({item['id']})")
                
    except Exception as e:
        print(f"[CRITICAL FAILURE] API Call Failed: {e}")
        if "invalid_grant" in str(e):
            print("\n>>> DIAGNOSIS: 'invalid_grant' usually means the Service Account (client_email) is deleted, disabled, or the keys are revoked in Google Cloud Console.")

if __name__ == "__main__":
    debug_drive_auth()
