import argparse
import logging
from typing import Optional

from ..app import ArxivMonitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_paper(
    app: ArxivMonitor,
    url: Optional[str] = None,
    arxiv_id: Optional[str] = None,
    save_only: bool = False,
    force: bool = False
) -> None:
    """Process a single paper."""
    if url:
        paper_url = url
    elif arxiv_id:
        paper_url = f"https://arxiv.org/abs/{arxiv_id}"
    else:
        raise ValueError("Either URL or ArXiv ID must be provided")

    paper = app.process_single_paper(
        paper_url,
        force=force,
        distribute=not save_only
    )

    if paper:
        logger.info("\nPaper processed successfully:")
        logger.info(f"Title: {paper['title']}")
        logger.info(f"Authors: {paper['authors']}")
        logger.info(f"Relevance Score: {paper['relevance_score']}/10")
        logger.info(f"URL: {paper['arxiv_url']}")
        logger.info("\nExecutive Summary:")
        logger.info(paper['summary'])
        logger.info("\nKey Findings:")
        logger.info(paper['key_findings'])
        logger.info("\nPotential Applications for Etsy:")
        logger.info(paper['etsy_applications'])
    else:
        logger.error("Failed to process paper")

def process_queue(app: ArxivMonitor, limit: int) -> None:
    """Process papers from the unprocessed queue."""
    # Get recent papers that haven't been processed
    papers = app.get_recent_papers(days=30)
    unprocessed = [p for p in papers if not p.get('processed_date')][:limit]

    logger.info(f"Processing {len(unprocessed)} papers from queue")
    for paper in unprocessed:
        process_paper(app, arxiv_id=paper['arxiv_id'])

def main():
    parser = argparse.ArgumentParser(description="ArXiv Paper Processor")
    
    # Create mutually exclusive argument group for paper identification
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--url",
        type=str,
        help="ArXiv paper URL"
    )
    group.add_argument(
        "--arxiv-id",
        type=str,
        help="ArXiv paper ID"
    )
    group.add_argument(
        "--process-queue",
        action="store_true",
        help="Process papers from the unprocessed queue"
    )

    # Additional arguments
    parser.add_argument(
        "--save-only",
        action="store_true",
        help="Save paper without distributing"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force reprocessing of paper"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Limit number of papers to process from queue (default: 5)"
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
        if args.process_queue:
            process_queue(app, args.limit)
        else:
            process_paper(
                app,
                url=args.url,
                arxiv_id=args.arxiv_id,
                save_only=args.save_only,
                force=args.force
            )

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    main() 