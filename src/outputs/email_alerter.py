import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.models import Article


def send_alert(article: Article, urgency_score: float, reasoning: str) -> None:
    from src.config import settings
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🚨 Alerta Los Calderas [{urgency_score}/10]: {article.title[:60]}"
    msg["From"] = settings.GMAIL_USER
    msg["To"] = settings.ALERT_EMAIL

    body = f"""ALERTA DE NOTICIA URGENTE — Los Calderas Bot

Urgencia: {urgency_score}/10
Fuente: {article.source}

TÍTULO:
{article.title}

RESUMEN:
{article.summary}

URL:
{article.url}

POR QUÉ ES RELEVANTE PARA EL CANAL:
{reasoning}

---
Los Calderas Bot — GitHub Actions
""".strip()

    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(settings.GMAIL_USER, settings.GMAIL_APP_PASSWORD)
        server.send_message(msg)
