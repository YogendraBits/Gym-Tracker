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

# Page config
st.set_page_config(
    page_title="Gym Tracker",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="expanded"
)

def load_css():
    import os
    css_file = "styles.css"
    if os.path.exists(css_file):
        with open(css_file, 'r') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    else:
        pass

load_css()

# Utility functions for authentication
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

# MongoDB connection
@st.cache_resource
def init_connection():
    try:
        client = MongoClient("mongodb+srv://2023sl93059:2023sl93059@cluster0.yvqvs.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
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
            return self.workouts.insert_one(workout_data)
    
    def log_attendance(self, date, attended, notes=""):
        if self.db is not None:
            return self.attendance.replace_one(
                self._add_user_filter({"date": date}),
                {"date": date, "attended": attended, "notes": notes, "timestamp": datetime.now(), "user_id": self.user_id},
                upsert=True
            )
    
    def log_nutrition(self, date, protein_intake, meals=None, notes=""):
        if self.db is not None:
            return self.nutrition.replace_one(
                self._add_user_filter({"date": date}),
                {"date": date, "protein_intake": protein_intake, "meals": meals or [], "notes": notes, "timestamp": datetime.now(), "user_id": self.user_id},
                upsert=True
            )
    
    def log_body_metrics(self, date, weight=None, measurements=None, notes=""):
        if self.db is not None:
            return self.body_metrics.replace_one(
                self._add_user_filter({"date": date}),
                {"date": date, "weight": weight, "measurements": measurements or {}, "notes": notes, "timestamp": datetime.now(), "user_id": self.user_id},
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

# Authentication UI
def show_auth_page():
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
        with st.form("login_form"):
            st.markdown("### Welcome Back!")
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                login_btn = st.form_submit_button("Login", use_container_width=True)
            
            if login_btn:
                if username and password:
                    success, user_data = authenticate_user(username, password)
                    if success:
                        st.session_state.authenticated = True
                        st.session_state.user_data = user_data
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
                else:
                    st.error("Please fill in all fields")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        st.markdown('<div class="auth-form">', unsafe_allow_html=True)
        with st.form("register_form"):
            st.markdown("### Join the Community!")
            full_name = st.text_input("Full Name", placeholder="Enter your full name")
            email = st.text_input("Email", placeholder="Enter your email")
            username = st.text_input("Username", placeholder="Choose a username")
            password = st.text_input("Password", type="password", placeholder="Create a password")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                register_btn = st.form_submit_button("Create Account", use_container_width=True)
            
            if register_btn:
                if all([full_name, email, username, password, confirm_password]):
                    if password == confirm_password:
                        if len(password) >= 6:
                            success, message = register_user(username, password, email, full_name)
                            if success:
                                st.success("" + message)
                                st.info("Please login with your new account")
                            else:
                                st.error(" " + message)
                        else:
                            st.error("Password must be at least 6 characters")
                    else:
                        st.error("Passwords don't match")
                else:
                    st.error("Please fill in all fields")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Default exercises database
DEFAULT_EXERCISES = {
    "Push": ["Bench Press", "Overhead Press", "Incline Dumbbell Press", "Dips", "Push-ups", "Tricep Extensions", "Lateral Raises"],
    "Pull": ["Pull-ups", "Lat Pulldowns", "Barbell Rows", "Dumbbell Rows", "Face Pulls", "Bicep Curls", "Hammer Curls"],
    "Legs": ["Squats", "Deadlifts", "Bulgarian Split Squats", "Leg Press", "Leg Curls", "Calf Raises", "Walking Lunges"],
    "Full Body": ["Burpees", "Mountain Climbers", "Kettlebell Swings", "Thrusters", "Clean and Press"],
    "Cardio": ["Treadmill", "Elliptical", "Cycling", "Rowing", "Stair Climber", "HIIT"]
}

# Timer functionality
def rest_timer(duration_minutes):
    if f"timer_start_{duration_minutes}" not in st.session_state:
        st.session_state[f"timer_start_{duration_minutes}"] = None
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button(f"▶️ Start {duration_minutes}min", key=f"start_{duration_minutes}", use_container_width=True):
            st.session_state[f"timer_start_{duration_minutes}"] = time.time()
    
    with col2:
        if st.button(f"⏹️ Stop", key=f"stop_{duration_minutes}", use_container_width=True):
            st.session_state[f"timer_start_{duration_minutes}"] = None
    
    if st.session_state[f"timer_start_{duration_minutes}"]:
        elapsed = time.time() - st.session_state[f"timer_start_{duration_minutes}"]
        remaining = (duration_minutes * 60) - elapsed
        
        if remaining > 0:
            mins, secs = divmod(int(remaining), 60)
            with col3:
                st.markdown(f"""
                <div class="timer-display">
                    <div class="timer-value">{mins:02d}:{secs:02d}</div>
                    <div class="timer-label">Remaining</div>
                </div>
                """, unsafe_allow_html=True)
            time.sleep(1)
            st.rerun()
        else:
            st.success("⏰ Rest time complete!")
            st.balloons()
            st.session_state[f"timer_start_{duration_minutes}"] = None

# Main app logic
def main_app():
    user_id = st.session_state.user_data["_id"]
    username = st.session_state.user_data["username"]
    full_name = st.session_state.user_data["full_name"]
    
    # Initialize database with user ID
    db = GymDatabase(user_id)
    
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
    
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user_data = None
        st.rerun()
    
    st.sidebar.markdown("---")
    
    # Navigation
    page = st.sidebar.selectbox(
        "🧭 Navigate",
        ["🏠 Dashboard", "💪 Today's Workout", "📊 Log Workout", "📅 Attendance", 
         "🥗 Nutrition", "📏 Body Metrics", "📈 Progress", "🎯 Goals", 
         "📋 Workout Plans", "⏱️ Timer", "📊 Export Data", "🗑️ Manage Data"]
    )
    
    # Dashboard
    if page == "🏠 Dashboard":
        st.markdown(f'<h1 class="page-title">Welcome back, {full_name.split()[0]}!</h1>', unsafe_allow_html=True)
        
        # Quick stats with enhanced styling
        col1, col2, col3, col4 = st.columns(4)
        
        # Get recent data
        recent_attendance = db.get_attendance_data(30)
        recent_nutrition = db.get_nutrition_data(30)
        recent_workouts = db.get_recent_workouts(30)
        
        with col1:
            attended_days = sum(1 for x in recent_attendance if x.get('attended', False))
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-icon">🏋️</div>
                <div class="metric-value">{attended_days}</div>
                <div class="metric-label">Gym Days (30d)</div>
                <div class="metric-delta">{attended_days/30*100:.1f}% attendance</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            protein_days = sum(1 for x in recent_nutrition if x.get('protein_intake', 0) > 0)
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-icon">🥩</div>
                <div class="metric-value">{protein_days}</div>
                <div class="metric-label">Protein Days (30d)</div>
                <div class="metric-delta">{protein_days/30*100:.1f}% consistency</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-icon">💪</div>
                <div class="metric-value">{len(recent_workouts)}</div>
                <div class="metric-label">Total Workouts (30d)</div>
                <div class="metric-delta">Keep it up!</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            current_streak = 0
            for record in sorted(recent_attendance, key=lambda x: x['date'], reverse=True):
                if record.get('attended', False):
                    current_streak += 1
                else:
                    break
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-icon">🔥</div>
                <div class="metric-value">{current_streak}</div>
                <div class="metric-label">Current Streak</div>
                <div class="metric-delta">days strong</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Quick log section
        st.markdown('<h2 class="section-title"> Quick Log</h2>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="quick-log-card">', unsafe_allow_html=True)
            st.write("**🏃 Today's Attendance**")
            today = date.today().strftime("%Y-%m-%d")
            attended_today = st.radio("Gym today?", ["Not logged", "✅ Yes", "❌ No"], key="quick_attendance")
            if attended_today != "Not logged":
                if st.button("📝 Log Attendance", use_container_width=True):
                    db.log_attendance(today, attended_today == "✅ Yes")
                    st.success("✅ Attendance logged!")
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="quick-log-card">', unsafe_allow_html=True)
            st.write("**🥩 Today's Protein**")
            protein_amount = st.number_input("Protein intake (g)", min_value=0, max_value=300, step=10, key="quick_protein")
            if st.button("📝 Log Protein", use_container_width=True):
                db.log_nutrition(today, protein_amount)
                st.success("✅ Protein logged!")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Recent activity
        st.markdown('<h2 class="section-title">  Recent Activity</h2>', unsafe_allow_html=True)
        if recent_workouts:
            latest_workout = recent_workouts[0]
            st.markdown(f"""
            <div class="activity-card">
                <div class="activity-icon">💪</div>
                <div class="activity-content">
                    <div class="activity-title">Last Workout</div>
                    <div class="activity-details">{latest_workout['date']} • {len(latest_workout.get('exercises', []))} exercises</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Weekly overview chart
        if recent_attendance:
            df_attendance = pd.DataFrame(recent_attendance)
            df_attendance['date'] = pd.to_datetime(df_attendance['date'], errors='coerce')
            df_attendance = df_attendance.dropna(subset=['date'])
            df_attendance['attended'] = df_attendance['attended'].astype(int)
            df_attendance = df_attendance.sort_values('date')

            fig = px.line(
                df_attendance,
                x='date',
                y='attended',
                title='🏋️ Gym Attendance Trend (Last 30 Days)',
                markers=True
            )

            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Attendance (1 = Yes, 0 = No)",
                font=dict(size=14),
                height=400,
                margin=dict(t=50, b=40, l=20, r=20),
            )

            st.plotly_chart(fig, use_container_width=True)


    # Today's Workout page
    elif page == "💪 Today's Workout":
        st.markdown('<h1 class="page-title">💪 Today\'s Workout</h1>', unsafe_allow_html=True)
        
        today = date.today().strftime("%Y-%m-%d")
        
        # Check if workout already exists for today
        today_workout = None
        recent_workouts = db.get_recent_workouts(1)
        if recent_workouts and recent_workouts[0]['date'] == today:
            today_workout = recent_workouts[0]
        
        if today_workout:
            st.markdown(f"""
            <div class="success-banner">
                <h3>✅ Workout Complete for {today}</h3>
                <p>Great job! You've already logged your workout today.</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown('<div class="workout-summary">', unsafe_allow_html=True)
            st.write("**Exercises completed:**")
            for exercise in today_workout.get('exercises', []):
                st.write(f"• {exercise['name']}: {len(exercise.get('sets', []))} sets")
            st.markdown('</div>', unsafe_allow_html=True)
            
            if st.button("✏️ Edit Today's Workout", use_container_width=True):
                st.session_state.edit_today = True
        
        if not today_workout or st.session_state.get('edit_today', False):
            # Get recommended workout
            st.markdown('<h2 class="section-title">🎯 Recommended Workout</h2>', unsafe_allow_html=True)
            
            last_workouts = db.get_recent_workouts(7)
            last_types = [w.get('type', 'Full Body') for w in last_workouts]
            
            if 'Push' not in last_types[-3:]:
                recommended = 'Push'
            elif 'Pull' not in last_types[-3:]:
                recommended = 'Pull'
            elif 'Legs' not in last_types[-3:]:
                recommended = 'Legs'
            else:
                recommended = 'Full Body'
            
            st.markdown(f"""
            <div class="recommendation-card">
                <div class="rec-icon">🎯</div>
                <div class="rec-content">
                    <div class="rec-title">Recommended: {recommended}</div>
                    <div class="rec-subtitle">Based on your recent workout pattern</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            workout_type = st.selectbox("Select Workout Type", list(DEFAULT_EXERCISES.keys()), 
                                      index=list(DEFAULT_EXERCISES.keys()).index(recommended))
            
            st.markdown('<h3 class="subsection-title">🎪 Select Exercises</h3>', unsafe_allow_html=True)
            selected_exercises = []
            
            # Create a grid of exercises
            exercises = DEFAULT_EXERCISES[workout_type]
            cols = st.columns(3)
            
            for i, exercise in enumerate(exercises):
                with cols[i % 3]:
                    if st.checkbox(exercise, key=f"ex_{exercise}"):
                        selected_exercises.append(exercise)
            
            # Custom exercise
            custom_exercise = st.text_input("➕ Add custom exercise", placeholder="Enter exercise name")
            if custom_exercise and st.button("Add Custom Exercise"):
                selected_exercises.append(custom_exercise)
                st.success(f"Added: {custom_exercise}")
            
            if selected_exercises:
                st.markdown(f"""
                <div class="selected-exercises">
                    <h4>Selected Exercises ({len(selected_exercises)})</h4>
                    <div class="exercise-tags">
                        {"".join([f'<span class="exercise-tag">{ex}</span>' for ex in selected_exercises])}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("🚀 Start Workout", use_container_width=True):
                    st.session_state.current_workout = {
                        'date': today,
                        'type': workout_type,
                        'exercises': [{'name': ex, 'sets': []} for ex in selected_exercises],
                        'start_time': datetime.now().isoformat(),
                        'notes': ''
                    }
                    st.rerun()
        
        # Active workout session
        if 'current_workout' in st.session_state:
            st.markdown('<h2 class="section-title">🔥 Active Workout Session</h2>', unsafe_allow_html=True)
            workout = st.session_state.current_workout
            
            # Exercise tabs
            exercise_names = [ex['name'] for ex in workout['exercises']]
            if exercise_names:
                selected_tab = st.selectbox("Current Exercise", exercise_names)
                
                # Find current exercise
                current_ex_idx = next(i for i, ex in enumerate(workout['exercises']) if ex['name'] == selected_tab)
                current_exercise = workout['exercises'][current_ex_idx]
                
                st.markdown(f'<h3 class="current-exercise">{current_exercise["name"]}</h3>', unsafe_allow_html=True)
                
                # Add set form
                with st.form(f"add_set_form_{selected_tab}"):
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        reps = st.number_input("Reps", min_value=1, max_value=50, value=10)
                    with col2:
                        weight = st.number_input("Weight (kg)", min_value=0.0, max_value=500.0, step=2.5)
                    with col3:
                        add_set = st.form_submit_button("➕ Add Set")
                    
                    if add_set:
                        new_set = {
                            'reps': reps,
                            'weight': weight,
                            'timestamp': datetime.now().isoformat()
                        }
                        st.session_state.current_workout['exercises'][current_ex_idx]['sets'].append(new_set)
                        st.success(f"Added: {reps} reps @ {weight}kg")
                        st.rerun()
                
                # Show current sets
                if current_exercise['sets']:
                    st.markdown('<h4 class="sets-title">Sets Completed</h4>', unsafe_allow_html=True)
                    for i, set_data in enumerate(current_exercise['sets']):
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.markdown(f"""
                            <div class="set-card">
                                <span class="set-number">Set {i+1}</span>
                                <span class="set-details">{set_data['reps']} reps @ {set_data['weight']}kg</span>
                            </div>
                            """, unsafe_allow_html=True)
                        with col2:
                            if st.button("🗑️", key=f"remove_set_{selected_tab}_{i}"):
                                st.session_state.current_workout['exercises'][current_ex_idx]['sets'].pop(i)
                                st.rerun()
                
                # Rest timer
                st.markdown('<h4 class="timer-title">⏱️ Rest Timer</h4>', unsafe_allow_html=True)
                rest_timer(2)
            
            # Finish workout
            st.markdown('<h3 class="section-title">🏁 Finish Workout</h3>', unsafe_allow_html=True)
            workout_notes = st.text_area("Workout Notes", placeholder="How did it go? Any observations?")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Save Workout", use_container_width=True):
                    workout['notes'] = workout_notes
                    workout['end_time'] = datetime.now().isoformat()
                    db.log_workout(workout)
                    del st.session_state.current_workout
                    st.success("Workout saved!")
                    st.balloons()
                    st.rerun()
            
            with col2:
                if st.button("Cancel Workout", use_container_width=True):
                    del st.session_state.current_workout
                    st.rerun()

    # Data Management Page
    elif page == "🗑️ Manage Data":
        st.markdown('<h1 class="page-title">Manage Your Data</h1>', unsafe_allow_html=True)
        
        tab1, tab2, tab3, tab4 = st.tabs(["🏋️ Workouts", "📅 Attendance", "🥗 Nutrition", "📏 Body Metrics"])
        
        with tab1:
            st.markdown("### Delete Workout Records")
            workouts = db.get_recent_workouts(90)
            if workouts:
                for workout in workouts:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.write(f"**{workout['date']}** - {workout.get('type', 'N/A')} ({len(workout.get('exercises', []))} exercises)")
                    with col2:
                        if st.button("🗑️", key=f"del_workout_{workout['_id']}"):
                            db.delete_workout(workout['_id'])
                            st.success("Workout deleted!")
                            st.rerun()
            else:
                st.info("No workout records found")
        
        with tab2:
            st.markdown("### Delete Attendance Records")
            attendance = db.get_attendance_data(90)
            if attendance:
                for record in attendance:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        status = "✅ Attended" if record.get('attended') else "❌ Missed"
                        st.write(f"**{record['date']}** - {status}")
                    with col2:
                        if st.button("🗑️", key=f"del_attendance_{record['date']}"):
                            db.delete_attendance(record['date'])
                            st.success("Attendance record deleted!")
                            st.rerun()
            else:
                st.info("No attendance records found")
        
        with tab3:
            st.markdown("### Delete Nutrition Records")
            nutrition = db.get_nutrition_data(90)
            if nutrition:
                for record in nutrition:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.write(f"**{record['date']}** - {record.get('protein_intake', 0)}g protein")
                    with col2:
                        if st.button("🗑️", key=f"del_nutrition_{record['date']}"):
                            db.delete_nutrition(record['date'])
                            st.success("Nutrition record deleted!")
                            st.rerun()
            else:
                st.info("No nutrition records found")
        
        with tab4:
            st.markdown("### Delete Body Metrics Records")
            metrics = db.get_body_metrics_data(90)
            if metrics:
                for record in metrics:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        weight_text = f"{record.get('weight', 'N/A')}kg" if record.get('weight') else "No weight"
                        st.write(f"**{record['date']}** - {weight_text}")
                    with col2:
                        if st.button("🗑️", key=f"del_metrics_{record['date']}"):
                            db.delete_body_metrics(record['date'])
                            st.success("Body metrics deleted!")
                            st.rerun()
            else:
                st.info("No body metrics records found")

    # Log Workout Page
    elif page == "📊 Log Workout":
        st.markdown('<h1 class="page-title">📊 Log Workout</h1>', unsafe_allow_html=True)
        
        with st.form("workout_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                workout_date = st.date_input("Workout Date", value=date.today())
                workout_type = st.selectbox("Workout Type", list(DEFAULT_EXERCISES.keys()))
            
            with col2:
                duration = st.number_input("Duration (minutes)", min_value=5, max_value=300, value=60)
                intensity = st.selectbox("Intensity", ["Low", "Moderate", "High", "Very High"])
            
            st.markdown("### Exercises")
            
            # Dynamic exercise input
            if "exercise_count" not in st.session_state:
                st.session_state.exercise_count = 1
            
            exercises_data = []
            for i in range(st.session_state.exercise_count):
                st.markdown(f"**Exercise {i+1}**")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    exercise_name = st.text_input(f"Exercise Name", key=f"ex_name_{i}")
                with col2:
                    sets = st.number_input(f"Sets", min_value=1, max_value=20, value=3, key=f"sets_{i}")
                with col3:
                    reps = st.text_input(f"Reps (e.g., 8-12)", key=f"reps_{i}")
                
                weight = st.number_input(f"Weight (kg)", min_value=0.0, step=2.5, key=f"weight_{i}")
                
                if exercise_name:
                    exercises_data.append({
                        "name": exercise_name,
                        "sets": [{"reps": reps, "weight": weight} for _ in range(sets)]
                    })
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("➕ Add Exercise"):
                    st.session_state.exercise_count += 1
                    st.rerun()
            
            workout_notes = st.text_area("Workout Notes")
            
            if st.form_submit_button("💾 Save Workout", use_container_width=True):
                workout_data = {
                    "date": workout_date.strftime("%Y-%m-%d"),
                    "type": workout_type,
                    "duration": duration,
                    "intensity": intensity,
                    "exercises": exercises_data,
                    "notes": workout_notes,
                    "timestamp": datetime.now()
                }
                
                db.log_workout(workout_data)
                st.success("✅ Workout logged successfully!")
                st.session_state.exercise_count = 1
                st.rerun()

    # Attendance Page
    elif page == "📅 Attendance":
        st.markdown('<h1 class="page-title">📅 Gym Attendance</h1>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### Log Attendance")
            attendance_date = st.date_input("Date", value=date.today())
            attended = st.selectbox("Attended Gym?", ["Yes", "No"])
            notes = st.text_area("Notes", placeholder="Any specific reason for missing?")
            
            if st.button("📝 Log Attendance", use_container_width=True):
                db.log_attendance(
                    attendance_date.strftime("%Y-%m-%d"),
                    attended == "Yes",
                    notes
                )
                st.success("✅ Attendance logged!")
                st.rerun()
        
        with col2:
            st.markdown("### Attendance History")
            attendance_data = db.get_attendance_data(30)
            
            if attendance_data:
                df = pd.DataFrame(attendance_data)
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date', ascending=False)
                
                # Attendance chart
                fig = px.scatter(df, x='date', y='attended', 
                               title='Gym Attendance (Last 30 Days)',
                               color='attended',
                               color_discrete_map={True: '#10b981', False: '#ef4444'})
                fig.update_layout(
                    yaxis=dict(tickvals=[0, 1], ticktext=['No', 'Yes']),
                    showlegend=False
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Attendance stats
                total_days = len(df)
                attended_days = df['attended'].sum()
                attendance_rate = (attended_days / total_days) * 100 if total_days > 0 else 0
                
                st.markdown(f"""
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-value">{attended_days}</div>
                        <div class="stat-label">Days Attended</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">{total_days - attended_days}</div>
                        <div class="stat-label">Days Missed</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">{attendance_rate:.1f}%</div>
                        <div class="stat-label">Attendance Rate</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("No attendance data available")

    # Nutrition Page
    elif page == "🥗 Nutrition":
        st.markdown('<h1 class="page-title">🥗 Nutrition Tracking</h1>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### Log Nutrition")
            nutrition_date = st.date_input("Date", value=date.today())
            protein_intake = st.number_input("Protein Intake (g)", min_value=0, max_value=500, step=5)
            
            st.markdown("**Meals**")
            meals = []
            for i in range(3):
                meal_name = ["Breakfast", "Lunch", "Dinner"][i]
                meal_desc = st.text_input(f"{meal_name}", placeholder=f"Describe your {meal_name.lower()}")
                if meal_desc:
                    meals.append({"meal": meal_name, "description": meal_desc})
            
            nutrition_notes = st.text_area("Nutrition Notes")
            
            if st.button("📝 Log Nutrition", use_container_width=True):
                db.log_nutrition(
                    nutrition_date.strftime("%Y-%m-%d"),
                    protein_intake,
                    meals,
                    nutrition_notes
                )
                st.success("✅ Nutrition logged!")
                st.rerun()
        
        with col2:
            st.markdown("### Nutrition History")
            nutrition_data = db.get_nutrition_data(30)
            
            if nutrition_data:
                df = pd.DataFrame(nutrition_data)
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')
                
                # Protein intake chart
                fig = px.line(df, x='date', y='protein_intake',
                             title='Daily Protein Intake (Last 30 Days)',
                             color_discrete_sequence=['#8b5cf6'])
                fig.add_hline(y=150, line_dash="dash", line_color="red", 
                             annotation_text="Target: 150g")
                st.plotly_chart(fig, use_container_width=True)
                
                # Nutrition stats
                avg_protein = df['protein_intake'].mean()
                max_protein = df['protein_intake'].max()
                days_above_target = (df['protein_intake'] >= 150).sum()
                
                st.markdown(f"""
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-value">{avg_protein:.1f}g</div>
                        <div class="stat-label">Avg Daily Protein</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">{max_protein:.0f}g</div>
                        <div class="stat-label">Highest Day</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">{days_above_target}</div>
                        <div class="stat-label">Days Above Target</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("No nutrition data available")

    # Body Metrics Page
    elif page == "📏 Body Metrics":
        st.markdown('<h1 class="page-title">📏 Body Metrics</h1>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### Log Body Metrics")
            metrics_date = st.date_input("Date", value=date.today())
            weight = st.number_input("Weight (kg)", min_value=30.0, max_value=200.0, step=0.1)
            
            st.markdown("**Body Measurements (cm)**")
            measurements = {}
            measurement_types = ["Chest", "Waist", "Hips", "Arms", "Thighs"]
            
            for measurement in measurement_types:
                value = st.number_input(f"{measurement}", min_value=0.0, max_value=200.0, step=0.5, key=f"measurement_{measurement}")
                if value > 0:
                    measurements[measurement.lower()] = value
            
            metrics_notes = st.text_area("Notes")
            
            if st.button("📝 Log Metrics", use_container_width=True):
                db.log_body_metrics(
                    metrics_date.strftime("%Y-%m-%d"),
                    weight if weight > 0 else None,
                    measurements,
                    metrics_notes
                )
                st.success("✅ Body metrics logged!")
                st.rerun()
        
        with col2:
            st.markdown("### Metrics History")
            metrics_data = db.get_body_metrics_data(90)
            
            if metrics_data:
                df = pd.DataFrame(metrics_data)
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')
                
                # Weight chart
                if 'weight' in df.columns and df['weight'].notna().any():
                    fig = px.line(df, x='date', y='weight',
                                 title='Weight Progress (Last 90 Days)',
                                 color_discrete_sequence=['#06b6d4'])
                    st.plotly_chart(fig, use_container_width=True)
                
                # Show latest measurements
                if measurements:
                    latest_metrics = df.iloc[-1] if len(df) > 0 else None
                    if latest_metrics and 'measurements' in latest_metrics:
                        st.markdown("### Latest Measurements")
                        latest_measurements = latest_metrics['measurements']
                        for key, value in latest_measurements.items():
                            st.metric(key.title(), f"{value} cm")
            else:
                st.info("No body metrics data available")

    # Progress Page
    elif page == "📈 Progress":
        st.markdown('<h1 class="page-title">📈 Your Progress</h1>', unsafe_allow_html=True)
        
        # Time period selector
        period = st.selectbox("Time Period", ["Last 30 Days", "Last 90 Days", "Last 6 Months", "All Time"])
        days_map = {"Last 30 Days": 30, "Last 90 Days": 90, "Last 6 Months": 180, "All Time": 365*2}
        days = days_map[period]
        
        # Get all data
        workouts = db.get_recent_workouts(days)
        attendance = db.get_attendance_data(days)
        nutrition = db.get_nutrition_data(days)
        
        if workouts or attendance or nutrition:
            # Create multi-metric dashboard
            col1, col2 = st.columns(2)
            
            with col1:
                # Workout frequency
                if workouts:
                    workout_df = pd.DataFrame(workouts)
                    workout_df['date'] = pd.to_datetime(workout_df['date'])
                    workout_counts = workout_df.groupby(workout_df['date'].dt.date).size().reset_index()
                    workout_counts.columns = ['date', 'workouts']
                    
                    fig = px.bar(workout_counts, x='date', y='workouts',
                               title='Workout Frequency',
                               color_discrete_sequence=['#10b981'])
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Attendance pattern
                if attendance:
                    attendance_df = pd.DataFrame(attendance)
                    attendance_df['date'] = pd.to_datetime(attendance_df['date'])
                    
                    fig = px.scatter(attendance_df, x='date', y='attended',
                                   title='Gym Attendance Pattern',
                                   color='attended',
                                   color_discrete_map={True: '#10b981', False: '#ef4444'})
                    fig.update_layout(yaxis=dict(tickvals=[0, 1], ticktext=['No', 'Yes']))
                    st.plotly_chart(fig, use_container_width=True)
            
            # Workout type distribution
            if workouts:
                type_counts = pd.Series([w.get('type', 'Unknown') for w in workouts]).value_counts()
                fig = px.pie(values=type_counts.values, names=type_counts.index,
                           title='Workout Type Distribution')
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available for the selected period")

    # Goals Page
    elif page == "🎯 Goals":
        st.markdown('<h1 class="page-title">🎯 Set Your Goals</h1>', unsafe_allow_html=True)
        
        st.markdown("""
        <div class="info-banner">
            <h3>🚀 Goal Setting Tips</h3>
            <p>Set SMART goals: Specific, Measurable, Achievable, Relevant, Time-bound</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Quick goal templates
        st.markdown("### Quick Goal Templates")
        goal_templates = {
            "Weight Loss": {"target": "Lose 5kg", "deadline": 90, "metric": "weight"},
            "Strength": {"target": "Bench press bodyweight", "deadline": 120, "metric": "strength"},
            "Consistency": {"target": "Gym 5 days/week", "deadline": 30, "metric": "attendance"},
            "Protein": {"target": "150g protein daily", "deadline": 30, "metric": "nutrition"}
        }
        
        selected_template = st.selectbox("Choose a template", ["Custom"] + list(goal_templates.keys()))
        
        with st.form("goal_form"):
            if selected_template != "Custom":
                template = goal_templates[selected_template]
                goal_title = st.text_input("Goal Title", value=template["target"])
                target_date = st.date_input("Target Date", 
                                          value=date.today() + timedelta(days=template["deadline"]))
            else:
                goal_title = st.text_input("Goal Title", placeholder="e.g., Run 5km without stopping")
                target_date = st.date_input("Target Date", value=date.today() + timedelta(days=30))
            
            goal_description = st.text_area("Description", 
                                          placeholder="Describe your goal and why it's important to you")
            goal_category = st.selectbox("Category", 
                                       ["Strength", "Endurance", "Weight Loss", "Weight Gain", 
                                        "Flexibility", "Consistency", "Other"])
            
            if st.form_submit_button("🎯 Set Goal", use_container_width=True):
                # In a real app, you'd save this to the database
                st.success("✅ Goal set successfully!")
                st.balloons()

    # Workout Plans Page
    elif page == "📋 Workout Plans":
        st.markdown('<h1 class="page-title">📋 Workout Plans</h1>', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["📝 Create Plan", "📚 My Plans"])
        
        with tab1:
            with st.form("workout_plan_form"):
                plan_name = st.text_input("Plan Name", placeholder="e.g., Push Pull Legs")
                plan_description = st.text_area("Description", 
                                               placeholder="Describe your workout plan")
                
                st.markdown("### Plan Structure")
                days = st.multiselect("Training Days", 
                                    ["Monday", "Tuesday", "Wednesday", "Thursday", 
                                     "Friday", "Saturday", "Sunday"])
                
                plan_data = {"name": plan_name, "description": plan_description, "days": days, "exercises": {}}
                
                for day in days:
                    st.markdown(f"**{day} Workout**")
                    workout_type = st.selectbox(f"Workout Type for {day}", 
                                              list(DEFAULT_EXERCISES.keys()), key=f"type_{day}")
                    selected_exercises = st.multiselect(f"Exercises for {day}", 
                                                      DEFAULT_EXERCISES[workout_type], key=f"ex_{day}")
                    plan_data["exercises"][day] = {"type": workout_type, "exercises": selected_exercises}
                
                if st.form_submit_button("💾 Save Plan", use_container_width=True):
                    if plan_name and days:
                        db.save_workout_plan(plan_data)
                        st.success("✅ Workout plan saved!")
                    else:
                        st.error("Please fill in plan name and select training days")
        
        with tab2:
            plans = db.get_workout_plans()
            if plans:
                for plan in plans:
                    with st.expander(f"📋 {plan['name']}"):
                        st.write(plan.get('description', 'No description'))
                        st.write(f"**Training Days:** {', '.join(plan.get('days', []))}")
                        
                        for day, workout in plan.get('exercises', {}).items():
                            st.write(f"**{day}:** {workout.get('type', 'N/A')} - {len(workout.get('exercises', []))} exercises")
                        
                        if st.button(f"🗑️ Delete {plan['name']}", key=f"del_plan_{plan['name']}"):
                            db.delete_workout_plan(plan['name'])
                            st.rerun()
            else:
                st.info("No workout plans created yet")

    # Timer Page
    elif page == "⏱️ Timer":
        st.markdown('<h1 class="page-title">⏱️ Workout Timers</h1>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Rest Timers")
            st.markdown("**Quick Rest Periods**")
            rest_timer(1)
            rest_timer(2)
            rest_timer(3)
            rest_timer(5)
        
        with col2:
            st.markdown("### Custom Timer")
            custom_minutes = st.number_input("Custom Timer (minutes)", min_value=1, max_value=60, value=2)
            rest_timer(custom_minutes)
        
        # Workout timer (simple implementation)
        st.markdown("---")
        st.markdown("### Workout Timer")
        
        if "workout_timer_start" not in st.session_state:
            st.session_state.workout_timer_start = None
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("▶️ Start Workout Timer", use_container_width=True):
                st.session_state.workout_timer_start = time.time()
        
        with col2:
            if st.button("⏹️ Stop Workout Timer", use_container_width=True):
                st.session_state.workout_timer_start = None
        
        if st.session_state.workout_timer_start:
            elapsed = time.time() - st.session_state.workout_timer_start
            hours, remainder = divmod(int(elapsed), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            with col3:
                st.markdown(f"""
                <div class="workout-timer">
                    <div class="timer-display-large">{hours:02d}:{minutes:02d}:{seconds:02d}</div>
                    <div class="timer-label">Workout Duration</div>
                </div>
                """, unsafe_allow_html=True)
            time.sleep(1)
            st.rerun()

    # Export Data Page
    elif page == "📊 Export Data":
        st.markdown('<h1 class="page-title">📊 Export Your Data</h1>', unsafe_allow_html=True)
        
        st.markdown("Export your fitness data for backup or analysis in other tools.")
        
        export_period = st.selectbox("Export Period", 
                                   ["Last 30 Days", "Last 90 Days", "Last 6 Months", "All Time"])
        days_map = {"Last 30 Days": 30, "Last 90 Days": 90, "Last 6 Months": 180, "All Time": 365*2}
        days = days_map[export_period]
        
        if st.button("📊 Generate Export", use_container_width=True):
            # Get all data
            workouts = db.get_recent_workouts(days)
            attendance = db.get_attendance_data(days)
            nutrition = db.get_nutrition_data(days)
            body_metrics = db.get_body_metrics_data(days)
            
            # Create export data
            export_data = {
                "export_date": datetime.now().isoformat(),
                "user": username,
                "period": export_period,
                "data": {
                    "workouts": workouts,
                    "attendance": attendance,
                    "nutrition": nutrition,
                    "body_metrics": body_metrics
                },
                "summary": {
                    "total_workouts": len(workouts),
                    "total_attendance_records": len(attendance),
                    "total_nutrition_records": len(nutrition),
                    "total_body_metrics": len(body_metrics)
                }
            }
            
            # Convert to JSON
            json_data = json.dumps(export_data, indent=2, default=str)
            
            # Provide download
            st.download_button(
                label="💾 Download JSON Export",
                data=json_data,
                file_name=f"gym_tracker_export_{username}_{date.today()}.json",
                mime="application/json"
            )
            
            # Show summary
            st.markdown("### Export Summary")
            st.json(export_data["summary"])

# Main execution
if __name__ == "__main__":
    if not check_authentication():
        show_auth_page()
    else:
        main_app()