import pytest
from unittest.mock import MagicMock, patch

from src.db import Database
from src.content_distributor import ContentDistributor

@pytest.fixture
def mock_db():
    return MagicMock(spec=Database)

@pytest.fixture
def mock_paper_data():
    return {
        "arxiv_id": "2301.12345",
        "title": "Test Paper",
        "authors": "Test Author",
        "relevance_score": 8,
        "arxiv_url": "https://arxiv.org/abs/2301.12345",
        "summary": "Test summary",
        "key_findings": "Test findings",
        "etsy_applications": "Test applications"
    }

@pytest.fixture
def distributor(mock_db):
    return ContentDistributor(
        mock_db,
        slack_token="mock_slack_token",
        smtp_settings={
            "host": "smtp.test.com",
            "port": 587,
            "username": "test@test.com",
            "password": "test_password",
            "from_email": "test@test.com",
            "use_tls": True
        }
    )

def test_format_paper_message_slack(distributor, mock_paper_data):
    """Test Slack message formatting."""
    message = distributor.format_paper_message(mock_paper_data, "slack")
    
    assert "*New Relevant Research Paper*" in message
    assert mock_paper_data["title"] in message
    assert mock_paper_data["authors"] in message
    assert str(mock_paper_data["relevance_score"]) in message
    assert mock_paper_data["arxiv_url"] in message
    assert mock_paper_data["summary"] in message
    assert mock_paper_data["key_findings"] in message
    assert mock_paper_data["etsy_applications"] in message

def test_format_paper_message_email(distributor, mock_paper_data):
    """Test email message formatting."""
    message = distributor.format_paper_message(mock_paper_data, "email")
    
    assert "New Relevant Research Paper" in message
    assert mock_paper_data["title"] in message
    assert mock_paper_data["authors"] in message
    assert str(mock_paper_data["relevance_score"]) in message
    assert mock_paper_data["arxiv_url"] in message
    assert mock_paper_data["summary"] in message
    assert mock_paper_data["key_findings"] in message
    assert mock_paper_data["etsy_applications"] in message

@patch('slack_sdk.WebClient.chat_postMessage')
def test_send_slack_message(mock_post_message, distributor, mock_paper_data, mock_db):
    """Test sending Slack messages."""
    channels = ["#test-channel", "#research"]
    
    distributor.send_slack_message(mock_paper_data, channels)
    
    # Verify Slack API calls
    assert mock_post_message.call_count == len(channels)
    for channel in channels:
        mock_post_message.assert_any_call(
            channel=channel,
            text=distributor.format_paper_message(mock_paper_data, "slack"),
            unfurl_links=True
        )
    
    # Verify distribution logging
    assert mock_db.log_distribution.call_count == len(channels)
    for channel in channels:
        mock_db.log_distribution.assert_any_call(
            mock_paper_data["arxiv_id"],
            f"slack:{channel}",
            True
        )

@patch('slack_sdk.WebClient.chat_postMessage')
def test_send_slack_message_error(mock_post_message, distributor, mock_paper_data, mock_db):
    """Test Slack error handling."""
    mock_post_message.side_effect = Exception("Slack error")
    
    distributor.send_slack_message(mock_paper_data, ["#test-channel"])
    
    mock_db.log_distribution.assert_called_once_with(
        mock_paper_data["arxiv_id"],
        "slack:#test-channel",
        False,
        "Failed to send to Slack channel #test-channel: Slack error"
    )

@patch('smtplib.SMTP')
def test_send_email(mock_smtp, distributor, mock_paper_data, mock_db):
    """Test sending emails."""
    recipients = ["test1@test.com", "test2@test.com"]
    
    distributor.send_email(mock_paper_data, recipients)
    
    # Verify SMTP setup
    mock_smtp.assert_called_once_with(
        distributor.smtp_settings["host"],
        distributor.smtp_settings["port"]
    )
    
    mock_smtp_instance = mock_smtp.return_value.__enter__.return_value
    
    # Verify TLS and login
    mock_smtp_instance.starttls.assert_called_once()
    mock_smtp_instance.login.assert_called_once_with(
        distributor.smtp_settings["username"],
        distributor.smtp_settings["password"]
    )
    
    # Verify emails sent
    assert mock_smtp_instance.send_message.call_count == len(recipients)
    
    # Verify distribution logging
    assert mock_db.log_distribution.call_count == len(recipients)
    for recipient in recipients:
        mock_db.log_distribution.assert_any_call(
            mock_paper_data["arxiv_id"],
            f"email:{recipient}",
            True
        )

@patch('smtplib.SMTP')
def test_send_email_error(mock_smtp, distributor, mock_paper_data, mock_db):
    """Test email error handling."""
    mock_smtp.side_effect = Exception("SMTP error")
    
    distributor.send_email(mock_paper_data, ["test@test.com"])
    
    mock_db.log_distribution.assert_called_once_with(
        mock_paper_data["arxiv_id"],
        "email:test@test.com",
        False,
        "SMTP connection failed: SMTP error"
    )

def test_distribute_paper(distributor, mock_paper_data):
    """Test paper distribution to all channels."""
    # Mock the individual distribution methods
    distributor.send_slack_message = MagicMock()
    distributor.send_email = MagicMock()
    
    slack_channels = ["#test-channel"]
    email_recipients = ["test@test.com"]
    
    distributor.distribute_paper(
        mock_paper_data,
        slack_channels,
        email_recipients
    )
    
    distributor.send_slack_message.assert_called_once_with(
        mock_paper_data,
        slack_channels
    )
    distributor.send_email.assert_called_once_with(
        mock_paper_data,
        email_recipients
    ) 