import toml
import os

SECRETS_PATH = ".streamlit/secrets.toml"

def diagnose():
    print(f"Checking secrets at: {SECRETS_PATH}")
    if not os.path.exists(SECRETS_PATH):
        print(f"ERROR: {SECRETS_PATH} not found!")
        return

    try:
        secrets = toml.load(SECRETS_PATH)
        oauth = secrets.get("google_oauth", {})
        
        if not oauth:
            print("ERROR: [google_oauth] section not found in secrets.toml")
            return

        print("\n--- OAuth Configuration ---")
        print(f"Client ID: {oauth.get('client_id', 'MISSING')}")
        print(f"Client Secret Present: {'Yes' if oauth.get('client_secret') else 'No'}")
        
        redirect_uri = oauth.get('redirect_uri', 'NOT SET (Will use default: http://localhost:8504)')
        print(f"Redirect URI in secrets: {redirect_uri}")
        
    except Exception as e:
        print(f"ERROR reading secrets: {e}")

if __name__ == "__main__":
    diagnose()
