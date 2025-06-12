import argparse
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from ..app import ArxivMonitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def backup_db(db_path: str) -> str:
    """Create a backup of the database file with timestamp."""
    if not os.path.exists(db_path):
        logger.info("No existing database to backup.")
        return None
        
    # Create backup directory if it doesn't exist
    backup_dir = os.path.join(os.path.dirname(db_path), "backups")
    Path(backup_dir).mkdir(parents=True, exist_ok=True)
    
    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"arxiv_monitor_{timestamp}.db")
    
    # Move the current database to backup
    shutil.move(db_path, backup_path)
    logger.info(f"Database backed up to: {backup_path}")
    return backup_path

def reset_db(app: ArxivMonitor) -> None:
    """Move the current database to a backup and create a fresh one."""
    db_path = app.db.db_path
    
    # Backup existing database
    backup_path = backup_db(db_path)
    if backup_path:
        logger.info(f"Previous database backed up to: {backup_path}")
    
    # The database will be automatically recreated when accessed
    logger.info("Database has been reset. A new one will be created automatically.")

def main():
    parser = argparse.ArgumentParser(description="ArXiv Monitor Database Management")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Move the current database to a backup and create a fresh one"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=".env",
        help="Path to configuration file"
    )

    args = parser.parse_args()
    app = ArxivMonitor(args.config)

    if args.reset:
        reset_db(app)
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 