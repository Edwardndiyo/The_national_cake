# # app/utils/email.py
# import os
# import resend
# from flask import current_app


# def send_email(subject: str, to_email: str, body: str, from_email: str = None):
#     """
#     Send email via Resend API (v0.9+).
#     """
#     api_key = os.getenv("RESEND_API_KEY")
#     if not api_key:
#         current_app.logger.warning("RESEND_API_KEY missing — email skipped")
#         return False

#     resend.api_key = api_key

#     sender = from_email or os.getenv("MAIL_DEFAULT_SENDER", "onboarding@resend.dev")

#     try:
#         response = resend.Emails.send(
#             from_=sender,  # ← CHANGE THIS TO: from=sender
#             to=[to_email],
#             subject=subject,
#             text=body,
#         )

#         # Log full response for debugging
#         current_app.logger.info(f"Resend response: {response}")

#         if response and response.get("id"):
#             current_app.logger.info(f"Email queued: {response['id']} → {to_email}")
#             return True
#         else:
#             current_app.logger.error(f"Resend failed (no ID): {response}")
#             return False

#     except Exception as e:
#         current_app.logger.error(f"Email exception: {str(e)}")
#         return False

# app/utils/email.py
import os
import resend  # Official import
from flask import current_app


def send_email(subject: str, to_email: str, body: str, from_email: str = None):
    """
    Send email via Resend API (v2.17.0+).

    Returns: True if queued (ID returned), False on fail.
    Secure: Env-only. Logs for debug. Fails gracefully.
    """
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        current_app.logger.warning("RESEND_API_KEY missing — email skipped")
        return False

    # v2.17.0: Module-level init
    resend.api_key = api_key

    sender = from_email or os.getenv("MAIL_DEFAULT_SENDER", "onboarding@resend.dev")

    # v2.17.0: Dict payload
    payload = {
        "from": sender,  # Plain 'from' in dict
        "to": [to_email],
        "subject": subject,
        "text": body,  # Plaintext; "html": body for styled
    }

    try:
        response = resend.Emails.send(payload)

        # Log full response
        current_app.logger.info(f"Resend response for {to_email}: {response}")

        # Success: Dict with 'id'
        if isinstance(response, dict) and "id" in response:
            current_app.logger.info(f"Email sent (ID: {response['id']}) to {to_email}")
            return True
        else:
            current_app.logger.error(f"Resend no ID: {response}")
            return False

    except Exception as e:
        current_app.logger.error(f"Email exception for {to_email}: {str(e)}")
        return False
