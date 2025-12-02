# src/data/supabase_client.py

import os
from supabase import create_client, Client
from typing import Optional
from dotenv import load_dotenv

# --- Singleton instance ---
_supabase_client_instance: Optional[Client] = None

def get_supabase_client() -> Client:
    """
    Initializes and returns a singleton Supabase client instance.
    It attempts to load credentials from Streamlit's secrets (for frontend)
    or from environment variables (for backend/non-Streamlit environments).
    """
    # Load environment variables from .env file if present (for local backend execution)
    load_dotenv()
    
    global _supabase_client_instance
    if _supabase_client_instance is None:
        SUPABASE_URL = None
        SUPABASE_KEY = None

        # Try to load from Streamlit secrets first (for frontend)
        try:
            import streamlit as st
            if "supabase" in st.secrets and "url" in st.secrets.supabase and "key" in st.secrets.supabase:
                SUPABASE_URL = st.secrets.supabase.url
                SUPABASE_KEY = st.secrets.supabase.key
                print("Supabase credentials loaded from Streamlit secrets.")
        except Exception:
            # Streamlit not available or secrets not configured, fall back to environment variables
            pass

        # If not loaded from Streamlit secrets, try environment variables (for backend)
        if SUPABASE_URL is None or SUPABASE_KEY is None:
            SUPABASE_URL = os.environ.get("SUPABASE_URL")
            SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
            print("Supabase credentials loaded from environment variables.")

        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError(
                "Supabase credentials (SUPABASE_URL and SUPABASE_KEY) not found. "
                "Please ensure they are set in Streamlit Secrets (for frontend) "
                "or as environment variables (for backend)."
            )

        print("Initializing Supabase client...")
        _supabase_client_instance = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("Supabase client initialized.")

    return _supabase_client_instance
