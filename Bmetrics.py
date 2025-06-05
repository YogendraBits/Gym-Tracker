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

def body_metrics():
        user_id = st.session_state.user_data["_id"]
        username = st.session_state.user_data["username"]
        full_name = st.session_state.user_data["full_name"]
        db = bk.GymDatabase(user_id)

        with open('css/body_metrics.css', 'r') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

        st.markdown('<div class="page-header"><h1 class="page-title">Body Metrics</h1><p class="page-subtitle">Track your body measurements and weight progress</p></div>', unsafe_allow_html=True)

        # Create tabs
        tab1, tab2, tab3 = st.tabs(
            ["Log Metrics", "Progress Charts", "History"])

        with tab1:
            st.markdown('<div class="tab-content">', unsafe_allow_html=True)

            # Modern form layout
            col1, col2 = st.columns([1, 1], gap="large")

            with col1:
                st.markdown('<div class="form-section">',
                            unsafe_allow_html=True)
                st.markdown(
                    '<h3 class="section-title">Basic Info</h3>', unsafe_allow_html=True)

                metrics_date = st.date_input(
                    "Date", value=date.today(), key="metrics_date")
                weight = st.number_input(
                    "Weight (kg)", min_value=30.0, max_value=200.0, step=0.1, key="weight_input")

                # Body fat percentage (optional)
                body_fat = st.number_input(
                    "Body Fat % (optional)", min_value=5.0, max_value=50.0, step=0.1, key="body_fat")

                st.markdown('</div>', unsafe_allow_html=True)

            with col2:
                st.markdown('<div class="form-section">',
                            unsafe_allow_html=True)
                st.markdown(
                    '<h3 class="section-title">Measurements (cm)</h3>', unsafe_allow_html=True)

                measurements = {}
                measurement_types = [
                    ("Chest", "💪"),
                    ("Waist", "⚡"),
                    ("Hips", "🍑"),
                    ("Arms", "💪"),
                    ("Thighs", "🦵"),
                    ("Neck", "👔"),
                    ("Forearms", "💪")
                ]

                for measurement, emoji in measurement_types:
                    value = st.number_input(
                        f"{emoji} {measurement}",
                        min_value=0.0,
                        max_value=200.0,
                        step=0.5,
                        key=f"measurement_{measurement}"
                    )
                    if value > 0:
                        measurements[measurement.lower()] = value

                st.markdown('</div>', unsafe_allow_html=True)

            # Notes section
            st.markdown('<div class="form-section full-width">',
                        unsafe_allow_html=True)
            st.markdown('<h3 class="section-title">Notes</h3>',
                        unsafe_allow_html=True)
            metrics_notes = st.text_area("Add any notes about your measurements",
                                         placeholder="e.g., Measured after workout, morning weight, etc.", key="metrics_notes")
            st.markdown('</div>', unsafe_allow_html=True)

            # Action buttons
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("Log Metrics", use_container_width=True, type="primary"):
                    db.log_body_metrics(
                        metrics_date.strftime("%Y-%m-%d"),
                        weight if weight > 0 else None,
                        measurements,
                        metrics_notes,
                        body_fat if body_fat > 0 else None
                    )
                    st.success("Body metrics logged successfully!")
                    st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)

        with tab2:
            st.markdown('<div class="tab-content">', unsafe_allow_html=True)

            # Time period selector
            time_period = st.selectbox("Select Time Period", [
                                       "Last 30 Days", "Last 90 Days", "Last 6 Months", "Last Year"], index=1)

            period_map = {
                "Last 30 Days": 30,
                "Last 90 Days": 90,
                "Last 6 Months": 180,
                "Last Year": 365
            }

            metrics_data = db.get_body_metrics_data(period_map[time_period])

            if metrics_data:
                df = pd.DataFrame(metrics_data)
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')

                # Weight progress chart
                if 'weight' in df.columns and df['weight'].notna().any():
                    st.markdown('<div class="chart-container">',
                                unsafe_allow_html=True)
                    fig = px.line(df, x='date', y='weight',
                                  title=f'Weight Progress ({time_period})',
                                  color_discrete_sequence=['#06b6d4'])
                    fig.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font_color='#374151',
                        title_font_size=20,
                        title_font_color='#1f2937'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)

                # Body measurements chart
                measurement_columns = [
                    col for col in df.columns if col.startswith('measurement_')]
                if measurement_columns:
                    st.markdown('<div class="chart-container">',
                                unsafe_allow_html=True)

                    # Create measurement trends
                    measurement_df = df[['date'] + measurement_columns].copy()
                    measurement_df_melted = measurement_df.melt(
                        id_vars=['date'], var_name='measurement', value_name='value')
                    measurement_df_melted['measurement'] = measurement_df_melted['measurement'].str.replace(
                        'measurement_', '').str.title()

                    fig = px.line(measurement_df_melted, x='date', y='value', color='measurement',
                                  title=f'Body Measurements Trends ({time_period})')
                    fig.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font_color='#374151',
                        title_font_size=20,
                        title_font_color='#1f2937'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)

            else:
                st.markdown('<div class="empty-state">',
                            unsafe_allow_html=True)
                st.markdown('<h3>No Data Available</h3>',
                            unsafe_allow_html=True)
                st.markdown(
                    '<p>Start logging your body metrics to see progress charts here!</p>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

        with tab3:
            st.markdown('<div class="tab-content">', unsafe_allow_html=True)

            metrics_data = db.get_body_metrics_data(
                365)  # Get full year of data

            if metrics_data:
                df = pd.DataFrame(metrics_data)
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date', ascending=False)

                # Latest measurements card
                if len(df) > 0:
                    latest = df.iloc[0]

                    st.markdown('<div class="metrics-summary">',
                                unsafe_allow_html=True)
                    st.markdown(
                        '<h3 class="section-title">Latest Measurements</h3>', unsafe_allow_html=True)

                    # Create metric cards
                    metric_cols = st.columns(4)

                    with metric_cols[0]:
                        if pd.notna(latest.get('weight')):
                            st.metric("Weight", f"{latest['weight']:.1f} kg")

                    with metric_cols[1]:
                        if pd.notna(latest.get('body_fat')):
                            st.metric("Body Fat", f"{latest['body_fat']:.1f}%")

                    # Show measurements
                    measurements = latest.get('measurements', {})
                    if measurements:
                        st.markdown(
                            '<h4 class="subsection-title">Body Measurements</h4>', unsafe_allow_html=True)
                        measurement_cols = st.columns(len(measurements))

                        for i, (key, value) in enumerate(measurements.items()):
                            with measurement_cols[i % len(measurement_cols)]:
                                st.metric(key.title(), f"{value} cm")

                    st.markdown('</div>', unsafe_allow_html=True)

                # History table
                st.markdown('<div class="history-table">',
                            unsafe_allow_html=True)
                st.markdown(
                    '<h3 class="section-title">📋 Measurement History</h3>', unsafe_allow_html=True)

                # Format data for display
                display_df = df.copy()
                display_df['Date'] = display_df['date'].dt.strftime('%Y-%m-%d')
                display_df = display_df[[
                    'Date', 'weight'] + [col for col in display_df.columns if col.startswith('measurement_')]]

                # Rename columns
                column_mapping = {'weight': 'Weight (kg)'}
                for col in display_df.columns:
                    if col.startswith('measurement_'):
                        column_mapping[col] = col.replace(
                            'measurement_', '').title() + ' (cm)'

                display_df = display_df.rename(columns=column_mapping)

                st.dataframe(display_df, use_container_width=True,
                             hide_index=True)
                st.markdown('</div>', unsafe_allow_html=True)

            else:
                st.markdown('<div class="empty-state">',
                            unsafe_allow_html=True)
                st.markdown('<h3>No History Available</h3>',
                            unsafe_allow_html=True)
                st.markdown(
                    '<p>Your measurement history will appear here once you start logging data.</p>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)