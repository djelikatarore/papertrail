import resend

from app.config.settings import EMAIL_FROM, RESEND_API_KEY
from app.utils.email_templates import reset_password_email_html


def send_reset_password_email(to_email: str, reset_link: str) -> None:
    resend.api_key = RESEND_API_KEY
    resend.Emails.send({
        "from": EMAIL_FROM,
        "to": [to_email],
        "subject": "Réinitialisez votre mot de passe PaperTrail",
        "html": reset_password_email_html(reset_link),
    })
