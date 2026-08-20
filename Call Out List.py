import os
import requests
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template_string

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)

# This will now pull securely from your .env file
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

def notify_slack(worker_name, notification_type, reason, eta=""):
    """Pushes formatted attendance data to the Slack channel with visual priority."""
    if notification_type == "Late":
        header = "⏳ *Running Late*"
        color = "#FF9500"  # Warning Orange
        details = f"*Name:* {worker_name}\n*ETA:* {eta}\n*Context:* {reason}"
    else:
        header = "🚨 *Call Out*"
        color = "#FF3B30"  # Critical Red
        details = f"*Name:* {worker_name}\n*Context:* {reason}"

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
    
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=5)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Slack webhook failed: {e}")
        return False

# --- UI Layout ---
st.title("Attendance Update")
st.write("Submit call outs or late notices directly to Slack.")

with st.form("attendance_form"):
    worker_name = st.text_input("Team Member Name", placeholder="e.g. John Doe")
    
    notification_type = st.selectbox("Notification Type", ["Late", "Call Out"])
    
    # We always show ETA, but we'll only enforce it if they select "Late"
    eta = st.text_input("ETA (Required if Running Late)", placeholder="e.g. 10:30 AM or 'in 15 mins'")
    
    reason = st.text_area("Reason / Context", placeholder="Brief reason for the delay or absence...")
    
    submitted = st.form_submit_button("Submit Notification", type="primary")

    if submitted:
        # Validation
        if not worker_name.strip():
            st.error("Please enter a Team Member Name.")
        elif not reason.strip():
            st.error("Please enter a Reason / Context.")
        elif notification_type == "Late" and not eta.strip():
            st.error("ETA is required when running late.")
        else:
            # Everything is valid, send the notification
            success = notify_slack(worker_name, notification_type, reason, eta)
            if success:
                st.success(f"Success! {notification_type} logged for {worker_name}.")
