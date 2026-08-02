from email.message import EmailMessage
import smtplib
import os
def send_email(to, cc, subject, body, attachment_bytes=None, attachment_filename="dinh_kem.zip"):
    EMAIL_ACCOUNT = os.getenv("GMAIL_USER")
    APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.getenv("GMAIL_USER")
    msg["To"] = to
    if cc:
        msg["Cc"] = cc
    msg.set_content(body)
    if attachment_bytes:
        msg.add_attachment(
            attachment_bytes,
            maintype="application",
            subtype="zip",
            filename=attachment_filename
        )
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_ACCOUNT, APP_PASSWORD)
        server.send_message(msg)

    print("Đã gửi email thành công!")