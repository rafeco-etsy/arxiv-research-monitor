import os
import pytest
from unittest.mock import MagicMock, patch

from src.app import ArxivMonitor
from src.db import Database
from src.rss_monitor import RSSMonitor
from src.paper_processor import PaperProcessor
from src.content_distributor import ContentDistributor

@pytest.fixture
def mock_env():
    """Set up mock environment variables."""
    with patch.dict(os.environ, {
        "CLAUDE_API_KEY": "mock_claude_key",
        "SLACK_TOKEN": "mock_slack_token",
        "SMTP_HOST": "smtp.test.com",
        "SMTP_PORT": "587",
        "SMTP_USERNAME": "test@test.com",
        "SMTP_PASSWORD": "test_password",
        "SMTP_FROM_EMAIL": "test@test.com",
        "SMTP_USE_TLS": "true"
    }):
        yield

@pytest.fixture
def mock_components():
    """Mock all component classes."""
    with patch("src.app.Database") as mock_db, \
         patch("src.app.RSSMonitor") as mock_monitor, \
         patch("src.app.PaperProcessor") as mock_processor, \
         patch("src.app.ContentDistributor") as mock_distributor:
        yield {
            "db": mock_db,
            "monitor": mock_monitor,
            "processor": mock_processor,
            "distributor": mock_distributor
        }

@pytest.fixture
def app(mock_env, mock_components):
    """Create test application instance."""
    app = ArxivMonitor()
    # Replace instance attributes with mocks
    app.db = mock_components["db"].return_value
    app.rss_monitor = mock_components["monitor"].return_value
    app.paper_processor = mock_components["processor"].return_value
    app.content_distributor = mock_components["distributor"].return_value
    return app

def test_app_initialization(mock_env, mock_components):
    """Test application initialization."""
    app = ArxivMonitor()
    
    # Verify component initialization
    mock_components["db"].assert_called_once()
    mock_components["monitor"].assert_called_once()
    mock_components["processor"].assert_called_once()
    mock_components["distributor"].assert_called_once()

def test_process_feeds(app, mock_components):
    """Test feed processing workflow."""
    # Mock component responses
    mock_papers = [
        {
            "arxiv_id": "2301.12345",
            "title": "Paper 1",
            "relevance_score": 8
        },
        {
            "arxiv_id": "2301.12346",
            "title": "Paper 2",
            "relevance_score": 6
        }
    ]
    
    app.rss_monitor.monitor_feeds.return_value = mock_papers
    app.paper_processor.process_paper.side_effect = mock_papers
    
    # Test processing with default settings
    results = app.process_feeds(
        slack_channels=["#test"],
        email_recipients=["test@test.com"]
    )
    
    assert len(results) == 2
    
    # Verify component calls
    app.rss_monitor.monitor_feeds.assert_called_once_with(None)
    assert app.paper_processor.process_paper.call_count == 2
    
    # Verify only relevant papers are distributed
    app.content_distributor.distribute_paper.assert_called_once_with(
        mock_papers[0],  # Only paper with score >= 7
        ["#test"],
        ["test@test.com"]
    )

def test_process_single_paper(app, mock_components):
    """Test single paper processing workflow."""
    mock_paper = {
        "arxiv_id": "2301.12345",
        "title": "Test Paper",
        "relevance_score": 8
    }
    
    # Mock component responses
    app.rss_monitor.extract_arxiv_id.return_value = "2301.12345"
    app.paper_processor.process_paper.return_value = mock_paper
    app.db.is_paper_processed.return_value = False
    
    # Test processing with distribution
    result = app.process_single_paper(
        "https://arxiv.org/abs/2301.12345",
        slack_channels=["#test"],
        email_recipients=["test@test.com"]
    )
    
    assert result == mock_paper
    
    # Verify component calls
    app.rss_monitor.extract_arxiv_id.assert_called_once()
    app.paper_processor.process_paper.assert_called_once()
    app.content_distributor.distribute_paper.assert_called_once_with(
        mock_paper,
        ["#test"],
        ["test@test.com"]
    )

def test_process_single_paper_no_distribute(app, mock_components):
    """Test single paper processing without distribution."""
    mock_paper = {
        "arxiv_id": "2301.12345",
        "title": "Test Paper",
        "relevance_score": 8
    }
    
    app.rss_monitor.extract_arxiv_id.return_value = "2301.12345"
    app.paper_processor.process_paper.return_value = mock_paper
    app.db.is_paper_processed.return_value = False
    
    result = app.process_single_paper(
        "https://arxiv.org/abs/2301.12345",
        distribute=False
    )
    
    assert result == mock_paper
    app.content_distributor.distribute_paper.assert_not_called()

def test_check_feed_health(app, mock_components):
    """Test feed health checking."""
    mock_health = {
        "status": "healthy",
        "message": "Feed is operating normally",
        "last_check": "2024-01-01 12:00:00"
    }
    
    app.rss_monitor.check_feed_health.return_value = mock_health
    
    result = app.check_feed_health("http://test.feed")
    
    assert result == mock_health
    app.rss_monitor.check_feed_health.assert_called_once_with("http://test.feed")

def test_get_recent_papers(app, mock_components):
    """Test recent papers retrieval."""
    mock_papers = [
        {"arxiv_id": "1", "relevance_score": 8},
        {"arxiv_id": "2", "relevance_score": 6},
        {"arxiv_id": "3", "relevance_score": 9}
    ]
    
    app.db.get_recent_papers.return_value = mock_papers
    
    # Test without relevance filter
    results = app.get_recent_papers(days=7)
    assert len(results) == 3
    app.db.get_recent_papers.assert_called_with(7)
    
    # Test with relevance filter
    results = app.get_recent_papers(days=7, min_relevance=7)
    assert len(results) == 2
    assert all(p["relevance_score"] >= 7 for p in results) 