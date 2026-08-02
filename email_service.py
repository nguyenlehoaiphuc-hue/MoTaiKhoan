from email.message import EmailMessage
import smtplib
import os
def send_email(to,cc,subject,body, attachment_bytes=None):
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
            subtype="vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename="mo_tai_khoan.docx"
        )
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_ACCOUNT, APP_PASSWORD)
        server.send_message(msg)
    print("Đã gửi email thành công!")