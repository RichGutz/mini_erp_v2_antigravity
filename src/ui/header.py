import streamlit as st
import os
import base64

def get_base64_image(image_path):
    """Encodes an image file to a base64 string."""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception as e:
        st.error(f"Error loading image {image_path}: {e}")
        return None

def render_header(title: str):
    """
    Renders the consistent application header.
    
    Layout:
    - Left: Geesoft Logo
    - Center: Page Title
    - Right: Logout Button (Top) + Inandes Logo (Bottom)
    """
    # Calculate project root relative to this file (src/ui/header.py -> project_root)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
    
    logo_geek_path = os.path.join(project_root, "static", "logo_geek.png")
    logo_inandes_path = os.path.join(project_root, "static", "logo_inandes.png")

    logo_geek_b64 = get_base64_image(logo_geek_path)
    logo_inandes_b64 = get_base64_image(logo_inandes_path)

    if not logo_geek_b64 or not logo_inandes_b64:
        return

    # Use a container to group the header elements
    with st.container(border=False):
        # 3-Column Layout: [Left, Center, Right]
        # We need 2 "Rows" visually. 
        # Row 1: Top Right Logout (Left/Center empty or spacers)
        # Row 2: Logos and Title aligned at bottom
        
        # To achieve this cleanly in Streamlit without complex CSS Grid hacks that might break:
        # We use a single set of columns, and inside each column we stack elements vertically.
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        # --- COL 1 (Left): Spacer + GeekSoft Logo ---
        with col1:
             st.write("") # Top Spacer (aligns with Logout button height approx)
             st.write("") 
             # Logo GeekSoft (Bottom)
             st.markdown(
                f"""<div style="display: flex; align-items: flex-end; height: 100%; padding-top: 20px;">
                <img src="data:image/png;base64,{logo_geek_b64}" style="max-width: 180px; width: 100%; object-fit: contain;">
                </div>""",
                unsafe_allow_html=True
            )

        # --- COL 2 (Center): Spacer + Title ---
        with col2:
            st.write("") # Top Spacer
            st.write("")
            # Title (Bottom Center)
            st.markdown(f"""
            <div style="display: flex; align-items: flex-end; justify-content: center; height: 100%; padding-top: 20px;">
                <h2 style='text-align: center; margin: 0; font-size: 2.2em;'>{title}</h2>
            </div>
            """, unsafe_allow_html=True)
            
        # --- COL 3 (Right): Logout (Top) + Inandes Logo (Bottom) ---
        with col3:
            # Row 1: Logout Button (Top Right)
            # We use a nested column to push it to the right-most edge if needed, or just alignment
            # Ratio [3, 2] pushes the button into the last 40% of the column width (increased from 33%)
            # to prevent text wrapping ("Cerrar Sesión") while keeping it compact.
            sub_c1, sub_c2 = st.columns([3, 2]) 
            with sub_c2:
                 if st.button("🔒 Cerrar Sesión", key="header_logout_btn", help="Cerrar sesión actual", use_container_width=True):
                    st.session_state.clear()
                    st.switch_page("00_Home.py")
            
            # Row 2: Inandes Logo (Bottom Right)
            st.markdown(
                f"""<div style="display: flex; justify-content: flex-end; align-items: flex-end; margin-top: 15px;">
                <img src="data:image/png;base64,{logo_inandes_b64}" style="max-width: 150px; width: 100%; object-fit: contain;">
                </div>""",
                unsafe_allow_html=True
            )
            
    st.markdown("---")
