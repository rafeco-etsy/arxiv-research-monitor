import feedparser
import logging
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs

from .db import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RSSMonitor:
    def __init__(self, db: Database):
        self.db = db
        self.default_feeds = [
            "http://export.arxiv.org/rss/cs.IR",  # Information Retrieval
            "http://export.arxiv.org/rss/cs.LG",  # Machine Learning
            "http://export.arxiv.org/rss/cs.AI",  # Artificial Intelligence
            "http://export.arxiv.org/rss/econ.GN"  # General Economics
        ]
        self.request_delay = 5  # seconds between requests
        self.papers_per_feed = 10  # maximum papers to process per feed
        self.max_retries = 3  # maximum number of retries per feed
        self.base_delay = 5  # base delay for exponential backoff

    def extract_arxiv_id(self, url: str) -> Optional[str]:
        """Extract ArXiv ID from URL."""
        # Handle both abstract and PDF URLs
        patterns = [
            r"arxiv\.org/abs/([0-9.]+)",
            r"arxiv\.org/pdf/([0-9.]+)\.pdf",  # Updated pattern for PDF URLs
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def parse_entry(self, entry: Dict) -> Optional[Dict]:
        """Parse a single RSS entry into paper data."""
        try:
            arxiv_id = self.extract_arxiv_id(entry.get('link', ''))
            if not arxiv_id:
                logger.warning(f"Could not extract ArXiv ID from {entry.get('link', '')}")
                return None

            # Extract authors - handle both string and list formats
            authors = entry.get('author', '')
            if 'authors' in entry:
                if isinstance(entry['authors'], list):
                    authors = ', '.join(author.get('name', '') for author in entry['authors'])

            return {
                "arxiv_id": arxiv_id,
                "title": entry.get('title', ''),
                "authors": authors,
                "abstract": entry.get('summary', ''),
                "arxiv_url": entry.get('link', ''),
                "published_date": entry.get('published', ''),
            }
        except Exception as e:
            logger.error(f"Error parsing entry: {e}")
            return None

    def fetch_feed_with_retry(self, feed_url: str, retry_count: int = 0) -> Optional[feedparser.FeedParserDict]:
        """Fetch feed with exponential backoff retry."""
        try:
            feed = feedparser.parse(feed_url)
            
            if feed.bozo:  # Feed parsing error
                logger.error(f"Feed error for {feed_url}: {feed.bozo_exception}")
                if retry_count < self.max_retries:
                    delay = self.base_delay * (2 ** retry_count)  # exponential backoff
                    logger.info(f"Retrying {feed_url} in {delay} seconds (attempt {retry_count + 1}/{self.max_retries})")
                    time.sleep(delay)
                    return self.fetch_feed_with_retry(feed_url, retry_count + 1)
                return None
            
            return feed

        except Exception as e:
            logger.error(f"Error fetching feed {feed_url}: {e}")
            if retry_count < self.max_retries:
                delay = self.base_delay * (2 ** retry_count)  # exponential backoff
                logger.info(f"Retrying {feed_url} in {delay} seconds (attempt {retry_count + 1}/{self.max_retries})")
                time.sleep(delay)
                return self.fetch_feed_with_retry(feed_url, retry_count + 1)
            return None

    def fetch_feed(self, feed_url: str) -> List[Dict]:
        """Fetch and parse an RSS feed."""
        logger.info(f"Fetching feed: {feed_url}")
        
        feed = self.fetch_feed_with_retry(feed_url)
        if not feed:
            self.db.update_feed_health(feed_url, 0)
            return []

        entries = []
        for entry in feed.entries:
            parsed_entry = self.parse_entry(entry)
            if parsed_entry and not self.db.is_paper_processed(parsed_entry["arxiv_id"]):
                parsed_entry["feed_url"] = feed_url
                entries.append(parsed_entry)
                # Record the feed-paper mapping
                with self.db._get_connection() as conn:
                    conn.execute("""
                        INSERT OR IGNORE INTO feed_paper_mapping (arxiv_id, feed_url)
                        VALUES (?, ?)
                    """, (parsed_entry["arxiv_id"], feed_url))
                if len(entries) >= self.papers_per_feed:
                    logger.info(f"Reached limit of {self.papers_per_feed} papers for {feed_url}")
                    break

        self.db.update_feed_health(feed_url, len(feed.entries))
        return entries

    def monitor_feeds(self, feed_urls: Optional[List[str]] = None) -> List[Dict]:
        """Monitor multiple RSS feeds for new papers."""
        feed_urls = feed_urls or self.default_feeds
        all_new_entries = []

        for feed_url in feed_urls:
            try:
                new_entries = self.fetch_feed(feed_url)
                all_new_entries.extend(new_entries)
                logger.info(f"Found {len(new_entries)} new papers in {feed_url}")
                time.sleep(self.request_delay)  # Wait between feed requests
            except Exception as e:
                logger.error(f"Error monitoring feed {feed_url}: {e}")

        return all_new_entries

    def check_feed_health(self, feed_url: str) -> Dict:
        """Check the health status of a feed."""
        health_data = self.db.get_feed_health(feed_url)
        
        if not health_data:
            return {
                "status": "unknown",
                "message": "No health data available",
                "last_check": None,
                "consecutive_empty_fetches": 0
            }

        # Convert health data for reporting
        status = "healthy"
        message = "Feed is operating normally"

        if health_data["consecutive_empty_fetches"] > 3:
            status = "warning"
            message = f"Feed has been empty for {health_data['consecutive_empty_fetches']} consecutive checks"

        return {
            "status": status,
            "message": message,
            "last_check": health_data["last_successful_fetch"],
            "consecutive_empty_fetches": health_data["consecutive_empty_fetches"]
        } 