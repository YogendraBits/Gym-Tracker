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
    with open("styles.css", "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


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

    # Enhanced Goals Page Function

    def show_goals_page(db):
        # Page header with enhanced styling
        st.markdown("""
        <div class="goals-header">
            <h1>🎯 Goals & Progress Tracking</h1>
            <div class="subtitle">Monitor your achievements and stay motivated</div>
        </div>
        """, unsafe_allow_html=True)

        # Get goal statistics (assuming db.get_goal_statistics() returns the stats)
        stats = db.get_goal_statistics()

        # Alternative: Using Streamlit's native columns with enhanced styling
        st.markdown("---")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown("""
            <div style='text-align: center; padding: 1rem; background: linear-gradient(135deg, #3498db, #2980b9); 
                        border-radius: 10px; color: white; margin-bottom: 1rem;'>
                <h3 style='margin: 0; font-size: 2rem;'>{}</h3>
                <p style='margin: 0; opacity: 0.9;'>Total Goals</p>
            </div>
            """.format(stats["total"]), unsafe_allow_html=True)

        with col2:
            st.markdown("""
            <div style='text-align: center; padding: 1rem; background: linear-gradient(135deg, #e74c3c, #c0392b); 
                        border-radius: 10px; color: white; margin-bottom: 1rem;'>
                <h3 style='margin: 0; font-size: 2rem;'>{}</h3>
                <p style='margin: 0; opacity: 0.9;'>Active Goals</p>
            </div>
            """.format(stats["active"]), unsafe_allow_html=True)

        with col3:
            st.markdown("""
            <div style='text-align: center; padding: 1rem; background: linear-gradient(135deg, #27ae60, #229954); 
                        border-radius: 10px; color: white; margin-bottom: 1rem;'>
                <h3 style='margin: 0; font-size: 2rem;'>{}</h3>
                <p style='margin: 0; opacity: 0.9;'>Completed Goals</p>
            </div>
            """.format(stats["completed"]), unsafe_allow_html=True)

        with col4:
            st.markdown("""
            <div style='text-align: center; padding: 1rem; background: linear-gradient(135deg, #f39c12, #e67e22); 
                        border-radius: 10px; color: white; margin-bottom: 1rem;'>
                <h3 style='margin: 0; font-size: 2rem;'>{:.1f}%</h3>
                <p style='margin: 0; opacity: 0.9;'>Completion Rate</p>
            </div>
            """.format(stats['completion_rate']), unsafe_allow_html=True)

        st.markdown("---")

        # Tabs for different sections
        tab1, tab2, tab3, tab4 = st.tabs(
            ["📋 All Goals", "➕ Add Goal", "📊 Progress", "📈 Analytics"])

        with tab1:
            db.show_all_goals()

        with tab2:
            db.show_add_goal_form()

        with tab3:
            db.show_goal_progress()

        with tab4:
            db.show_goal_analytics()


    def show_all_goals(db):
        """Display all goals with management options"""
        st.markdown("### 📋 Your Goals")

        # Filter options
        col1, col2 = st.columns(2)
        with col1:
            status_filter = st.selectbox(
                "Filter by Status", ["All", "Active", "Completed", "Paused"])
        with col2:
            sort_option = st.selectbox(
                "Sort by", ["Newest First", "Oldest First", "Target Date"])

        # Get goals based on filter
        if status_filter == "All":
            goals = db.get_goals()
        else:
            goals = db.get_goals(status_filter.lower())

        if not goals:
            st.info("No goals found. Start by adding your first goal!")
            return

        # Sort goals
        if sort_option == "Oldest First":
            goals = sorted(goals, key=lambda x: x.get(
                "created_at", datetime.now()))
        elif sort_option == "Target Date":
            goals = sorted(goals, key=lambda x: x.get("target_date", "9999-12-31"))

        # Display goals
        for goal in goals:
            db.display_goal_card(goal)


    def display_goal_card(db, goal):
        """Display individual goal card with actions"""
        status_colors = {
            "active": "🟢",
            "completed": "✅",
            "paused": "⏸️"
        }

        status_icon = status_colors.get(goal.get("status", "active"), "🟢")

        with st.container():
            st.markdown(f"""
            <div class="goal-card">
                <div class="goal-header">
                    <h3>{status_icon} {goal['title']}</h3>
                    <span class="goal-category">{goal.get('category', 'General')}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                st.write(
                    f"**Description:** {goal.get('description', 'No description')}")
                st.write(f"**Target Date:** {goal.get('target_date', 'Not set')}")

                # Progress bar if current progress exists
                if goal.get("current_progress") is not None and goal.get("target_value"):
                    progress = min(goal["current_progress"] /
                                goal["target_value"] * 100, 100)
                    st.progress(progress / 100, f"Progress: {progress:.1f}%")

            with col2:
                # Quick actions
                if goal.get("status") == "active":
                    if st.button("✅ Complete", key=f"complete_{goal['_id']}", use_container_width=True):
                        db.update_goal_status(goal["_id"], "completed")
                        st.success("Goal marked as completed!")
                        st.rerun()

                    if st.button("⏸️ Pause", key=f"pause_{goal['_id']}", use_container_width=True):
                        db.update_goal_status(goal["_id"], "paused")
                        st.rerun()

                elif goal.get("status") == "paused":
                    if st.button("▶️ Resume", key=f"resume_{goal['_id']}", use_container_width=True):
                        db.update_goal_status(goal["_id"], "active")
                        st.rerun()

                elif goal.get("status") == "completed":
                    if st.button("🔄 Reactivate", key=f"reactivate_{goal['_id']}", use_container_width=True):
                        db.update_goal_status(goal["_id"], "active")
                        st.rerun()

            with col3:
                # Progress update
                if goal.get("status") == "active":
                    with st.popover("📊 Update Progress"):
                        with st.form(f"progress_form_{goal['_id']}"):
                            progress_value = st.number_input("Current Progress",
                                                            value=goal.get("current_progress", 0))
                            progress_notes = st.text_area("Notes (optional)")

                            if st.form_submit_button("Update Progress"):
                                progress_data = {
                                    "progress_value": progress_value,
                                    "notes": progress_notes
                                }
                                db.update_goal_progress(goal["_id"], progress_data)
                                st.success("Progress updated!")
                                st.rerun()

                # Delete option
                with st.popover("🗑️ Delete"):
                    st.warning("This action cannot be undone!")
                    if st.button("Confirm Delete", key=f"delete_{goal['_id']}", type="secondary"):
                        db.delete_goal(goal["_id"])
                        st.success("Goal deleted!")
                        st.rerun()

            st.markdown("---")


    def show_add_goal_form(db):
        """Show form to add new goal"""
        st.markdown("### ➕ Add New Goal")

        st.markdown("""
        <div class="info-banner">
            <h3>🚀 Goal Setting Tips</h3>
            <p>Set SMART goals: Specific, Measurable, Achievable, Relevant, Time-bound</p>
        </div>
        """, unsafe_allow_html=True)

        # Goal templates
        st.markdown("#### Quick Goal Templates")
        goal_templates = {
            "Weight Loss": {"target": "Lose 5kg", "deadline": 90, "metric": "weight", "target_value": 5},
            "Strength": {"target": "Bench press bodyweight", "deadline": 120, "metric": "strength", "target_value": 100},
            "Consistency": {"target": "Gym 5 days/week", "deadline": 30, "metric": "attendance", "target_value": 20},
            "Protein": {"target": "150g protein daily", "deadline": 30, "metric": "nutrition", "target_value": 150}
        }

        selected_template = st.selectbox(
            "Choose a template", ["Custom"] + list(goal_templates.keys()))

        with st.form("goal_form"):
            col1, col2 = st.columns(2)

            with col1:
                if selected_template != "Custom":
                    template = goal_templates[selected_template]
                    goal_title = st.text_input(
                        "Goal Title", value=template["target"])
                    target_date = st.date_input("Target Date",
                                                value=date.today() + timedelta(days=template["deadline"]))
                    target_value = st.number_input(
                        "Target Value", value=float(template["target_value"]))
                    goal_category = st.selectbox("Category",
                                                ["Strength", "Endurance", "Weight Loss", "Weight Gain",
                                                "Flexibility", "Consistency", "Nutrition", "Other"],
                                                index=["Weight Loss", "Strength", "Consistency", "Nutrition"].index(selected_template) if selected_template in ["Weight Loss", "Strength", "Consistency", "Nutrition"] else 0)
                else:
                    goal_title = st.text_input(
                        "Goal Title", placeholder="e.g., Run 5km without stopping")
                    target_date = st.date_input(
                        "Target Date", value=date.today() + timedelta(days=30))
                    target_value = st.number_input(
                        "Target Value (if measurable)", value=0.0, help="Enter target number for measurable goals")
                    goal_category = st.selectbox("Category",
                                                ["Strength", "Endurance", "Weight Loss", "Weight Gain",
                                                "Flexibility", "Consistency", "Nutrition", "Other"])

            with col2:
                goal_description = st.text_area("Description",
                                                placeholder="Describe your goal and why it's important to you",
                                                height=100)
                priority = st.selectbox("Priority", ["Low", "Medium", "High"])
                is_public = st.checkbox(
                    "Make this goal visible to others (if applicable)")
                reminder_frequency = st.selectbox("Reminder Frequency",
                                                ["None", "Daily", "Weekly", "Monthly"])

            current_progress = st.number_input("Current Progress", value=0.0,
                                            help="Your starting point for this goal")

            if st.form_submit_button("🎯 Create Goal", use_container_width=True):
                if goal_title and target_date:
                    goal_data = {
                        "title": goal_title,
                        "description": goal_description,
                        "category": goal_category,
                        "target_date": target_date.strftime("%Y-%m-%d"),
                        "target_value": target_value if target_value > 0 else None,
                        "current_progress": current_progress,
                        "priority": priority,
                        "is_public": is_public,
                        "reminder_frequency": reminder_frequency
                    }

                    db.save_goal(goal_data)
                    st.success("✅ Goal created successfully!")
                    st.balloons()
                else:
                    st.error(
                        "Please fill in the required fields (Title and Target Date)")


    def show_goal_progress(db):
        """Show goal progress tracking"""
        st.markdown("### 📊 Goal Progress Tracking")

        active_goals = db.get_goals("active")

        if not active_goals:
            st.info("No active goals to track progress for.")
            return

        # Select goal to update
        goal_options = {
            f"{goal['title']} ({goal['category']})": goal for goal in active_goals}
        selected_goal_name = st.selectbox(
            "Select Goal to Update", list(goal_options.keys()))

        if selected_goal_name:
            selected_goal = goal_options[selected_goal_name]

            # Display current progress
            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"**Current Goal:** {selected_goal['title']}")
                st.markdown(f"**Category:** {selected_goal['category']}")
                st.markdown(
                    f"**Target Date:** {selected_goal.get('target_date', 'Not set')}")

                if selected_goal.get("target_value"):
                    current = selected_goal.get("current_progress", 0)
                    target = selected_goal["target_value"]
                    progress_percentage = min(current / target * 100, 100)
                    st.progress(progress_percentage / 100,
                                f"Progress: {progress_percentage:.1f}%")
                    st.markdown(f"**Progress:** {current} / {target}")

            with col2:
                # Progress update form
                with st.form("update_progress_form"):
                    st.markdown("#### Update Progress")
                    new_progress = st.number_input("New Progress Value",
                                                value=selected_goal.get("current_progress", 0))
                    progress_date = st.date_input(
                        "Progress Date", value=date.today())
                    progress_notes = st.text_area(
                        "Notes", placeholder="What did you accomplish?")

                    if st.form_submit_button("Update Progress"):
                        progress_data = {
                            "progress_value": new_progress,
                            "date": progress_date.strftime("%Y-%m-%d"),
                            "notes": progress_notes
                        }
                        db.update_goal_progress(
                            selected_goal["_id"], progress_data)
                        st.success("Progress updated successfully!")
                        st.rerun()

            # Progress history
            if selected_goal.get("progress_logs"):
                st.markdown("#### Progress History")
                progress_logs = selected_goal["progress_logs"]

                # Create progress chart
                dates = [log["date"] for log in progress_logs]
                values = [log["progress_value"] for log in progress_logs]

                if len(dates) > 1:
                    fig = px.line(x=dates, y=values, title="Progress Over Time",
                                labels={"x": "Date", "y": "Progress Value"})
                    st.plotly_chart(fig, use_container_width=True)

                # Progress table
                progress_df = pd.DataFrame(progress_logs)
                if not progress_df.empty:
                    progress_df = progress_df.sort_values("date", ascending=False)
                    st.dataframe(
                        progress_df[["date", "progress_value", "notes"]], use_container_width=True)


    def show_goal_analytics(db):
        """Show goal analytics and insights"""
        st.markdown("### 📈 Goal Analytics & Insights")

        all_goals = db.get_goals()

        if not all_goals:
            st.info("No goals found for analytics.")
            return

        # Create analytics
        goals_df = pd.DataFrame(all_goals)

        col1, col2 = st.columns(2)

        with col1:
            # Goals by category
            if "category" in goals_df.columns:
                category_counts = goals_df["category"].value_counts()
                fig_category = px.pie(values=category_counts.values, names=category_counts.index,
                                    title="Goals by Category")
                st.plotly_chart(fig_category, use_container_width=True)

        with col2:
            # Goals by status
            if "status" in goals_df.columns:
                status_counts = goals_df["status"].value_counts()
                fig_status = px.bar(x=status_counts.index, y=status_counts.values,
                                    title="Goals by Status")
                st.plotly_chart(fig_status, use_container_width=True)

        # Goals timeline
        if "created_at" in goals_df.columns:
            goals_df["created_date"] = pd.to_datetime(
                goals_df["created_at"]).dt.date
            goals_timeline = goals_df.groupby(
                "created_date").size().reset_index(name="count")

            fig_timeline = px.line(goals_timeline, x="created_date", y="count",
                                title="Goals Created Over Time")
            st.plotly_chart(fig_timeline, use_container_width=True)

        # Success insights
        st.markdown("#### 🎯 Success Insights")

        completed_goals = [g for g in all_goals if g.get("status") == "completed"]

        if completed_goals:
            avg_completion_time = []
            for goal in completed_goals:
                if goal.get("completed_at") and goal.get("created_at"):
                    completion_time = (
                        goal["completed_at"] - goal["created_at"]).days
                    avg_completion_time.append(completion_time)

            if avg_completion_time:
                avg_days = sum(avg_completion_time) / len(avg_completion_time)
                st.metric("Average Goal Completion Time", f"{avg_days:.1f} days")

            # Most successful categories
            completed_df = pd.DataFrame(completed_goals)
            if "category" in completed_df.columns:
                successful_categories = completed_df["category"].value_counts()
                st.markdown("**Most Successful Categories:**")
                for category, count in successful_categories.head(3).items():
                    st.write(f"• {category}: {count} completed goals")

        else:
            st.info("Complete some goals to see success insights!")


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
            st.markdown("### Your Personalized Dashboard")
            username = st.text_input(
                "Username", placeholder="Enter your username")
            password = st.text_input(
                "Password", type="password", placeholder="Enter your password")

            col1, col2 = st.columns([1, 1])
            with col1:
                login_btn = st.form_submit_button(
                    "Login", use_container_width=True)

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
            full_name = st.text_input(
                "Full Name", placeholder="Enter your full name")
            email = st.text_input("Email", placeholder="Enter your email")
            username = st.text_input(
                "Username", placeholder="Choose a username")
            password = st.text_input(
                "Password", type="password", placeholder="Create a password")
            confirm_password = st.text_input(
                "Confirm Password", type="password", placeholder="Confirm your password")

            col1, col2 = st.columns([1, 1])
            with col1:
                register_btn = st.form_submit_button(
                    "Create Account", use_container_width=True)

            if register_btn:
                if all([full_name, email, username, password, confirm_password]):
                    if password == confirm_password:
                        if len(password) >= 6:
                            success, message = register_user(
                                username, password, email, full_name)
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


# Profile management page
def show_profile_page(user_data, db):
    # Main container
    st.markdown('<div class="profile-container">', unsafe_allow_html=True)

    # Page header with enhanced styling
    st.markdown('''
    <div class="profile-header">
        <h1 class="page-title">🧑‍💻Profile Settings</h1>
        <p class="page-subtitle">Manage your account information and preferences</p>
    </div>
    ''', unsafe_allow_html=True)

    # Account Information Section
    st.markdown('''
    <div class="info-section">
        <h2 class="section-title">
            <span class="section-icon"> 📋 </span>
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
            <span class="section-icon">📎</span>
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
            <span class="section-icon">⚠️</span>
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
            if st.button("❌ Cancel", use_container_width=True, key="cancel_btn"):
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
                            <div class="error-icon">❌</div>
                            <p>Failed to delete account: {message}</p>
                        </div>
                        ''', unsafe_allow_html=True)
                else:
                    st.markdown('''
                    <div class="error-message">
                        <div class="error-icon">❌</div>
                        <p>Username doesn't match. Please try again.</p>
                    </div>
                    ''', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)  # Close button-container

    st.markdown('</div>', unsafe_allow_html=True)  # Close delete-actions
    st.markdown('</div>', unsafe_allow_html=True)  # Close profile-container


# Default exercises database
DEFAULT_EXERCISES = {
    "Full Body Warm-Up": [
        "Arm Circles (forward/backward, 30 sec each)",
        "Torso Twists (30 sec)",
        "Leg Swings (forward/backward + side-to-side, 15 each leg)",
        "Hip Circles (20 seconds each direction)",
        "Jumping Jacks (30-60 sec)"
    ],
    "Lower Body Activation": [
        "Bodyweight Squats (15 reps)",
        "Walking Lunges (10-12 steps each leg)",
        "High Knees (30 sec)",
        "Butt Kicks (30 sec)",
        "Glute Bridges (15 reps)"
    ],
    "Upper Body Activation": [
        "Shoulder Rolls (forward/backward, 30 sec each)",
        "Arm Swings (across chest, 30 sec)",
        "Scapular Push-ups (10-15 reps)",
        "Wall Angels (10 slow reps)",
        "Inchworms with Reach (5-8 reps)"
    ],
    "Chest + Triceps + Cardio": [
        "Bench Press",
        "Incline Dumbbell Press",
        "Overhead Press",
        "Dips",
        "Tricep Extensions",
        "Treadmill Sprints (HIIT)"
    ],
    "Legs + Core": [
        "Squats",
        "Bulgarian Split Squats",
        "Leg Curls",
        "Calf Raises",
        "Planks",
        "Cycling (Light)"
    ],
    "Back + Biceps": [
        "Deadlifts",
        "Pull-ups",
        "Barbell Rows",
        "Face Pulls",
        "Bicep Curls",
        "Hammer Curls"
    ],
    "Active Recovery / Cardio": [
        "Elliptical (Steady State)",
        "Cycling (Steady)",
        "Walking",
        "Mobility Work",
        "Stretching"
    ],
    "Legs + Glutes": [
        "Leg Press",
        "Walking Lunges",
        "Romanian Deadlifts",
        "Step-ups",
        "Calf Raises",
        "Mountain Climbers"
    ],
    "Full Body Conditioning + Shoulders": [
        "Kettlebell Swings",
        "Thrusters",
        "Clean and Press",
        "Lateral Raises",
        "Burpees",
        "HIIT Circuit"
    ],
    "Rest / Light Cardio": [
        "Light Treadmill Walk",
        "Stretching",
        "Yoga",
        "Foam Rolling"
    ]
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
        elapsed = time.time() - \
            st.session_state[f"timer_start_{duration_minutes}"]
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

    col1, col2 = st.sidebar.columns(2)

    with col2:
        if st.button("Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user_data = None
            st.rerun()

    st.sidebar.markdown("---")

    # Navigation
    page = st.sidebar.radio(
        "🧭 Navigate",
        ["👤 Profile", "🏠 Dashboard", "👁️ View Workouts", "📊 Log Workout", "📅 Attendance",
         "🥗 Nutrition", "📏 Body Metrics", "📈 Progress", "🎯 Goals",
         "📋 Workout Plans", "⏱️ Timer", "📊 Export Data", "🗑️ Manage Data"],
        label_visibility="collapsed",  # Optional: hide label text
        index=1  # Default selection
    )

    # Check if profile page is requested
    if page == "👤 Profile":
        def load_css():
            with open("profile.css", "r", encoding="utf-8") as f:
                st.markdown(f"<style>{f.read()}</style>",
                            unsafe_allow_html=True)
        load_css()
        show_profile_page(st.session_state.user_data, db)
        return

    # Dashboard
    if page == "🏠 Dashboard":

        def load_css():
            with open("dashboard.css", "r", encoding="utf-8") as f:
                st.markdown(f"<style>{f.read()}</style>",
                            unsafe_allow_html=True)

        load_css()
        # Main dashboard container with gradient background
        st.markdown(
            f'''
            <div class="dashboard-container">
                <div class="welcome-section">
                    <h1 class="welcome-title">Welcome back, {full_name.split()[0]}!</h1>
                    <p class="welcome-subtitle">Here's your fitness journey overview</p>
                </div>
            </div>
            ''',
            unsafe_allow_html=True
        )

        # Enhanced metrics section with glassmorphism effect
        st.markdown('<div class="metrics-container">', unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)

        # Get recent data
        recent_attendance = db.get_attendance_data(30)
        recent_nutrition = db.get_nutrition_data(30)
        recent_workouts = db.get_recent_workouts(30)

        with col1:
            attended_days = sum(
                1 for x in recent_attendance if x.get('attended', False))
            attendance_rate = attended_days/30*100 if recent_attendance else 0
            st.markdown(f"""
            <div class="metric-card gym-card">
                <div class="metric-header">
                    <div class="metric-icon-container">
                        <div class="metric-icon">🏋️</div>
                    </div>
                    <div class="metric-trend positive">↗</div>
                </div>
                <div class="metric-content">
                    <div class="metric-value">{attended_days}</div>
                    <div class="metric-label">Gym Days</div>
                    <div class="metric-period">Last 30 days</div>
                    <div class="metric-progress">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {attendance_rate}%"></div>
                        </div>
                        <div class="metric-delta">{attendance_rate:.1f}% attendance</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            protein_days = sum(
                1 for x in recent_nutrition if x.get('protein_intake', 0) > 0)
            protein_rate = protein_days/30*100 if recent_nutrition else 0
            st.markdown(f"""
            <div class="metric-card protein-card">
                <div class="metric-header">
                    <div class="metric-icon-container">
                        <div class="metric-icon">🥩</div>
                    </div>
                    <div class="metric-trend positive">↗</div>
                </div>
                <div class="metric-content">
                    <div class="metric-value">{protein_days}</div>
                    <div class="metric-label">Protein Days</div>
                    <div class="metric-period">Last 30 days</div>
                    <div class="metric-progress">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {protein_rate}%"></div>
                        </div>
                        <div class="metric-delta">{protein_rate:.1f}% consistency</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            workout_count = len(recent_workouts)
            st.markdown(f"""
            <div class="metric-card workout-card">
                <div class="metric-header">
                    <div class="metric-icon-container">
                        <div class="metric-icon">💪</div>
                    </div>
                    <div class="metric-trend positive">↗</div>
                </div>
                <div class="metric-content">
                    <div class="metric-value">{workout_count}</div>
                    <div class="metric-label">Total Workouts</div>
                    <div class="metric-period">Last 30 days</div>
                    <div class="metric-progress">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {min(workout_count*3.33, 100)}%"></div>
                        </div>
                        <div class="metric-delta">Keep it up! 🔥</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            current_streak = 0
            for record in sorted(recent_attendance, key=lambda x: x['date'], reverse=True):
                if record.get('attended', False):
                    current_streak += 1
                else:
                    break

            streak_level = "🔥" if current_streak > 7 else "⚡" if current_streak > 3 else "💫"
            st.markdown(f"""
            <div class="metric-card streak-card">
                <div class="metric-header">
                    <div class="metric-icon-container">
                        <div class="metric-icon">{streak_level}</div>
                    </div>
                    <div class="metric-trend {"positive" if current_streak > 0 else "neutral"}">{"↗" if current_streak > 0 else "→"}</div>
                </div>
                <div class="metric-content">
                    <div class="metric-value">{current_streak}</div>
                    <div class="metric-label">Current Streak</div>
                    <div class="metric-period">Days strong</div>
                    <div class="metric-progress">
                        <div class="streak-indicator">{"🔥" * min(current_streak, 10)}</div>
                        <div class="metric-delta">{"Amazing!" if current_streak > 7 else "Good job!" if current_streak > 3 else "Keep going!"}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # Enhanced quick log section
        st.markdown('''
        <div class="section-divider"></div>
        <div class="section-header">
            <h2 class="section-title">⚡ Quick Log</h2>
        </div>
        ''', unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown('''
            <div class="quick-log-card attendance-log">
                <div class="log-header">
                    <div class="log-icon">🏃</div>
                    <div class="log-title">Today's Attendance</div>
                </div>
                <div class="log-content">
            ''', unsafe_allow_html=True)

            today = date.today().strftime("%Y-%m-%d")
            attended_today = st.radio(
                "Did you go to the gym today?",
                ["Not logged", "✅ Yes", "❌ No"],
                key="quick_attendance",
                label_visibility="collapsed"
            )

            if attended_today != "Not logged":
                if st.button("📝 Log Attendance", use_container_width=True, key="log_att_btn"):
                    db.log_attendance(today, attended_today == "✅ Yes")
                    st.success("✅ Attendance logged successfully!")
                    st.rerun()

            st.markdown('</div></div>', unsafe_allow_html=True)

        with col2:
            st.markdown('''
            <div class="quick-log-card protein-log">
                <div class="log-header">
                    <div class="log-icon">🥩</div>
                    <div class="log-title">Today's Protein</div>
                </div>
                <div class="log-content">
            ''', unsafe_allow_html=True)

            protein_amount = st.number_input(
                "Protein intake (grams)",
                min_value=0,
                max_value=300,
                step=10,
                key="quick_protein",
                label_visibility="collapsed",
                placeholder="Enter protein amount..."
            )

            if st.button("📝 Log Protein", use_container_width=True, key="log_protein_btn"):
                db.log_nutrition(today, protein_amount)
                st.success("✅ Protein intake logged successfully!")
                st.rerun()

            st.markdown('</div></div>', unsafe_allow_html=True)

        # Enhanced recent activity section
        st.markdown('''
        <div class="section-divider"></div>
        <div class="section-header">
            <h2 class="section-title">📊 Recent Activity</h2>
        </div>
        ''', unsafe_allow_html=True)

        if recent_workouts:
            latest_workout = recent_workouts[0]
            exercise_count = len(latest_workout.get('exercises', []))
            st.markdown(f"""
            <div class="activity-showcase">
                <div class="activity-card latest-workout">
                    <div class="activity-header">
                        <div class="activity-icon-large">💪</div>
                        <div class="activity-badge">Latest</div>
                    </div>
                    <div class="activity-body">
                        <div class="activity-title">Last Workout Session</div>
                        <div class="activity-meta">
                            <span class="activity-date">📅 {latest_workout['date']}</span>
                            <span class="activity-exercises">🎯 {exercise_count} exercises</span>
                        </div>
                        <div class="activity-progress">
                            <div class="activity-stats">
                                <div class="stat-item">
                                    <span class="stat-label">Exercises</span>
                                    <span class="stat-value">{exercise_count}</span>
                                </div>
                                <div class="stat-item">
                                    <span class="stat-label">Status</span>
                                    <span class="stat-value completed">✅ Completed</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown('''
            <div class="activity-showcase">
                <div class="empty-state">
                    <div class="empty-icon">💪</div>
                    <div class="empty-title">No recent workouts</div>
                    <div class="empty-subtitle">Start logging your workouts to see activity here!</div>
                </div>
            </div>
            ''', unsafe_allow_html=True)

        # Enhanced attendance chart
        st.markdown('''
        <div class="section-divider"></div>
        <div class="section-header">
            <h2 class="section-title">📈 Attendance Trends</h2>
            <p class="section-subtitle">Your gym attendance over the last 30 days</p>
        </div>
        ''', unsafe_allow_html=True)

        if recent_attendance:
            df_attendance = pd.DataFrame(recent_attendance)
            df_attendance['date'] = pd.to_datetime(
                df_attendance['date'], errors='coerce')
            df_attendance = df_attendance.dropna(subset=['date'])
            df_attendance['attended'] = df_attendance['attended'].astype(int)
            df_attendance = df_attendance.sort_values('date')

            # Create enhanced chart
            fig = px.line(
                df_attendance,
                x='date',
                y='attended',
                title='',
                markers=True,
                line_shape='spline'
            )

            # Enhanced styling for the chart
            fig.update_traces(
                line=dict(color='#6366f1', width=3),
                marker=dict(
                    size=8,
                    color='#6366f1',
                    line=dict(width=2, color='white')
                ),
                fill='tonexty',
                fillcolor='rgba(99, 102, 241, 0.1)'
            )

            fig.update_layout(
                xaxis_title="",
                yaxis_title="",
                font=dict(size=12, family="Inter, sans-serif"),
                height=350,
                margin=dict(t=20, b=40, l=20, r=20),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(
                    showgrid=True,
                    gridwidth=1,
                    gridcolor='rgba(0,0,0,0.1)',
                    showline=False,
                    zeroline=False
                ),
                yaxis=dict(
                    showgrid=True,
                    gridwidth=1,
                    gridcolor='rgba(0,0,0,0.1)',
                    showline=False,
                    zeroline=False,
                    tickmode='array',
                    tickvals=[0, 1],
                    ticktext=['Missed', 'Attended']
                )
            )

            st.markdown('<div class="chart-container">',
                        unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('''
            <div class="chart-container">
                <div class="empty-chart">
                    <div class="empty-icon">📊</div>
                    <div class="empty-title">No attendance data yet</div>
                    <div class="empty-subtitle">Start logging your gym visits to see trends!</div>
                </div>
            </div>
            ''', unsafe_allow_html=True)

    elif page == "👁️ View Workouts":
        st.markdown('<h1 class="page-title">Past Workouts</h1>',
                    unsafe_allow_html=True)

        # Date range selector
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            days_back = st.selectbox("Show workouts from",
                                     ["Last 7 days", "Last 30 days", "Last 90 days", "All time"])
        with col2:
            sort_order = st.selectbox(
                "Sort by", ["Newest first", "Oldest first"])

        days_map = {"Last 7 days": 7, "Last 30 days": 30,
                    "Last 90 days": 90, "All time": 365*2}
        days = days_map[days_back]

        # Get workouts
        workouts = db.get_recent_workouts(days)

        if sort_order == "Oldest first":
            workouts = sorted(workouts, key=lambda x: x['date'])

        if workouts:
            st.markdown(f"### Found {len(workouts)} workout(s)")

            # Search/filter
            search_term = st.text_input(
                "🔍 Search workouts", placeholder="Search by exercise name, workout type, or notes...")

            # Filter workouts based on search
            if search_term:
                filtered_workouts = []
                for workout in workouts:
                    search_lower = search_term.lower()
                    # Search in workout type
                    if search_lower in workout.get('type', '').lower():
                        filtered_workouts.append(workout)
                        continue
                    # Search in notes
                    if search_lower in workout.get('notes', '').lower():
                        filtered_workouts.append(workout)
                        continue
                    # Search in exercise names
                    for exercise in workout.get('exercises', []):
                        if search_lower in exercise.get('name', '').lower():
                            filtered_workouts.append(workout)
                            break
                workouts = filtered_workouts

            # Display workouts
            for i, workout in enumerate(workouts):
                with st.expander(f"📅 {workout['date']} - {workout.get('type', 'Unknown Type')} ({len(workout.get('exercises', []))} exercises)", expanded=(i == 0)):

                    # Workout header info
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"**📅 Date:** {workout['date']}")
                        st.markdown(
                            f"**🏋️ Type:** {workout.get('type', 'N/A')}")
                    with col2:
                        duration = workout.get('duration', 'N/A')
                        intensity = workout.get('intensity', 'N/A')
                        st.markdown(
                            f"**⏱️ Duration:** {duration} min" if duration != 'N/A' else "**⏱️ Duration:** N/A")
                        st.markdown(f"**🔥 Intensity:** {intensity}")
                    with col3:
                        start_time = workout.get('start_time', '')
                        end_time = workout.get('end_time', '')
                        if start_time:
                            start_dt = datetime.fromisoformat(start_time)
                            st.markdown(
                                f"**🕐 Started:** {start_dt.strftime('%H:%M')}")
                        if end_time:
                            end_dt = datetime.fromisoformat(end_time)
                            st.markdown(
                                f"**🕑 Ended:** {end_dt.strftime('%H:%M')}")

                    # Workout notes
                    if workout.get('notes'):
                        st.markdown("**📝 Workout Notes:**")
                        st.markdown(
                            f'<div class="workout-notes">{workout["notes"]}</div>', unsafe_allow_html=True)

                    st.markdown("---")

                    # Exercises details
                    exercises = workout.get('exercises', [])
                    if exercises:
                        st.markdown("**💪 Exercises:**")

                        for j, exercise in enumerate(exercises):
                            st.markdown(
                                f"**{j+1}. {exercise.get('name', 'Unknown Exercise')}**")

                            sets = exercise.get('sets', [])
                            if sets:
                                # Create a table for sets
                                sets_data = []
                                total_volume = 0
                                max_weight = 0
                                total_reps = 0

                                for k, set_info in enumerate(sets):
                                    reps = set_info.get('reps', 0)
                                    weight = set_info.get('weight', 0)
                                    timestamp = set_info.get('timestamp', '')

                                    # Convert timestamp if available
                                    time_str = ""
                                    if timestamp:
                                        try:
                                            time_dt = datetime.fromisoformat(
                                                timestamp)
                                            time_str = time_dt.strftime(
                                                '%H:%M:%S')
                                        except:
                                            time_str = ""

                                    # Calculate stats
                                    if isinstance(reps, (int, float)) and isinstance(weight, (int, float)):
                                        volume = reps * weight
                                        total_volume += volume
                                        total_reps += reps
                                        max_weight = max(max_weight, weight)
                                    else:
                                        volume = 0

                                    sets_data.append({
                                        'Set': k + 1,
                                        'Reps': reps,
                                        'Weight (kg)': weight,
                                        'Volume (kg)': volume,
                                        'Time': time_str
                                    })

                                # Display sets table
                                df_sets = pd.DataFrame(sets_data)
                                st.dataframe(df_sets, hide_index=True,
                                             use_container_width=True)

                                # Exercise summary stats
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.metric("Total Sets", len(sets))
                                with col2:
                                    st.metric("Total Reps", total_reps)
                                with col3:
                                    st.metric("Max Weight", f"{max_weight} kg")
                                with col4:
                                    st.metric("Total Volume",
                                              f"{total_volume} kg")
                            else:
                                st.info("No sets recorded for this exercise")

                            if j < len(exercises) - 1:  # Add separator except for last exercise
                                st.markdown("---")
                    else:
                        st.info("No exercises recorded for this workout")
        else:
            st.info(f"No workouts found for the selected period ({days_back})")
            st.markdown("""
            <div class="info-banner">
                <p>💡 <strong>Tip:</strong> Start logging your workouts to see them here!</p>
                <p>Use the "💪 Today's Workout" or "📊 Log Workout" pages to add workouts.</p>
            </div>
            """, unsafe_allow_html=True)

    elif page == "📊 Log Workout":
        st.markdown('<h1 class="page-title">📊 Log Workout</h1>',
                    unsafe_allow_html=True)

        # Initialize workout flow state
        if 'workout_flow_step' not in st.session_state:
            st.session_state.workout_flow_step = 'setup'

        # Check for active workout conflict
        if 'current_workout' in st.session_state and st.session_state.workout_flow_step == 'setup':
            st.markdown(f"""
            <div class="warning-banner">
                <h3>⚠️ Active Workout Session Detected</h3>
                <p>You have an ongoing workout. Complete or cancel it first.</p>
            </div>
            """, unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔙 Continue Active Workout", use_container_width=True):
                    st.session_state.workout_flow_step = 'active'
                    st.rerun()
            with col2:
                if st.button("❌ Cancel Active Session", use_container_width=True):
                    del st.session_state.current_workout
                    st.success("Active session cancelled")
                    st.rerun()
            return

        # ============================================================================
        # STEP 1: WORKOUT SETUP
        # ============================================================================
        if st.session_state.workout_flow_step == 'setup':
            st.markdown(
                '<h2 class="section-title">📋 Workout Setup</h2>', unsafe_allow_html=True)

            # Get workout recommendation
            today = date.today().strftime("%Y-%m-%d")
            last_workouts = db.get_recent_workouts(7)
            last_types = [w.get('type', 'Full Body Conditioning + Shoulders')
                          for w in last_workouts]

            if 'Chest + Triceps + Cardio' not in last_types[-3:]:
                recommended = 'Chest + Triceps + Cardio'
            elif 'Back + Biceps' not in last_types[-3:]:
                recommended = 'Back + Biceps'
            elif 'Legs + Core' not in last_types[-3:]:
                recommended = 'Legs + Core'
            else:
                recommended = 'Full Body Conditioning + Shoulders'

            # Show recommendation
            if last_workouts:
                st.markdown(
                    '<h3 class="subsection-title">📈 Recent Activity</h3>', unsafe_allow_html=True)
                cols = st.columns(min(3, len(last_workouts)))
                for i, workout in enumerate(last_workouts[:3]):
                    with cols[i]:
                        days_ago = (
                            date.today() - datetime.strptime(workout['date'], "%Y-%m-%d").date()).days
                        st.markdown(f"""
                        <div class="recent-workout-card">
                            <div class="workout-type">{workout['type']}</div>
                            <div class="workout-date">{days_ago} day{'s' if days_ago != 1 else ''} ago</div>
                        </div>
                        """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class="recommendation-card">
                <div class="rec-icon">🎯</div>
                <div class="rec-content">
                    <div class="rec-title">Recommended: {recommended}</div>
                    <div class="rec-subtitle">Based on your workout rotation</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Workout details form
            with st.form("workout_setup_form"):
                col1, col2 = st.columns(2)

                with col1:
                    workout_date = st.date_input(
                        "📅 Workout Date", value=date.today())
                    default_type_index = list(
                        DEFAULT_EXERCISES.keys()).index(recommended)
                    workout_type = st.selectbox("🏋️ Workout Type", list(DEFAULT_EXERCISES.keys()),
                                                index=default_type_index)

                with col2:
                    estimated_duration = st.number_input("⏱️ Estimated Duration (minutes)",
                                                         min_value=15, max_value=180, value=60, step=15)
                    target_intensity = st.selectbox("🔥 Target Intensity",
                                                    ["Light", "Moderate", "High", "Very High"], index=1)

                workout_goals = st.text_input("🎯 Today's Goals",
                                              placeholder="e.g., Focus on form, increase weight, endurance...")

                if st.form_submit_button("➡️ Select Exercises", use_container_width=True):
                    st.session_state.workout_setup = {
                        'date': workout_date.strftime("%Y-%m-%d"),
                        'type': workout_type,
                        'estimated_duration': estimated_duration,
                        'target_intensity': target_intensity,
                        'goals': workout_goals
                    }
                    st.session_state.workout_flow_step = 'exercises'
                    st.rerun()

        # ============================================================================
        # STEP 2: EXERCISE SELECTION
        # ============================================================================
        elif st.session_state.workout_flow_step == 'exercises':
            setup = st.session_state.workout_setup

            st.markdown(
                '<h2 class="section-title">💪 Select Exercises</h2>', unsafe_allow_html=True)

            # Show workout info
            st.markdown(f"""
            <div class="workout-info-bar">
                <span><strong>📋 {setup['type']}</strong></span>
                <span>📅 {setup['date']}</span>
                <span>⏱️ {setup['estimated_duration']} min</span>
                <span>🔥 {setup['target_intensity']}</span>
            </div>
            """, unsafe_allow_html=True)

            if setup['goals']:
                st.markdown(f"🎯 **Goals:** {setup['goals']}")

            st.markdown(
                '<h3 class="subsection-title">Available Exercises</h3>', unsafe_allow_html=True)

            # Exercise selection
            available_exercises = DEFAULT_EXERCISES[setup['type']]
            selected_exercises = []

            # Create exercise grid with more details
            cols = st.columns(2)
            for i, exercise in enumerate(available_exercises):
                with cols[i % 2]:
                    if st.checkbox(f"💪 {exercise}", key=f"exercise_{exercise}", value=True):
                        selected_exercises.append(exercise)

            # Custom exercises section
            st.markdown(
                '<h3 class="subsection-title">➕ Custom Exercises</h3>', unsafe_allow_html=True)

            if 'custom_exercises' not in st.session_state:
                st.session_state.custom_exercises = []

            col1, col2 = st.columns([3, 1])
            with col1:
                custom_exercise = st.text_input("Add custom exercise",
                                                placeholder="Enter exercise name...", key="custom_input")
            with col2:
                if st.button("Add", key="add_custom") and custom_exercise:
                    if custom_exercise not in st.session_state.custom_exercises:
                        st.session_state.custom_exercises.append(
                            custom_exercise)
                        st.success(f"Added: {custom_exercise}")
                        st.rerun()

            # Show custom exercises
            if st.session_state.custom_exercises:
                for custom_ex in st.session_state.custom_exercises:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        if st.checkbox(f"✨ {custom_ex}", key=f"custom_{custom_ex}"):
                            selected_exercises.append(custom_ex)
                    with col2:
                        if st.button("🗑️", key=f"remove_{custom_ex}"):
                            st.session_state.custom_exercises.remove(custom_ex)
                            st.rerun()

            # Exercise summary
            if selected_exercises:
                st.markdown(f"""
                <div class="selected-exercises">
                    <h4>Selected Exercises ({len(selected_exercises)})</h4>
                    <div class="exercise-tags">
                        {"".join([f'<span class="exercise-tag">{ex}</span>' for ex in selected_exercises])}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Navigation buttons
                col1, col2, col3 = st.columns([1, 1, 2])

                with col1:
                    if st.button("🔙 Back to Setup", use_container_width=True):
                        st.session_state.workout_flow_step = 'setup'
                        st.rerun()

                with col2:
                    if st.button("🔄 Clear All", use_container_width=True):
                        st.session_state.custom_exercises = []
                        st.rerun()

                with col3:
                    if st.button("🚀 Start Workout", use_container_width=True):
                        # Create workout session
                        st.session_state.current_workout = {
                            'date': setup['date'],
                            'type': setup['type'],
                            'estimated_duration': setup['estimated_duration'],
                            'target_intensity': setup['target_intensity'],
                            'goals': setup['goals'],
                            'exercises': [{'name': ex, 'sets': []} for ex in selected_exercises],
                            'start_time': datetime.now().isoformat(),
                            'notes': ''
                        }
                        st.session_state.workout_flow_step = 'active'
                        st.session_state.current_exercise_index = 0
                        st.success("🔥 Workout started!")
                        st.rerun()
            else:
                st.warning("Please select at least one exercise to continue.")

        # ============================================================================
        # STEP 3: ACTIVE WORKOUT
        # ============================================================================
        elif st.session_state.workout_flow_step == 'active':
            workout = st.session_state.current_workout

            st.markdown(
                '<h2 class="section-title">🔥 Active Workout Session</h2>', unsafe_allow_html=True)

            # Workout progress bar
            total_exercises = len(workout['exercises'])
            completed_exercises = sum(
                1 for ex in workout['exercises'] if ex['sets'])
            progress = completed_exercises / total_exercises if total_exercises > 0 else 0

            st.markdown(f"""
            <div class="progress-container">
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {progress*100}%"></div>
                </div>
                <div class="progress-text">{completed_exercises}/{total_exercises} exercises completed</div>
            </div>
            """, unsafe_allow_html=True)

            # Exercise navigation
            exercise_names = [ex['name'] for ex in workout['exercises']]
            current_exercise_name = st.selectbox("Current Exercise", exercise_names,
                                                 index=st.session_state.get(
                                                     'current_exercise_index', 0),
                                                 key="current_exercise_selector")

            # Update current exercise index
            st.session_state.current_exercise_index = exercise_names.index(
                current_exercise_name)
            current_ex_idx = st.session_state.current_exercise_index
            current_exercise = workout['exercises'][current_ex_idx]

            # Exercise header
            st.markdown(
                f'<h3 class="current-exercise">💪 {current_exercise["name"]}</h3>', unsafe_allow_html=True)

            # Quick navigation
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                if st.button("⬅️ Previous") and current_ex_idx > 0:
                    st.session_state.current_exercise_index = current_ex_idx - 1
                    st.rerun()

            with col3:
                if st.button("Next ➡️") and current_ex_idx < len(workout['exercises']) - 1:
                    st.session_state.current_exercise_index = current_ex_idx + 1
                    st.rerun()

            # Set entry form
            st.markdown('<h4 class="subsection-title">📝 Add Set</h4>',
                        unsafe_allow_html=True)

            with st.form(f"add_set_form_{current_exercise_name}"):
                col1, col2, col3, col4 = st.columns([1.5, 1.5, 1, 1])

                with col1:
                    reps = st.number_input(
                        "Reps", min_value=1, max_value=100, value=10, key=f"reps_{current_ex_idx}")

                with col2:
                    weight = st.number_input("Weight (kg)", min_value=0.0, max_value=500.0,
                                             step=2.5, value=0.0, key=f"weight_{current_ex_idx}")

                with col3:
                    rpe = st.selectbox("RPE", list(
                        range(6, 11)), index=2, key=f"rpe_{current_ex_idx}")

                with col4:
                    add_set = st.form_submit_button(
                        "➕ Add Set", use_container_width=True)

                set_notes = st.text_input("Set Notes (optional)",
                                          placeholder="Form cues, how it felt...", key=f"set_notes_{current_ex_idx}")

                if add_set:
                    new_set = {
                        'reps': reps,
                        'weight': weight,
                        'rpe': rpe,
                        'notes': set_notes,
                        'timestamp': datetime.now().isoformat()
                    }
                    st.session_state.current_workout['exercises'][current_ex_idx]['sets'].append(
                        new_set)
                    st.success(
                        f"✅ Added: {reps} reps @ {weight}kg (RPE {rpe})")
                    st.rerun()

            # Display completed sets
            if current_exercise['sets']:
                st.markdown(
                    '<h4 class="subsection-title">📊 Completed Sets</h4>', unsafe_allow_html=True)

                for i, set_data in enumerate(current_exercise['sets']):
                    col1, col2 = st.columns([5, 1])

                    with col1:
                        weight_display = f"{set_data['weight']}kg" if set_data['weight'] > 0 else "Bodyweight"
                        notes_display = f" • {set_data['notes']}" if set_data.get(
                            'notes') else ""

                        st.markdown(f"""
                        <div class="set-card">
                            <span class="set-number">Set {i+1}</span>
                            <span class="set-details">{set_data['reps']} reps @ {weight_display} (RPE {set_data['rpe']}){notes_display}</span>
                        </div>
                        """, unsafe_allow_html=True)

                    with col2:
                        if st.button("🗑️", key=f"remove_set_{current_ex_idx}_{i}"):
                            st.session_state.current_workout['exercises'][current_ex_idx]['sets'].pop(
                                i)
                            st.rerun()

            # Rest timer
            st.markdown(
                '<h4 class="subsection-title">⏱️ Rest Timer</h4>', unsafe_allow_html=True)
            rest_duration = st.slider(
                "Rest time (minutes)", 0.5, 5.0, 2.0, 0.5, key=f"rest_{current_ex_idx}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("▶️ Start Rest Timer", use_container_width=True):
                    st.session_state.rest_start = datetime.now()
                    st.session_state.rest_duration = rest_duration

            with col2:
                if st.button("⏹️ Stop Timer", use_container_width=True):
                    if 'rest_start' in st.session_state:
                        del st.session_state.rest_start

            # Show active timer
            if 'rest_start' in st.session_state:
                elapsed = (datetime.now() -
                           st.session_state.rest_start).total_seconds() / 60
                remaining = max(0, st.session_state.rest_duration - elapsed)

                if remaining > 0:
                    st.markdown(f"""
                    <div class="timer-display">
                        ⏱️ Rest: {remaining:.1f} minutes remaining
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="timer-complete">
                        🔔 Rest complete! Ready for next set.
                    </div>
                    """, unsafe_allow_html=True)

            # Workout control buttons
            st.markdown(
                '<h3 class="section-title">🏁 Workout Controls</h3>', unsafe_allow_html=True)

            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("💾 Finish Workout", use_container_width=True):
                    st.session_state.workout_flow_step = 'finish'
                    st.rerun()

            with col2:
                if st.button("⏸️ Pause & Save", use_container_width=True):
                    # Save current progress
                    workout['end_time'] = datetime.now().isoformat()
                    workout['status'] = 'paused'
                    workout['actual_duration'] = (datetime.now(
                    ) - datetime.fromisoformat(workout['start_time'])).total_seconds() / 60
                    db.log_workout(workout)
                    del st.session_state.current_workout
                    st.session_state.workout_flow_step = 'setup'
                    st.success("Workout paused and saved!")
                    st.rerun()

            with col3:
                if st.button("❌ Cancel Workout", use_container_width=True):
                    del st.session_state.current_workout
                    st.session_state.workout_flow_step = 'setup'
                    st.warning("Workout cancelled")
                    st.rerun()

        # ============================================================================
        # STEP 4: FINISH WORKOUT
        # ============================================================================
        elif st.session_state.workout_flow_step == 'finish':
            workout = st.session_state.current_workout

            st.markdown(
                '<h2 class="section-title">🏁 Finish Workout</h2>', unsafe_allow_html=True)

            # Calculate workout stats
            start_time = datetime.fromisoformat(workout['start_time'])
            actual_duration = (
                datetime.now() - start_time).total_seconds() / 60
            total_sets = sum(len(ex['sets']) for ex in workout['exercises'])
            total_reps = sum(sum(s['reps'] for s in ex['sets'])
                             for ex in workout['exercises'])
            total_weight = sum(sum(s['weight'] * s['reps']
                               for s in ex['sets']) for ex in workout['exercises'])

            # Workout summary
            st.markdown(f"""
            <div class="workout-summary-card">
                <h3>🎉 Workout Complete!</h3>
                <div class="summary-stats">
                    <div class="stat">
                        <div class="stat-value">{len(workout['exercises'])}</div>
                        <div class="stat-label">Exercises</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{total_sets}</div>
                        <div class="stat-label">Sets</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{total_reps}</div>
                        <div class="stat-label">Reps</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{actual_duration:.0f}</div>
                        <div class="stat-label">Minutes</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if total_weight > 0:
                st.markdown(
                    f"**💪 Total Volume:** {total_weight:.1f} kg lifted")

            # Exercise breakdown
            st.markdown(
                '<h3 class="subsection-title">📋 Exercise Summary</h3>', unsafe_allow_html=True)

            for exercise in workout['exercises']:
                if exercise['sets']:
                    sets_summary = []
                    for s in exercise['sets']:
                        weight_str = f"{s['weight']}kg" if s['weight'] > 0 else "BW"
                        sets_summary.append(f"{s['reps']}@{weight_str}")

                    st.markdown(
                        f"**{exercise['name']}:** {' • '.join(sets_summary)}")

            # Workout feedback form
            with st.form("finish_workout_form"):
                st.markdown(
                    '<h3 class="subsection-title">📝 Workout Feedback</h3>', unsafe_allow_html=True)

                col1, col2 = st.columns(2)

                with col1:
                    actual_intensity = st.selectbox("How intense was it?",
                                                    ["Light", "Moderate",
                                                        "High", "Very High"],
                                                    index=["Light", "Moderate", "High", "Very High"].index(workout.get('target_intensity', 'Moderate')))

                    energy_level = st.selectbox("Energy Level",
                                                ["Very Low", "Low", "Good", "High", "Very High"], index=2)

                with col2:
                    satisfaction = st.selectbox("Satisfaction",
                                                ["Poor", "Fair", "Good", "Great", "Excellent"], index=2)

                    recovery_feeling = st.selectbox("How do you feel?",
                                                    ["Exhausted", "Tired", "Good", "Energized", "Amazing"], index=2)

                workout_notes = st.text_area("Workout Notes",
                                             placeholder="How did it go? Achievements, observations, areas for improvement...")

                goals_achieved = st.text_area("Goals Achievement",
                                              placeholder=f"Did you achieve your goals: {workout.get('goals', 'N/A')}?")

                next_focus = st.text_input("Next Workout Focus",
                                           placeholder="What to focus on next time...")

                if st.form_submit_button("💾 Save Workout", use_container_width=True):
                    # Compile final workout data
                    workout.update({
                        'end_time': datetime.now().isoformat(),
                        'actual_duration': actual_duration,
                        'actual_intensity': actual_intensity,
                        'energy_level': energy_level,
                        'satisfaction': satisfaction,
                        'recovery_feeling': recovery_feeling,
                        'notes': workout_notes,
                        'goals_achieved': goals_achieved,
                        'next_focus': next_focus,
                        'total_sets': total_sets,
                        'total_reps': total_reps,
                        'total_weight': total_weight,
                        'status': 'completed'
                    })

                    db.log_workout(workout)

                    # Cleanup session state
                    keys_to_remove = ['current_workout', 'workout_flow_step', 'workout_setup',
                                      'current_exercise_index', 'custom_exercises']
                    for key in keys_to_remove:
                        if key in st.session_state:
                            del st.session_state[key]

                    st.success("🎉 Workout saved successfully!")
                    st.balloons()
                    st.rerun()

            # Option to continue without saving notes
            if st.button("⚡ Quick Save (Skip Notes)", use_container_width=True):
                workout.update({
                    'end_time': datetime.now().isoformat(),
                    'actual_duration': actual_duration,
                    'total_sets': total_sets,
                    'total_reps': total_reps,
                    'total_weight': total_weight,
                    'status': 'completed'
                })

                db.log_workout(workout)

                # Cleanup session state
                keys_to_remove = ['current_workout', 'workout_flow_step', 'workout_setup',
                                  'current_exercise_index', 'custom_exercises']
                for key in keys_to_remove:
                    if key in st.session_state:
                        del st.session_state[key]

                st.success("✅ Workout saved!")
                st.rerun()

    # Data Management Page
    elif page == "🗑️ Manage Data":
        st.markdown('<h1 class="page-title">Manage Your Data</h1>',
                    unsafe_allow_html=True)

        tab1, tab2, tab3, tab4 = st.tabs(
            ["🏋️ Workouts", "📅 Attendance", "🥗 Nutrition", "📏 Body Metrics"])

        with tab1:
            st.markdown("### Delete Workout Records")
            workouts = db.get_recent_workouts(90)
            if workouts:
                for workout in workouts:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.write(
                            f"**{workout['date']}** - {workout.get('type', 'N/A')} ({len(workout.get('exercises', []))} exercises)")
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
                        status = "✅ Attended" if record.get(
                            'attended') else "❌ Missed"
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
                        st.write(
                            f"**{record['date']}** - {record.get('protein_intake', 0)}g protein")
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
                        weight_text = f"{record.get('weight', 'N/A')}kg" if record.get(
                            'weight') else "No weight"
                        st.write(f"**{record['date']}** - {weight_text}")
                    with col2:
                        if st.button("🗑️", key=f"del_metrics_{record['date']}"):
                            db.delete_body_metrics(record['date'])
                            st.success("Body metrics deleted!")
                            st.rerun()
            else:
                st.info("No body metrics records found")

    # Attendance Page
    elif page == "📅 Attendance":
        # Load custom CSS
        try:
            with open('attendance.css') as f:
                st.markdown(f'<style>{f.read()}</style>',
                            unsafe_allow_html=True)
        except:
            pass

        # Page Header
        st.markdown("""
        <div class="main-header">
            <h1 style="margin:0; font-size: 2.5rem;">📅 Gym Attendance</h1>
            <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">Track your fitness journey and maintain consistency</p>
        </div>
        """, unsafe_allow_html=True)

        # Create columns with proper spacing
        # col1, col2 = st.columns([1, 2], gap="large")

        # with col1:
        # Form section with container
        with st.container():
            st.markdown("### 🏋️ Log Today's Attendance")

            # Date input
            attendance_date = st.date_input(
                "📅 Date",
                value=date.today(),
                help="Select the date for attendance logging"
            )

            # Attendance selector
            attended = st.selectbox(
                "💪 Did you attend the gym?",
                ["Yes", "No"],
                help="Select whether you attended the gym on this date"
            )

            # Notes input
            notes = st.text_area(
                "📝 Notes (Optional)",
                placeholder="Any specific reason for missing? What did you accomplish?",
                height=100,
                help="Add any additional notes about your gym session"
            )

            # Submit button with styling
            st.markdown("<br>", unsafe_allow_html=True)

            # Center the button
            col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
            with col_btn2:
                if st.button("✨ Log Attendance", type="primary", use_container_width=True):
                    try:
                        db.log_attendance(
                            attendance_date.strftime("%Y-%m-%d"),
                            attended == "Yes",
                            notes
                        )
                        st.success("🎉 Attendance logged successfully!")
                        st.balloons()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error logging attendance: {str(e)}")

        # with col2:
            # History section
        st.markdown("### 📊 Your Fitness Journey")

        try:
            attendance_data = db.get_attendance_data(30)
        except Exception as e:
            st.error(f"Error fetching attendance data: {str(e)}")
            attendance_data = None

        if attendance_data:
            df = pd.DataFrame(attendance_data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date', ascending=False)

            # Create the attendance chart
            fig = px.scatter(
                df,
                x='date',
                y='attended',
                title='Your Attendance Pattern (Last 30 Days)',
                color='attended',
                color_discrete_map={True: '#22c55e', False: '#ef4444'},
                height=400
            )

            # Enhance chart styling
            fig.update_traces(
                marker=dict(size=12, line=dict(width=2, color='white')),
                hovertemplate="<b>%{x|%B %d, %Y}</b><br>" +
                "Status: %{customdata}<br>" +
                "<extra></extra>",
                customdata=[
                    'Attended' if x else 'Missed' for x in df['attended']]
            )

            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#374151'),
                title=dict(
                    font=dict(size=18, color='#1f2937'),
                    x=0.5
                ),
                yaxis=dict(
                    tickvals=[0, 1],
                    ticktext=['Missed', 'Attended'],
                    gridcolor='#e5e7eb',
                    title=''
                ),
                xaxis=dict(
                    gridcolor='#e5e7eb',
                    title='Date'
                ),
                showlegend=False,
                margin=dict(l=20, r=20, t=50, b=40)
            )

            st.plotly_chart(fig, use_container_width=True)

            # Calculate statistics
            total_days = len(df)
            attended_days = df['attended'].sum()
            missed_days = total_days - attended_days
            attendance_rate = (attended_days / total_days) * \
                100 if total_days > 0 else 0

            # Calculate current streak
            current_streak = 0
            for _, row in df.iterrows():
                if row['attended']:
                    current_streak += 1
                else:
                    break

            # Display stats using Streamlit metrics
            st.markdown("#### 📈 Your Statistics")

            metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

            with metric_col1:
                st.metric(
                    label="🎯 Days Attended",
                    value=attended_days,
                    delta=f"{attendance_rate:.1f}% success rate"
                )

            with metric_col2:
                st.metric(
                    label="😴 Days Missed",
                    value=missed_days,
                    delta=f"{100-attendance_rate:.1f}% missed"
                )

            with metric_col3:
                st.metric(
                    label="📊 Success Rate",
                    value=f"{attendance_rate:.1f}%",
                    delta="Last 30 days"
                )

            with metric_col4:
                st.metric(
                    label="🔥 Current Streak",
                    value=current_streak,
                    delta="Consecutive days"
                )

            # Recent activity section
            st.markdown("#### 🕒 Recent Activity")

            recent_entries = df.head(10)

            # Create tabs for better organization
            tab1, tab2 = st.tabs(["📋 Activity List", "📅 Calendar View"])

            with tab1:
                for i, (_, row) in enumerate(recent_entries.iterrows()):
                    date_str = row['date'].strftime("%B %d, %Y")
                    status = "Attended" if row['attended'] else "Missed"
                    status_emoji = "✅" if row['attended'] else "❌"

                    # Create expandable row for each entry
                    with st.expander(f"{status_emoji} {date_str} - {status}", expanded=False):
                        col_status, col_notes = st.columns([1, 2])

                        with col_status:
                            if row['attended']:
                                st.success("Attended Gym")
                            else:
                                st.error("Missed Gym")

                        with col_notes:
                            # Show notes if available (you may need to add this to your data)
                            if hasattr(row, 'notes') and row.get('notes'):
                                st.write(f"**Notes:** {row['notes']}")
                            else:
                                st.write("*No notes recorded*")

            with tab2:
                # Create a simple calendar view using a dataframe
                calendar_df = df.copy()
                calendar_df['Status'] = calendar_df['attended'].map(
                    {True: '✅ Attended', False: '❌ Missed'})
                calendar_df['Date'] = calendar_df['date'].dt.strftime(
                    '%Y-%m-%d')

                st.dataframe(
                    calendar_df[['Date', 'Status']].set_index('Date'),
                    use_container_width=True,
                    height=300
                )

            # Progress visualization
            st.markdown("#### 🎯 Weekly Progress")

            # Group by week and show progress
            df['week'] = df['date'].dt.isocalendar().week
            df['year'] = df['date'].dt.year

            weekly_stats = df.groupby(['year', 'week']).agg({
                'attended': ['sum', 'count']
            }).reset_index()

            weekly_stats.columns = ['year', 'week',
                                    'attended_days', 'total_days']
            weekly_stats['attendance_rate'] = (
                weekly_stats['attended_days'] / weekly_stats['total_days'] * 100).round(1)

            if len(weekly_stats) > 0:
                fig_weekly = px.bar(
                    weekly_stats.tail(8),  # Last 8 weeks
                    x='week',
                    y='attendance_rate',
                    title='Weekly Attendance Rate (%)',
                    color='attendance_rate',
                    color_continuous_scale='RdYlGn',
                    height=300
                )

                fig_weekly.update_layout(
                    showlegend=False,
                    xaxis_title="Week Number",
                    yaxis_title="Attendance Rate (%)"
                )

                st.plotly_chart(fig_weekly, use_container_width=True)

        else:
            # Empty state
            st.info("📊 No attendance data available yet")

            # Motivational content for new users
            st.markdown("""
                ### 🚀 Start Your Fitness Journey!
                
                Welcome to your attendance tracker! Here's what you can expect:
                
                - 📈 **Track Progress**: Monitor your gym attendance over time
                - 🔥 **Build Streaks**: See your consecutive attendance days
                - 📊 **Analyze Patterns**: Understand your workout habits
                - 🎯 **Stay Motivated**: Visualize your fitness commitment
                
                **💪 Ready to begin?** Log your first gym session using the form on the left!
                """)

            # Add some motivational quotes
            motivational_quotes = [
                "The only bad workout is the one that didn't happen.",
                "Your body can do it. It's your mind you need to convince.",
                "Don't wish for it, work for it.",
                "Success is what comes after you stop making excuses.",
                "The groundwork for all happiness is good health."
            ]

            import random
            quote = random.choice(motivational_quotes)
            st.info(f"💭 **Daily Motivation:** {quote}")

        # Footer with additional tips
        st.markdown("---")

        with st.expander("💡 Tips for Consistent Gym Attendance"):
            tip_col1, tip_col2 = st.columns(2)

            with tip_col1:
                st.markdown("""
                **🎯 Setting Goals:**
                - Start with realistic targets
                - Aim for 3-4 days per week initially
                - Track your progress regularly
                - Celebrate small wins
                """)

            with tip_col2:
                st.markdown("""
                **🔥 Building Habits:**
                - Schedule gym time like appointments
                - Prepare gym clothes the night before
                - Find a workout buddy
                - Mix up your routine to stay engaged
                """)

    # Nutrition Page
    elif page == "🥗 Nutrition":

        try:
            # Load custom CSS
            with open("nutrition_styles.css", "r") as f:
                st.markdown(f"<style>{f.read()}</style>",
                            unsafe_allow_html=True)
        except FileNotFoundError:
            st.warning("CSS file not found. Using default styling.")

        # Page Header with gradient background
        st.markdown("""
        <div class="nutrition-header">
            <div class="header-content">
                <h1 class="page-title">
                    Nutrition Dashboard
                </h1>
                <p class="page-subtitle">Track your daily nutrition and build healthy habits</p>
            </div>
            <div class="header-pattern"></div>
        </div>
        """, unsafe_allow_html=True)

        # Create tabs instead of columns
        tab1, tab2 = st.tabs(["📝 Log Nutrition", "📊 Analytics & History"])

        with tab1:
            # Nutrition logging card
            st.markdown("""
            <div class="nutrition-card log-card">
                <div class="card-header">
                    <h2 class="card-title">
                        <span class="card-icon">📝</span>
                        Log Your Nutrition
                    </h2>
                </div>
                <div class="card-content">
            """, unsafe_allow_html=True)

            nutrition_date = st.date_input(
                "📅 Date",
                value=date.today(),
                help="Select the date for your nutrition log"
            )

            # Protein intake with visual feedback
            protein_intake = st.number_input(
                "🥩 Protein Intake (g)",
                min_value=0,
                max_value=500,
                step=5,
                help="Track your daily protein consumption"
            )

            # Progress bar for protein target
            protein_target = 150
            protein_progress = min(protein_intake / protein_target * 100, 100)
            st.markdown(f"""
            <div class="protein-progress">
                <div class="progress-label">
                    <span>Daily Target Progress</span>
                    <span class="progress-value">{protein_intake}g / {protein_target}g</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {protein_progress}%"></div>
                </div>
                <div class="progress-status {'on-track' if protein_progress >= 80 else 'needs-attention'}">
                    {'🎯 On Track!' if protein_progress >= 80 else '💪 Keep Going!'}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Meals section with enhanced UI
            st.markdown("""
            <div class="meals-section">
                <h3 class="section-title">🍽️ Today's Meals</h3>
            </div>
            """, unsafe_allow_html=True)

            meals = []
            meal_icons = ["🌅", "☀️", "🌙"]
            meal_names = ["Breakfast", "Lunch", "Dinner"]

            for i in range(3):
                meal_name = meal_names[i]
                meal_icon = meal_icons[i]

                st.markdown(f"""
                <div class="meal-input">
                    <label class="meal-label">
                        <span class="meal-icon">{meal_icon}</span>
                        {meal_name}
                    </label>
                </div>
                """, unsafe_allow_html=True)

                meal_desc = st.text_input(
                    f"{meal_name}",
                    placeholder=f"What did you have for {meal_name.lower()}?",
                    label_visibility="collapsed",
                    key=f"meal_{i}"
                )
                if meal_desc:
                    meals.append({"meal": meal_name, "description": meal_desc})

            # Notes section
            st.markdown("""
            <div class="notes-section">
                <label class="notes-label">
                    <span class="notes-icon">📋</span>
                    Additional Notes
                </label>
            </div>
            """, unsafe_allow_html=True)

            nutrition_notes = st.text_area(
                "Notes",
                placeholder="Any additional notes about your nutrition today...",
                label_visibility="collapsed",
                height=80
            )

            # Log button with enhanced styling
            st.markdown('<div class="button-container">',
                        unsafe_allow_html=True)
            if st.button("📝 Log Nutrition", use_container_width=True, type="primary"):
                try:
                    db.log_nutrition(
                        nutrition_date.strftime("%Y-%m-%d"),
                        protein_intake,
                        meals,
                        nutrition_notes
                    )
                    st.success("✅ Nutrition logged successfully!")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error logging nutrition: {str(e)}")
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown("""
                </div>
            </div>
            """, unsafe_allow_html=True)

        with tab2:
            # Analytics and history card
            st.markdown("""
            <div class="nutrition-card analytics-card">
                <div class="card-header">
                    <h2 class="card-title">
                        <span class="card-icon">📊</span>
                        Nutrition Analytics
                    </h2>
                </div>
                <div class="card-content">
            """, unsafe_allow_html=True)

            try:
                nutrition_data = db.get_nutrition_data(30)

                if nutrition_data:
                    df = pd.DataFrame(nutrition_data)
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.sort_values('date')

                    # Enhanced protein intake chart
                    fig = px.line(
                        df,
                        x='date',
                        y='protein_intake',
                        title='Daily Protein Intake - Last 30 Days',
                        color_discrete_sequence=['#6366f1']
                    )

                    # Styling the chart
                    fig.update_traces(
                        line=dict(width=3),
                        mode='lines+markers',
                        marker=dict(size=6, color='#6366f1',
                                    line=dict(width=2, color='white'))
                    )

                    fig.add_hline(
                        y=150,
                        line_dash="dash",
                        line_color="#ef4444",
                        annotation_text="Target: 150g",
                        annotation_position="top right"
                    )

                    fig.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(family="Inter, sans-serif"),
                        title=dict(font=dict(size=16, color='#1f2937')),
                        xaxis=dict(
                            gridcolor='rgba(156, 163, 175, 0.2)',
                            showgrid=True
                        ),
                        yaxis=dict(
                            gridcolor='rgba(156, 163, 175, 0.2)',
                            showgrid=True
                        )
                    )

                    st.plotly_chart(fig, use_container_width=True)

                    # Enhanced nutrition stats
                    avg_protein = df['protein_intake'].mean()
                    max_protein = df['protein_intake'].max()
                    days_above_target = (df['protein_intake'] >= 150).sum()
                    total_days = len(df)
                    success_rate = (days_above_target /
                                    total_days * 100) if total_days > 0 else 0

                    st.markdown(f"""
                    <div class="stats-container">
                        <div class="stat-card">
                            <div class="stat-icon">📈</div>
                            <div class="stat-content">
                                <div class="stat-value">{avg_protein:.1f}g</div>
                                <div class="stat-label">Average Daily</div>
                            </div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-icon">🏆</div>
                            <div class="stat-content">
                                <div class="stat-value">{max_protein:.1f}g</div>
                                <div class="stat-label">Personal Best</div>
                            </div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-icon">🎯</div>
                            <div class="stat-content">
                                <div class="stat-value">{days_above_target}/{total_days}</div>
                                <div class="stat-label">Target Days</div>
                            </div>
                        </div>
                        <div class="stat-card success-rate">
                            <div class="stat-icon">✨</div>
                            <div class="stat-content">
                                <div class="stat-value">{success_rate:.0f}%</div>
                                <div class="stat-label">Success Rate</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Recent meals section
                    if len(df) > 0:
                        st.markdown("""
                        <div class="recent-meals">
                            <h3 class="section-title">🍽️ Recent Meals</h3>
                        </div>
                        """, unsafe_allow_html=True)

                        # Show last 5 days of meals
                        recent_data = df.tail(5)
                        for _, row in recent_data.iterrows():
                            date_str = row['date'].strftime('%B %d, %Y')
                            st.markdown(f"""
                            <div class="meal-history-item">
                                <div class="meal-date">📅 {date_str}</div>
                                <div class="meal-protein">🥩 {row['protein_intake']}g protein</div>
                            </div>
                            """, unsafe_allow_html=True)

                else:
                    # Empty state with call to action
                    st.markdown("""
                    <div class="empty-state">
                        <div class="empty-icon">📊</div>
                        <h3 class="empty-title">No Data Yet</h3>
                        <p class="empty-message">Start logging your nutrition to see beautiful analytics and track your progress!</p>
                        <div class="empty-tips">
                            <h4>💡 Quick Tips:</h4>
                            <ul>
                                <li>Log your meals daily for better insights</li>
                                <li>Aim for 150g of protein per day</li>
                                <li>Track consistently for best results</li>
                            </ul>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            except Exception as e:
                st.error(f"Error loading nutrition data: {str(e)}")
                st.info(
                    "Please check your database connection and make sure the get_nutrition_data method is properly implemented.")

            st.markdown("""
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Body Metrics Page
    elif page == "📏 Body Metrics":
        # Load external CSS
        with open('body_metrics.css', 'r') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

        st.markdown('<div class="page-header"><h1 class="page-title">📏 Body Metrics</h1><p class="page-subtitle">Track your body measurements and weight progress</p></div>', unsafe_allow_html=True)

        # Create tabs
        tab1, tab2, tab3 = st.tabs(
            ["📝 Log Metrics", "📊 Progress Charts", "📋 History"])

        with tab1:
            st.markdown('<div class="tab-content">', unsafe_allow_html=True)

            # Modern form layout
            col1, col2 = st.columns([1, 1], gap="large")

            with col1:
                st.markdown('<div class="form-section">',
                            unsafe_allow_html=True)
                st.markdown(
                    '<h3 class="section-title">📅 Basic Info</h3>', unsafe_allow_html=True)

                metrics_date = st.date_input(
                    "Date", value=date.today(), key="metrics_date")
                weight = st.number_input(
                    "Weight (kg)", min_value=30.0, max_value=200.0, step=0.1, key="weight_input")

                # Body fat percentage (optional)
                body_fat = st.number_input(
                    "Body Fat % (optional)", min_value=5.0, max_value=50.0, step=0.1, key="body_fat")

                st.markdown('</div>', unsafe_allow_html=True)

            with col2:
                st.markdown('<div class="form-section">',
                            unsafe_allow_html=True)
                st.markdown(
                    '<h3 class="section-title">📐 Measurements (cm)</h3>', unsafe_allow_html=True)

                measurements = {}
                measurement_types = [
                    ("Chest", "💪"),
                    ("Waist", "⚡"),
                    ("Hips", "🍑"),
                    ("Arms", "💪"),
                    ("Thighs", "🦵"),
                    ("Neck", "👔"),
                    ("Forearms", "💪")
                ]

                for measurement, emoji in measurement_types:
                    value = st.number_input(
                        f"{emoji} {measurement}",
                        min_value=0.0,
                        max_value=200.0,
                        step=0.5,
                        key=f"measurement_{measurement}"
                    )
                    if value > 0:
                        measurements[measurement.lower()] = value

                st.markdown('</div>', unsafe_allow_html=True)

            # Notes section
            st.markdown('<div class="form-section full-width">',
                        unsafe_allow_html=True)
            st.markdown('<h3 class="section-title">📝 Notes</h3>',
                        unsafe_allow_html=True)
            metrics_notes = st.text_area("Add any notes about your measurements",
                                         placeholder="e.g., Measured after workout, morning weight, etc.", key="metrics_notes")
            st.markdown('</div>', unsafe_allow_html=True)

            # Action buttons
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("📝 Log Metrics", use_container_width=True, type="primary"):
                    db.log_body_metrics(
                        metrics_date.strftime("%Y-%m-%d"),
                        weight if weight > 0 else None,
                        measurements,
                        metrics_notes,
                        body_fat if body_fat > 0 else None
                    )
                    st.success("✅ Body metrics logged successfully!")
                    st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)

        with tab2:
            st.markdown('<div class="tab-content">', unsafe_allow_html=True)

            # Time period selector
            time_period = st.selectbox("Select Time Period", [
                                       "Last 30 Days", "Last 90 Days", "Last 6 Months", "Last Year"], index=1)

            period_map = {
                "Last 30 Days": 30,
                "Last 90 Days": 90,
                "Last 6 Months": 180,
                "Last Year": 365
            }

            metrics_data = db.get_body_metrics_data(period_map[time_period])

            if metrics_data:
                df = pd.DataFrame(metrics_data)
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')

                # Weight progress chart
                if 'weight' in df.columns and df['weight'].notna().any():
                    st.markdown('<div class="chart-container">',
                                unsafe_allow_html=True)
                    fig = px.line(df, x='date', y='weight',
                                  title=f'Weight Progress ({time_period})',
                                  color_discrete_sequence=['#06b6d4'])
                    fig.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font_color='#374151',
                        title_font_size=20,
                        title_font_color='#1f2937'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)

                # Body measurements chart
                measurement_columns = [
                    col for col in df.columns if col.startswith('measurement_')]
                if measurement_columns:
                    st.markdown('<div class="chart-container">',
                                unsafe_allow_html=True)

                    # Create measurement trends
                    measurement_df = df[['date'] + measurement_columns].copy()
                    measurement_df_melted = measurement_df.melt(
                        id_vars=['date'], var_name='measurement', value_name='value')
                    measurement_df_melted['measurement'] = measurement_df_melted['measurement'].str.replace(
                        'measurement_', '').str.title()

                    fig = px.line(measurement_df_melted, x='date', y='value', color='measurement',
                                  title=f'Body Measurements Trends ({time_period})')
                    fig.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font_color='#374151',
                        title_font_size=20,
                        title_font_color='#1f2937'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)

            else:
                st.markdown('<div class="empty-state">',
                            unsafe_allow_html=True)
                st.markdown('<h3>📈 No Data Available</h3>',
                            unsafe_allow_html=True)
                st.markdown(
                    '<p>Start logging your body metrics to see progress charts here!</p>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

        with tab3:
            st.markdown('<div class="tab-content">', unsafe_allow_html=True)

            metrics_data = db.get_body_metrics_data(
                365)  # Get full year of data

            if metrics_data:
                df = pd.DataFrame(metrics_data)
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date', ascending=False)

                # Latest measurements card
                if len(df) > 0:
                    latest = df.iloc[0]

                    st.markdown('<div class="metrics-summary">',
                                unsafe_allow_html=True)
                    st.markdown(
                        '<h3 class="section-title">📊 Latest Measurements</h3>', unsafe_allow_html=True)

                    # Create metric cards
                    metric_cols = st.columns(4)

                    with metric_cols[0]:
                        if pd.notna(latest.get('weight')):
                            st.metric("Weight", f"{latest['weight']:.1f} kg")

                    with metric_cols[1]:
                        if pd.notna(latest.get('body_fat')):
                            st.metric("Body Fat", f"{latest['body_fat']:.1f}%")

                    # Show measurements
                    measurements = latest.get('measurements', {})
                    if measurements:
                        st.markdown(
                            '<h4 class="subsection-title">Body Measurements</h4>', unsafe_allow_html=True)
                        measurement_cols = st.columns(len(measurements))

                        for i, (key, value) in enumerate(measurements.items()):
                            with measurement_cols[i % len(measurement_cols)]:
                                st.metric(key.title(), f"{value} cm")

                    st.markdown('</div>', unsafe_allow_html=True)

                # History table
                st.markdown('<div class="history-table">',
                            unsafe_allow_html=True)
                st.markdown(
                    '<h3 class="section-title">📋 Measurement History</h3>', unsafe_allow_html=True)

                # Format data for display
                display_df = df.copy()
                display_df['Date'] = display_df['date'].dt.strftime('%Y-%m-%d')
                display_df = display_df[[
                    'Date', 'weight'] + [col for col in display_df.columns if col.startswith('measurement_')]]

                # Rename columns
                column_mapping = {'weight': 'Weight (kg)'}
                for col in display_df.columns:
                    if col.startswith('measurement_'):
                        column_mapping[col] = col.replace(
                            'measurement_', '').title() + ' (cm)'

                display_df = display_df.rename(columns=column_mapping)

                st.dataframe(display_df, use_container_width=True,
                             hide_index=True)
                st.markdown('</div>', unsafe_allow_html=True)

            else:
                st.markdown('<div class="empty-state">',
                            unsafe_allow_html=True)
                st.markdown('<h3>📋 No History Available</h3>',
                            unsafe_allow_html=True)
                st.markdown(
                    '<p>Your measurement history will appear here once you start logging data.</p>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

    # Progress Page
    elif page == "📈 Progress":
        st.markdown('<h1 class="page-title">📈 Your Progress</h1>',
                    unsafe_allow_html=True)

        # Time period selector
        period = st.selectbox(
            "Time Period", ["Last 30 Days", "Last 90 Days", "Last 6 Months", "All Time"])
        days_map = {"Last 30 Days": 30, "Last 90 Days": 90,
                    "Last 6 Months": 180, "All Time": 365*2}
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
                    workout_counts = workout_df.groupby(
                        workout_df['date'].dt.date).size().reset_index()
                    workout_counts.columns = ['date', 'workouts']

                    fig = px.bar(workout_counts, x='date', y='workouts',
                                 title='Workout Frequency',
                                 color_discrete_sequence=['#10b981'])
                    st.plotly_chart(fig, use_container_width=True)

            with col2:
                # Attendance pattern
                if attendance:
                    attendance_df = pd.DataFrame(attendance)
                    attendance_df['date'] = pd.to_datetime(
                        attendance_df['date'])

                    fig = px.scatter(attendance_df, x='date', y='attended',
                                     title='Gym Attendance Pattern',
                                     color='attended',
                                     color_discrete_map={True: '#10b981', False: '#ef4444'})
                    fig.update_layout(yaxis=dict(
                        tickvals=[0, 1], ticktext=['No', 'Yes']))
                    st.plotly_chart(fig, use_container_width=True)

            # Workout type distribution
            if workouts:
                type_counts = pd.Series(
                    [w.get('type', 'Unknown') for w in workouts]).value_counts()
                fig = px.pie(values=type_counts.values, names=type_counts.index,
                             title='Workout Type Distribution')
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available for the selected period")

    # Goals Page
    elif page == "🎯 Goals":
        try:
            with open('goals.css') as f:
                st.markdown(f'<style>{f.read()}</style>',
                            unsafe_allow_html=True)
        except:
            pass
        db.show_goals_page()

    # Workout Plans Page
    elif page == "📋 Workout Plans":
        st.markdown('<h1 class="page-title">📋 Workout Plans</h1>',
                    unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["📝 Create Plan", "📚 My Plans"])

        with tab1:
            with st.form("workout_plan_form"):
                plan_name = st.text_input(
                    "Plan Name", placeholder="e.g., Push Pull Legs")
                plan_description = st.text_area("Description",
                                                placeholder="Describe your workout plan")

                st.markdown("### Plan Structure")
                days = st.multiselect("Training Days",
                                      ["Monday", "Tuesday", "Wednesday", "Thursday",
                                       "Friday", "Saturday", "Sunday"])

                plan_data = {
                    "name": plan_name, "description": plan_description, "days": days, "exercises": {}}

                for day in days:
                    st.markdown(f"**{day} Workout**")
                    workout_type = st.selectbox(f"Workout Type for {day}",
                                                list(DEFAULT_EXERCISES.keys()), key=f"type_{day}")
                    selected_exercises = st.multiselect(f"Exercises for {day}",
                                                        DEFAULT_EXERCISES[workout_type], key=f"ex_{day}")
                    plan_data["exercises"][day] = {
                        "type": workout_type, "exercises": selected_exercises}

                if st.form_submit_button("💾 Save Plan", use_container_width=True):
                    if plan_name and days:
                        db.save_workout_plan(plan_data)
                        st.success("✅ Workout plan saved!")
                    else:
                        st.error(
                            "Please fill in plan name and select training days")

        with tab2:
            plans = db.get_workout_plans()
            if plans:
                for plan in plans:
                    with st.expander(f"📋 {plan['name']}"):
                        st.write(plan.get('description', 'No description'))
                        st.write(
                            f"**Training Days:** {', '.join(plan.get('days', []))}")

                        for day, workout in plan.get('exercises', {}).items():
                            st.write(
                                f"**{day}:** {workout.get('type', 'N/A')} - {len(workout.get('exercises', []))} exercises")

                        if st.button(f"🗑️ Delete {plan['name']}", key=f"del_plan_{plan['name']}"):
                            db.delete_workout_plan(plan['name'])
                            st.rerun()
            else:
                st.info("No workout plans created yet")

    elif page == "⏱️ Timer":
        # Timer Page
        try:
            with open('timer.css') as f:
                st.markdown(f'<style>{f.read()}</style>',
                            unsafe_allow_html=True)
        except:
            pass
            # Fallback if CSS file not found

        # Main page title
        st.markdown('<h1 class="page-title">⏱️ Workout Timers</h1>',
                    unsafe_allow_html=True)

        # --- Workout Timer Section ---
        st.markdown("---")

        st.markdown('<div class="timer-container">', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-header">🏋️ Workout Session Timer</div>', unsafe_allow_html=True)

        if "workout_timer_start" not in st.session_state:
            st.session_state.workout_timer_start = None

        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            if st.button("▶️ Start Workout", use_container_width=True, help="Begin tracking your workout session"):
                st.session_state.workout_timer_start = time.time()

        with col2:
            if st.button("⏹️ Stop Workout", use_container_width=True, help="End your workout session"):
                st.session_state.workout_timer_start = None

        if st.session_state.workout_timer_start:
            elapsed = time.time() - st.session_state.workout_timer_start
            hours, remainder = divmod(int(elapsed), 3600)
            minutes, seconds = divmod(remainder, 60)

            with col3:
                st.markdown(f"""
                <div class="workout-timer">
                    <div class="timer-display-large">{hours:02d}:{minutes:02d}:{seconds:02d}</div>
                    <div class="timer-label">💪 Workout Duration</div>
                </div>
                """, unsafe_allow_html=True)

            time.sleep(1)
            st.rerun()
        else:
            with col3:
                st.markdown("""
                <div class="workout-timer">
                    <div class="timer-display-large">00:00:00</div>
                    <div class="timer-label">Ready to Start! 🚀</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # Additional features section
        st.markdown("---")
        st.markdown('<div class="timer-container">', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            <div class="timer-card">
                <h4>💡 Timer Tips</h4>
                <ul>
                    <li>🎯 Use 1-2 min rest for light exercises</li>
                    <li>💪 Use 2-3 min rest for moderate weights</li>
                    <li>🏋️ Use 3-5 min rest for heavy lifts</li>
                    <li>⏰ Track total workout time for consistency</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown("""
            <div class="timer-card">
                <h4>📊 Quick Stats</h4>
                <p>🔥 <strong>Active Timers:</strong> Visual countdown displays</p>
                <p>⚡ <strong>Quick Access:</strong> Pre-set common rest periods</p>
                <p>🎨 <strong>Custom Duration:</strong> Set any rest time you need</p>
                <p>📱 <strong>Responsive:</strong> Works on all devices</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # Export Data Page
    elif page == "📊 Export Data":
        st.markdown('<h1 class="page-title">📊 Export Your Data</h1>',
                    unsafe_allow_html=True)

        st.markdown(
            "Export your fitness data for backup or analysis in other tools.")

        export_period = st.selectbox("Export Period",
                                     ["Last 30 Days", "Last 90 Days", "Last 6 Months", "All Time"])
        days_map = {"Last 30 Days": 30, "Last 90 Days": 90,
                    "Last 6 Months": 180, "All Time": 365*2}
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
