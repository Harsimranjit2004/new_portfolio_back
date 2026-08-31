from ..schemas import ContactCreate
from ..services.email_service import send_contact_email


def main() -> None:
    sent = send_contact_email(ContactCreate(
        name="Portfolio deployment test",
        email="test@example.com",
        topic="Gmail SMTP verification",
        message="If you received this message, portfolio contact email delivery is configured correctly.",
        website="",
    ))
    if not sent:
        raise SystemExit("Email was not sent. Check the SMTP configuration and backend logs.")
    print("Test email sent successfully.")


if __name__ == "__main__":
    main()
