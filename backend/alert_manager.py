import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = os.getenv("SMTP_EMAIL")
SENDER_PASSWORD = os.getenv("SMTP_PASSWORD")

def send_otp_email(receiver_email: str, otp_code: str, purpose: str):
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        return False

    subject = "GuardianAI - Verification Code"
    body = f"Your 6-digit verification code is: {otp_code}\n\nDo not share this code with anyone."

    msg = MIMEMultipart()
    msg['From'] = f"GuardianAI Security <{SENDER_EMAIL}>"
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"SMTP Error: {e}")
        return False
def send_threat_alert_email(receiver_email: str, threat_type: str, confidence: float, timestamp: str):
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("CRITICAL: SMTP details missing.")
        return False

    subject = f"🚨 CRITICAL ALERT: {threat_type} Detected!"
    body = f"""
GUARDIAN-AI TACTICAL ALERT SYSTEM
---------------------------------
THREAT DETECTED: {threat_type.upper()}
CONFIDENCE: {confidence}%
TIMESTAMP: {timestamp}

Please check the GuardianAI Command Center immediately for the video snapshot.
    """

    msg = MIMEMultipart()
    msg['From'] = f"GuardianAI Security <{SENDER_EMAIL}>"
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"SUCCESS: Threat Alert sent to {receiver_email}")
        return True
    except Exception as e:
        print(f"SMTP Error: {e}")
        return False