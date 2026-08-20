import os
import requests
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# Configure via environment variable in production
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/YOUR/WEBHOOK/URL")

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
    except requests.exceptions.RequestException as e:
        print(f"Slack webhook execution failed: {e}")

@app.route("/", methods=["GET"])
def index():
    """Serves the baseline frontend for attendance notifications."""
    html_interface = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Attendance Notification</title>
        <script>
            function toggleETA() {
                var type = document.getElementById("notification_type").value;
                var etaInput = document.getElementById("eta_input");
                if (type === "Late") {
                    etaInput.style.display = "block";
                    etaInput.required = true;
                } else {
                    etaInput.style.display = "none";
                    etaInput.required = false;
                }
            }
        </script>
    </head>
    <body style="font-family: sans-serif; max-width: 400px; margin: 2rem auto;">
        <h2>Attendance Update</h2>
        <form action="/notify" method="POST">
            <input type="text" name="worker_name" placeholder="Team Member Name" required style="width: 100%; margin-bottom: 1rem; padding: 0.5rem; box-sizing: border-box;" />
            
            <select name="notification_type" id="notification_type" onchange="toggleETA()" style="width: 100%; margin-bottom: 1rem; padding: 0.5rem; box-sizing: border-box;">
                <option value="Late">Running Late</option>
                <option value="Call Out">Call Out (Absent)</option>
            </select>
            
            <input type="text" name="eta" id="eta_input" placeholder="ETA (e.g., 10:30 AM or 'in 15 mins')" required style="width: 100%; margin-bottom: 1rem; padding: 0.5rem; box-sizing: border-box;" />
            
            <textarea name="reason" placeholder="Reason / Context" required style="width: 100%; height: 80px; margin-bottom: 1rem; padding: 0.5rem; box-sizing: border-box;"></textarea>
            
            <button type="submit" style="width: 100%; padding: 0.75rem; background: #000; color: #fff; border: none; cursor: pointer;">Submit Notification</button>
        </form>
    </body>
    </html>
    """
    return render_template_string(html_interface)

@app.route("/notify", methods=["POST"])
def notify():
    """Handles the form submission and executes the Slack payload."""
    worker_name = request.form.get("worker_name")
    notification_type = request.form.get("notification_type")
    reason = request.form.get("reason")
    eta = request.form.get("eta", "")
    
    # Validate base fields
    if not worker_name or not notification_type or not reason:
        return jsonify({"error": "Missing required fields"}), 400
        
    # Validate ETA if running late
    if notification_type == "Late" and not eta:
        return jsonify({"error": "ETA is required when running late"}), 400

    # Execute Slack notification
    notify_slack(worker_name, notification_type, reason, eta)
    
    return jsonify({"message": f"Success. {notification_type} logged for {worker_name}."}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
