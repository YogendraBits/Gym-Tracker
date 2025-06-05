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

def progress():
        user_id = st.session_state.user_data["_id"]
        username = st.session_state.user_data["username"]
        full_name = st.session_state.user_data["full_name"]
        db = bk.GymDatabase(user_id)
        def calculate_current_streak(attendance_data):
            """Calculate current attendance streak"""
            if not attendance_data:
                return 0

            # Sort by date descending
            sorted_data = sorted(
                attendance_data, key=lambda x: x.get('date', ''), reverse=True)

            streak = 0
            for record in sorted_data:
                if record.get('attended', False):
                    streak += 1
                else:
                    break

            return streak
        with open('css/progress_styles.css') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

        # Modern header with gradient background
        st.markdown('''
            <div class="progress-header">
                <div class="header-content">
                    <h1 class="main-title">Your Fitness Journey</h1>
                    <p class="subtitle">Track your progress and celebrate your achievements</p>
                </div>
            </div>
        ''', unsafe_allow_html=True)

        # Modern time period selector with custom styling
        st.markdown('<div class="section-container">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            period = st.selectbox(
                "📅 Select Time Period",
                ["Last 30 Days", "Last 90 Days", "Last 6 Months", "All Time"],
                key="period_selector"
            )
        st.markdown('</div>', unsafe_allow_html=True)

        days_map = {"Last 30 Days": 30, "Last 90 Days": 90,
                    "Last 6 Months": 180, "All Time": 365*2}
        days = days_map[period]

        # Get all data
        workouts = db.get_recent_workouts(days)
        attendance = db.get_attendance_data(days)
        nutrition = db.get_nutrition_data(days)

        if workouts or attendance or nutrition:
            # Key Metrics Cards
            st.markdown('<div class="metrics-section">',
                        unsafe_allow_html=True)
            st.markdown('<h2 class="section-title">Key Metrics</h2>',
                        unsafe_allow_html=True)

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                workout_count = len(workouts) if workouts else 0
                st.markdown(f'''
                    <div class="metric-card workout-card">
                        <div class="metric-icon">🏋️</div>
                        <div class="metric-value">{workout_count}</div>
                        <div class="metric-label">Total Workouts</div>
                    </div>
                ''', unsafe_allow_html=True)

            with col2:
                if attendance:
                    attendance_rate = sum(1 for a in attendance if a.get(
                        'attended', False)) / len(attendance) * 100
                else:
                    attendance_rate = 0
                st.markdown(f'''
                    <div class="metric-card attendance-card">
                        <div class="metric-icon">📅</div>
                        <div class="metric-value">{attendance_rate:.1f}%</div>
                        <div class="metric-label">Attendance Rate</div>
                    </div>
                ''', unsafe_allow_html=True)

            with col3:
                avg_workouts = workout_count / (days / 7) if days > 0 else 0
                st.markdown(f'''
                    <div class="metric-card frequency-card">
                        <div class="metric-icon">⚡</div>
                        <div class="metric-value">{avg_workouts:.1f}</div>
                        <div class="metric-label">Workouts/Week</div>
                    </div>
                ''', unsafe_allow_html=True)

            with col4:
                streak = calculate_current_streak(
                    attendance) if attendance else 0
                st.markdown(f'''
                    <div class="metric-card streak-card">
                        <div class="metric-icon">🔥</div>
                        <div class="metric-value">{streak}</div>
                        <div class="metric-label">Current Streak</div>
                    </div>
                ''', unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

            # Charts Section
            st.markdown('<div class="charts-section">', unsafe_allow_html=True)

            # Workout Frequency Chart
            if workouts:
                st.markdown(
                    '<h2 class="section-title">Workout Frequency</h2>', unsafe_allow_html=True)

                workout_df = pd.DataFrame(workouts)
                workout_df['date'] = pd.to_datetime(workout_df['date'])
                workout_counts = workout_df.groupby(
                    workout_df['date'].dt.date).size().reset_index()
                workout_counts.columns = ['date', 'workouts']

                fig = px.bar(workout_counts, x='date', y='workouts',
                             title='Daily Workout Count',
                             color_discrete_sequence=['#667eea'])


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
                    ))
                st.plotly_chart(fig, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

            # Two column layout for remaining charts
            col1, col2 = st.columns([1, 1])

            with col1:
                # Attendance Heatmap
                if attendance:
                    st.markdown(
                        '<h3 class="chart-title">Attendance Pattern</h3>', unsafe_allow_html=True)
                    st.markdown('<div class="chart-container small">',
                                unsafe_allow_html=True)

                    attendance_df = pd.DataFrame(attendance)
                    attendance_df['date'] = pd.to_datetime(
                        attendance_df['date'])

                    # Create a more sophisticated attendance visualization
                    fig = px.scatter(attendance_df, x='date', y='attended',
                                     color='attended',
                                     color_discrete_map={
                                         True: '#10b981', False: '#ef4444'},
                                     size_max=10)

                    fig.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#374151'),
                        yaxis=dict(tickvals=[0, 1], ticktext=[
                                   'Missed', 'Attended']),
                        showlegend=False,
                        height=300
                    )

                    st.plotly_chart(fig, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)

            with col2:
                # Workout Type Distribution
                if workouts:
                    st.markdown(
                        '<h3 class="chart-title">Workout Types</h3>', unsafe_allow_html=True)
                    st.markdown('<div class="chart-container small">',
                                unsafe_allow_html=True)

                    type_counts = pd.Series(
                        [w.get('type', 'Unknown') for w in workouts]).value_counts()

                    colors = ['#667eea', '#764ba2',
                              '#f093fb', '#f5576c', '#4facfe']

                    fig = px.pie(values=type_counts.values, names=type_counts.index,
                                 color_discrete_sequence=colors)

                    fig.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#374151'),
                        height=300,
                        showlegend=True,
                        legend=dict(orientation="v", yanchor="middle", y=0.5)
                    )

                    st.plotly_chart(fig, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

            # Progress Insights
            st.markdown('<div class="insights-section">',
                        unsafe_allow_html=True)
            st.markdown(
                '<h2 class="section-title">Progress Insights</h2>', unsafe_allow_html=True)

            insights_col1, insights_col2 = st.columns(2)

            with insights_col1:
                st.markdown('''
                    <div class="insight-card positive">
                        <h4>🎉 Achievements</h4>
                        <ul>
                            <li>Maintained consistent workout schedule</li>
                            <li>Improved attendance rate by 15%</li>
                            <li>Diversified workout types</li>
                        </ul>
                    </div>
                ''', unsafe_allow_html=True)

            with insights_col2:
                st.markdown('''
                    <div class="insight-card neutral">
                        <h4>🎯 Areas for Growth</h4>
                        <ul>
                            <li>Try to maintain 4+ workouts per week</li>
                            <li>Focus on consistency during weekends</li>
                            <li>Consider adding more cardio sessions</li>
                        </ul>
                    </div>
                ''', unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

        else:
            # Empty state with modern design
            st.markdown('''
                <div class="empty-state">
                    <div class="empty-icon">📊</div>
                    <h2>No Data Available</h2>
                    <p>Start logging your workouts to see your progress here!</p>
                    <div class="empty-actions">
                        <button class="cta-button">Log Your First Workout</button>
                    </div>
                </div>
            ''', unsafe_allow_html=True)