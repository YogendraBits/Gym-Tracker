import streamlit as st
import pymongo
from pymongo import MongoClient
import pandas as pd
from datetime import datetime, timedelta, date
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import json
import io
import hashlib
from typing import Dict, List, Optional


import backend as bk

# Page config
st.set_page_config(
    page_title="Gym Tracker",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="expanded"
)


def load_css():
    with open("css/styles.css", "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


load_css()


# Main app logic


def main_app():
    user_id = st.session_state.user_data["_id"]
    username = st.session_state.user_data["username"]
    full_name = st.session_state.user_data["full_name"]

    # Initialize database with user ID
    db = bk.GymDatabase(user_id)

    # Sidebar with user info
    st.sidebar.markdown(f"""
    <div class="user-info">
        <div class="user-avatar">👤</div>
        <div class="user-details">
            <div class="user-name">{full_name}</div>
            <div class="user-username">@{username}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.sidebar.columns(2)

    with col1:
        profile_clicked = st.button("Profile", use_container_width=True)

    with col2:
        logout_clicked = st.button("Logout", use_container_width=True)
    
    # Handle button clicks
    if logout_clicked:
        st.session_state.authenticated = False
        st.session_state.user_data = None
        st.rerun()
    
    if profile_clicked:
        # Clear radio selection when profile is clicked
        if "radio_selection" in st.session_state:
            del st.session_state.radio_selection
        
    st.sidebar.markdown("---")

    # Navigation (removed Profile from here)
    page = st.sidebar.radio(
        "Navigate",
        ["Dashboard", "Log Workout", "View Workouts", "Progress", "Goals",
            "Body Metrics", "Attendance", "Nutrition", "Workout Plans", "Timer",
            "Export Data", "Manage Data"],
        label_visibility="collapsed",  # Optional: hide label text
        index=None if profile_clicked else 0,  # No default selection if profile was clicked
        key="radio_selection"
    )

    # Check if profile page is requested
    if profile_clicked:
        def load_css():
            with open("css/profile.css", "r", encoding="utf-8") as f:
                st.markdown(f"<style>{f.read()}</style>",
                            unsafe_allow_html=True)
        load_css()
        from backend import show_profile_page
        show_profile_page(st.session_state.user_data, db)
        return

    # Handle other navigation options (only if something is selected)
    if page is None:
        st.write("Please select an option from the navigation menu.")
        return

    # Dashboard
    if page == "Dashboard":

        from Dashboard import dashboard
        dashboard()

    elif page == "View Workouts":
        from Vworkouts import view_workouts
        view_workouts()

    elif page == "Log Workout":
        from Lworkout import log_workout
        log_workout()

    # Data Management Page
    elif page == "Manage Data":
        from Mdata import manage_data
        manage_data()
    
    # Attendance Page
    elif page == "Attendance":
        from Attendance import attendance
        attendance()

    # Nutrition Page
    elif page == "Nutrition":
        from Nutrition import nutrition
        nutrition()

    # Body Metrics Page
    elif page == "Body Metrics":
        from Bmetrics import body_metrics
        body_metrics()

    # Progress Page
    elif page == "Progress":
        from Progress import progress
        progress()


    # Goals Page
    elif page == "Goals":
        try:
            with open('css/goals.css') as f:
                st.markdown(f'<style>{f.read()}</style>',
                            unsafe_allow_html=True)
        except:
            pass
        
        from Goals import goals
        goals()

    # Workout Plans Page
    elif page == "Workout Plans":
        from Wplan import workout_plan
        workout_plan()

    elif page == "Timer":
        from Timer import timer
        timer()

    # Export Data Page
    elif page == "Export Data":
        from Export import export_data
        export_data()


# Main execution
if __name__ == "__main__":
    if not bk.check_authentication():
        bk.show_auth_page()
    else:
        main_app()