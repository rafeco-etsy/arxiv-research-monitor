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
    total_tokens = sum(paper.get('token_usage', 0) for paper in papers)
    logger.info(f"Processed {len(papers)} papers")
    logger.info(f"Total token usage: {total_tokens} tokens")
    for paper in papers:
        logger.info(f"Paper: {paper['title']} (Score: {paper['relevance_score']}, Tokens: {paper.get('token_usage', 0)})")

def monitor_feed(app: ArxivMonitor, feed_url: str) -> None:
    """Monitor a specific feed."""
    papers = app.process_feeds([feed_url])
    total_tokens = sum(paper.get('token_usage', 0) for paper in papers)
    logger.info(f"Processed {len(papers)} papers from {feed_url}")
    logger.info(f"Total token usage: {total_tokens} tokens")
    for paper in papers:
        logger.info(f"Paper: {paper['title']} (Score: {paper['relevance_score']}, Tokens: {paper.get('token_usage', 0)})")

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

def show_recent(app: ArxivMonitor, days: int, reprocess: bool = False) -> None:
    """Show recent feed activity."""
    papers = app.get_recent_papers(days)
    
    if reprocess:
        logger.info(f"Reprocessing {len(papers)} papers...")
        reprocessed_papers = []
        for paper in papers:
            processed = app.process_single_paper(paper['arxiv_url'], force=True, distribute=False)
            if processed:
                reprocessed_papers.append(processed)
        papers = reprocessed_papers
    
    total_tokens = sum(paper.get('token_usage', 0) for paper in papers)
    
    logger.info(f"\nPapers processed in the last {days} days:")
    logger.info(f"Total papers: {len(papers)}")
    logger.info(f"Total token usage: {total_tokens} tokens\n")
    
    for paper in papers:
        logger.info("=" * 80)
        logger.info(f"Title: {paper['title']}")
        logger.info(f"URL: {paper['arxiv_url']}")
        logger.info(f"Processed: {paper.get('processed_date', 'Just now')}")
        logger.info(f"Relevance Score: {paper['relevance_score']}/10")
        logger.info(f"Token Usage: {paper.get('token_usage', 0)} tokens")
        logger.info("\nExecutive Summary:")
        logger.info(paper['summary'])
        logger.info("\nKey Findings:")
        logger.info(paper['key_findings'])
        logger.info("\nPotential Applications for Etsy:")
        logger.info(paper['etsy_applications'])
        logger.info("=" * 80 + "\n")

def show_usage_report(app: ArxivMonitor, days: int) -> None:
    """Show usage statistics for the specified time period."""
    papers = app.get_recent_papers(days)
    
    # Calculate date ranges
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Basic stats
    total_papers = len(papers)
    total_tokens = sum(paper.get('token_usage', 0) for paper in papers)
    
    # Papers by feed
    feed_counts = {}
    for paper in papers:
        feed_url = paper.get('feed_url', 'unknown')
        feed_counts[feed_url] = feed_counts.get(feed_url, 0) + 1
    
    # Papers by relevance score
    relevance_counts = {}
    for paper in papers:
        score = paper.get('relevance_score', 0)
        relevance_counts[score] = relevance_counts.get(score, 0) + 1
    
    # Average tokens per paper
    avg_tokens = total_tokens / total_papers if total_papers > 0 else 0
    
    # Print report
    logger.info("\nUsage Report")
    logger.info("=" * 80)
    logger.info(f"Time Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    logger.info(f"Total Papers Processed: {total_papers}")
    logger.info(f"Total Token Usage: {total_tokens:,} tokens")
    logger.info(f"Average Tokens per Paper: {avg_tokens:.1f}")
    
    logger.info("\nPapers by Feed:")
    for feed, count in feed_counts.items():
        feed_name = feed.split('/')[-1] if feed != 'unknown' else 'Unknown'
        logger.info(f"  {feed_name}: {count} papers")
    
    logger.info("\nPapers by Relevance Score:")
    for score in sorted(relevance_counts.keys()):
        count = relevance_counts[score]
        logger.info(f"  Score {score}/10: {count} papers")
    
    logger.info("=" * 80)

def main():
    parser = argparse.ArgumentParser(description="ArXiv RSS Monitor")
    
    # Create mutually exclusive argument group for commands
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--monitor-all",
        action="store_true",
        help="Monitor all configured feeds"
    )
    group.add_argument(
        "--monitor-feed",
        type=str,
        help="Monitor a specific feed URL"
    )
    group.add_argument(
        "--show-recent",
        action="store_true",
        help="Show recent feed activity"
    )
    group.add_argument(
        "--usage-report",
        action="store_true",
        help="Show usage statistics"
    )
    
    # Additional arguments
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="Number of days to look back (default: 1)"
    )
    parser.add_argument(
        "--reprocess",
        action="store_true",
        help="Force reprocessing of papers"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=".env",
        help="Path to configuration file"
    )

    args = parser.parse_args()
    app = ArxivMonitor(args.config)

    try:
        if args.monitor_all:
            monitor_all(app)
        elif args.monitor_feed:
            monitor_feed(app, args.monitor_feed)
        elif args.show_recent:
            show_recent(app, args.days, args.reprocess)
        elif args.usage_report:
            show_usage_report(app, args.days)

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    main() 