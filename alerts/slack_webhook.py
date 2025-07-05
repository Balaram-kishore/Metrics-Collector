import requests

def send_slack_alert(message):
    webhook_url = "YOUR_SLACK_WEBHOOK_URL"
    payload = {"text": f"🚨 ALERT: {message}"}
    requests.post(webhook_url, json=payload)