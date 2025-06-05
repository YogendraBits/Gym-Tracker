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

def goals():
    user_id = st.session_state.user_data["_id"]
    username = st.session_state.user_data["username"]
    full_name = st.session_state.user_data["full_name"]
    db = bk.GymDatabase(user_id)
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
            ["All Goals", "Add Goal", "Progress", "Analytics"])

        with tab1:
            show_all_goals(db)

        with tab2:
            show_add_goal_form(db)

        with tab3:
            show_goal_progress(db)

        with tab4:
            show_goal_analytics(db)

    def show_all_goals(db):
        """Display all goals with management options"""
        st.markdown("### Your Goals")

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
            goals = sorted(goals, key=lambda x: x.get(
                "target_date", "9999-12-31"))

        # Display goals
        for goal in goals:
            display_goal_card(db,goal)

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
                st.write(
                    f"**Target Date:** {goal.get('target_date', 'Not set')}")

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
                    with st.popover("Update Progress"):
                        with st.form(f"progress_form_{goal['_id']}"):
                            progress_value = st.number_input("Current Progress",
                                                             value=goal.get("current_progress", 0))
                            progress_notes = st.text_area("Notes (optional)")

                            if st.form_submit_button("Update Progress"):
                                progress_data = {
                                    "progress_value": progress_value,
                                    "notes": progress_notes
                                }
                                db.update_goal_progress(
                                    goal["_id"], progress_data)
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
        st.markdown("### Add New Goal")

        st.markdown("""
        <div class="info-banner">
            <h3>Goal Setting Tips</h3>
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

            if st.form_submit_button("Create Goal", use_container_width=True):
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
                    st.success("Goal created successfully!")
                    st.balloons()
                else:
                    st.error(
                        "Please fill in the required fields (Title and Target Date)")

    def show_goal_progress(db):
        """Show goal progress tracking"""
        st.markdown("### Goal Progress Tracking")

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
                    progress_df = progress_df.sort_values(
                        "date", ascending=False)
                    st.dataframe(
                        progress_df[["date", "progress_value", "notes"]], use_container_width=True)

    def show_goal_analytics(db):
        """Show goal analytics and insights"""
        st.markdown("### Goal Analytics & Insights")

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
        st.markdown("#### Success Insights")

        completed_goals = [
            g for g in all_goals if g.get("status") == "completed"]

        if completed_goals:
            avg_completion_time = []
            for goal in completed_goals:
                if goal.get("completed_at") and goal.get("created_at"):
                    completion_time = (
                        goal["completed_at"] - goal["created_at"]).days
                    avg_completion_time.append(completion_time)

            if avg_completion_time:
                avg_days = sum(avg_completion_time) / len(avg_completion_time)
                st.metric("Average Goal Completion Time",
                          f"{avg_days:.1f} days")

            # Most successful categories
            completed_df = pd.DataFrame(completed_goals)
            if "category" in completed_df.columns:
                successful_categories = completed_df["category"].value_counts()
                st.markdown("**Most Successful Categories:**")
                for category, count in successful_categories.head(3).items():
                    st.write(f"• {category}: {count} completed goals")

        else:
            st.info("Complete some goals to see success insights!")
    
    return show_goals_page(db)
