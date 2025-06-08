import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from .db import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContentDistributor:
    def __init__(
        self,
        db: Database,
        slack_token: Optional[str] = None,
        smtp_settings: Optional[Dict] = None
    ):
        self.db = db
        self.slack_client = WebClient(token=slack_token) if slack_token else None
        self.smtp_settings = smtp_settings or {}

    def format_paper_message(self, paper_data: Dict, format_type: str = "slack") -> str:
        """Format paper data for distribution."""
        if format_type == "slack":
            return f"""*New Relevant Research Paper*
*Title*: {paper_data['title']}
*Authors*: {paper_data['authors']}
*Relevance Score*: {paper_data['relevance_score']}/10
*ArXiv Link*: {paper_data['arxiv_url']}

*Executive Summary*
{paper_data['summary']}

*Key Findings*
{paper_data['key_findings']}

*Potential Applications for Etsy*
{paper_data['etsy_applications']}"""
        else:  # email
            return f"""New Relevant Research Paper

Title: {paper_data['title']}
Authors: {paper_data['authors']}
Relevance Score: {paper_data['relevance_score']}/10
ArXiv Link: {paper_data['arxiv_url']}

Executive Summary
{paper_data['summary']}

Key Findings
{paper_data['key_findings']}

Potential Applications for Etsy
{paper_data['etsy_applications']}"""

    def send_slack_message(
        self,
        paper_data: Dict,
        channels: List[str]
    ) -> None:
        """Send paper information to Slack channels."""
        if not self.slack_client:
            logger.warning("Slack client not configured")
            return

        message = self.format_paper_message(paper_data, "slack")

        for channel in channels:
            try:
                response = self.slack_client.chat_postMessage(
                    channel=channel,
                    text=message,
                    unfurl_links=True
                )
                self.db.log_distribution(
                    paper_data["arxiv_id"],
                    f"slack:{channel}",
                    True
                )
                logger.info(f"Sent to Slack channel {channel}")

            except SlackApiError as e:
                error_message = f"Failed to send to Slack channel {channel}: {str(e)}"
                logger.error(error_message)
                self.db.log_distribution(
                    paper_data["arxiv_id"],
                    f"slack:{channel}",
                    False,
                    error_message
                )

    def send_email(
        self,
        paper_data: Dict,
        recipients: List[str]
    ) -> None:
        """Send paper information via email."""
        if not self.smtp_settings:
            logger.warning("SMTP settings not configured")
            return

        message = MIMEMultipart()
        message["Subject"] = f"New Research Paper: {paper_data['title']}"
        message["From"] = self.smtp_settings.get("from_email", "noreply@example.com")

        body = self.format_paper_message(paper_data, "email")
        message.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP(
                self.smtp_settings["host"],
                self.smtp_settings["port"]
            ) as server:
                if self.smtp_settings.get("use_tls"):
                    server.starttls()
                
                if "username" in self.smtp_settings:
                    server.login(
                        self.smtp_settings["username"],
                        self.smtp_settings["password"]
                    )

                for recipient in recipients:
                    try:
                        message["To"] = recipient
                        server.send_message(message)
                        self.db.log_distribution(
                            paper_data["arxiv_id"],
                            f"email:{recipient}",
                            True
                        )
                        logger.info(f"Sent email to {recipient}")

                    except Exception as e:
                        error_message = f"Failed to send email to {recipient}: {str(e)}"
                        logger.error(error_message)
                        self.db.log_distribution(
                            paper_data["arxiv_id"],
                            f"email:{recipient}",
                            False,
                            error_message
                        )

        except Exception as e:
            error_message = f"SMTP connection failed: {str(e)}"
            logger.error(error_message)
            for recipient in recipients:
                self.db.log_distribution(
                    paper_data["arxiv_id"],
                    f"email:{recipient}",
                    False,
                    error_message
                )

    def distribute_paper(
        self,
        paper_data: Dict,
        slack_channels: Optional[List[str]] = None,
        email_recipients: Optional[List[str]] = None
    ) -> None:
        """Distribute paper to all configured channels."""
        if slack_channels:
            self.send_slack_message(paper_data, slack_channels)
        
        if email_recipients:
            self.send_email(paper_data, email_recipients) 