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

def dashboard():
        def load_css():
                with open("css/dashboard.css", "r", encoding="utf-8") as f:
                    st.markdown(f"<style>{f.read()}</style>",
                                unsafe_allow_html=True)

        load_css()
        # Main dashboard container with gradient background
        user_id = st.session_state.user_data["_id"]
        username = st.session_state.user_data["username"]
        full_name = st.session_state.user_data["full_name"]
        db = bk.GymDatabase(user_id)

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
            <h2 class="section-title">Quick Log</h2>
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
                ["Not logged", "Yes", "No"],
                key="quick_attendance",
                label_visibility="collapsed"
            )

            if attended_today != "Not logged":
                if st.button("Log Attendance", use_container_width=True, key="log_att_btn"):
                    db.log_attendance(today, attended_today == "Yes")
                    st.success("Attendance logged successfully!")
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

            if st.button("Log Protein", use_container_width=True, key="log_protein_btn"):
                db.log_nutrition(today, protein_amount)
                st.success("Protein intake logged successfully!")
                st.rerun()

            st.markdown('</div></div>', unsafe_allow_html=True)

        # Enhanced recent activity section
        st.markdown('''
        <div class="section-divider"></div>
        <div class="section-header">
            <h2 class="section-title">Recent Activity</h2>
        </div>
        ''', unsafe_allow_html=True)

        if recent_workouts:
            latest_workout = recent_workouts[0]
            exercise_count = len(latest_workout.get('exercises', []))
            st.markdown(f"""
            <div class="activity-showcase">
                <div class="activity-card latest-workout">
                    <div class="activity-header">
                        <div class="activity-icon-large"></div>
                        <div class="activity-badge">Latest</div>
                    </div>
                    <div class="activity-body">
                        <div class="activity-title">Last Workout Session</div>
                        <div class="activity-meta">
                            <span class="activity-date">{latest_workout['date']}</span>
                            <span class="activity-exercises">{exercise_count} exercises</span>
                        </div>
                        <div class="activity-progress">
                            <div class="activity-stats">
                                <div class="stat-item">
                                    <span class="stat-label">Exercises</span>
                                    <span class="stat-value">{exercise_count}</span>
                                </div>
                                <div class="stat-item">
                                    <span class="stat-label">Status</span>
                                    <span class="stat-value completed">Completed</span>
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
                    <div class="empty-icon"></div>
                    <div class="empty-title">No recent workouts</div>
                    <div class="empty-subtitle">Start logging your workouts to see activity here!</div>
                </div>
            </div>
            ''', unsafe_allow_html=True)

        # Enhanced attendance chart
        st.markdown('''
        <div class="section-divider"></div>
        <div class="section-header">
            <h2 class="section-title">Attendance Trends</h2>
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
                    <div class="empty-icon"></div>
                    <div class="empty-title">No attendance data yet</div>
                    <div class="empty-subtitle">Start logging your gym visits to see trends!</div>
                </div>
            </div>
            ''', unsafe_allow_html=True)