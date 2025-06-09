import os
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from src.db import Database
from src.paper_processor import PaperProcessor

@pytest.fixture
def mock_db():
    return MagicMock(spec=Database)

@pytest.fixture
def paper_processor(mock_db):
    return PaperProcessor(mock_db, "mock_api_key")

@patch('anthropic.Anthropic')
def test_assess_relevance(mock_anthropic, paper_processor):
    """Test paper relevance assessment."""
    # Mock Claude response
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client
    
    mock_content = MagicMock()
    mock_content.text = """Relevance score: 8/10

Executive summary: This paper presents novel techniques for improving e-commerce search relevance.

Key findings:
- Finding 1
- Finding 2

Potential applications for Etsy:
- Application 1
- Application 2"""

    mock_message = MagicMock()
    mock_message.content = [mock_content]
    mock_client.messages.create.return_value = mock_message
    
    # Replace the Anthropic client in the paper processor
    paper_processor.anthropic = mock_client
    
    # Test assessment
    result = paper_processor.assess_relevance(
        "Test Paper",
        "Test abstract"
    )
    
    assert result["relevance_score"] == 8
    assert "techniques for improving e-commerce search relevance" in result["summary"].lower()
    assert "finding 1" in result["key_findings"].lower()
    assert "application 1" in result["etsy_applications"].lower()
    
    # Verify Claude was called correctly
    mock_client.messages.create.assert_called_once()

def test_process_paper(paper_processor, mock_db):
    """Test end-to-end paper processing."""
    # Mock the component functions
    paper_processor.assess_relevance = MagicMock(return_value={
        "relevance_score": 8,
        "summary": "Mock summary",
        "key_findings": "Mock findings",
        "etsy_applications": "Mock applications"
    })
    
    # Test processing new paper
    mock_db.is_paper_processed.return_value = False
    
    paper_data = {
        "arxiv_id": "2301.12345",
        "arxiv_url": "https://arxiv.org/abs/2301.12345",
        "title": "Test Paper",
        "authors": "Test Author",
        "abstract": "Test abstract"
    }
    
    result = paper_processor.process_paper(paper_data)
    
    assert result is not None
    assert result["arxiv_id"] == "2301.12345"
    assert result["relevance_score"] == 8
    
    # Verify all steps were called
    paper_processor.assess_relevance.assert_called_once()
    mock_db.save_paper.assert_called_once()

def test_process_existing_paper(paper_processor, mock_db):
    """Test handling of already processed papers."""
    # Mock the component methods
    with patch.object(paper_processor, 'assess_relevance', return_value=None) as mock_assess:
        
        mock_db.is_paper_processed.return_value = True
        mock_db.get_paper_by_id.return_value = {
            "arxiv_id": "2301.12345",
            "title": "Test Paper",
            "relevance_score": 8
        }
        
        paper_data = {
            "arxiv_id": "2301.12345",
            "arxiv_url": "https://arxiv.org/abs/2301.12345"
        }
        
        result = paper_processor.process_paper(paper_data)
        
        assert result is not None
        assert result["arxiv_id"] == "2301.12345"
        assert result["relevance_score"] == 8
        
        # Verify no processing was done
        mock_assess.assert_not_called()
        mock_db.save_paper.assert_not_called() 