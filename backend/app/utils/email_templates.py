def reset_password_email_html(reset_link: str) -> str:
    return f"""\
<!DOCTYPE html>
<html>
  <body style="margin:0; padding:0; background-color:#ffffff; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#ffffff;">
      <tr>
        <td align="center" style="padding:40px 20px;">
          <table role="presentation" width="480" cellpadding="0" cellspacing="0" style="max-width:480px;">
            <tr>
              <td style="padding-bottom:32px;">
                <span style="font-size:24px; font-weight:700; color:#7C3AED;">PaperTrail</span>
              </td>
            </tr>
            <tr>
              <td style="color:#111111; font-size:16px; line-height:1.5;">
                <p style="margin:0 0 16px 0;">Bonjour,</p>
                <p style="margin:0 0 24px 0;">
                  Une demande de réinitialisation de mot de passe a été effectuée pour ce compte.
                  Cliquez sur le bouton ci-dessous pour choisir un nouveau mot de passe.
                  Ce lien expire dans 30 minutes.
                </p>
              </td>
            </tr>
            <tr>
              <td align="center" style="padding:8px 0 32px 0;">
                <a href="{reset_link}"
                   style="background-color:#7C3AED; color:#ffffff; text-decoration:none;
                          font-size:16px; font-weight:600; padding:14px 32px;
                          border-radius:8px; display:inline-block;">
                  Réinitialiser mon mot de passe
                </a>
              </td>
            </tr>
            <tr>
              <td style="color:#666666; font-size:13px; line-height:1.5;">
                <p style="margin:0;">
                  Si vous n'êtes pas à l'origine de cette demande, vous pouvez ignorer cet email.
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""
