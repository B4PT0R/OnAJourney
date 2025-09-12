# app.py
# Main Streamlit app for RPG-style streak challenge

import streamlit as st
from core.business import get_current_view, check_rerun
from core.components import (
    render_auth, render_sidebar, render_journey_start, 
    render_chapter_view, render_journey_failed, render_journey_completed, render_editor,
    render_intro, render_challenge_view, render_chapters_view
)

# Page config
st.set_page_config(
    page_title="On A Journey!",
    page_icon="🧭"
)

# Initialize user
user=st.session_state.setdefault('user',None)

# Determine current view
current_view = get_current_view(user)

# View routing
VIEWS = {
    "auth": render_auth,
    "journey_start": lambda: render_journey_start(user),
    "intro": lambda: render_intro(user),
    "chapter": lambda: render_chapter_view(user),  # Renommé: "day" → "chapter"
    "chapters": lambda: render_chapters_view(user),
    "challenge": lambda: render_challenge_view(user),
    "journey_failed": lambda: render_journey_failed(user),
    "journey_completed": lambda: render_journey_completed(user),
    "editor": lambda: render_editor(user),
}

# Render sidebar for logged-in users
if user and current_view != "auth":
    render_sidebar(user)

# Main content routing
if current_view in VIEWS:
    VIEWS[current_view]()
else:
    st.error(f"Unknown view: {current_view}")

# Check for pending reruns
check_rerun()