"""Email notification service — dev mode logs, production mode sends via SMTP."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from shared_config.settings import get_settings

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.settings = get_settings()
        self._is_configured = bool(self.settings.smtp_host)

    def _send(self, to: str, subject: str, html_body: str) -> None:
        if not self._is_configured:
            logger.info(
                "[email-dev] To: %s | Subject: %s | Body length: %d chars",
                to, subject, len(html_body),
            )
            return

        msg = MIMEMultipart("alternative")
        msg["From"] = self.settings.smtp_from
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port) as server:
            if self.settings.smtp_tls:
                server.starttls()
            if self.settings.smtp_user:
                server.login(self.settings.smtp_user, self.settings.smtp_password)
            server.sendmail(self.settings.smtp_from, to, msg.as_string())

        logger.info("[email] Sent '%s' to %s", subject, to)

    def send_welcome_email(self, to: str, username: str) -> None:
        self._send(
            to=to,
            subject="欢迎使用 KB Platform",
            html_body=f"<h2>欢迎，{username}！</h2><p>你的知识管理平台账户已创建。</p>",
        )

    def send_reset_email(self, to: str, reset_link: str) -> None:
        self._send(
            to=to,
            subject="KB Platform — 重置密码",
            html_body=f'<p>点击以下链接重置密码：</p><p><a href="{reset_link}">{reset_link}</a></p><p>链接 1 小时内有效。</p>',
        )

    def send_review_notification(self, to: str, doc_title: str, project_name: str) -> None:
        self._send(
            to=to,
            subject=f"KB Platform — 文档待审核: {doc_title}",
            html_body=f"<p>项目 <strong>{project_name}</strong> 中的文档 <strong>{doc_title}</strong> 已提交审核，请查看。</p>",
        )
