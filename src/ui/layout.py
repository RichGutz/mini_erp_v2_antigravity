import streamlit as st
import os

def init_page(page_title: str, page_icon: str = "📊", layout: str = "wide", initial_sidebar_state: str = "expanded"):
    """
    Initializes the page configuration and injects standard CSS.
    Should be the FIRST call in every module.
    """
    # 1. Set Page Config
    st.set_page_config(
        page_title=page_title,
        page_icon=page_icon,
        layout=layout,
        initial_sidebar_state=initial_sidebar_state
    )

    # 2. Inject Standard CSS (The "Frame")
    # Enforce consistent padding and alignment globally
    st.markdown("""
        <style>
            /* Standardize main container padding */
            .block-container {
                padding-top: 2rem !important;
                padding-bottom: 3rem !important;
                padding-left: 1rem !important;
                padding-right: 1rem !important;
                max-width: 100% !important;
            }
            /* Ensure horizontal blocks (columns) align to top by default */
            [data-testid="stHorizontalBlock"] {
                align-items: flex-start;
            }
            /* Global Button Styles (Optional centralization) */
            .stButton>button {
                width: auto;
            }
        </style>
    """, unsafe_allow_html=True)
