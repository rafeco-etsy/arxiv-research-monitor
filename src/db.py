import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "./data/arxiv_monitor.db"):
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_db()

    def _ensure_db_directory(self):
        """Ensure the database directory exists."""
        db_dir = os.path.dirname(self.db_path)
        Path(db_dir).mkdir(parents=True, exist_ok=True)

    def _init_db(self):
        """Initialize the database with required tables."""
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS processed_papers (
                    arxiv_id TEXT PRIMARY KEY,
                    processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    relevance_score INTEGER,
                    title TEXT,
                    authors TEXT,
                    abstract TEXT,
                    summary TEXT,
                    key_findings TEXT,
                    etsy_applications TEXT,
                    arxiv_url TEXT,
                    pdf_path TEXT,
                    token_usage INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS feed_health (
                    feed_url TEXT PRIMARY KEY,
                    last_successful_fetch TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_entry_count INTEGER DEFAULT 0,
                    skip_days TEXT,
                    consecutive_empty_fetches INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS distribution_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    arxiv_id TEXT,
                    channel TEXT,
                    distribution_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN,
                    error_message TEXT,
                    FOREIGN KEY (arxiv_id) REFERENCES processed_papers (arxiv_id)
                );

                CREATE TABLE IF NOT EXISTS feed_paper_mapping (
                    arxiv_id TEXT,
                    feed_url TEXT,
                    fetch_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (arxiv_id, feed_url),
                    FOREIGN KEY (arxiv_id) REFERENCES processed_papers (arxiv_id),
                    FOREIGN KEY (feed_url) REFERENCES feed_health (feed_url)
                );
            """)

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def is_paper_processed(self, arxiv_id: str) -> bool:
        """Check if a paper has already been processed."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM processed_papers WHERE arxiv_id = ?",
                (arxiv_id,)
            )
            return cursor.fetchone() is not None

    def save_paper(self, paper_data: Dict) -> Dict:
        """Save processed paper data to the database."""
        with self._get_connection() as conn:
            # First save the paper
            conn.execute("""
                INSERT OR REPLACE INTO processed_papers (
                    arxiv_id, processed_date, relevance_score, title, authors,
                    abstract, summary, key_findings, etsy_applications,
                    arxiv_url, pdf_path, token_usage
                ) VALUES (?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                paper_data["arxiv_id"],
                paper_data.get("relevance_score"),
                paper_data.get("title"),
                paper_data.get("authors"),
                paper_data.get("abstract"),
                paper_data.get("summary"),
                paper_data.get("key_findings"),
                paper_data.get("etsy_applications"),
                paper_data.get("arxiv_url"),
                paper_data.get("pdf_path"),
                paper_data.get("token_usage", 0)
            ))
            
            # Then fetch the saved paper to get the processed_date
            cursor = conn.execute(
                "SELECT * FROM processed_papers WHERE arxiv_id = ?",
                (paper_data["arxiv_id"],)
            )
            saved_paper = dict(cursor.fetchone())
            
            # Update the paper_data with the processed_date
            paper_data["processed_date"] = saved_paper["processed_date"]
            return paper_data

    def update_feed_health(self, feed_url: str, entry_count: int) -> None:
        """Update feed health information."""
        with self._get_connection() as conn:
            # First, get current consecutive_empty_fetches value
            cursor = conn.execute(
                "SELECT consecutive_empty_fetches FROM feed_health WHERE feed_url = ?",
                (feed_url,)
            )
            row = cursor.fetchone()
            current_empty_fetches = row['consecutive_empty_fetches'] if row else 0
            
            # Then update or insert
            conn.execute("""
                INSERT OR REPLACE INTO feed_health (
                    feed_url, last_successful_fetch, last_entry_count,
                    consecutive_empty_fetches
                ) VALUES (?, CURRENT_TIMESTAMP, ?, ?)
            """, (
                feed_url,
                entry_count,
                current_empty_fetches + 1 if entry_count == 0 else 0
            ))

    def log_distribution(self, arxiv_id: str, channel: str, success: bool, error_message: Optional[str] = None) -> None:
        """Log paper distribution attempt."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO distribution_log (
                    arxiv_id, channel, success, error_message
                ) VALUES (?, ?, ?, ?)
            """, (arxiv_id, channel, success, error_message))

    def get_recent_papers(self, days: int = 7) -> List[Dict]:
        """Get papers processed in the last N days."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM processed_papers
                WHERE processed_date >= datetime('now', '-' || ? || ' days')
                ORDER BY processed_date DESC
            """, (days,))
            return [dict(row) for row in cursor.fetchall()]

    def get_paper_by_id(self, arxiv_id: str) -> Optional[Dict]:
        """Get a specific paper by its ArXiv ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM processed_papers WHERE arxiv_id = ?",
                (arxiv_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_feed_health(self, feed_url: str) -> Optional[Dict]:
        """Get health information for a specific feed."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM feed_health WHERE feed_url = ?",
                (feed_url,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None 