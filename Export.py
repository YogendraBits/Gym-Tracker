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

def export_data():
        user_id = st.session_state.user_data["_id"]
        username = st.session_state.user_data["username"]
        full_name = st.session_state.user_data["full_name"]
        db = bk.GymDatabase(user_id)

        with open('css/export_styles.css') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
        
        st.markdown("""

            <div class="export-container">
                <h1 class="export-title">Export Your Data</h1>
                <p class="export-subtitle">Export your fitness data for backup, analysis, or sharing with other tools</p>
            </div>
        """, unsafe_allow_html=True)

        
        # Export configuration section
        st.markdown('<h3 class="section-title">Export Configuration</h3>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="input-group">', unsafe_allow_html=True)
            st.markdown('<label class="input-label">Time Period</label>', unsafe_allow_html=True)
            export_period = st.selectbox(
                "Export Period",
                ["Last 7 Days", "Last 30 Days", "Last 90 Days", "Last 6 Months", "Last Year", "All Time"],
                label_visibility="collapsed"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="input-group">', unsafe_allow_html=True)
            st.markdown('<label class="input-label">Export Format</label>', unsafe_allow_html=True)
            export_format = st.selectbox(
                "Export Format",
                ["JSON (Structured)", "CSV (Spreadsheet)", "Excel (Workbook)", "PDF (Report)"],
                label_visibility="collapsed"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Data selection section
        st.markdown('<h3 class="section-title">  Data to Include</h3>', unsafe_allow_html=True)
        
        # data_options = st.columns(4)
        
        # with data_options[0]:
        #     include_workouts = st.checkbox("Workouts", value=True)
        # with data_options[1]:
        #     include_attendance = st.checkbox("Attendance", value=True)
        # with data_options[2]:
        #     include_nutrition = st.checkbox("Nutrition", value=True)
        # with data_options[3]:
        #     include_body_metrics = st.checkbox("Body Metrics", value=True)

        options = st.multiselect(
            "Select data to include:",
            ["Workouts", "Attendance", "Nutrition", "Body Metrics"],
            default=["Workouts", "Attendance", "Nutrition", "Body Metrics"]
        )

        include_workouts = "Workouts" in options
        include_attendance = "Attendance" in options
        include_nutrition = "Nutrition" in options
        include_body_metrics = "Body Metrics" in options


        if st.button("Generate Export", use_container_width=True, type="primary"):
            
            # Progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Map time periods to days
            days_map = {
                "Last 7 Days": 7,
                "Last 30 Days": 30, 
                "Last 90 Days": 90,
                "Last 6 Months": 180, 
                "Last Year": 365,
                "All Time": 365*10
            }
            days = days_map[export_period]
            
            # Collect data based on selections
            export_data = {
                "export_date": datetime.now().isoformat(),
                "user": username,
                "period": export_period,
                "format": export_format,
                "data": {},
                "summary": {}
            }
            
            progress = 0
            total_steps = sum([include_workouts, include_attendance, include_nutrition, include_body_metrics])
            
            # Fetch selected data
            if include_workouts:
                status_text.text("Fetching workout data...")
                workouts = db.get_recent_workouts(days)
                export_data["data"]["workouts"] = workouts
                export_data["summary"]["total_workouts"] = len(workouts)
                progress += 1
                progress_bar.progress(progress / total_steps)
            
            if include_attendance:
                status_text.text("Fetching attendance data...")
                attendance = db.get_attendance_data(days)
                export_data["data"]["attendance"] = attendance
                export_data["summary"]["total_attendance_records"] = len(attendance)
                progress += 1
                progress_bar.progress(progress / total_steps)
            
            if include_nutrition:
                status_text.text("Fetching nutrition data...")
                nutrition = db.get_nutrition_data(days)
                export_data["data"]["nutrition"] = nutrition
                export_data["summary"]["total_nutrition_records"] = len(nutrition)
                progress += 1
                progress_bar.progress(progress / total_steps)
            
            if include_body_metrics:
                status_text.text("Fetching body metrics data...")
                body_metrics = db.get_body_metrics_data(days)
                export_data["data"]["body_metrics"] = body_metrics
                export_data["summary"]["total_body_metrics"] = len(body_metrics)
                progress += 1
                progress_bar.progress(progress / total_steps)
            
            status_text.text("Preparing export file...")
            
            # Generate export based on format
            today_str = date.today().strftime("%Y%m%d")
            base_filename = f"gym_tracker_export_{username}_{today_str}"
            
            if export_format == "JSON (Structured)":
                json_data = json.dumps(export_data, indent=2, default=str)
                st.download_button(
                    label="📥 Download JSON Export",
                    data=json_data,
                    file_name=f"{base_filename}.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            elif export_format == "CSV (Spreadsheet)":
                # Create CSV data for each type
                csv_files = {}
                
                if include_workouts and export_data["data"].get("workouts"):
                    workouts_df = pd.DataFrame(export_data["data"]["workouts"])
                    csv_files["workouts"] = workouts_df.to_csv(index=False)
                
                if include_attendance and export_data["data"].get("attendance"):
                    attendance_df = pd.DataFrame(export_data["data"]["attendance"])
                    csv_files["attendance"] = attendance_df.to_csv(index=False)
                
                if include_nutrition and export_data["data"].get("nutrition"):
                    nutrition_df = pd.DataFrame(export_data["data"]["nutrition"])
                    csv_files["nutrition"] = nutrition_df.to_csv(index=False)
                
                if include_body_metrics and export_data["data"].get("body_metrics"):
                    metrics_df = pd.DataFrame(export_data["data"]["body_metrics"])
                    csv_files["body_metrics"] = metrics_df.to_csv(index=False)
                
                # Create ZIP file with all CSVs
                import zipfile
                import io
                
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for name, csv_data in csv_files.items():
                        zip_file.writestr(f"{name}.csv", csv_data)
                    # Add summary file
                    summary_df = pd.DataFrame([export_data["summary"]])
                    zip_file.writestr("summary.csv", summary_df.to_csv(index=False))
                
                st.download_button(
                    label="📥 Download CSV Package (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name=f"{base_filename}_csv.zip",
                    mime="application/zip",
                    use_container_width=True
                )
            
            elif export_format == "Excel (Workbook)":
                # Create Excel file with multiple sheets
                import io
                
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    # Summary sheet
                    summary_df = pd.DataFrame([export_data["summary"]])
                    summary_df.to_excel(writer, sheet_name='Summary', index=False)
                    
                    if include_workouts and export_data["data"].get("workouts"):
                        workouts_df = pd.DataFrame(export_data["data"]["workouts"])
                        workouts_df.to_excel(writer, sheet_name='Workouts', index=False)
                    
                    if include_attendance and export_data["data"].get("attendance"):
                        attendance_df = pd.DataFrame(export_data["data"]["attendance"])
                        attendance_df.to_excel(writer, sheet_name='Attendance', index=False)
                    
                    if include_nutrition and export_data["data"].get("nutrition"):
                        nutrition_df = pd.DataFrame(export_data["data"]["nutrition"])
                        nutrition_df.to_excel(writer, sheet_name='Nutrition', index=False)
                    
                    if include_body_metrics and export_data["data"].get("body_metrics"):
                        metrics_df = pd.DataFrame(export_data["data"]["body_metrics"])
                        metrics_df.to_excel(writer, sheet_name='Body_Metrics', index=False)
                
                st.download_button(
                    label="📥 Download Excel Workbook",
                    data=excel_buffer.getvalue(),
                    file_name=f"{base_filename}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            
            elif export_format == "PDF (Report)":
                # Generate PDF report
                from reportlab.lib.pagesizes import letter, A4
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib.units import inch
                from reportlab.lib import colors
                
                pdf_buffer = io.BytesIO()
                doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
                styles = getSampleStyleSheet()
                story = []
                
                # Title
                title_style = ParagraphStyle(
                    'CustomTitle',
                    parent=styles['Heading1'],
                    fontSize=24,
                    spaceAfter=30,
                    textColor=colors.HexColor('#2E86AB')
                )
                story.append(Paragraph("Gym Tracker Export Report", title_style))
                story.append(Spacer(1, 12))
                
                # Export info
                info_data = [
                    ['Export Date:', export_data['export_date'][:10]],
                    ['User:', export_data['user']],
                    ['Period:', export_data['period']],
                    ['Format:', export_data['format']]
                ]
                info_table = Table(info_data, colWidths=[2*inch, 4*inch])
                info_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F4F8')),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(info_table)
                story.append(Spacer(1, 24))
                
                # Summary
                story.append(Paragraph("Data Summary", styles['Heading2']))
                summary_data = [['Data Type', 'Records Count']]
                for key, value in export_data['summary'].items():
                    summary_data.append([key.replace('_', ' ').title(), str(value)])
                
                summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
                summary_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E86AB')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 14),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(summary_table)
                
                doc.build(story)
                
                st.download_button(
                    label="📥 Download PDF Report",
                    data=pdf_buffer.getvalue(),
                    file_name=f"{base_filename}_report.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            
            progress_bar.progress(1.0)
            status_text.text("✅ Export ready!")

            st.markdown('<h3 class="section-title">Export Summary</h3>', unsafe_allow_html=True)
            
            summary_cols = st.columns(len(export_data["summary"]))
            for i, (key, value) in enumerate(export_data["summary"].items()):
                with summary_cols[i]:
                    st.markdown(f'''
                    <div class="summary-card">
                        <div class="summary-number">{value}</div>
                        <div class="summary-label">{key.replace('_', ' ').replace('total ', '').title()}</div>
                    </div>
                    ''', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Quick tips section
        st.markdown('<h3 class="section-title">💡 Export Tips</h3>', unsafe_allow_html=True)
        
        tips_cols = st.columns(2)
        
        with tips_cols[0]:
            st.markdown('''
            <div class="tip-card">
                <h4>📊 For Data Analysis</h4>
                <p>Use <strong>CSV</strong> or <strong>Excel</strong> formats for importing into analysis tools like Python, R, or Excel pivot tables.</p>
            </div>
            ''', unsafe_allow_html=True)
            
            st.markdown('''
            <div class="tip-card">
                <h4>🔄 For Backup</h4>
                <p>Use <strong>JSON</strong> format to preserve all data structure and metadata for complete backup.</p>
            </div>
            ''', unsafe_allow_html=True)
        
        with tips_cols[1]:
            st.markdown('''
            <div class="tip-card">
                <h4>📋 For Sharing</h4>
                <p>Use <strong>PDF</strong> format to create professional reports for trainers or healthcare providers.</p>
            </div>
            ''', unsafe_allow_html=True)
            
            st.markdown('''
            <div class="tip-card">
                <h4>⚡ Performance Tip</h4>
                <p>For large datasets, consider shorter time periods or specific data types to reduce file size.</p>
            </div>
            ''', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)