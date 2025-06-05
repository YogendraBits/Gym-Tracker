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

def log_workout():
    
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
        st.markdown('<h1 class="page-title">Log Workout</h1>',
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
                '<h2 class="section-title">Workout Setup</h2>', unsafe_allow_html=True)

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
