import os
from datetime import date
import requests
import streamlit as st

# Set page config & styling
st.set_page_config(page_title="Attendance Notice", page_icon="📋", layout="centered")

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

def notify_slack(worker_name, date_entries, reason):
    """Pushes formatted multi-date attendance data to Slack."""
    schedule_lines = []
    has_call_out = False
    
    for entry in date_entries:
        d_str = entry["date"].strftime("%a, %b %d, %Y")
        ntype = entry["type"]
        time_info = entry["time_info"]
        emoji = TYPE_CONFIGS[ntype]["emoji"]
        
        line = f"• *{d_str}*: {emoji} {ntype}"
        if time_info:
            line += f" _({time_info})_"
        schedule_lines.append(line)
        
        if "Call Out" in ntype:
            has_call_out = True

    schedule_text = "\n".join(schedule_lines)
    color = "#FF3B30" if has_call_out else "#FF9500"

    payload = {
        "attachments": [
            {
                "color": color,
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"📋 *Attendance Schedule Update*\n*Name:* {worker_name}\n\n*Schedule Details:*\n{schedule_text}\n\n*Context:* {reason}"
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

# --- Form Inputs ---
worker_name = st.text_input("Team Member Name", placeholder="e.g. John Doe")

# Native Streamlit Calendar widget configured for picking multiple independent dates
selected_dates = st.date_input(
    "Select Date(s) from Calendar",
    value=[date.today()],
    selection_mode="multiple"
)

date_entries = []
options = ["Call Out (Full Day)", "Call Out AM", "Call Out PM", "Late", "Leave Early"]

if selected_dates:
    st.subheader("Configure Selected Dates")
    
    with st.form("attendance_form"):
        for d in sorted(selected_dates):
            date_str = d.strftime("%A, %b %d, %Y")
            
            with st.container(border=True):
                st.markdown(f"**📅 {date_str}**")
                col_status, col_time = st.columns([1, 1])
                with col_status:
                    ntype = st.selectbox("Status", options, key=f"type_{d}")
                with col_time:
                    time_info = st.text_input(
                        "Time Details", 
                        placeholder="e.g., 10:30 AM / Leaving 2 PM", 
                        key=f"time_{d}"
                    )
                    
                date_entries.append({
                    "date": d,
                    "type": ntype,
                    "time_info": time_info.strip()
                })

        st.markdown("---")
        reason = st.text_area("Reason / Context", placeholder="Brief explanation for your shift adjustment...")
        submitted = st.form_submit_button("Submit Notification", type="primary", use_container_width=True)

        if submitted:
            # Validation
            validation_error = None
            if not worker_name.strip():
                validation_error = "Please enter your name."
            elif not reason.strip():
                validation_error = "Please provide a reason/context."
            else:
                for entry in date_entries:
                    if entry["type"] in ["Late", "Leave Early"] and not entry["time_info"]:
                        validation_error = f"Time details required for {entry['date'].strftime('%b %d')} ({entry['type']})."
                        break

            if validation_error:
                st.error(validation_error)
            else:
                if notify_slack(worker_name, date_entries, reason):
                    st.success(f"Notification successfully sent to Slack for {worker_name}!")
else:
    st.info("Please click and select at least one date from the calendar widget above.")
