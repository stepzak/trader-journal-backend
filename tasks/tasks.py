import smtplib
from email.message import EmailMessage
from email.mime.text import MIMEText

from celery import Celery

cel = Celery("tasks", broker="redis://localhost:6379")


@cel.task
def send_email(uid, mail: str):
    msg = EmailMessage()
    msg["To"] = mail
    msg["From"] = 'Служба поддержки'
    msg["Subject"] = "Восстановление пароля"
    msg.set_content("Код для восстановления пароля: " + uid)
    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.starttls()
    s.ehlo()
    s.login('newbinancetest@gmail.com', "pyznbdytqydrjkfe")
    s.sendmail('newbinancetest@gmail.com',[mail], msg.as_string())
    s.quit()
    return {"status": "success"}
