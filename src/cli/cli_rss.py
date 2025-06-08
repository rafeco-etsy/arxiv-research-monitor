import argparse
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from ..app import ArxivMonitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def monitor_all(app: ArxivMonitor) -> None:
    """Monitor all configured feeds."""
    papers = app.process_feeds()
    logger.info(f"Processed {len(papers)} papers")
    for paper in papers:
        logger.info(f"Paper: {paper['title']} (Score: {paper['relevance_score']})")

def monitor_feed(app: ArxivMonitor, feed_url: str) -> None:
    """Monitor a specific feed."""
    papers = app.process_feeds([feed_url])
    logger.info(f"Processed {len(papers)} papers from {feed_url}")
    for paper in papers:
        logger.info(f"Paper: {paper['title']} (Score: {paper['relevance_score']})")

def check_health(app: ArxivMonitor, feed_url: Optional[str] = None) -> None:
    """Check feed health status."""
    if feed_url:
        health = app.check_feed_health(feed_url)
        logger.info(f"Health status for {feed_url}:")
        logger.info(f"Status: {health['status']}")
        logger.info(f"Message: {health['message']}")
        logger.info(f"Last check: {health['last_check']}")
    else:
        for feed in app.rss_monitor.default_feeds:
            health = app.check_feed_health(feed)
            logger.info(f"\nHealth status for {feed}:")
            logger.info(f"Status: {health['status']}")
            logger.info(f"Message: {health['message']}")
            logger.info(f"Last check: {health['last_check']}")

def show_recent(app: ArxivMonitor, days: int) -> None:
    """Show recent feed activity."""
    papers = app.get_recent_papers(days)
    logger.info(f"Papers processed in the last {days} days:")
    for paper in papers:
        logger.info(
            f"\nTitle: {paper['title']}\n"
            f"Score: {paper['relevance_score']}/10\n"
            f"URL: {paper['arxiv_url']}\n"
            f"Processed: {paper['processed_date']}"
        )

def main():
    parser = argparse.ArgumentParser(description="ArXiv RSS Feed Monitor")
    
    # Create mutually exclusive argument group
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--monitor-all",
        action="store_true",
        help="Monitor all configured feeds"
    )
    group.add_argument(
        "--feed",
        type=str,
        help="Monitor specific feed URL"
    )
    group.add_argument(
        "--check-health",
        action="store_true",
        help="Check feed health status"
    )
    group.add_argument(
        "--show-recent",
        action="store_true",
        help="Show recent feed activity"
    )

    # Additional arguments
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days for recent activity (default: 7)"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=".env",
        help="Path to configuration file"
    )

    args = parser.parse_args()

    # Initialize application
    app = ArxivMonitor(args.config)

    try:
        if args.monitor_all:
            monitor_all(app)
        elif args.feed:
            monitor_feed(app, args.feed)
        elif args.check_health:
            check_health(app)
        elif args.show_recent:
            show_recent(app, args.days)

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    main() 