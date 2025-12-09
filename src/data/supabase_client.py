import os
from supabase import create_client, Client
from typing import Optional
from dotenv import load_dotenv

# Try to import streamlit
try:
    import streamlit as st
    cache_resource = st.cache_resource
except ImportError:
    # If streamlit is not installed or we are in a script
    st = None
    # Dummy decorator that does nothing
    def cache_resource(func):
        return func

# --- Singleton implementation ---
@cache_resource
def get_supabase_client() -> Client:
    """
    Initializes and returns a cached Supabase client instance.
    Uses st.cache_resource to correctly manage the singleton lifecycle in Streamlit.
    """
    # Load environment variables from .env file if present (for local backend execution)
    load_dotenv()
    
    SUPABASE_URL = None
    SUPABASE_KEY = None

    # Try to load from Streamlit secrets first (for frontend)
    try:
        if "supabase" in st.secrets and "url" in st.secrets.supabase and "key" in st.secrets.supabase:
            SUPABASE_URL = st.secrets.supabase.url
            SUPABASE_KEY = st.secrets.supabase.key
            # print("Supabase credentials loaded from Streamlit secrets.") 
    except Exception:
        pass

    # If not loaded from Streamlit secrets, try environment variables (for backend)
    if SUPABASE_URL is None or SUPABASE_KEY is None:
        SUPABASE_URL = os.environ.get("SUPABASE_URL")
        SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
        # print("Supabase credentials loaded from environment variables.")

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError(
            "Supabase credentials (SUPABASE_URL and SUPABASE_KEY) not found. "
            "Please ensure they are set in Streamlit Secrets (for frontend) "
            "or as environment variables (for backend)."
        )

    # print("Initializing Supabase client...")
    return create_client(SUPABASE_URL, SUPABASE_KEY)
