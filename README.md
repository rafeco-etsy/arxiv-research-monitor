# ArXiv Research Monitor

A tool that monitors ArXiv RSS feeds for new research papers, evaluates their relevance to Etsy's business, and automatically distributes summaries to relevant stakeholders via Slack and email.

## Features

- Monitor ArXiv RSS feeds for new papers
- Evaluate paper relevance using Claude AI
- Generate executive summaries and key findings
- Distribute relevant papers via Slack and email
- Track and query processed papers
- Export data for analysis

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/arxiv-monitor.git
cd arxiv-monitor
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your configuration:
```ini
# Required
CLAUDE_API_KEY=your_claude_api_key

# Optional - Slack Integration
SLACK_TOKEN=your_slack_bot_token

# Optional - Email Integration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_specific_password
SMTP_FROM_EMAIL=your_email@gmail.com
SMTP_USE_TLS=true
```

## Usage

### Monitor RSS Feeds

```bash
# Monitor all configured feeds
python -m src.cli.cli_rss --monitor-all

# Monitor specific feed
python -m src.cli.cli_rss --feed "http://export.arxiv.org/rss/cs.IR"

# Check feed health
python -m src.cli.cli_rss --check-health

# Show recent activity
python -m src.cli.cli_rss --show-recent --days 7
```

### Process Papers

```bash
# Process single paper
python -m src.cli.cli_process --url "https://arxiv.org/abs/2301.12345"

# Process and save without distributing
python -m src.cli.cli_process --url "https://arxiv.org/abs/2301.12345" --save-only

# Reprocess paper
python -m src.cli.cli_process --arxiv-id "2301.12345" --force

# Process from queue
python -m src.cli.cli_process --process-queue --limit 5
```

### Distribute Content

```bash
# Send specific paper
python -m src.cli.cli_distribute --arxiv-id "2301.12345"

# Send recent papers above threshold
python -m src.cli.cli_distribute --recent --min-relevance 7 --days 1

# Test message format
python -m src.cli.cli_distribute --arxiv-id "2301.12345" --dry-run

# Send to specific channel
python -m src.cli.cli_distribute --arxiv-id "2301.12345" --slack-only --channel "#test"
```

### Query Database

```bash
# Show recent papers
python -m src.cli.cli_query --recent --days 30

# Show papers by relevance
python -m src.cli.cli_query --relevance-range 7 10

# Search papers
python -m src.cli.cli_query --search "recommendation system"

# Export to CSV
python -m src.cli.cli_query --export papers_2024.csv --year 2024

# Show statistics
python -m src.cli.cli_query --stats --monthly
```

## Development

### Project Structure

```
arxiv-monitor/
├── src/
│   ├── __init__.py
│   ├── app.py              # Main application class
│   ├── db.py              # Database operations
│   ├── rss_monitor.py     # RSS feed monitoring
│   ├── paper_processor.py # Paper processing with Claude
│   ├── content_distributor.py # Content distribution
│   └── cli/               # Command line tools
│       ├── __init__.py
│       ├── cli_rss.py
│       ├── cli_process.py
│       ├── cli_distribute.py
│       └── cli_query.py
├── tests/                 # Test files
├── data/                  # Database and PDFs
├── docs/                  # Documentation
├── requirements.txt       # Dependencies
└── README.md             # This file
```

### Running Tests

```bash
python -m pytest tests/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

MIT License
