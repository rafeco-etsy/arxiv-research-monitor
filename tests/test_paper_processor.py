import os
import pytest
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path

from src.db import Database
from src.paper_processor import PaperProcessor

@pytest.fixture
def mock_db():
    return MagicMock(spec=Database)

@pytest.fixture
def paper_processor(mock_db):
    return PaperProcessor(mock_db, "mock_api_key")

@patch('requests.get')
def test_download_pdf(mock_get, paper_processor, tmp_path):
    """Test PDF downloading."""
    # Set up mock response
    mock_response = MagicMock()
    mock_response.content = b"Mock PDF content"
    mock_get.return_value = mock_response
    
    # Temporarily change pdf_dir to tmp_path
    paper_processor.pdf_dir = tmp_path
    
    # Test downloading from abstract URL
    arxiv_id = "2301.12345"
    url = f"https://arxiv.org/abs/2301.12345"
    pdf_path = paper_processor.download_pdf(arxiv_id, url)
    
    assert pdf_path is not None
    assert Path(pdf_path).exists()
    assert Path(pdf_path).read_bytes() == b"Mock PDF content"
    
    # Verify correct URL conversion
    mock_get.assert_called_with("https://arxiv.org/pdf/2301.12345.pdf")

@patch('PyPDF2.PdfReader')
def test_extract_text(mock_pdf_reader, paper_processor):
    """Test text extraction from PDF."""
    # Mock PDF pages
    mock_pages = [
        MagicMock(extract_text=lambda: "Page 1 content"),
        MagicMock(extract_text=lambda: "Page 2 content")
    ]
    mock_pdf_reader.return_value.pages = mock_pages
    
    # Test text extraction
    with patch("builtins.open", mock_open(read_data="mock pdf data")):
        text = paper_processor.extract_text("mock.pdf")
    
    assert text == "Page 1 content\nPage 2 content"

@patch('anthropic.Anthropic')
def test_assess_relevance(mock_anthropic, paper_processor):
    """Test paper relevance assessment."""
    # Mock Claude response
    mock_message = MagicMock()
    mock_message.content = [
        MagicMock(
            text="""Relevance score: 8/10

Executive summary: This paper presents novel techniques for improving e-commerce search relevance.

Key findings:
- Finding 1
- Finding 2

Potential applications for Etsy:
- Application 1
- Application 2"""
        )
    ]
    mock_anthropic.return_value.messages.create.return_value = mock_message
    
    # Test assessment
    result = paper_processor.assess_relevance(
        "paper text",
        "Test Paper",
        "Test abstract"
    )
    
    assert result["relevance_score"] == 8
    assert "search relevance" in result["summary"].lower()
    assert "findings" in result["key_findings"].lower()
    assert "applications" in result["etsy_applications"].lower()

def test_process_paper(paper_processor, mock_db):
    """Test end-to-end paper processing."""
    # Mock all the component functions
    paper_processor.download_pdf = MagicMock(return_value="/tmp/mock.pdf")
    paper_processor.extract_text = MagicMock(return_value="Mock paper text")
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
    assert result["pdf_path"] == "/tmp/mock.pdf"
    
    # Verify all steps were called
    paper_processor.download_pdf.assert_called_once()
    paper_processor.extract_text.assert_called_once()
    paper_processor.assess_relevance.assert_called_once()
    mock_db.save_paper.assert_called_once()

def test_process_existing_paper(paper_processor, mock_db):
    """Test handling of already processed papers."""
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
    paper_processor.download_pdf.assert_not_called()
    paper_processor.extract_text.assert_not_called()
    paper_processor.assess_relevance.assert_not_called()
    mock_db.save_paper.assert_not_called() 