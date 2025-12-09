import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import streamlit as st
import os

def send_email_with_attachments(to_email: str, subject: str, body: str, attachments: list = None):
    """
    Sends an email with optional attachments using SMTP credentials from st.secrets.
    
    Args:
        to_email (str): Recipient email address.
        subject (str): Email subject.
        body (str): Email body text (HTML supported if modified, currently plain text).
        attachments (list): List of dicts [{'name': 'filename.pdf', 'bytes': b'...'}]
    
    Returns:
        tuple: (bool, str) -> (Success, Message)
    """
    try:
        # Load secrets
        smtp_config = st.secrets["smtp"]
        smtp_server = smtp_config["server"]
        smtp_port = smtp_config["port"]
        smtp_user = smtp_config["user"]
        smtp_password = smtp_config["password"]
    except Exception as e:
        return False, f"Configuración SMTP faltante o incorrecta en secrets.toml: {e}"

    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    if attachments:
        for att in attachments:
            try:
                part = MIMEApplication(att['bytes'], Name=att['name'])
                part['Content-Disposition'] = f'attachment; filename="{att["name"]}"'
                msg.attach(part)
            except Exception as e:
                return False, f"Error adjuntando archivo {att.get('name', 'bqe')}: {e}"

    try:
        # Connect to server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        text = msg.as_string()
        server.sendmail(smtp_user, to_email, text)
        server.quit()
        return True, "Email enviado correctamente."
    except Exception as e:
        return False, f"Error enviando email: {e}"
