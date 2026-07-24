import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config.settings import EMAIL_FROM, GMAIL_ADDRESS, GMAIL_APP_PASSWORD, GMAIL_SMTP_HOST, GMAIL_SMTP_PORT
from app.utils.email_templates import reset_password_email_html


def send_reset_password_email(to_email: str, reset_link: str) -> None:
    message = MIMEMultipart("alternative")
    message["Subject"] = "Réinitialisez votre mot de passe PaperTrail"
    message["From"] = EMAIL_FROM
    message["To"] = to_email
    message.attach(MIMEText(reset_password_email_html(reset_link), "html"))

    with smtplib.SMTP(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT) as server:
        server.starttls()
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, [to_email], message.as_string())
