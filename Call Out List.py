import streamlit as st
import requests
from datetime import date, timedelta

st.set_page_config(page_title="Attendance Notification", page_icon="📝")

# 1. Retrieve the webhook securely
try:
    WEBHOOK_URL = st.secrets["SLACK_WEBHOOK_URL"]
except KeyError:
    st.error("Configuration Error: SLACK_WEBHOOK_URL is missing from Streamlit secrets.")
    st.stop()

def notify_slack(worker_name, notification_type, reason, formatted_date, eta=""):
    """Pushes formatted attendance data to the Slack channel with visual priority."""
    if notification_type == "Running Late":
        header = "⏳ *Running Late*"
        color = "#FF9500"  # Warning Orange
        details = f"*Name:* {worker_name}\n*Date(s):* {formatted_date}\n*ETA:* {eta}\n*Context:* {reason}"
    else:
        header = "🚨 *Call Out*"
        color = "#FF3B30"  # Critical Red
        details = f"*Name:* {worker_name}\n*Date(s):* {formatted_date}\n*Context:* {reason}"

    payload = {
        "attachments": [
            {
                "color": color,
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"{header}\n{details}"
                        }
                    }
                ]
            }
        ]
    }
    
    response = requests.post(WEBHOOK_URL, json=payload, timeout=5)
    response.raise_for_status()

# 2. Generate a rolling window of dates (Today up to 30 days in the future)
today = date.today()
date_options = [(today + timedelta(days=i)).strftime("%A, %b %d, %Y") for i in range(0, 31)]
default_date = [today.strftime("%A, %b %d, %Y")]

# 3. Build the interface
st.title("Attendance Update")

with st.form("attendance_form"):
    worker_name = st.text_input("Team Member Name", placeholder="Enter name...")
    
    col1, col2 = st.columns(2)
    with col1:
        notification_type = st.selectbox("Notification Type", ["Running Late", "Call Out (Absent)"])
    with col2:
        absence_dates = st.multiselect("Select Date(s)", options=date_options, default=default_date)
        
    eta = st.text_input("ETA (If running late)", placeholder="e.g., 15 minutes, 9:30 AM")
    reason = st.text_area("Reason / Context", placeholder="Enter the reason...")
    
    submitted = st.form_submit_button("Submit Notification", use_container_width=True)

# 4. Execute payload on submission
if submitted:
    if not worker_name.strip() or not reason.strip():
        st.error("Team Member Name and Reason are required fields.")
    elif not absence_dates:
        st.error("Please select at least one date.")
    else:
        formatted_date = "\n> " + "\n> ".join(absence_dates)

        try:
            notify_slack(worker_name, notification_type, reason, formatted_date, eta)
            st.success(f"Success. {notification_type} logged for {worker_name}.")
        except requests.exceptions.RequestException as e:
            st.error(f"Slack webhook execution failed: {e}")
