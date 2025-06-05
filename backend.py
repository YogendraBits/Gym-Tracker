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



# Utility functions for authentication


def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()


def verify_password(password, hashed):
    return hash_password(password) == hashed

# MongoDB connection


@st.cache_resource
def init_connection():
    try:
        client = MongoClient(
            "mongodb+srv://2023sl93059:2023sl93059@cluster0.yvqvs.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
        return client
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None

# Initialize database


def get_database():
    client = init_connection()
    if client:
        return client.gym_tracker
    return None

# Authentication functions


def register_user(username, password, email, full_name):
    db = get_database()
    if db is not None:
        users = db.users
        # Check if user already exists
        if users.find_one({"username": username}):
            return False, "Username already exists"
        if users.find_one({"email": email}):
            return False, "Email already exists"

        # Create new user
        user_data = {
            "username": username,
            "password": hash_password(password),
            "email": email,
            "full_name": full_name,
            "created_at": datetime.now(),
            "profile_image": None
        }
        users.insert_one(user_data)
        return True, "User registered successfully"
    return False, "Database connection failed"


def authenticate_user(username, password):
    db = get_database()
    if db is not None:
        users = db.users
        user = users.find_one({"username": username})
        if user and verify_password(password, user["password"]):
            return True, user
        return False, None
    return False, None


def delete_user_profile(user_id):
    """Delete user profile and all associated data"""
    db = get_database()
    if db is not None:
        try:
            # Delete user data from all collections
            db.workouts.delete_many({"user_id": user_id})
            db.attendance.delete_many({"user_id": user_id})
            db.nutrition.delete_many({"user_id": user_id})
            db.body_metrics.delete_many({"user_id": user_id})
            db.exercise_progress.delete_many({"user_id": user_id})
            db.goals.delete_many({"user_id": user_id})
            db.workout_plans.delete_many({"user_id": user_id})

            # Delete user account
            result = db.users.delete_one({"_id": user_id})

            if result.deleted_count > 0:
                return True, "Profile deleted successfully"
            else:
                return False, "User not found"
        except Exception as e:
            return False, f"Error deleting profile: {str(e)}"
    return False, "Database connection failed"


def check_authentication():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_data' not in st.session_state:
        st.session_state.user_data = None
    return st.session_state.authenticated

# Database operations with user filtering


class GymDatabase:
    def __init__(self, user_id=None):
        self.db = get_database()
        self.user_id = user_id
        if self.db is not None:
            self.workouts = self.db.workouts
            self.attendance = self.db.attendance
            self.nutrition = self.db.nutrition
            self.body_metrics = self.db.body_metrics
            self.exercise_progress = self.db.exercise_progress
            self.goals = self.db.goals
            self.workout_plans = self.db.workout_plans

    def _add_user_filter(self, query=None):
        if query is None:
            query = {}
        if self.user_id:
            query["user_id"] = self.user_id
        return query

    def log_workout(self, workout_data):
        if self.db is not None:
            workout_data["user_id"] = self.user_id
            workout_data["created_at"] = datetime.now()
            return self.workouts.insert_one(workout_data)

    def log_attendance(self, date, attended, notes=""):
        if self.db is not None:
            return self.attendance.replace_one(
                self._add_user_filter({"date": date}),
                {"date": date, "attended": attended, "notes": notes,
                    "timestamp": datetime.now(), "user_id": self.user_id},
                upsert=True
            )

    def log_nutrition(self, date, protein_intake, meals=None, notes=""):
        if self.db is not None:
            return self.nutrition.replace_one(
                self._add_user_filter({"date": date}),
                {"date": date, "protein_intake": protein_intake, "meals": meals or [
                ], "notes": notes, "timestamp": datetime.now(), "user_id": self.user_id},
                upsert=True
            )

    def log_body_metrics(self, date, weight=None, measurements=None, notes=""):
        if self.db is not None:
            return self.body_metrics.replace_one(
                self._add_user_filter({"date": date}),
                {"date": date, "weight": weight, "measurements": measurements or {
                }, "notes": notes, "timestamp": datetime.now(), "user_id": self.user_id},
                upsert=True
            )

    def save_workout_plan(self, plan_data):
        if self.db is not None:
            plan_data["user_id"] = self.user_id
            return self.workout_plans.replace_one(
                self._add_user_filter({"name": plan_data["name"]}),
                plan_data,
                upsert=True
            )

    def get_workout_plans(self):
        if self.db is not None:
            return list(self.workout_plans.find(self._add_user_filter()))
        return []

    def get_recent_workouts(self, days=30):
        if self.db is not None:
            start_date = datetime.now() - timedelta(days=days)
            return list(self.workouts.find(self._add_user_filter({"date": {"$gte": start_date.strftime("%Y-%m-%d")}})).sort("date", -1))
        return []

    def get_attendance_data(self, days=30):
        if self.db is not None:
            start_date = datetime.now() - timedelta(days=days)
            return list(self.attendance.find(self._add_user_filter({"date": {"$gte": start_date.strftime("%Y-%m-%d")}})).sort("date", -1))
        return []

    def get_nutrition_data(self, days=30):
        if self.db is not None:
            start_date = datetime.now() - timedelta(days=days)
            return list(self.nutrition.find(self._add_user_filter({"date": {"$gte": start_date.strftime("%Y-%m-%d")}})).sort("date", -1))
        return []

    def get_body_metrics_data(self, days=90):
        if self.db is not None:
            start_date = datetime.now() - timedelta(days=days)
            return list(self.body_metrics.find(self._add_user_filter({"date": {"$gte": start_date.strftime("%Y-%m-%d")}})).sort("date", 1))
        return []

    # Delete functions
    def delete_workout(self, workout_id):
        if self.db is not None:
            return self.workouts.delete_one(self._add_user_filter({"_id": workout_id}))

    def delete_attendance(self, date):
        if self.db is not None:
            return self.attendance.delete_one(self._add_user_filter({"date": date}))

    def delete_nutrition(self, date):
        if self.db is not None:
            return self.nutrition.delete_one(self._add_user_filter({"date": date}))

    def delete_body_metrics(self, date):
        if self.db is not None:
            return self.body_metrics.delete_one(self._add_user_filter({"date": date}))

    def delete_workout_plan(self, plan_name):
        if self.db is not None:
            return self.workout_plans.delete_one(self._add_user_filter({"name": plan_name}))

    # Add these methods to the GymDatabase class

    def save_goal(self, goal_data):
        """Save a new goal to the database"""
        if self.db is not None:
            goal_data["user_id"] = self.user_id
            goal_data["created_at"] = datetime.now()
            goal_data["status"] = "active"  # active, completed, paused
            goal_data["progress_logs"] = []
            return self.goals.insert_one(goal_data)

    def get_goals(self, status=None):
        """Get all goals for the user, optionally filtered by status"""
        if self.db is not None:
            query = self._add_user_filter()
            if status:
                query["status"] = status
            return list(self.goals.find(query).sort("created_at", -1))
        return []

    def update_goal_progress(self, goal_id, progress_data):
        """Update goal progress"""
        if self.db is not None:
            progress_entry = {
                "date": progress_data.get("date", datetime.now().strftime("%Y-%m-%d")),
                "progress_value": progress_data["progress_value"],
                "notes": progress_data.get("notes", ""),
                "timestamp": datetime.now()
            }

            # Add to progress logs
            self.goals.update_one(
                self._add_user_filter({"_id": goal_id}),
                {"$push": {"progress_logs": progress_entry}}
            )

            # Update current progress
            return self.goals.update_one(
                self._add_user_filter({"_id": goal_id}),
                {"$set": {"current_progress": progress_data["progress_value"]}}
            )

    def update_goal_status(self, goal_id, status):
        """Update goal status (active, completed, paused)"""
        if self.db is not None:
            update_data = {"status": status}
            if status == "completed":
                update_data["completed_at"] = datetime.now()
            return self.goals.update_one(
                self._add_user_filter({"_id": goal_id}),
                {"$set": update_data}
            )

    def delete_goal(self, goal_id):
        """Delete a goal"""
        if self.db is not None:
            return self.goals.delete_one(self._add_user_filter({"_id": goal_id}))

    def get_goal_statistics(self):
        """Get goal statistics for the user"""
        if self.db is not None:
            all_goals = self.get_goals()
            total_goals = len(all_goals)
            completed_goals = len(
                [g for g in all_goals if g.get("status") == "completed"])
            active_goals = len(
                [g for g in all_goals if g.get("status") == "active"])

            return {
                "total": total_goals,
                "completed": completed_goals,
                "active": active_goals,
                "completion_rate": (completed_goals / total_goals * 100) if total_goals > 0 else 0
            }
        return {"total": 0, "completed": 0, "active": 0, "completion_rate": 0}

    

# Authentication UI


import time  # Add this import at the top

def show_auth_page():
    # Initialize session state for loading
    if 'login_loading' not in st.session_state:
        st.session_state.login_loading = False
    if 'register_loading' not in st.session_state:
        st.session_state.register_loading = False
    
    # Check if user should be remembered (auto-login)
    if 'remember_me' not in st.session_state:
        st.session_state.remember_me = False
    
    # Auto-login if remembered
    if st.session_state.get('remember_me', False) and not st.session_state.get('authenticated', False):
        remembered_user = st.session_state.get('remembered_user_data')
        if remembered_user:
            st.session_state.authenticated = True
            st.session_state.user_data = remembered_user
            st.rerun()
    
    st.markdown('<div class="auth-container">', unsafe_allow_html=True)
    
    # Hero Section
    st.markdown("""
    <div class="hero-section">
        <div class="hero-content">
            <h1 class="hero-title">Gym Tracker Pro</h1>
            <p class="hero-subtitle">Transform Your Fitness Journey</p>
            <p class="hero-description">Track workouts, monitor progress, achieve your goals</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Auth Form
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        st.markdown('<div class="auth-form">', unsafe_allow_html=True)
        with st.form("login_form", clear_on_submit=False):
            st.markdown("### Your Personalized Dashboard")
            
            username = st.text_input(
                "Username", 
                placeholder="Enter your username",
                disabled=st.session_state.login_loading
            )
            password = st.text_input(
                "Password", 
                type="password", 
                placeholder="Enter your password",
                disabled=st.session_state.login_loading
            )
            
            # Remember Me Checkbox
            remember_me = st.checkbox(
                "Remember Me", 
                value=st.session_state.get('remember_me_checked', False),
                disabled=st.session_state.login_loading,
                help="Keep me logged in on this browser"
            )
            
            col1, col2 = st.columns([1, 1])
            with col1:
                # Dynamic button text based on loading state
                button_text = "Verifying..." if st.session_state.login_loading else "Login"
                login_btn = st.form_submit_button(
                    button_text, 
                    use_container_width=True,
                    disabled=st.session_state.login_loading
                )
            
            # Remove the separate loading indicator section since we're using spinner context
            
            if login_btn and not st.session_state.login_loading:
                if username and password:
                    # Set loading state and perform authentication
                    st.session_state.login_loading = True
                    
                    # Show loading indicator immediately
                    with st.spinner("Authenticating your credentials..."):
                        try:
                            # Perform authentication
                            success, user_data = authenticate_user(username, password)
                            
                            if success:
                                st.session_state.authenticated = True
                                st.session_state.user_data = user_data
                                
                                # Handle Remember Me
                                if remember_me:
                                    st.session_state.remember_me = True
                                    st.session_state.remember_me_checked = True
                                    st.session_state.remembered_user_data = user_data
                                else:
                                    st.session_state.remember_me = False
                                    st.session_state.remember_me_checked = False
                                    if 'remembered_user_data' in st.session_state:
                                        del st.session_state.remembered_user_data
                                
                                # Reset loading state
                                st.session_state.login_loading = False
                                st.success("Login successful!")
                                time.sleep(0.5)  # Brief pause to show success message
                                st.rerun()
                            else:
                                st.session_state.login_loading = False
                                st.error("Invalid username or password")
                        except Exception as e:
                            st.session_state.login_loading = False
                            st.error("An error occurred during login. Please try again.")
                else:
                    st.error("Please fill in all fields")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        st.markdown('<div class="auth-form">', unsafe_allow_html=True)
        with st.form("register_form", clear_on_submit=False):
            st.markdown("### Join the Community!")
            
            full_name = st.text_input(
                "Full Name", 
                placeholder="Enter your full name",
                disabled=st.session_state.register_loading
            )
            email = st.text_input(
                "Email", 
                placeholder="Enter your email",
                disabled=st.session_state.register_loading
            )
            username = st.text_input(
                "Username", 
                placeholder="Choose a username",
                disabled=st.session_state.register_loading
            )
            password = st.text_input(
                "Password", 
                type="password", 
                placeholder="Create a password",
                disabled=st.session_state.register_loading
            )
            confirm_password = st.text_input(
                "Confirm Password", 
                type="password", 
                placeholder="Confirm your password",
                disabled=st.session_state.register_loading
            )
            
            col1, col2 = st.columns([1, 1])
            with col1:
                # Dynamic button text for registration
                button_text = "Creating Account..." if st.session_state.register_loading else "Create Account"
                register_btn = st.form_submit_button(
                    button_text, 
                    use_container_width=True,
                    disabled=st.session_state.register_loading
                )
            
            # Remove the separate loading indicator section since we're using spinner context
            
            if register_btn and not st.session_state.register_loading:
                if all([full_name, email, username, password, confirm_password]):
                    if password == confirm_password:
                        if len(password) >= 6:
                            # Set loading state and perform registration
                            st.session_state.register_loading = True
                            
                            # Show loading indicator immediately
                            with st.spinner("Creating your account..."):
                                try:
                                    success, message = register_user(
                                        username, password, email, full_name)
                                    
                                    st.session_state.register_loading = False
                                    
                                    if success:
                                        st.success("" + message)
                                        st.info("Please login with your new account")
                                    else:
                                        st.error(" " + message)
                                except Exception as e:
                                    st.session_state.register_loading = False
                                    st.error("An error occurred during registration. Please try again.")
                        else:
                            st.error("Password must be at least 6 characters")
                    else:
                        st.error("Passwords don't match")
                else:
                    st.error("Please fill in all fields")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)


# Add this function to handle logout and clear remember me
def logout_user():
    """Clear all authentication data including remember me"""
    st.session_state.authenticated = False
    st.session_state.remember_me = False
    st.session_state.remember_me_checked = False
    
    # Clear user data
    if 'user_data' in st.session_state:
        del st.session_state.user_data
    if 'remembered_user_data' in st.session_state:
        del st.session_state.remembered_user_data
    
    # Clear loading states
    st.session_state.login_loading = False
    st.session_state.register_loading = False
    
    st.success("Logged out successfully!")
    st.rerun()


# Optional: Add this function to check if user should stay logged in
def check_remember_me():
    """Check if user should be automatically logged in"""
    if st.session_state.get('remember_me', False):
        remembered_user = st.session_state.get('remembered_user_data')
        if remembered_user and not st.session_state.get('authenticated', False):
            st.session_state.authenticated = True
            st.session_state.user_data = remembered_user
            return True
    return False


# Profile management page
def show_profile_page(user_data, db):
    # Main container
    st.markdown('<div class="profile-container">', unsafe_allow_html=True)

    # Page header with enhanced styling
    st.markdown('''
    <div class="profile-header">
        <h1 class="page-title">Profile Settings</h1>
        <p class="page-subtitle">Manage your account information and preferences</p>
    </div>
    ''', unsafe_allow_html=True)

    # Account Information Section
    st.markdown('''
    <div class="info-section">
        <h2 class="section-title">
            <span class="section-icon"> </span>
            <span class="section-text">Account Information</span>
        </h2>
    </div>
    ''', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown('''
        <div class="profile-avatar-container">
            <div class="profile-avatar">
                <div class="avatar-circle">
                    <span class="avatar-icon">👤</span>
                </div>
                <div class="avatar-status">
                    <div class="status-dot"></div>
                    <span class="status-text">Active</span>
                </div>
            </div>
        </div>
        ''', unsafe_allow_html=True)

    with col2:

        # User information with enhanced styling
        user_info_items = [
            ("👤", "Full Name", user_data['full_name']),
            ("🏷️", "Username", user_data['username']),
            ("📧", "Email", user_data['email']),
            ("📅", "Member Since",
             user_data['created_at'].strftime('%B %d, %Y'))
        ]

        for icon, label, value in user_info_items:
            st.markdown(f'''
            <div class="info-item">
                <div class="info-icon">{icon}</div>
                <div class="info-content">
                    <div class="info-label">{label}</div>
                    <div class="info-value">{value}</div>
                </div>
            </div>
            ''', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)  # Close profile-card

    # Divider with style
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # Statistics Section
    st.markdown('''
    <div class="stats-section">
        <h2 class="section-title">
            <span class="section-icon"> </span>
            <span class="section-text">Your Statistics Report</span>
        </h2>
    </div>
    ''', unsafe_allow_html=True)

    # Get user stats
    total_workouts = len(db.get_recent_workouts(365*2))
    total_attendance = len(db.get_attendance_data(365*2))
    total_nutrition = len(db.get_nutrition_data(365*2))

    col1, col2, col3 = st.columns(3)

    stats_data = [
        ("💪", "Total Workouts", total_workouts, "#667eea"),
        ("📅", "Attendance Records", total_attendance, "#764ba2"),
        ("🥗", "Nutrition Logs", total_nutrition, "#f093fb")
    ]

    for i, (icon, label, value, color) in enumerate(stats_data):
        with [col1, col2, col3][i]:
            st.markdown(f'''
            <div class="stat-card" style="--accent-color: {color}">
                <div class="stat-icon">{icon}</div>
                <div class="stat-content">
                    <div class="stat-number">{value}</div>
                    <div class="stat-label">{label}</div>
                </div>
                <div class="stat-background"></div>
            </div>
            ''', unsafe_allow_html=True)

    # Another divider
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # Danger Zone Section
    st.markdown('''
    <div class="danger-section">
        <h2 class="section-title danger-title">
            <span class="section-icon"> </span>
            <span class="section-text">Danger Zone</span>
        </h2>
    </div>
    ''', unsafe_allow_html=True)

    # Enhanced warning banner
    st.markdown('''
    <div class="warning-banner">
        <div class="warning-header">
            <div class="warning-icon">🗑️</div>
            <h3 class="warning-title">Delete Account</h3>
        </div>
        <div class="warning-content">
            <p class="warning-text">
                <strong>Warning:</strong> This action cannot be undone. All your data including 
                workouts, attendance, nutrition logs, and account information will be 
                permanently deleted.
            </p>
        </div>
    </div>
    ''', unsafe_allow_html=True)

    # Delete confirmation logic with enhanced styling
    if 'show_delete_confirmation' not in st.session_state:
        st.session_state.show_delete_confirmation = False

    st.markdown('<div class="delete-actions">', unsafe_allow_html=True)

    if not st.session_state.show_delete_confirmation:
        if st.button("🗑️ Delete My Account", type="secondary", key="delete_btn"):
            st.session_state.show_delete_confirmation = True
            st.rerun()
    else:
        # Confirmation dialog
        st.markdown('''
        <div class="confirmation-dialog">
            <div class="dialog-header">
                <h3 class="dialog-title">⚠️ Confirm Account Deletion</h3>
                <p class="dialog-subtitle">This action is irreversible</p>
            </div>
            <div class="dialog-content">
                <p class="confirmation-text">Type your username to confirm deletion:</p>
            </div>
        </div>
        ''', unsafe_allow_html=True)

        # Input container
        st.markdown('<div class="input-container">', unsafe_allow_html=True)
        confirmation_input = st.text_input(
            "Enter your username:",
            key="delete_confirmation",
            placeholder="Type your username here..."
        )
        st.markdown('</div>', unsafe_allow_html=True)

        # Button container
        st.markdown('<div class="button-container">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1, 1])

        with col1:
            if st.button("Cancel", use_container_width=True, key="cancel_btn"):
                st.session_state.show_delete_confirmation = False
                st.rerun()

        with col2:
            st.markdown('<div class="spacer"></div>', unsafe_allow_html=True)

        with col3:
            if st.button("🗑️ DELETE ACCOUNT", type="primary", use_container_width=True, key="confirm_delete_btn"):
                if confirmation_input == user_data['username']:
                    success, message = delete_user_profile(user_data['_id'])
                    if success:
                        # Clear session state
                        st.session_state.authenticated = False
                        st.session_state.user_data = None
                        if 'show_delete_confirmation' in st.session_state:
                            del st.session_state.show_delete_confirmation

                        st.markdown('''
                        <div class="success-message">
                            <div class="success-icon">✅</div>
                            <p>Account deleted successfully. You will be redirected to the login page.</p>
                        </div>
                        ''', unsafe_allow_html=True)
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.markdown(f'''
                        <div class="error-message">
                            <div class="error-icon"></div>
                            <p>Failed to delete account: {message}</p>
                        </div>
                        ''', unsafe_allow_html=True)
                else:
                    st.markdown('''
                    <div class="error-message">
                        <div class="error-icon"></div>
                        <p>Username doesn't match. Please try again.</p>
                    </div>
                    ''', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)  # Close button-container

    st.markdown('</div>', unsafe_allow_html=True)  # Close delete-actions
    st.markdown('</div>', unsafe_allow_html=True)  # Close profile-container
