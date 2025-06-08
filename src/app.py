import os
import logging
from typing import Dict, List, Optional
from dotenv import load_dotenv

from .db import Database
from .rss_monitor import RSSMonitor
from .paper_processor import PaperProcessor
from .content_distributor import ContentDistributor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ArxivMonitor:
    def __init__(self, config_path: str = ".env"):
        # Load environment variables
        load_dotenv(config_path)
        
        # Initialize database
        self.db = Database()
        
        # Initialize components
        self.rss_monitor = RSSMonitor(self.db)
        self.paper_processor = PaperProcessor(
            self.db,
            os.getenv("CLAUDE_API_KEY")
        )
        
        # Initialize content distributor with optional Slack and SMTP settings
        slack_token = os.getenv("SLACK_TOKEN")
        
        smtp_settings = None
        if os.getenv("SMTP_HOST"):
            smtp_settings = {
                "host": os.getenv("SMTP_HOST"),
                "port": int(os.getenv("SMTP_PORT", "587")),
                "username": os.getenv("SMTP_USERNAME"),
                "password": os.getenv("SMTP_PASSWORD"),
                "from_email": os.getenv("SMTP_FROM_EMAIL"),
                "use_tls": os.getenv("SMTP_USE_TLS", "true").lower() == "true"
            }
        
        self.content_distributor = ContentDistributor(
            self.db,
            slack_token,
            smtp_settings
        )

    def process_feeds(
        self,
        feed_urls: Optional[List[str]] = None,
        min_relevance: int = 7,
        slack_channels: Optional[List[str]] = None,
        email_recipients: Optional[List[str]] = None
    ) -> List[Dict]:
        """Process RSS feeds and distribute relevant papers."""
        processed_papers = []

        # Monitor feeds for new papers
        new_papers = self.rss_monitor.monitor_feeds(feed_urls)
        logger.info(f"Found {len(new_papers)} new papers")

        # Process each paper
        for paper_data in new_papers:
            processed_paper = self.paper_processor.process_paper(paper_data)
            if not processed_paper:
                continue

            processed_papers.append(processed_paper)

            # Distribute if relevance meets threshold
            if processed_paper["relevance_score"] >= min_relevance:
                self.content_distributor.distribute_paper(
                    processed_paper,
                    slack_channels,
                    email_recipients
                )

        return processed_papers

    def process_single_paper(
        self,
        arxiv_url: str,
        force: bool = False,
        distribute: bool = True,
        slack_channels: Optional[List[str]] = None,
        email_recipients: Optional[List[str]] = None
    ) -> Optional[Dict]:
        """Process a single paper by its ArXiv URL."""
        # Extract paper ID and create initial data
        arxiv_id = self.rss_monitor.extract_arxiv_id(arxiv_url)
        if not arxiv_id:
            logger.error(f"Invalid ArXiv URL: {arxiv_url}")
            return None

        # Check if already processed
        if not force and self.db.is_paper_processed(arxiv_id):
            paper_data = self.db.get_paper_by_id(arxiv_id)
            logger.info(f"Paper {arxiv_id} already processed")
            return paper_data

        # Fetch paper details (simplified as we don't have RSS data)
        paper_data = {
            "arxiv_id": arxiv_id,
            "arxiv_url": arxiv_url,
            "title": "",  # Will be updated by paper processor
            "authors": "",
            "abstract": ""
        }

        # Process the paper
        processed_paper = self.paper_processor.process_paper(paper_data)
        if not processed_paper:
            return None

        # Distribute if requested
        if distribute:
            self.content_distributor.distribute_paper(
                processed_paper,
                slack_channels,
                email_recipients
            )

        return processed_paper

    def check_feed_health(self, feed_url: str) -> Dict:
        """Check health status of a specific feed."""
        return self.rss_monitor.check_feed_health(feed_url)

    def get_recent_papers(
        self,
        days: int = 7,
        min_relevance: Optional[int] = None
    ) -> List[Dict]:
        """Get papers processed in the last N days."""
        papers = self.db.get_recent_papers(days)
        if min_relevance is not None:
            papers = [p for p in papers if p["relevance_score"] >= min_relevance]
        return papers 