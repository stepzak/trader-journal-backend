import smtplib
from email.message import EmailMessage
from email.mime.text import MIMEText
from dotenv import load_dotenv
from celery import Celery

cel = Celery("tasks", broker="redis://localhost:6379")


@cel.task
def send_email(uid, mail: str):
    msg = EmailMessage()
    msg["To"] = mail
    msg["From"] = 'Служба поддержки'
    msg["Subject"] = "Восстановление пароля"
    msg.set_content("Код для восстановления пароля: " + uid)
    s = smtplib.SMTP(os.getenv("SMTP_SERVER")), int(os.getenv("SMTP_PORT")))
    s.starttls()
    s.ehlo()
    s.login(os.getenv("SMTP_LOGIN"), os.getenv("SMTP_PASSWORD"))
    s.sendmail((os.getenv("SMTP_LOGIN"),[mail], msg.as_string())
    s.quit()
    return {"status": "success"}
