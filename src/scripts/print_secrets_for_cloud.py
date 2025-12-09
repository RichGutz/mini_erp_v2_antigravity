
import os

SECRETS_PATH = ".streamlit/secrets.toml"

def print_secrets():
    if not os.path.exists(SECRETS_PATH):
        print("Error: secrets.toml not found!")
        return
        
    print("\n" + "="*50)
    print("COPIA TODO EL CONTENIDO DE ABAJO PARA STREAMLIT CLOUD:")
    print("="*50 + "\n")
    
    with open(SECRETS_PATH, "r", encoding="utf-8") as f:
        print(f.read())
        
    print("\n" + "="*50)
    print("END OF SECRETS")
    print("="*50 + "\n")

if __name__ == "__main__":
    print_secrets()
