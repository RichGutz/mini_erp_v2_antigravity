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
        # 3-Column Layout: [Logo Geek (1), Title (2), Right Stack (1)]
        # Removed vertical_alignment="center" to allow the button to sit at the top ("más arriba")
        col1, col2, col3 = st.columns([1, 2, 1])
        
        # --- Left: Geesoft Logo ---
        with col1:
             st.markdown(
                f"""<div style="display: flex; align-items: center;">
                <img src="data:image/png;base64,{logo_geek_b64}" style="max-width: 180px; width: 100%; object-fit: contain;">
                </div>""",
                unsafe_allow_html=True
            )

        # --- Center: Title ---
        with col2:
            st.markdown(f"<h2 style='text-align: center; margin: 0; font-size: 2.2em;'>{title}</h2>", unsafe_allow_html=True)
            
        # --- Right: Logout + Inandes Logo Stack ---
        with col3:
            # Create a 2-column layout inside the right column to push content to the far right
            # [Spacer, Content]
            _, right_content = st.columns([1, 2]) 
            
            with right_content:
                # 1. Logout Button (Discreet, Top)
                # Removed use_container_width=True to make it smaller ("mitad de ancho")
                if st.button("🔒 Cerrar Sesión", key="header_logout_btn", help="Cerrar sesión actual"):
                    st.session_state.clear()
                    st.switch_page("00_Home.py")
                
                # 2. Inandes Logo (Bottom)
                st.markdown(
                    f"""<div style="display: flex; justify-content: flex-end; margin-top: 8px;">
                    <img src="data:image/png;base64,{logo_inandes_b64}" style="max-width: 150px; width: 100%; object-fit: contain;">
                    </div>""",
                    unsafe_allow_html=True
                )
    
    st.markdown("---")
