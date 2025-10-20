"""Email sending module."""
import asyncio
from typing import Optional
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import aiosmtplib
from sqlalchemy.ext.asyncio import AsyncSession

from database import FileRecord
from config import settings
from watcher import log_audit


async def send_email(
    record: FileRecord,
    db: AsyncSession,
    recipient: str,
    subject: str = "Ваш результат анализа готов",
    body: Optional[str] = None
) -> bool:
    """Send email with PDF attachment."""
    try:
        if not body:
            body = f"""
Здравствуйте!

Ваш результат анализа (номер исследования: {record.order_no}) готов.

Результаты прикреплены к данному письму.

С уважением,
Медицинский центр
"""
        
        # Create message
        message = MIMEMultipart()
        message['From'] = settings.SMTP_FROM
        message['To'] = recipient
        message['Subject'] = subject
        
        # Add body
        message.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # Attach PDF
        file_path = Path(record.file_path)
        if file_path.exists():
            with open(file_path, 'rb') as f:
                pdf_attachment = MIMEApplication(f.read(), _subtype='pdf')
                pdf_attachment.add_header(
                    'Content-Disposition',
                    'attachment',
                    filename=record.file_name
                )
                message.attach(pdf_attachment)
        
        # Send email
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            use_tls=settings.SMTP_USE_TLS
        )
        
        await log_audit(
            db, record.id, "email_sent", "success",
            f"Email sent to {recipient}"
        )
        
        print(f"[Mailer] ✓ Email sent to {recipient} for order {record.order_no}")
        return True
        
    except Exception as e:
        await log_audit(
            db, record.id, "email_sent", "error",
            f"Failed to send email: {str(e)}"
        )
        print(f"[Mailer] ✗ Failed to send email: {e}")
        return False

