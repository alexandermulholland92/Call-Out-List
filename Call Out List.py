import streamlit as st
import requests
import json

st.set_page_config(page_title="Slack Notifier", page_icon="💬")
st.title("Send Message to Slack")

# 1. Retrieve the webhook URL securely
try:
    WEBHOOK_URL = st.secrets["SLACK_WEBHOOK_URL"]
except KeyError:
    st.error("Configuration Error: SLACK_WEBHOOK_URL is missing from Streamlit secrets.")
    st.stop()

# 2. Build the interface
message_text = st.text_area("Message", placeholder="Enter the update to send to the team...")

# 3. Execute the webhook
if st.button("Send to Slack"):
    if not message_text.strip():
        st.warning("Message cannot be empty.")
    else:
        payload = {
            "text": message_text
        }
        
        try:
            response = requests.post(
                WEBHOOK_URL, 
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'}
            )
            
            # Verify execution
            if response.status_code == 200:
                st.success("Message delivered successfully.")
            else:
                st.error(f"Delivery failed. HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            st.error(f"System error: {e}")
