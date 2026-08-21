import os
import uuid
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

def notify_slack(worker_name, bundles, reason):
    """Pushes formatted multi-date attendance data to Slack."""
    schedule_lines = []
    has_call_out = False
    
    for bundle in bundles:
        start_d = bundle["start_date"]
        end_d = bundle["end_date"]
        
        # Format the date text based on whether it's a single day or a range
        if start_d == end_d:
            d_str = start_d.strftime("%a, %b %d, %Y")
        else:
            d_str = f"{start_d.strftime('%a, %b %d')} ➔ {end_d.strftime('%a, %b %d, %Y')}"
            
        ntype = bundle["type"]
        time_info = bundle["time_info"]
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

# Initialize session state for bundled dates
if "bundles" not in st.session_state:
    st.session_state.bundles = []

if "last_submission" not in st.session_state:
    st.session_state.last_submission = None

if "cal_key" not in st.session_state:
    st.session_state.cal_key = 0

# Show persistent confirmation alert upon successful submission
if st.session_state.last_submission:
    sub = st.session_state.last_submission
    st.success(f"🎉 **Attendance Notice Submitted Successfully!**\n\nNotification sent to Slack for **{sub['name']}** covering **{sub['count']} total date(s)**.")
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
selected_status = st.selectbox("Status / Action", options)

# Split into two robust Start & End date pickers
col_start, col_end = st.columns(2)
with col_start:
    start_date = st.date_input("Start Date", value=None, key=f"start_{st.session_state.cal_key}")
with col_end:
    end_date = st.date_input("End Date (Optional)", value=None, help="Leave blank for a single day.", key=f"end_{st.session_state.cal_key}")

col_add, col_clear = st.columns([3, 1])
with col_add:
    if st.button("➕ Add Date(s)", type="primary", use_container_width=True):
        st.session_state.last_submission = None
        
        if start_date:
            actual_end = end_date if end_date else start_date
            
            if actual_end < start_date:
                st.error("End Date cannot be before the Start Date.")
            else:
                # Add the date block as ONE single bundle instead of splitting it up
                st.session_state.bundles.append({
                    "id": str(uuid.uuid4()), # Generate a unique ID for the UI
                    "start_date": start_date,
                    "end_date": actual_end,
                    "type": selected_status,
                    "time_info": ""
                })

                # Increment key to completely reset the calendar widgets to blank
                st.session_state.cal_key += 1
                st.rerun()
        else:
            st.warning("Please select a Start Date first.")

with col_clear:
    if st.button("🗑️ Clear All", type="secondary", use_container_width=True):
        st.session_state.bundles = []
        st.session_state.last_submission = None
        st.session_state.cal_key += 1
        st.rerun()

# --- STEP 3: CONFIGURE EACH BUNDLE & SUBMIT ---
st.markdown("---")
st.subheader("2. Configured Dates & Details")

if st.session_state.bundles:
    final_bundles = []
    
    # Loop through each bundled date block
    for bundle in st.session_state.bundles:
        b_id = bundle["id"]
        start_d = bundle["start_date"]
        end_d = bundle["end_date"]
        
        # Display nicely based on if it's a single day or a range
        if start_d == end_d:
            ui_date_label = f"**📅 {start_d.strftime('%A, %b %d, %Y')}**"
        else:
            ui_date_label = f"**📅 {start_d.strftime('%a, %b %d')} ➔ {end_d.strftime('%a, %b %d, %Y')}**"
        
        with st.container(border=True):
            col_head, col_del = st.columns([5, 1])
            with col_head:
                st.markdown(ui_date_label)
            with col_del:
                # If deleted, remove this bundle's ID from the session state list
                if st.button("❌ Remove", key=f"del_{b_id}", use_container_width=True):
                    st.session_state.bundles = [b for b in st.session_state.bundles if b["id"] != b_id]
                    st.rerun()

            col_status, col_time = st.columns([1, 1])
            with col_status:
                current_status_idx = options.index(bundle["type"]) if bundle["type"] in options else 0
                ntype = st.selectbox("Status", options, index=current_status_idx, key=f"type_{b_id}")
            with col_time:
                time_info = st.text_input(
                    "Time Details", 
                    value=bundle["time_info"],
                    placeholder="e.g., 10:30 AM / Leaving 2 PM", 
                    key=f"time_{b_id}"
                )
                
            # Collect current states for submission
            final_bundles.append({
                "start_date": start_d,
                "end_date": end_d,
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
            for bundle in final_bundles:
                if bundle["type"] in ["Late", "Leave Early"] and not bundle["time_info"]:
                    # Create a friendly error text
                    err_lbl = bundle['start_date'].strftime('%b %d') if bundle['start_date'] == bundle['end_date'] else f"{bundle['start_date'].strftime('%b %d')} to {bundle['end_date'].strftime('%b %d')}"
                    validation_error = f"Time details required for {err_lbl} ({bundle['type']})."
                    break

        if validation_error:
            st.error(validation_error)
        else:
            # PUSH TO SLACK
            if notify_slack(worker_name, final_bundles, reason):
                # Calculate total number of actual days covered
                total_days = sum((b["end_date"] - b["start_date"]).days + 1 for b in final_bundles)
                
                st.session_state.last_submission = {
                    "name": worker_name,
                    "count": total_days
                }
                
                st.session_state.bundles = []
                st.session_state.cal_key += 1
                st.rerun()
else:
    st.info("No dates added yet. Choose a status, pick a Start Date, and click **➕ Add Date(s)**.")
