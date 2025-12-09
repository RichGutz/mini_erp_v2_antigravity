import os

SECRETS_PATH = ".streamlit/secrets.toml"
SMTP_CONFIG = {
    "server": "smtp.gmail.com",
    "port": 587,
    "user": "inandesfactorcapital@gmail.com",
    "password": "dvux qutk yheh cevl"  # Spaces removed in logic if needed, but usually kept for display, let's keep as is
}

# Clean password for usage if strictly needed, but let's write it as provided, typically SMTP libs handle spaces or user removes them. 
# Google App Passwords often work with spaces in some UIs, but standard is without. Let's remove spaces to be safe.
SMTP_CONFIG["password"] = SMTP_CONFIG["password"].replace(" ", "")

def update_secrets():
    if not os.path.exists(SECRETS_PATH):
        print(f"Error: {SECRETS_PATH} not found.")
        return

    try:
        # Read existing content
        with open(SECRETS_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Remove old [smtp] section if it exists to avoid duplicates/mess
        lines = content.splitlines()
        new_lines = []
        in_smtp = False
        
        for line in lines:
            if line.strip().startswith("[smtp]"):
                in_smtp = True
                continue
            
            if in_smtp and line.strip().startswith("["):
                in_smtp = False
                new_lines.append(line)
                continue
            
            if in_smtp:
                continue
            
            new_lines.append(line)
            
        # Ensure clean spacing
        if new_lines and new_lines[-1].strip() != "":
            new_lines.append("")
            
        # Append new [smtp] section
        new_lines.append("[smtp]")
        new_lines.append(f'server = "{SMTP_CONFIG["server"]}"')
        new_lines.append(f'port = {SMTP_CONFIG["port"]}')
        new_lines.append(f'user = "{SMTP_CONFIG["user"]}"') # Key is now 'user'
        new_lines.append(f'password = "{SMTP_CONFIG["password"]}"')
        
        final_content = "\n".join(new_lines) + "\n"
        
        with open(SECRETS_PATH, "w", encoding="utf-8") as f:
            f.write(final_content)
            
        print("Successfully updated secrets.toml with NEW SMTP config.")

    except Exception as e:
        print(f"Error updating secrets: {e}")

if __name__ == "__main__":
    update_secrets()
