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

def attendance():
        user_id = st.session_state.user_data["_id"]
        username = st.session_state.user_data["username"]
        full_name = st.session_state.user_data["full_name"]
        db = bk.GymDatabase(user_id)
        try:
            with open('css/attendance.css') as f:
                st.markdown(f'<style>{f.read()}</style>',
                            unsafe_allow_html=True)
        except:
            pass

        # Page Header
        st.markdown("""
        <div class="main-header">
            <h1 style="margin:0; font-size: 2.5rem;">Gym Attendance</h1>
            <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">Track your fitness journey and maintain consistency</p>
        </div>
        """, unsafe_allow_html=True)

        # Create columns with proper spacing
        # col1, col2 = st.columns([1, 2], gap="large")

        # with col1:
        # Form section with container
        with st.container():
            st.markdown("### Log Today's Attendance")

            # Date input
            attendance_date = st.date_input(
                "📅 Date",
                value=date.today(),
                help="Select the date for attendance logging"
            )

            # Attendance selector
            attended = st.selectbox(
                "Did you attend the gym?",
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
                        st.success("Attendance logged successfully!")
                        st.balloons()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error logging attendance: {str(e)}")

        # with col2:
            # History section
        st.markdown("### Your Fitness Journey")

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
            st.markdown("#### Your Statistics")

            metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

            with metric_col1:
                st.metric(
                    label="Days Attended",
                    value=attended_days,
                    delta=f"{attendance_rate:.1f}% success rate"
                )

            with metric_col2:
                st.metric(
                    label="Days Missed",
                    value=missed_days,
                    delta=f"{100-attendance_rate:.1f}% missed"
                )

            with metric_col3:
                st.metric(
                    label="Success Rate",
                    value=f"{attendance_rate:.1f}%",
                    delta="Last 30 days"
                )

            with metric_col4:
                st.metric(
                    label="Current Streak",
                    value=current_streak,
                    delta="Consecutive days"
                )

            # Recent activity section
            st.markdown("#### Recent Activity")

            recent_entries = df.head(10)

            # Create tabs for better organization
            tab1, tab2 = st.tabs(["Activity List", "Calendar View"])

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
            st.markdown("#### Weekly Progress")

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
            st.info("No attendance data available yet")

            # Motivational content for new users
            st.markdown("""
                ### Start Your Fitness Journey!
                
                Welcome to your attendance tracker! Here's what you can expect:
                
                - **Track Progress**: Monitor your gym attendance over time
                - **Build Streaks**: See your consecutive attendance days
                - **Analyze Patterns**: Understand your workout habits
                - **Stay Motivated**: Visualize your fitness commitment
                
                **Ready to begin?** Log your first gym session using the form on the left!
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

        with st.expander("Tips for Consistent Gym Attendance"):
            tip_col1, tip_col2 = st.columns(2)

            with tip_col1:
                st.markdown("""
                **Setting Goals:**
                - Start with realistic targets
                - Aim for 3-4 days per week initially
                - Track your progress regularly
                - Celebrate small wins
                """)

            with tip_col2:
                st.markdown("""
                **Building Habits:**
                - Schedule gym time like appointments
                - Prepare gym clothes the night before
                - Find a workout buddy
                - Mix up your routine to stay engaged
                """)