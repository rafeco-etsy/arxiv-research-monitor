import argparse
import logging
from typing import List, Optional

from ..app import ArxivMonitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def distribute_paper(
    app: ArxivMonitor,
    arxiv_id: str,
    slack_only: bool = False,
    email_only: bool = False,
    channel: Optional[str] = None,
    email: Optional[str] = None,
    dry_run: bool = False
) -> None:
    """Distribute a paper to specified channels."""
    # Get paper data
    paper = app.db.get_paper_by_id(arxiv_id)
    if not paper:
        logger.error(f"Paper {arxiv_id} not found in database")
        return

    # Prepare distribution channels
    slack_channels = [channel] if channel else None
    email_recipients = [email] if email else None

    if not slack_only and not email_only:
        # Use both channels if neither is specified
        slack_channels = slack_channels or ["#research-papers"]
        email_recipients = email_recipients or []
    elif slack_only:
        email_recipients = None
        slack_channels = slack_channels or ["#research-papers"]
    elif email_only:
        slack_channels = None
        email_recipients = email_recipients or []

    if dry_run:
        logger.info("\nDRY RUN - Would distribute paper:")
        logger.info(f"Title: {paper['title']}")
        logger.info(f"Relevance Score: {paper['relevance_score']}/10")
        if slack_channels:
            logger.info(f"Slack channels: {slack_channels}")
        if email_recipients:
            logger.info(f"Email recipients: {email_recipients}")
        return

    # Distribute paper
    app.content_distributor.distribute_paper(
        paper,
        slack_channels,
        email_recipients
    )
    logger.info("Paper distributed successfully")

def distribute_recent(
    app: ArxivMonitor,
    days: int,
    min_relevance: int,
    slack_only: bool = False,
    email_only: bool = False,
    channel: Optional[str] = None,
    email: Optional[str] = None,
    dry_run: bool = False
) -> None:
    """Distribute recent papers above relevance threshold."""
    papers = app.get_recent_papers(days, min_relevance)
    logger.info(f"Found {len(papers)} papers to distribute")

    for paper in papers:
        distribute_paper(
            app,
            paper['arxiv_id'],
            slack_only,
            email_only,
            channel,
            email,
            dry_run
        )

def main():
    parser = argparse.ArgumentParser(description="ArXiv Content Distributor")
    
    # Create mutually exclusive argument group for paper selection
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--arxiv-id",
        type=str,
        help="ArXiv paper ID to distribute"
    )
    group.add_argument(
        "--recent",
        action="store_true",
        help="Distribute recent papers"
    )

    # Channel selection arguments
    channel_group = parser.add_mutually_exclusive_group()
    channel_group.add_argument(
        "--slack-only",
        action="store_true",
        help="Only distribute to Slack"
    )
    channel_group.add_argument(
        "--email-only",
        action="store_true",
        help="Only distribute to email"
    )

    # Additional arguments
    parser.add_argument(
        "--channel",
        type=str,
        help="Specific Slack channel to send to"
    )
    parser.add_argument(
        "--email",
        type=str,
        help="Specific email address to send to"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="Number of days for recent papers (default: 1)"
    )
    parser.add_argument(
        "--min-relevance",
        type=int,
        default=7,
        help="Minimum relevance score for distribution (default: 7)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be distributed without sending"
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
        if args.arxiv_id:
            distribute_paper(
                app,
                args.arxiv_id,
                args.slack_only,
                args.email_only,
                args.channel,
                args.email,
                args.dry_run
            )
        else:  # --recent
            distribute_recent(
                app,
                args.days,
                args.min_relevance,
                args.slack_only,
                args.email_only,
                args.channel,
                args.email,
                args.dry_run
            )

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    main() 