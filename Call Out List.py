import streamlit as st
import requests

st.set_page_config(page_title="Attendance Notification", page_icon="📝")

# 1. Retrieve the webhook securely
try:
    WEBHOOK_URL = st.secrets["SLACK_WEBHOOK_URL"]
except KeyError:
    st.error("Configuration Error: SLACK_WEBHOOK_URL is missing from Streamlit secrets.")
    st.stop()

def notify_slack(worker_name, notification_type, reason, eta=""):
    """Pushes formatted attendance data to the Slack channel with visual priority."""
    if notification_type == "Running Late":
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
    
    response = requests.post(WEBHOOK_URL, json=payload, timeout=5)
    response.raise_for_status()

# 2. Build the interface
st.title("Attendance Update")

with st.form("attendance_form"):
    worker_name = st.text_input("Team Member Name", placeholder="Enter name...")
    notification_type = st.selectbox("Notification Type", ["Running Late", "Call Out (Absent)"])
    eta = st.text_input("ETA (If running late)", placeholder="e.g., 15 minutes, 9:30 AM")
    reason = st.text_area("Reason / Context", placeholder="Enter the reason...")
    
    # use_container_width makes the button span the full width like your HTML version
    submitted = st.form_submit_button("Submit Notification", use_container_width=True)

# 3. Execute payload on submission
if submitted:
    if not worker_name.strip() or not reason.strip():
        st.error("Team Member Name and Reason are required fields.")
    else:
        try:
            notify_slack(worker_name, notification_type, reason, eta)
            st.success(f"Success. {notification_type} logged for {worker_name}.")
        except requests.exceptions.RequestException as e:
            st.error(f"Slack webhook execution failed: {e}")
