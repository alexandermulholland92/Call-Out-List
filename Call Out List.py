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

# Initialize session state
if "date_entries" not in st.session_state:
    st.session_state.date_entries = {}

if "last_submission" not in st.session_state:
    st.session_state.last_submission = None

# Show persistent confirmation alert upon successful submission
if st.session_state.last_submission:
    sub = st.session_state.last_submission
    st.success(f"🎉 **Attendance Notice Submitted Successfully!**\n\nNotification sent to Slack for **{sub['name']}** covering **{sub['count']} date(s)** ({sub['dates_str']}).")
    st.balloons()
    if st.button("Dismiss Confirmation", type="secondary"):
        st.session_state.last_submission = None
        st.rerun()

# --- STEP 1: TEAM MEMBER NAME ---
worker_name = st.text_input("Team Member Name", placeholder="e.g. John Doe")

# --- STEP 2: SELECT STATUS THEN DATE ---
st.markdown("---")
st.subheader("1. Add Date Entry")

options = ["Call Out (Full Day)", "Call Out AM", "Call Out PM", "Late", "Leave Early"]

# Status selection right before the date picker
selected_status = st.selectbox("Status / Action", options)

col_cal, col_add, col_clear = st.columns([2, 1, 1])

with col_cal:
    picked_dates = st.date_input(
        "Select Date or Date Range", 
        value=() # Empty tuple starts calendar unselected
    )
    
with col_add:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    if st.button("➕ Add Date(s)", type="primary", use_container_width=True):
        st.session_state.last_submission = None
        
        if picked_dates:
            dates_to_add = []
            if len(picked_dates) == 1:
                dates_to_add.append(picked_dates[0])
            elif len(picked_dates) == 2:
                start_date, end_date = picked_dates
                delta = end_date - start_date
                for i in range(delta.days + 1):
                    dates_to_add.append(start_date + timedelta(days=i))

            for d in dates_to_add:
                # Store entry mapped by date with pre-selected status
                st.session_state.date_entries[d] = {
                    "type": selected_status,
                    "time_info": ""
                }

            st.rerun()
        else:
            st.warning("Please select a date on the calendar first.")

with col_clear:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    if st.button("🗑️ Clear All", type="secondary", use_container_width=True):
        st.session_state.date_entries = {}
        st.session_state.last_submission = None
        st.rerun()

# --- STEP 3: CONFIGURE EACH DATE & SUBMIT ---
st.markdown("---")
st.subheader("2. Configured Dates & Details")

if st.session_state.date_entries:
    final_entries = []
    
    for d in sorted(st.session_state.date_entries.keys()):
        date_str = d.strftime("%A, %b %d, %Y")
        saved_entry = st.session_state.date_entries[d]
        
        with st.container(border=True):
            col_head, col_del = st.columns([5, 1])
            with col_head:
                st.markdown(f"**📅 {date_str}**")
            with col_del:
                if st.button("❌ Remove", key=f"del_{d}", use_container_width=True):
                    del st.session_state.date_entries[d]
                    st.rerun()

            col_status, col_time = st.columns([1, 1])
            with col_status:
                current_status_idx = options.index(saved_entry["type"]) if saved_entry["type"] in options else 0
                ntype = st.selectbox("Status", options, index=current_status_idx, key=f"type_{d}")
            with col_time:
                time_info = st.text_input(
                    "Time Details", 
                    value=saved_entry["time_info"],
                    placeholder="e.g., 10:30 AM / Leaving 2 PM", 
                    key=f"time_{d}"
                )
                
            final_entries.append({
                "date": d,
                "type": ntype,
                "time_info": time_info.strip()
            })

    st.markdown("<br>", unsafe_allow_html=True)
    reason = st.text_area("Reason / Context", placeholder="Brief explanation for your shift adjustment...")
    
    if st.button("Submit Notification", type="primary", use_container_width=True):
        st.session_state.last_submission = None
        
        # Validation
        validation_error = None
        if not worker_name.strip():
            validation_error = "Please enter your name."
        elif not reason.strip():
            validation_error = "Please provide a reason/context."
        else:
            for entry in final_entries:
                if entry["type"] in ["Late", "Leave Early"] and not entry["time_info"]:
                    validation_error = f"Time details required for {entry['date'].strftime('%b %d')} ({entry['type']})."
                    break

        if validation_error:
            st.error(validation_error)
        else:
            if notify_slack(worker_name, final_entries, reason):
                dates_formatted = ", ".join([e["date"].strftime("%b %d") for e in final_entries])
                st.session_state.last_submission = {
                    "name": worker_name,
                    "count": len(final_entries),
                    "dates_str": dates_formatted
                }
                st.session_state.date_entries = {}
                st.rerun()
else:
    st.info("No dates added yet. Choose a status, pick date(s) on the calendar, and click **➕ Add Date(s)**.")
