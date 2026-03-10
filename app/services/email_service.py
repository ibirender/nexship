# app/email.py

import smtplib, os
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# LOAD .env FILE
load_dotenv()

MAIL_HOST = os.getenv("MAIL_HOST")
MAIL_PORT = int(os.getenv("MAIL_PORT"))
MAIL_USER = os.getenv("MAIL_USER")
MAIL_PASS = os.getenv("MAIL_PASS")


def send_reset_email(to_email: str, otp: str):

    subject = "🔐 Your Password Reset OTP"

    html_content = f"""
    <h2>Password Reset OTP</h2>
    <p>Your OTP is:</p>
    <h1>{otp}</h1>
    <p>This OTP expires in 10 minutes.</p>
    """

    text_content = f"""
    Password Reset OTP
    Your OTP is: {otp}
    """

    msg = MIMEMultipart("alternative")
    msg["From"] = MAIL_USER
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(text_content, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP(MAIL_HOST, MAIL_PORT) as server:
            server.starttls()
            server.login(MAIL_USER, MAIL_PASS)
            server.send_message(msg)

        print("Email sent successfully")
        return True

    except Exception as e:
        print("Email error:", e)
        return False