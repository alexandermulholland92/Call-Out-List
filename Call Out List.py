import streamlit as st
import requests
import os
from datetime import date, timedelta

# Fetch Slack Webhook URL from Streamlit Secrets or Environment Variables
SLACK_WEBHOOK_URL = st.secrets.get("SLACK_WEBHOOK_URL", os.environ.get("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"))

def format_date_list(dates):
    """Sorts and formats multiple independent dates into readable text."""
    if not dates:
        return "N/A"
    
    sorted_dates = sorted(dates)
    if len(sorted_dates) == 1:
        return sorted_dates[0].strftime("%A, %B %d, %Y")
    
    # Formats multiple dates as: "Mon, Aug 24, 2026 | Wed, Aug 26, 2026"
    return " | ".join(d.strftime("%a, %b %d, %Y") for d in sorted_dates)

def notify_slack(worker_name, notification_type, formatted_date, reason, time_info=""):
    """Pushes formatted attendance data to Slack with distinct visual priority."""
    
    configs = {
        "Late": {
            "header": "⏳ *Running Late*",
            "color": "#FF9500",
            "details": f"*Name:* {worker_name}\n*Date(s):* {formatted_date}\n*ETA:* {time_info}\n*Context:* {reason}"
        },
        "Call Out": {
            "header": "🚨 *Call Out (Full Day)*",
            "color": "#FF3B30",
            "details": f"*Name:* {worker_name}\n*Date(s):* {formatted_date}\n*Context:* {reason}"
        },
        "Call Out AM": {
            "header": "🌅 *Call Out (AM Shift)*",
            "color": "#FF3B30",
            "details": f"*Name:* {worker_name}\n*Date(s):* {formatted_date}\n*Context:* {reason}"
        },
        "Call Out PM": {
            "header": "🌇 *Call Out (PM Shift)*",
            "color": "#FF3B30",
            "details": f"*Name:* {worker_name}\n*Date(s):* {formatted_date}\n*Context:* {reason}"
        },
        "Leave Early": {
            "header": "🏃 *Leaving Early*",
            "color": "#FFCC00",
            "details": f"*Name:* {worker_name}\n*Date(s):* {formatted_date}\n*Departure Time:* {time_info}\n*Context:* {reason}"
        }
    }

    config = configs.get(notification_type, configs["Call Out"])

    payload = {
        "attachments": [
            {
                "color": config["color"],
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"{config['header']}\n{config['details']}"
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
st.write("Submit call outs or attendance notices directly to Slack.")

with st.form("attendance_form"):
    worker_name = st.text_input("Team Member Name", placeholder="e.g. John Doe")
    
    options = ["Late", "Call Out", "Call Out AM", "Call Out PM", "Leave Early"]
    notification_type = st.selectbox("Notification Type", options)
    
    # Generate rolling window of dates (3 days in past to 60 days in future)
    today = date.today()
    available_dates = [today + timedelta(days=i) for i in range(-3, 60)]
    
    selected_dates = st.multiselect(
        "Select Date(s)",
        options=available_dates,
        default=[today],
        format_func=lambda d: d.strftime("%a, %b %d, %Y")
    )
    
    time_info = st.text_input(
        "Time Details (ETA if Late / Departure Time if Leaving Early)", 
        placeholder="e.g. 10:30 AM or 'Leaving at 2:00 PM'"
    )
    
    reason = st.text_area("Reason / Context", placeholder="Brief reason for the schedule adjustment...")
    
    submitted = st.form_submit_button("Submit Notification", type="primary")

    if submitted:
        formatted_date = format_date_list(selected_dates)
        
        if not worker_name.strip():
            st.error("Please enter a Team Member Name.")
        elif not selected_dates:
            st.error("Please select at least one date.")
        elif not reason.strip():
            st.error("Please enter a Reason / Context.")
        elif notification_type in ["Late", "Leave Early"] and not time_info.strip():
            st.error(f"Time details are required when selecting '{notification_type}'.")
        else:
            success = notify_slack(worker_name, notification_type, formatted_date, reason, time_info)
            if success:
                st.success(f"Success! '{notification_type}' logged for {worker_name} ({formatted_date}).")
