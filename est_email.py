# # test_email.py (run: python test_email.py)
# from app.utils.email import send_email
# from flask import Flask

# app = Flask(__name__)
# app.config["RESEND_API_KEY"] = "re_8NSK6X4u_JgWVTHLY1xXoAsaCoA3n9Hpr"  # Temp for test (mask!)
# with app.app_context():
#     success = send_email("Test OTP", "ndiyoedward@gmail.com", "Code: 123456")
#     print(f"Success: {success}")


# test_email.py
from app import create_app  # ← Import create_app
from app.utils.email import send_email

import os

# Set env vars
os.environ["RESEND_API_KEY"] = "re_8NSK6X4u_JgWVTHLY1xXoAsaCoA3n9Hpr"
os.environ["MAIL_DEFAULT_SENDER"] = "no-reply@nationalcake.ng"

# Create app + context
app = create_app()
with app.app_context():
    success = send_email(
        subject="Test OTP",
        to_email="ndiyoedward@icloud.com",
        body="Your code is: 123456",
    )
    print(f"Success: {success}")
