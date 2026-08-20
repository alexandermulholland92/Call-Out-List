import streamlit as st
import requests
import json
from datetime import datetime

st.set_page_config(page_title="Call-Out Portal", page_icon="🚨")
st.title("Log a Call-Out")

# 1. Retrieve the webhook securely
try:
    WEBHOOK_URL = st.secrets["SLACK_WEBHOOK_URL"]
except KeyError:
    st.error("Configuration Error: SLACK_WEBHOOK_URL is missing from Streamlit secrets.")
    st.stop()

# 2. Build the operational interface
team_members = [
    "Harrison", "Malavika St", "Michael Renteria", 
    "Ana Sedic", "Koby", "Evan", "Other"
]

with st.form("call_out_form"):
    employee = st.selectbox("Team Member", team_members)
    reason = st.selectbox("Reason", ["Sick", "Personal Emergency", "Running Late", "No Call / No Show"])
    details = st.text_area("Additional Context", placeholder="e.g., Covering shift with...")
    
    submitted = st.form_submit_button("Notify Team")

# 3. Execute the webhook
if submitted:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Format the Slack message
    slack_message = f"🚨 *Call-Out Logged*\n*Team Member:* {employee}\n*Reason:* {reason}\n*Time:* {timestamp}"
    if details.strip():
        slack_message += f"\n*Notes:* {details}"

    payload = {"text": slack_message}
    
    try:
        response = requests.post(
            WEBHOOK_URL, 
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            st.success(f"Call-out for {employee} broadcasted successfully.")
        else:
            st.error(f"Delivery failed. HTTP {response.status_code}: {response.text}")
            
    except Exception as e:
        st.error(f"System error: {e}")
