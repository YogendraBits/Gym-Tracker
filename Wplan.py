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

def workout_plan():
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

        user_id = st.session_state.user_data["_id"]
        username = st.session_state.user_data["username"]
        full_name = st.session_state.user_data["full_name"]
        db = bk.GymDatabase(user_id)
        with open('css/workout_plans.css', 'r') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

        # Page header with enhanced styling
        st.markdown('''
            <div class="page-header">
                <div class="header-content">
                    <h1 class="page-title">
                        <span class="title-icon"></span>
                        Workout Plans
                    </h1>
                    <p class="page-subtitle">Create and manage your personalized training programs</p>
                </div>
            </div>
        ''', unsafe_allow_html=True)

        # Enhanced tabs with custom styling
        tab1, tab2 = st.tabs(["Create Plan", "My Plans"])

        with tab1:
            st.markdown('<div class="tab-content">', unsafe_allow_html=True)

            # Plan basics section
            st.markdown('''
                <div class="section-header">
                    <h3>Plan Basics</h3>
                    <p>Start by giving your workout plan a name and description</p>
                </div>
            ''', unsafe_allow_html=True)

            col1, col2 = st.columns([2, 3])

            with col1:
                plan_name = st.text_input(
                    "Plan Name",
                    placeholder="e.g., Push Pull Legs, Upper Lower Split",
                    help="Choose a memorable name for your workout plan"
                )

            with col2:
                plan_description = st.text_area(
                    "Description",
                    placeholder="Describe your goals, focus areas, or any special notes about this plan",
                    height=100,
                    help="Optional: Add details about your training goals"
                )

            st.markdown('<div class="section-divider"></div>',
                        unsafe_allow_html=True)

            # Training schedule section
            st.markdown('''
                <div class="section-header">
                    <h3>Training Schedule</h3>
                    <p>Select the days you want to train</p>
                </div>
            ''', unsafe_allow_html=True)

            # Custom day selector with better UX
            days_options = ["Monday", "Tuesday", "Wednesday",
                            "Thursday", "Friday", "Saturday", "Sunday"]
            selected_days = []

            cols = st.columns(7)
            for i, day in enumerate(days_options):
                with cols[i]:
                    day_short = day[:3]
                    if st.checkbox(day_short, key=f"day_{day}"):
                        selected_days.append(day)

            if selected_days:
                st.markdown('<div class="section-divider"></div>',
                            unsafe_allow_html=True)

                # Workout structure section
                st.markdown('''
                    <div class="section-header">
                        <h3>Workout Structure</h3>
                        <p>Configure exercises for each training day</p>
                    </div>
                ''', unsafe_allow_html=True)

                plan_data = {
                    "name": plan_name,
                    "description": plan_description,
                    "days": selected_days,
                    "exercises": {}
                }

                # Exercise configuration for each day
                for i, day in enumerate(selected_days):
                    with st.expander(f"🏋️ {day} Workout", expanded=i == 0):
                        col1, col2 = st.columns([1, 2])

                        with col1:
                            workout_type = st.selectbox(
                                "Workout Focus",
                                list(DEFAULT_EXERCISES.keys()),
                                key=f"type_{day}",
                                help=f"Choose the primary focus for {day}"
                            )

                        with col2:
                            selected_exercises = st.multiselect(
                                "Select Exercises",
                                DEFAULT_EXERCISES[workout_type],
                                key=f"ex_{day}",
                                help="Choose exercises from the selected category"
                            )

                        # Show exercise count
                        if selected_exercises:
                            st.markdown(f'''
                                <div class="exercise-count">
                                    ✅ {len(selected_exercises)} exercises selected
                                </div>
                            ''', unsafe_allow_html=True)

                        plan_data["exercises"][day] = {
                            "type": workout_type,
                            "exercises": selected_exercises
                        }

                st.markdown('<div class="section-divider"></div>',
                            unsafe_allow_html=True)

                # Save button section
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    if st.button("Save Workout Plan", use_container_width=True, type="primary"):
                        if plan_name and selected_days:
                            # Validate that at least one day has exercises
                            has_exercises = any(plan_data["exercises"].get(day, {}).get("exercises", [])
                                                for day in selected_days)

                            if has_exercises:
                                db.save_workout_plan(plan_data)
                                st.success(
                                    "🎉 Workout plan saved successfully!")
                                st.balloons()
                            else:
                                st.warning(
                                    "⚠️ Please add at least one exercise to your plan")
                        else:
                            st.error(
                                "❌ Please fill in plan name and select training days")

            st.markdown('</div>', unsafe_allow_html=True)

        with tab2:
            st.markdown('<div class="tab-content">', unsafe_allow_html=True)

            plans = db.get_workout_plans()

            if plans:
                # Plans header with stats
                st.markdown(f'''
                    <div class="plans-header">
                        <h3>Your Workout Plans</h3>
                        <div class="plans-stats">
                            <span class="stat-badge">{len(plans)} Plans Created</span>
                        </div>
                    </div>
                ''', unsafe_allow_html=True)

                # Plans grid
                for i, plan in enumerate(plans):
                    # Calculate plan stats
                    total_days = len(plan.get('days', []))
                    total_exercises = sum(len(workout.get('exercises', []))
                                          for workout in plan.get('exercises', {}).values())

                    st.markdown(f'''
                        <div class="plan-card">
                            <div class="plan-header">
                                <h4 class="plan-name">{plan['name']}</h4>
                                <div class="plan-stats">
                                    <span class="stat-item">📅 {total_days} days</span>
                                    <span class="stat-item">🏋️ {total_exercises} exercises</span>
                                </div>
                            </div>
                            <div>{f'<p class="plan-description">{plan.get("description", "")}</p>' if plan.get("description") else "No Plan Description"}</div>
                            <div class="plan-schedule">
                                <strong>Training Days:</strong>
                                <div class="days-list">{" ".join([f'<span class="day-badge">{day[:3]}</span>' for day in plan.get("days", [])])}</div>
                            </div>
                        </div>
                    ''', unsafe_allow_html=True)

                    # Expandable workout details
                    with st.expander("📋 View Workout Details"):
                        for day, workout in plan.get('exercises', {}).items():
                            st.markdown(f'''
                                <div class="workout-detail">
                                    <h5>{day}</h5>
                                    <p><strong>Focus:</strong> {workout.get('type', 'N/A')}</p>
                                    <p><strong>Exercises:</strong> {', '.join(workout.get('exercises', [])[:])}</p>
                                </div>
                            ''', unsafe_allow_html=True)

                    # Action buttons
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col2:
                        if st.button("📝 Edit", key=f"edit_{i}", help="Edit this plan"):
                            st.info("Edit functionality coming soon!")

                    with col3:
                        if st.button("🗑️ Delete", key=f"del_{i}", help="Delete this plan"):
                            if st.session_state.get(f"confirm_delete_{i}", False):
                                db.delete_workout_plan(plan['name'])
                                st.success("Plan deleted!")
                                st.rerun()
                            else:
                                st.session_state[f"confirm_delete_{i}"] = True
                                st.warning("Click again to confirm deletion")

                    st.markdown('<div class="plan-divider"></div>',
                                unsafe_allow_html=True)

            else:
                # Empty state with better design
                st.markdown('''
                    <div class="empty-state">
                        <div class="empty-icon">🏋️‍♀️</div>
                        <h3>No workout plans yet</h3>
                        <p>Create your first workout plan to get started on your fitness journey!</p>
                        <div class="empty-action">
                            Switch to the "Create Plan" tab to begin
                        </div>
                    </div>
                ''', unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)