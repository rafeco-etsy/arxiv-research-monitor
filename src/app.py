import os
import logging
from typing import Dict, List, Optional
from dotenv import load_dotenv
import feedparser
import time
import re
from datetime import datetime
from urllib.parse import urlparse, parse_qs

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
            logger.info(f"Paper {arxiv_id} already processed")
            return self.db.get_paper_by_id(arxiv_id)

        # Add delay before making ArXiv API request
        time.sleep(3)  # 3 second delay to respect rate limits

        # Fetch paper details from ArXiv RSS feed with retries
        max_retries = 3
        base_delay = 3  # seconds
        feed_url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
        
        for attempt in range(max_retries):
            try:
                time.sleep(base_delay * (2 ** attempt))  # Exponential backoff
                feed = feedparser.parse(feed_url)
                
                if not feed.entries:
                    logger.error(f"Could not fetch paper details from ArXiv: {arxiv_id}")
                    continue
                    
                entry = feed.entries[0]
                paper_data = {
                    "arxiv_id": arxiv_id,
                    "arxiv_url": arxiv_url,
                    "title": entry.get('title', '').replace('\n', ' '),
                    "authors": ', '.join(author.get('name', '') for author in entry.get('authors', [])),
                    "abstract": entry.get('summary', '').replace('\n', ' ')
                }
                break
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {arxiv_id}: {e}")
                if attempt == max_retries - 1:
                    logger.error(f"Failed to fetch paper details after {max_retries} attempts")
                    return None

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

    def get_recent_papers(self, days: int) -> List[Dict]:
        """Get papers processed in the last N days."""
        with self.db._get_connection() as conn:
            cursor = conn.execute("""
                SELECT p.*, f.feed_url
                FROM processed_papers p
                LEFT JOIN (
                    SELECT DISTINCT arxiv_id, feed_url
                    FROM feed_paper_mapping
                ) f ON p.arxiv_id = f.arxiv_id
                WHERE p.processed_date >= datetime('now', ?)
                ORDER BY p.processed_date DESC
            """, (f"-{days} days",))
            return [dict(row) for row in cursor.fetchall()] 