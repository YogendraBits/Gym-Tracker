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

def load_css():
    """Load the external CSS file"""
    try:
        with open('css/workout_viewer_styles.css', 'r', encoding="utf-8") as f:
            css = f.read()
        st.markdown(f'<style>{css}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.error("CSS file not found. Please make sure 'workout_viewer_styles.css' is in the same directory.")

def view_workouts():
    # Load CSS styles
    load_css()
    
    user_id = st.session_state.user_data["_id"]
    username = st.session_state.user_data["username"]
    full_name = st.session_state.user_data["full_name"]
    db = bk.GymDatabase(user_id)
    
    # Page title with modern styling
    st.markdown('<h1 class="page-title">Past Workouts</h1>', unsafe_allow_html=True)

    # Controls section with modern styling
    st.markdown('<div class="controls-section">', unsafe_allow_html=True)
    
    # Date range and sort controls
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        days_back = st.selectbox(
            "Show workouts from",
            ["Last 7 days", "Last 30 days", "Last 90 days", "All time"],
            help="Select the time period for workouts to display"
        )
    with col2:
        sort_order = st.selectbox(
            "Sort by", 
            ["Newest first", "Oldest first"],
            help="Choose how to sort your workouts"
        )

    days_map = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90, "All time": 365*2}
    days = days_map[days_back]

    # Search functionality with modern styling
    st.markdown('<div class="search-container">', unsafe_allow_html=True)
    search_term = st.text_input(
        "", 
        placeholder="🔍 Search workouts by exercise name, workout type, or notes...",
        key="workout_search",
        help="Search through your workouts to find specific exercises or notes"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

    # Get workouts
    with st.spinner("Loading your workouts..."):
        workouts = db.get_recent_workouts(days)

    if sort_order == "Oldest first":
        workouts = sorted(workouts, key=lambda x: x['date'])

    if workouts:
        # Workout count with modern styling
        st.markdown(f'<div class="workout-count">Found {len(workouts)} workout(s)</div>', 
                   unsafe_allow_html=True)

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
            
            if search_term and len(workouts) != len(db.get_recent_workouts(days)):
                st.markdown(f'<div class="workout-count">Showing {len(workouts)} workout(s) matching "{search_term}"</div>', 
                           unsafe_allow_html=True)

        # Display workouts with modern card design
        for i, workout in enumerate(workouts):
            # Workout card container
            st.markdown('<div class="workout-card fade-in">', unsafe_allow_html=True)
            
            # Workout header
            workout_type = workout.get('type', 'Unknown Type')
            exercise_count = len(workout.get('exercises', []))
            
            with st.expander(
                f"📅 {workout['date']} - {workout_type} ({exercise_count} exercises)", 
                expanded=(i == 0)
            ):
                # Workout content
                st.markdown('<div class="workout-content">', unsafe_allow_html=True)
                
                # Workout info grid
                st.markdown('<div class="workout-info-grid">', unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"""
                        <div class="info-item">
                            <div class="info-label">📅 Date</div>
                            <div class="info-value">{workout['date']}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">🏋️ Type</div>
                            <div class="info-value">{workout.get('type', 'N/A')}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                with col2:
                    duration = workout.get('duration', 'N/A')
                    intensity = workout.get('intensity', 'N/A')
                    st.markdown(f"""
                        <div class="info-item">
                            <div class="info-label">⏱️ Duration</div>
                            <div class="info-value">{"" if duration == 'N/A' else f"{duration} min"}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">🔥 Intensity</div>
                            <div class="info-value">{intensity}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                with col3:
                    start_time = workout.get('start_time', '')
                    end_time = workout.get('end_time', '')
                    start_display = ""
                    end_display = ""
                    
                    if start_time:
                        try:
                            start_dt = datetime.fromisoformat(start_time)
                            start_display = start_dt.strftime('%H:%M')
                        except:
                            start_display = "N/A"
                    
                    if end_time:
                        try:
                            end_dt = datetime.fromisoformat(end_time)
                            end_display = end_dt.strftime('%H:%M')
                        except:
                            end_display = "N/A"
                    
                    st.markdown(f"""
                        <div class="info-item">
                            <div class="info-label">🕐 Started</div>
                            <div class="info-value">{start_display or "N/A"}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">🕑 Ended</div>
                            <div class="info-value">{end_display or "N/A"}</div>
                        </div>
                    """, unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)

                # Workout notes with modern styling
                if workout.get('notes'):
                    st.markdown(f"""
                        <div class="workout-notes">
                            <strong>📝 Workout Notes:</strong><br>
                            {workout["notes"]}
                        </div>
                    """, unsafe_allow_html=True)

                # Section separator
                st.markdown('<div class="section-separator"></div>', unsafe_allow_html=True)

                # Exercises section
                exercises = workout.get('exercises', [])
                if exercises:
                    st.markdown('<div class="exercises-section">', unsafe_allow_html=True)
                    st.markdown('<div class="exercises-title">💪 Exercises</div>', unsafe_allow_html=True)

                    for j, exercise in enumerate(exercises):
                        st.markdown('<div class="exercise-card slide-in">', unsafe_allow_html=True)
                        
                        # Exercise name
                        st.markdown(f"""
                            <div class="exercise-name">
                                {j+1}. {exercise.get('name', 'Unknown Exercise')}
                            </div>
                        """, unsafe_allow_html=True)

                        sets = exercise.get('sets', [])
                        if sets:
                            # Calculate exercise statistics
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
                                        time_dt = datetime.fromisoformat(timestamp)
                                        time_str = time_dt.strftime('%H:%M:%S')
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
                                    'Time': time_str if time_str else '-'
                                })

                            # Display sets table with modern styling
                            st.markdown('<div class="sets-table-container">', unsafe_allow_html=True)
                            df_sets = pd.DataFrame(sets_data)
                            st.dataframe(
                                df_sets, 
                                hide_index=True,
                                use_container_width=True,
                                column_config={
                                    "Set": st.column_config.NumberColumn("Set", width="small"),
                                    "Reps": st.column_config.NumberColumn("Reps", width="small"),
                                    "Weight (kg)": st.column_config.NumberColumn("Weight (kg)", width="medium"),
                                    "Volume (kg)": st.column_config.NumberColumn("Volume (kg)", width="medium"),
                                    "Time": st.column_config.TextColumn("Time", width="small")
                                }
                            )
                            st.markdown('</div>', unsafe_allow_html=True)

                            # Exercise summary stats with modern cards
                            st.markdown('<div class="exercise-stats">', unsafe_allow_html=True)
                            
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.markdown(f"""
                                    <div class="stat-card">
                                        <div class="stat-value">{len(sets)}</div>
                                        <div class="stat-label">Total Sets</div>
                                    </div>
                                """, unsafe_allow_html=True)
                            with col2:
                                st.markdown(f"""
                                    <div class="stat-card">
                                        <div class="stat-value">{total_reps}</div>
                                        <div class="stat-label">Total Reps</div>
                                    </div>
                                """, unsafe_allow_html=True)
                            with col3:
                                st.markdown(f"""
                                    <div class="stat-card">
                                        <div class="stat-value">{max_weight}</div>
                                        <div class="stat-label">Max Weight (kg)</div>
                                    </div>
                                """, unsafe_allow_html=True)
                            with col4:
                                st.markdown(f"""
                                    <div class="stat-card">
                                        <div class="stat-value">{total_volume}</div>
                                        <div class="stat-label">Total Volume (kg)</div>
                                    </div>
                                """, unsafe_allow_html=True)
                            
                            st.markdown('</div>', unsafe_allow_html=True)
                            
                        else:
                            st.markdown("""
                                <div class="empty-state">
                                    <div class="empty-state-icon">📊</div>
                                    <div class="empty-state-title">No Sets Recorded</div>
                                    <div class="empty-state-description">
                                        No sets were recorded for this exercise
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)

                        st.markdown('</div>', unsafe_allow_html=True)  # Close exercise-card
                        
                        if j < len(exercises) - 1:  # Add separator except for last exercise
                            st.markdown('<div class="exercise-separator"></div>', unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)  # Close exercises-section
                else:
                    st.markdown("""
                        <div class="empty-state">
                            <div class="empty-state-icon">🏋️</div>
                            <div class="empty-state-title">No Exercises Recorded</div>
                            <div class="empty-state-description">
                                No exercises were recorded for this workout
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)  # Close workout-content
            
            st.markdown('</div>', unsafe_allow_html=True)  # Close workout-card
            
    else:
        # Empty state with modern styling
        st.markdown(f"""
            <div class="empty-state">
                <div class="empty-state-icon">🏋️‍♀️</div>
                <div class="empty-state-title">No Workouts Found</div>
                <div class="empty-state-description">
                    No workouts found for the selected period ({days_back})
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
            <div class="info-banner">
                <p>💡 <strong>Ready to Start Your Fitness Journey?</strong></p>
                <p>Begin logging your workouts to track your progress and see your achievements here!</p>
                <p>Use the "Log Workout" pages to add your first workout.</p>
            </div>
        """, unsafe_allow_html=True)

# Additional helper functions for enhanced functionality
def get_workout_statistics(workouts):
    """Calculate overall workout statistics"""
    if not workouts:
        return {}
    
    total_workouts = len(workouts)
    total_exercises = sum(len(w.get('exercises', [])) for w in workouts)
    total_sets = sum(
        len(ex.get('sets', [])) 
        for w in workouts 
        for ex in w.get('exercises', [])
    )
    total_volume = sum(
        set_info.get('reps', 0) * set_info.get('weight', 0)
        for w in workouts
        for ex in w.get('exercises', [])
        for set_info in ex.get('sets', [])
        if isinstance(set_info.get('reps'), (int, float)) and 
           isinstance(set_info.get('weight'), (int, float))
    )
    
    return {
        'total_workouts': total_workouts,
        'total_exercises': total_exercises,
        'total_sets': total_sets,
        'total_volume': total_volume
    }

def display_workout_summary(workouts):
    """Display a summary dashboard of workout statistics"""
    stats = get_workout_statistics(workouts)
    
    if stats:
        st.markdown('<div class="workout-summary-dashboard">', unsafe_allow_html=True)
        st.markdown('<h3 class="summary-title">📊 Workout Summary</h3>', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
                <div class="summary-stat-card">
                    <div class="summary-stat-value">{stats['total_workouts']}</div>
                    <div class="summary-stat-label">Total Workouts</div>
                </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
                <div class="summary-stat-card">
                    <div class="summary-stat-value">{stats['total_exercises']}</div>
                    <div class="summary-stat-label">Total Exercises</div>
                </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
                <div class="summary-stat-card">
                    <div class="summary-stat-value">{stats['total_sets']}</div>
                    <div class="summary-stat-label">Total Sets</div>
                </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
                <div class="summary-stat-card">
                    <div class="summary-stat-value">{stats['total_volume']:,.0f}</div>
                    <div class="summary-stat-label">Total Volume (kg)</div>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

# Enhanced view_workouts function with summary
def view_workouts_with_summary():
    """Enhanced version of view_workouts with summary dashboard"""
    # Load CSS styles
    load_css()
    
    user_id = st.session_state.user_data["_id"]
    username = st.session_state.user_data["username"]
    full_name = st.session_state.user_data["full_name"]
    db = bk.GymDatabase(user_id)
    
    # Page title with modern styling
    st.markdown('<h1 class="page-title">Past Workouts</h1>', unsafe_allow_html=True)

    # Get all workouts for summary
    all_workouts = db.get_recent_workouts(365*2)  # Get all workouts
    
    # Display summary if workouts exist
    if all_workouts:
        display_workout_summary(all_workouts)
    
    # Continue with the rest of the view_workouts function...
    view_workouts()

if __name__ == "__main__":
    # You can call either function
    view_workouts()  # Original function with modern styling
    # view_workouts_with_summary()  # Enhanced version with summary dashboard