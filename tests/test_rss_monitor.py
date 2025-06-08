import os
import pytest
from unittest.mock import MagicMock, patch

from src.db import Database
from src.rss_monitor import RSSMonitor

@pytest.fixture
def mock_db():
    return MagicMock(spec=Database)

@pytest.fixture
def rss_monitor(mock_db):
    return RSSMonitor(mock_db)

def test_extract_arxiv_id():
    """Test ArXiv ID extraction from different URL formats."""
    monitor = RSSMonitor(MagicMock())
    
    # Test abstract URL
    assert monitor.extract_arxiv_id("https://arxiv.org/abs/2301.12345") == "2301.12345"
    
    # Test PDF URL
    assert monitor.extract_arxiv_id("https://arxiv.org/pdf/2301.12345.pdf") == "2301.12345"
    
    # Test invalid URL
    assert monitor.extract_arxiv_id("https://example.com") is None

def test_parse_entry(rss_monitor):
    """Test RSS entry parsing."""
    # Mock RSS entry
    entry = {
        'title': 'Test Paper',
        'link': 'https://arxiv.org/abs/2301.12345',
        'author': 'John Doe',
        'summary': 'Test abstract',
        'published': '2024-01-01'
    }
    
    result = rss_monitor.parse_entry(entry)
    
    assert result is not None
    assert result['arxiv_id'] == '2301.12345'
    assert result['title'] == 'Test Paper'
    assert result['authors'] == 'John Doe'
    assert result['abstract'] == 'Test abstract'
    assert result['arxiv_url'] == 'https://arxiv.org/abs/2301.12345'
    assert result['published_date'] == '2024-01-01'

@patch('feedparser.parse')
def test_fetch_feed(mock_parse, rss_monitor, mock_db):
    """Test RSS feed fetching."""
    # Mock feedparser response
    mock_parse.return_value = MagicMock(
        bozo=False,
        entries=[
            {
                'title': 'Paper 1',
                'link': 'https://arxiv.org/abs/2301.12345',
                'author': 'John Doe',
                'summary': 'Abstract 1',
                'published': '2024-01-01'
            },
            {
                'title': 'Paper 2',
                'link': 'https://arxiv.org/abs/2301.12346',
                'author': 'Jane Smith',
                'summary': 'Abstract 2',
                'published': '2024-01-02'
            }
        ]
    )
    
    # Mock database to say papers aren't processed
    mock_db.is_paper_processed.return_value = False
    
    # Test feed fetching
    feed_url = "http://export.arxiv.org/rss/cs.IR"
    results = rss_monitor.fetch_feed(feed_url)
    
    assert len(results) == 2
    assert results[0]['arxiv_id'] == '2301.12345'
    assert results[1]['arxiv_id'] == '2301.12346'
    
    # Verify database calls
    mock_db.update_feed_health.assert_called_once_with(feed_url, 2)
    assert mock_db.is_paper_processed.call_count == 2

@patch('feedparser.parse')
def test_fetch_feed_error(mock_parse, rss_monitor, mock_db):
    """Test RSS feed error handling."""
    # Mock feedparser error
    mock_parse.return_value = MagicMock(
        bozo=True,
        bozo_exception="Mock error"
    )
    
    feed_url = "http://export.arxiv.org/rss/cs.IR"
    results = rss_monitor.fetch_feed(feed_url)
    
    assert len(results) == 0
    mock_db.update_feed_health.assert_called_once_with(feed_url, 0)

def test_check_feed_health(rss_monitor, mock_db):
    """Test feed health checking."""
    feed_url = "http://export.arxiv.org/rss/cs.IR"
    
    # Mock healthy feed
    mock_db.get_feed_health.return_value = {
        "last_successful_fetch": "2024-01-01 12:00:00",
        "consecutive_empty_fetches": 0
    }
    
    health = rss_monitor.check_feed_health(feed_url)
    assert health["status"] == "healthy"
    
    # Mock warning feed
    mock_db.get_feed_health.return_value = {
        "last_successful_fetch": "2024-01-01 12:00:00",
        "consecutive_empty_fetches": 4
    }
    
    health = rss_monitor.check_feed_health(feed_url)
    assert health["status"] == "warning"
    
    # Mock unknown feed
    mock_db.get_feed_health.return_value = None
    
    health = rss_monitor.check_feed_health(feed_url)
    assert health["status"] == "unknown" 