import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config.settings import EMAIL_FROM, GMAIL_ADDRESS, GMAIL_APP_PASSWORD, GMAIL_SMTP_HOST, GMAIL_SMTP_PORT
from app.utils.email_templates import (
    reset_password_email_html,
    verification_email_html,
    workspace_invitation_email_html,
)


def _send_email(to_email: str, subject: str, html_body: str) -> None:
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = EMAIL_FROM
    message["To"] = to_email
    message.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT) as server:
        server.starttls()
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, [to_email], message.as_string())


def send_reset_password_email(to_email: str, reset_link: str) -> None:
    _send_email(to_email, "Réinitialisez votre mot de passe PaperTrail", reset_password_email_html(reset_link))


def send_verification_email(to_email: str, verify_link: str) -> None:
    """Raises (smtplib.SMTPException and friends) on immediate SMTP
    rejection — e.g. a nonexistent domain — which signup() in auth_router.py
    uses to reject the signup outright. A genuine async bounce (mailbox
    doesn't exist on an otherwise valid domain) happens after this call
    already returned successfully and can't be caught here — see the plan
    discussed with the user."""
    _send_email(to_email, "Confirmez votre email PaperTrail", verification_email_html(verify_link))


def send_workspace_invitation_email(to_email: str, workspace_name: str, join_link: str) -> None:
    _send_email(
        to_email,
        f"Invitation à rejoindre {workspace_name} sur PaperTrail",
        workspace_invitation_email_html(workspace_name, join_link),
    )
