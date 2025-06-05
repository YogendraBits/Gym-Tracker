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


def nutrition():
        user_id = st.session_state.user_data["_id"]
        username = st.session_state.user_data["username"]
        full_name = st.session_state.user_data["full_name"]
        db = bk.GymDatabase(user_id)
        try:
            # Load custom CSS
            with open("css/nutrition_styles.css", "r") as f:
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
        tab1, tab2 = st.tabs(["Log Nutrition", "Analytics & History"])

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
                    {'On Track!' if protein_progress >= 80 else 'Keep Going!'}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Meals section with enhanced UI
            st.markdown("""
            <div class="meals-section">
                <h3 class="section-title">Today's Meals</h3>
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
                    <span class="notes-icon"></span>
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
            if st.button("Log Nutrition", use_container_width=True, type="primary"):
                try:
                    db.log_nutrition(
                        nutrition_date.strftime("%Y-%m-%d"),
                        protein_intake,
                        meals,
                        nutrition_notes
                    )
                    st.success("Nutrition logged successfully!")
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
                        <span class="card-icon"></span>
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
                            <h3 class="section-title">Recent Meals</h3>
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
                        <div class="empty-icon"></div>
                        <h3 class="empty-title">No Data Yet</h3>
                        <p class="empty-message">Start logging your nutrition to see beautiful analytics and track your progress!</p>
                        <div class="empty-tips">
                            <h4>💡Quick Tips:</h4>
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