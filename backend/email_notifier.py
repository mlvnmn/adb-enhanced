"""
Layer 4: Email Alert Notifier
SMTP email sender for HIGH/CRITICAL forensic alerts.
Configured via environment variables for security.
"""
import os
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


# Configuration from environment variables
SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASS = os.environ.get('SMTP_PASS', '')
ALERT_RECIPIENT = os.environ.get('ALERT_RECIPIENT', '')
SENDER_NAME = 'ADB Forensic Monitor'

# Rate limiting: max 1 email per 5 minutes
_last_email_time = 0
RATE_LIMIT_SECONDS = 300


def is_configured():
    """Check if SMTP is configured."""
    return bool(SMTP_USER and SMTP_PASS and ALERT_RECIPIENT)


def send_alert_email(alert_type, description, severity='HIGH', device_info=None):
    """
    Send an HTML-formatted alert email.
    Returns True on success, False on failure.
    """
    global _last_email_time

    if not is_configured():
        print("[EMAIL] SMTP not configured — skipping email alert")
        return False

    # Rate limiting
    now = time.time()
    if now - _last_email_time < RATE_LIMIT_SECONDS:
        print("[EMAIL] Rate limited — skipping email")
        return False

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'[{severity}] ADB Forensic Alert: {alert_type}'
        msg['From'] = f'{SENDER_NAME} <{SMTP_USER}>'
        msg['To'] = ALERT_RECIPIENT

        # Build HTML email
        severity_colors = {
            'LOW': '#10b981',
            'MEDIUM': '#f59e0b',
            'HIGH': '#f97316',
            'CRITICAL': '#ef4444',
        }
        color = severity_colors.get(severity, '#ef4444')

        device_html = ''
        if device_info:
            device_html = f"""
            <tr>
                <td style="padding:8px;color:#94a3b8;">Device</td>
                <td style="padding:8px;font-family:monospace;">{device_info.get('model', 'Unknown')} ({device_info.get('serial', 'N/A')})</td>
            </tr>
            """

        html = f"""
        <html>
        <body style="background:#070b0f;color:#e0e6ed;font-family:Inter,Arial,sans-serif;padding:24px;">
            <div style="max-width:600px;margin:0 auto;background:#10171e;border:1px solid rgba(0,242,255,0.1);border-radius:12px;overflow:hidden;">
                <div style="background:{color};padding:16px 24px;">
                    <h2 style="margin:0;color:white;font-size:1.1rem;">⚠ FORENSIC ALERT — {severity}</h2>
                </div>
                <div style="padding:24px;">
                    <h3 style="color:#00f2ff;margin:0 0 12px 0;">{alert_type}</h3>
                    <p style="color:#e0e6ed;line-height:1.6;">{description}</p>
                    <table style="width:100%;border-collapse:collapse;margin-top:16px;">
                        <tr>
                            <td style="padding:8px;color:#94a3b8;">Timestamp</td>
                            <td style="padding:8px;font-family:monospace;">{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</td>
                        </tr>
                        <tr>
                            <td style="padding:8px;color:#94a3b8;">Severity</td>
                            <td style="padding:8px;"><span style="background:{color};color:white;padding:2px 10px;border-radius:4px;font-size:0.8rem;font-weight:700;">{severity}</span></td>
                        </tr>
                        {device_html}
                    </table>
                </div>
                <div style="padding:16px 24px;border-top:1px solid rgba(255,255,255,0.05);font-size:0.75rem;color:#64748b;">
                    Enhanced ADB Forensic Monitor — Automated Alert System
                </div>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html, 'html'))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, [ALERT_RECIPIENT], msg.as_string())

        _last_email_time = time.time()
        print(f"[EMAIL] Alert sent: {alert_type} ({severity})")
        return True

    except Exception as e:
        print(f"[EMAIL] Failed to send: {e}")
        return False
