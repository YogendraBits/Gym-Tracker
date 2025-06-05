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

def timer():
        user_id = st.session_state.user_data["_id"]
        username = st.session_state.user_data["username"]
        full_name = st.session_state.user_data["full_name"]
        db = bk.GymDatabase(user_id)
        try:
            with open('css/timer.css') as f:
                st.markdown(f'<style>{f.read()}</style>',
                            unsafe_allow_html=True)
        except:
            pass
            # Fallback if CSS file not found

        # Main page title
        st.markdown('<h1 class="page-title">Workout Timers</h1>',
                    unsafe_allow_html=True)

        # --- Workout Timer Section ---
        st.markdown("---")

        st.markdown('<div class="timer-container">', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-header">Workout Session Timer</div>', unsafe_allow_html=True)

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
                    <div class="timer-label">Workout Duration</div>
                </div>
                """, unsafe_allow_html=True)

            time.sleep(1)
            st.rerun()
        else:
            with col3:
                st.markdown("""
                <div class="workout-timer">
                    <div class="timer-display-large">00:00:00</div>
                    <div class="timer-label">Ready to Start!</div>
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
                <h4>Timer Tips</h4>
                <ul>
                    <li>Use 1-2 min rest for light exercises</li>
                    <li>Use 2-3 min rest for moderate weights</li>
                    <li>Use 3-5 min rest for heavy lifts</li>
                    <li>Track total workout time for consistency</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown("""
            <div class="timer-card">
                <h4>Quick Stats</h4>
                <p><strong>Active Timers:</strong> Visual countdown displays</p>
                <p><strong>Quick Access:</strong> Pre-set common rest periods</p>
                <p><strong>Custom Duration:</strong> Set any rest time you need</p>
                <p><strong>Responsive:</strong> Works on all devices</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)