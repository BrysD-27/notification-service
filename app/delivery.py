import asyncio
import smtplib
from email.message import EmailMessage
from datetime import datetime, timezone
from .models import EnqueuedNotification
import os

GMAIL_ADDRESS = "brysondavis65@gmail.com"
GMAIL_APP_PASSWORD = "lprt hsqj jonj fpaq"


def now_utc():
    """Return current UTC."""
    return datetime.now(timezone.utc)


def _send_email_sync(to_email: str, subject: str, body: str):
    """Blocking function that sends email using Gmail SMTP."""
    msg = EmailMessage()
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = subject or "(No subject)"
    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        smtp.send_message(msg)


async def deliver_email(to_email: str, subject: str | None, body: str):
    """Async wrapper to deliver email using Gmail SMTP."""
    # Offload blocking SMTP work to a thread so FastAPI’s event loop stays responsive.
    await asyncio.to_thread(_send_email_sync, to_email, subject or "", body)
    print(f"Sent email to {to_email}")


async def deliver_sms(to_number: str, body: str):
    """"Deliver notification by SMS. Not implemented due to government regulation. Opt to log to console."""
    await asyncio.sleep(0)
    print(f"SMS {to_number}, body={body!r}")


async def deliver(notification: EnqueuedNotification):
    """Delivery entry method: Gather notification tasks."""
    tasks = []

    if "email" in notification.channels and notification.recipient.email:
        tasks.append(
            deliver_email(
                notification.recipient.email, notification.subject, notification.message
            )
        )

    if "sms" in notification.channels and notification.recipient.sms:
        # tasks.append(deliver_sms(notification.recipient.sms, notification.message))
        print("Skipping SMS")

    if not tasks:
        print(f"{notification.id} no reachable channels/recipients.")
        return

    await asyncio.gather(*tasks)
    print(f"Delivered {notification.id} at {now_utc().isoformat()}")
