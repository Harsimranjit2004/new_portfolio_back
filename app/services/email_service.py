import logging
import smtplib
from email.message import EmailMessage

from ..config import get_settings
from ..schemas import ContactCreate

logger = logging.getLogger(__name__)


def send_contact_email(contact: ContactCreate) -> bool:
    settings = get_settings()
    if not settings.smtp_host or not settings.contact_to or not settings.smtp_from:
        logger.info("Contact email not sent because SMTP is not configured")
        return False

    message = EmailMessage()
    message["Subject"] = f"Portfolio contact: {contact.topic}"
    message["From"] = settings.smtp_from
    message["To"] = settings.contact_to
    message["Reply-To"] = str(contact.email)
    message.set_content(
        f"Name: {contact.name}\nEmail: {contact.email}\nTopic: {contact.topic}\n\n{contact.message}"
    )

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException):
        logger.exception("Failed to deliver portfolio contact email")
        return False

    logger.info("Portfolio contact email delivered to %s", settings.contact_to)
    return True
