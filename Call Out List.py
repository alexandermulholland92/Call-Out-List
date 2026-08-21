import os
from datetime import date, timedelta
import requests
import streamlit as st

# Configure page & favicons
st.set_page_config(
    page_title="Attendance Notice", 
    page_icon="📋", 
    layout="centered"
)

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 680px; }
    </style>
""", unsafe_allow_html=True)

# Fetch Slack Webhook URL
SLACK_WEBHOOK_URL = st.secrets.get("SLACK_WEBHOOK_URL", os.environ.get("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"))

TYPE_CONFIGS = {
    "Call Out (Full Day)": {"emoji": "🚨"},
    "Call Out AM": {"emoji": "🌅"},
    "Call Out PM": {"emoji": "🌇"},
    "Late": {"emoji": "⏳"},
    "Leave Early": {"emoji": "🏃"}
}

def notify_slack(name, start_d, end_d, status, time_info, reason):
    """Pushes a formatted attendance notice to Slack."""
    # Format the date text
    if start_d == end_d:
        d_str = start_d.strftime("%A, %b %d, %Y")
    else:
        d_str = f"{start_d.strftime('%a, %b %d')} ➔ {end_d.strftime('%a, %b %d, %Y')}"
        
    emoji = TYPE_CONFIGS[status]["emoji"]
    
    # Build schedule line
    schedule_line = f"• *{d_str}*: {emoji} {status}"
    if time_info:
        schedule_line += f" _({time_info})_"
        
    color = "#FF3B30" if "Call Out" in status else "#FF9500"

    payload = {
        "attachments": [
            {
                "color": color,
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"📋 *Attendance Schedule Update*\n*Name:* {name}\n\n*Schedule Details:*\n{schedule_line}\n\n*Context:* {reason}"
                        }
                    }
                ]
            }
        ]
    }
    
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=5)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Slack webhook failed: {e}")
        return False

# --- App Header ---
st.title("📋 Attendance Update")
st.caption("Submit attendance notices directly to Slack.")

# Initialize session state to reset form after submission
if "form_key" not in st.session_state:
    st.session_state.form_key = 0
if "last_submission" not in st.session_state:
    st.session_state.last_submission = None

fk = st.session_state.form_key

# Show success message if just submitted
if st.session_state.last_submission:
    st.success(f"🎉 **Notice Submitted Successfully!**\n\nNotification sent to Slack for **{st.session_state.last_submission}**.")
    st.balloons()
    if st.button("Dismiss Confirmation", type="secondary"):
        st.session_state.last_submission = None
        st.rerun()

st.markdown("---")

# --- UNIFIED FORM ---
worker_name = st.text_input("Team Member Name", placeholder="e.g. John Doe", key=f"name_{fk}")

options = ["Call Out (Full Day)", "Call Out AM", "Call Out PM", "Late", "Leave Early"]
selected_status = st.selectbox("Status / Action", options, key=f"status_{fk}")

# Date Pickers
col_start, col_end = st.columns(2)
with col_start:
    start_date = st.date_input("Start Date", value=None, key=f"start_{fk}")
with col_end:
    end_date = st.date_input("End Date (Optional)", value=None, help="Leave blank for a single day.", key=f"end_{fk}")

time_info = st.text_input(
    "Time Details (Optional for Full Day)", 
    placeholder="e.g., Arriving at 10:30 AM / Leaving at 2 PM", 
    key=f"time_{fk}"
)

reason = st.text_area("Reason / Context", placeholder="Brief explanation for your shift adjustment...", key=f"reason_{fk}")

# Submit Button
if st.button("Submit Notification", type="primary", use_container_width=True):
    # Determine the actual end date
    actual_end = end_date if end_date else start_date
    
    # Form Validation
    if not worker_name.strip():
        st.error("Please enter your name.")
    elif not start_date:
        st.error("Please select a Start Date.")
    elif actual_end < start_date:
        st.error("End Date cannot be before the Start Date.")
    elif selected_status in ["Late", "Leave Early"] and not time_info.strip():
        st.error(f"Please provide Time Details for '{selected_status}'.")
    elif not reason.strip():
        st.error("Please provide a Reason / Context.")
    else:
        # PUSH TO SLACK
        if notify_slack(worker_name.strip(), start_date, actual_end, selected_status, time_info.strip(), reason.strip()):
            st.session_state.last_submission = worker_name.strip()
            st.session_state.form_key += 1  # Increments key, completely resetting the form
            st.rerun()
