import streamlit as st
import requests
import os
from datetime import date, timedelta

# Fetch Slack Webhook URL from Streamlit Secrets or Environment Variables
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
    color = "#FF3B30" if has_call_out else "#FF9500"  # Red if call out, Orange if late/leaving early

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

# --- UI Layout ---
st.title("Attendance Update")
st.write("Submit call outs or attendance notices directly to Slack.")

worker_name = st.text_input("Team Member Name", placeholder="e.g. John Doe")

# Generate rolling window of dates
today = date.today()
available_dates = [today + timedelta(days=i) for i in range(-3, 60)]

selected_dates = st.multiselect(
    "1. Select Date(s)",
    options=available_dates,
    default=[today],
    format_func=lambda d: d.strftime("%a, %b %d, %Y")
)

if selected_dates:
    st.subheader("2. Configure Status per Date")
    
    with st.form("attendance_form"):
        date_entries = []
        options = ["Call Out (Full Day)", "Call Out AM", "Call Out PM", "Late", "Leave Early"]
        
        for d in sorted(selected_dates):
            date_str = d.strftime("%a, %b %d, %Y")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                ntype = st.selectbox(
                    f"{date_str}", 
                    options, 
                    key=f"type_{d}"
                )
            with col2:
                time_info = st.text_input(
                    f"Time Details ({date_str})", 
                    placeholder="ETA / Departure Time (if applicable)", 
                    key=f"time_{d}"
                )
                
            date_entries.append({
                "date": d,
                "type": ntype,
                "time_info": time_info.strip()
            })

        st.markdown("---")
        reason = st.text_area("Reason / Context", placeholder="Brief reason for the schedule adjustment...")
        submitted = st.form_submit_button("Submit Notification", type="primary")

        if submitted:
            # Validation
            validation_error = None
            if not worker_name.strip():
                validation_error = "Please enter a Team Member Name."
            elif not reason.strip():
                validation_error = "Please enter a Reason / Context."
            else:
                for entry in date_entries:
                    if entry["type"] in ["Late", "Leave Early"] and not entry["time_info"]:
                        validation_error = f"Time details are required for {entry['date'].strftime('%b %d')} ({entry['type']})."
                        break

            if validation_error:
                st.error(validation_error)
            else:
                success = notify_slack(worker_name, date_entries, reason)
                if success:
                    st.success(f"Success! Attendance update logged for {worker_name}.")
