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
    """Load external CSS file"""
    with open('css/manage.css', 'r') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def create_record_card(record_info: str, record_details: str, delete_key: str, delete_callback, icon: str = "📊"):
    """Create a styled record card with delete functionality"""
    col1, col2 = st.columns([6, 1])
    
    with col1:
        st.markdown(f"""
        <div class="data-record fade-in">
            <div class="record-content">
                <div class="record-info">
                    <div class="record-date">{record_info}</div>
                    <div class="record-details">
                        <span class="record-icon">{icon}</span>
                        <span>{record_details}</span>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if st.button("🗑️", key=delete_key, help="Delete this record", use_container_width=True):
            delete_callback()
            st.success("Record deleted successfully!")
            time.sleep(0.5)  # Brief pause for user feedback
            st.rerun()

def show_empty_state(message: str, icon: str = "📭"):
    """Display styled empty state"""
    st.markdown(f"""
    <div class="empty-state fade-in">
        <div class="empty-state-icon">{icon}</div>
        <div class="empty-state-text">{message}</div>
    </div>
    """, unsafe_allow_html=True)

def manage_data():
    # Load CSS styling
    load_css()
    
    # Get user data
    user_id = st.session_state.user_data["_id"]
    username = st.session_state.user_data["username"]
    full_name = st.session_state.user_data["full_name"]
    db = bk.GymDatabase(user_id)
    
    # Page title with gradient effect
    st.markdown("""
    <div class="fade-in">
        <h1 class="page-title">Manage Your Data</h1>
    </div>
    """, unsafe_allow_html=True)

    # Create tabs with modern styling
    tab1, tab2, tab3, tab4 = st.tabs([
        "💪 Workouts", 
        "📅 Attendance", 
        "🍎 Nutrition", 
        "⚖️ Body Metrics"
    ])

    with tab1:
        st.markdown('<h3 class="section-header">Workout Records</h3>', unsafe_allow_html=True)
        
        # Add stats summary
        workouts = db.get_recent_workouts(90)
        if workouts:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📊 Total Workouts", len(workouts))
            with col2:
                total_exercises = sum(len(w.get('exercises', [])) for w in workouts)
                st.metric("🏋️ Total Exercises", total_exercises)
            with col3:
                latest_date = max(w['date'] for w in workouts) if workouts else "N/A"
                st.metric("📅 Latest Workout", latest_date)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Display workout records
            for workout in workouts:
                workout_type = workout.get('type', 'General Workout')
                exercise_count = len(workout.get('exercises', []))
                exercise_text = f"{exercise_count} exercise{'s' if exercise_count != 1 else ''}"
                
                create_record_card(
                    record_info=f"{workout['date']} - {workout_type}",
                    record_details=exercise_text,
                    delete_key=f"del_workout_{workout['_id']}",
                    delete_callback=lambda w_id=workout['_id']: db.delete_workout(w_id),
                    icon="💪"
                )
        else:
            show_empty_state("No workout records found in the last 90 days", "💪")

    with tab2:
        st.markdown('<h3 class="section-header">Attendance Records</h3>', unsafe_allow_html=True)
        
        attendance = db.get_attendance_data(90)
        if attendance:
            # Stats summary
            attended_count = sum(1 for record in attendance if record.get('attended'))
            total_count = len(attendance)
            attendance_rate = (attended_count / total_count * 100) if total_count > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📊 Total Days", total_count)
            with col2:
                st.metric("✅ Days Attended", attended_count)
            with col3:
                st.metric("📈 Attendance Rate", f"{attendance_rate:.1f}%")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Display attendance records
            for record in attendance:
                status = "Attended" if record.get('attended') else "Missed"
                icon = "✅" if record.get('attended') else "❌"
                
                create_record_card(
                    record_info=record['date'],
                    record_details=f"{status}",
                    delete_key=f"del_attendance_{record['date']}",
                    delete_callback=lambda date=record['date']: db.delete_attendance(date),
                    icon=icon
                )
        else:
            show_empty_state("No attendance records found in the last 90 days", "📅")

    with tab3:
        st.markdown('<h3 class="section-header">Nutrition Records</h3>', unsafe_allow_html=True)
        
        nutrition = db.get_nutrition_data(90)
        if nutrition:
            # Stats summary
            total_protein = sum(record.get('protein_intake', 0) for record in nutrition)
            avg_protein = total_protein / len(nutrition) if nutrition else 0
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📊 Total Records", len(nutrition))
            with col2:
                st.metric("🥩 Total Protein", f"{total_protein:.1f}g")
            with col3:
                st.metric("📈 Avg Daily Protein", f"{avg_protein:.1f}g")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Display nutrition records
            for record in nutrition:
                protein_intake = record.get('protein_intake', 0)
                calories = record.get('calories', 0)
                
                details = f"{protein_intake}g protein"
                if calories > 0:
                    details += f" • {calories} cal"
                
                create_record_card(
                    record_info=record['date'],
                    record_details=details,
                    delete_key=f"del_nutrition_{record['date']}",
                    delete_callback=lambda date=record['date']: db.delete_nutrition(date),
                    icon="🍎"
                )
        else:
            show_empty_state("No nutrition records found in the last 90 days", "🍎")

    with tab4:
        st.markdown('<h3 class="section-header">Body Metrics Records</h3>', unsafe_allow_html=True)
        
        metrics = db.get_body_metrics_data(90)
        if metrics:
            # Stats summary
            weights = [m.get('weight') for m in metrics if m.get('weight')]
            if weights:
                latest_weight = weights[-1] if weights else 0
                weight_change = weights[-1] - weights[0] if len(weights) > 1 else 0
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📊 Total Records", len(metrics))
                with col2:
                    st.metric("⚖️ Current Weight", f"{latest_weight:.1f}kg")
                with col3:
                    delta_color = "normal" if abs(weight_change) < 0.1 else ("inverse" if weight_change < 0 else "normal")
                    st.metric("📈 Weight Change", f"{weight_change:+.1f}kg", delta_color=delta_color)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Display body metrics records
            for record in metrics:
                weight = record.get('weight')
                body_fat = record.get('body_fat_percentage')
                
                if weight:
                    details = f"{weight}kg"
                    if body_fat:
                        details += f" • {body_fat}% body fat"
                else:
                    details = "No weight recorded"
                
                create_record_card(
                    record_info=record['date'],
                    record_details=details,
                    delete_key=f"del_metrics_{record['date']}",
                    delete_callback=lambda date=record['date']: db.delete_body_metrics(date),
                    icon="⚖️"
                )
        else:
            show_empty_state("No body metrics records found in the last 90 days", "⚖️")

    # Add footer with additional info
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
    <div class="glass p-md" style="text-align: center; margin-top: 2rem;">
        <p class="text-muted">💡 <strong>Tip:</strong> Deleted records cannot be recovered. Make sure you want to permanently remove the data.</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    manage_data()