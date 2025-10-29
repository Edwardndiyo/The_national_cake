# verify_sender.py
# One-time script to verify your sender email with Resend
# Run: python verify_sender.py

import os
import resend
from dotenv import load_dotenv

# Load .env (make sure RESEND_API_KEY is in your .env)
load_dotenv()

api_key = os.getenv("RESEND_API_KEY")
if not api_key:
    print("❌ RESEND_API_KEY not found in .env")
    exit(1)

# Initialize Resend SDK
resend.api_key = api_key  # ← This is the correct way

sender_email = "no-reply@nationalcake.ng"

print(f"📧 Sending verification email to {sender_email}...")

try:
    # Resend sends a verification email when you try to send from an unverified address
    response = resend.Emails.send(
        {
            "from": "onboarding@resend.dev",  # Must use this for first send
            "to": [sender_email],
            "subject": "Verify your sender email",
            "text": "Please verify your email to send from no-reply@nationalcake.ng",
        }
    )

    print("✅ Verification email sent!")
    print("   → Check your inbox at:", sender_email)
    print("   → Click the verification link from Resend.")
    print("   → Once clicked, you can use this sender in production.")

except Exception as e:
    print("❌ Failed to send verification email:")
    print(e)
    print("\nTry this fallback:")
    print("   → Set MAIL_DEFAULT_SENDER=onboarding@resend.dev in Render")
    print("   → It works instantly, no verification needed.")
