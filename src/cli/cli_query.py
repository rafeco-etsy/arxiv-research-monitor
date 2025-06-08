import argparse
import csv
import logging
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

from ..app import ArxivMonitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def show_recent_papers(app: ArxivMonitor, days: int) -> None:
    """Show recent papers with scores."""
    papers = app.get_recent_papers(days)
    logger.info(f"\nPapers from the last {days} days:")
    for paper in papers:
        logger.info(
            f"\nTitle: {paper['title']}\n"
            f"Score: {paper['relevance_score']}/10\n"
            f"URL: {paper['arxiv_url']}\n"
            f"Processed: {paper['processed_date']}"
        )

def show_papers_by_relevance(app: ArxivMonitor, min_score: int, max_score: int) -> None:
    """Show papers within relevance score range."""
    papers = app.get_recent_papers(days=365)  # Get last year's papers
    filtered_papers = [
        p for p in papers
        if min_score <= p['relevance_score'] <= max_score
    ]

    logger.info(f"\nPapers with relevance score {min_score}-{max_score}:")
    for paper in filtered_papers:
        logger.info(
            f"\nTitle: {paper['title']}\n"
            f"Score: {paper['relevance_score']}/10\n"
            f"URL: {paper['arxiv_url']}\n"
            f"Processed: {paper['processed_date']}"
        )

def search_papers(app: ArxivMonitor, keyword: str) -> None:
    """Search papers by keyword."""
    papers = app.get_recent_papers(days=365)  # Get last year's papers
    keyword = keyword.lower()
    
    matching_papers = [
        p for p in papers
        if (keyword in p['title'].lower() or
            keyword in p['abstract'].lower() or
            keyword in p['summary'].lower() or
            keyword in p['key_findings'].lower() or
            keyword in p['etsy_applications'].lower())
    ]

    logger.info(f"\nPapers matching '{keyword}':")
    for paper in matching_papers:
        logger.info(
            f"\nTitle: {paper['title']}\n"
            f"Score: {paper['relevance_score']}/10\n"
            f"URL: {paper['arxiv_url']}\n"
            f"Processed: {paper['processed_date']}"
        )

def export_papers(app: ArxivMonitor, output_file: str, year: Optional[int] = None) -> None:
    """Export papers to CSV file."""
    papers = app.get_recent_papers(days=365 if year else 3650)
    
    if year:
        papers = [
            p for p in papers
            if datetime.strptime(p['processed_date'], '%Y-%m-%d %H:%M:%S').year == year
        ]

    # Define CSV fields
    fields = [
        'arxiv_id', 'title', 'authors', 'relevance_score',
        'arxiv_url', 'processed_date', 'summary',
        'key_findings', 'etsy_applications'
    ]

    try:
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for paper in papers:
                # Only write specified fields
                row = {field: paper.get(field, '') for field in fields}
                writer.writerow(row)
        
        logger.info(f"Exported {len(papers)} papers to {output_file}")

    except Exception as e:
        logger.error(f"Error exporting to CSV: {e}")

def show_statistics(app: ArxivMonitor, monthly: bool = False) -> None:
    """Show distribution statistics."""
    papers = app.get_recent_papers(days=365)  # Get last year's papers
    
    # Calculate basic stats
    total_papers = len(papers)
    avg_score = sum(p['relevance_score'] for p in papers) / total_papers if total_papers else 0
    
    # Group by score
    score_dist = defaultdict(int)
    for paper in papers:
        score_dist[paper['relevance_score']] += 1

    # Group by month if requested
    if monthly:
        monthly_stats = defaultdict(list)
        for paper in papers:
            date = datetime.strptime(paper['processed_date'], '%Y-%m-%d %H:%M:%S')
            month_key = f"{date.year}-{date.month:02d}"
            monthly_stats[month_key].append(paper)

        logger.info("\nMonthly Statistics:")
        for month in sorted(monthly_stats.keys()):
            month_papers = monthly_stats[month]
            month_avg = sum(p['relevance_score'] for p in month_papers) / len(month_papers)
            logger.info(
                f"\n{month}:\n"
                f"Papers processed: {len(month_papers)}\n"
                f"Average relevance: {month_avg:.1f}"
            )

    # Print overall stats
    logger.info(f"\nOverall Statistics:")
    logger.info(f"Total papers processed: {total_papers}")
    logger.info(f"Average relevance score: {avg_score:.1f}")
    logger.info("\nScore Distribution:")
    for score in range(1, 11):
        count = score_dist[score]
        percentage = (count / total_papers * 100) if total_papers else 0
        logger.info(f"Score {score}: {count} papers ({percentage:.1f}%)")

def main():
    parser = argparse.ArgumentParser(description="ArXiv Database Query Tool")
    
    # Create mutually exclusive argument group
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--recent",
        action="store_true",
        help="Show recent papers"
    )
    group.add_argument(
        "--relevance-range",
        nargs=2,
        type=int,
        metavar=('MIN', 'MAX'),
        help="Show papers by relevance score range"
    )
    group.add_argument(
        "--search",
        type=str,
        help="Search papers by keyword"
    )
    group.add_argument(
        "--export",
        type=str,
        metavar="FILE",
        help="Export papers to CSV file"
    )
    group.add_argument(
        "--stats",
        action="store_true",
        help="Show distribution statistics"
    )

    # Additional arguments
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days for recent papers (default: 30)"
    )
    parser.add_argument(
        "--year",
        type=int,
        help="Filter by year for export"
    )
    parser.add_argument(
        "--monthly",
        action="store_true",
        help="Show monthly statistics"
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
        if args.recent:
            show_recent_papers(app, args.days)
        elif args.relevance_range:
            show_papers_by_relevance(app, args.relevance_range[0], args.relevance_range[1])
        elif args.search:
            search_papers(app, args.search)
        elif args.export:
            export_papers(app, args.export, args.year)
        elif args.stats:
            show_statistics(app, args.monthly)

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    main() 