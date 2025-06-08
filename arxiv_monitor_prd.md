# ArXiv Research Monitor - PRD & Implementation Plan

## Product Requirements Document

### Overview
A tool that monitors ArXiv RSS feeds for new research papers, evaluates their relevance to Etsy's business, and automatically distributes summaries to relevant stakeholders via Slack and email.

### Goals
- **Primary**: Automate discovery and assessment of relevant research papers for Etsy
- **Secondary**: Reduce manual effort in research monitoring and increase team awareness of applicable academic findings
- **Success Metrics**: Papers processed per week, relevance accuracy, team engagement with summaries

### Core Features

#### 1. RSS Feed Monitoring
- Monitor specified ArXiv RSS feeds (e.g., cs.IR, cs.LG, econ.GN)
- Track processed papers to avoid duplicates
- Configurable polling intervals
- Support for multiple feed sources

#### 2. Paper Processing & Analysis
- Download PDF from ArXiv URLs
- Extract and process paper content
- Use Claude API to assess relevance to Etsy's business
- Generate executive summaries with key findings
- Identify practical applications for Etsy

#### 3. Content Distribution
- Send notifications via Slack (with configurable channels)
- Send email summaries (with configurable recipients)
- Include ArXiv links and generated summaries
- Support for different notification preferences per stakeholder

### Technical Requirements

#### Performance
- Process feeds every 4-6 hours
- Handle 50+ papers per day
- Response time < 30 seconds per paper
- 99% uptime for monitoring

#### Data Storage
- Persistent tracking of processed papers
- Configuration storage for feeds, recipients, channels
- Log retention for debugging and metrics

#### Security & Compliance
- **API Key Management**: All API keys externalized via environment variables (never in code)
- **Environment File**: Use `.env` file for local development (add to `.gitignore`)
- **Email credential protection**: SMTP credentials via environment variables
- **Rate limiting**: Respect external APIs with exponential backoff
- **Error handling**: Comprehensive retry logic for API failures

---

## Implementation Plan

### Architecture Overview
```
RSS Monitor → Paper Processor → Content Distributor
     ↓              ↓               ↓
  State DB    ←  Claude API   →  Slack/Email APIs
```

### Command Line Interface Tools

#### CLI Tool 1: RSS Feed Monitor (`cli_rss.py`)
**Purpose**: Download and process RSS feeds manually

```bash
# Monitor all configured feeds
python cli_rss.py --monitor-all

# Monitor specific feed
python cli_rss.py --feed "http://export.arxiv.org/rss/cs.IR"

# Check feed health without processing
python cli_rss.py --check-health

# Show recent feed activity
python cli_rss.py --show-recent --days 7
```

**Functions**:
- Process RSS feeds on demand
- Display new papers found
- Show feed health status
- Export new paper URLs for manual processing

#### CLI Tool 2: Paper Processor (`cli_process.py`)
**Purpose**: Process individual ArXiv papers with Claude

```bash
# Process single paper
python cli_process.py --url "https://arxiv.org/abs/2301.12345"

# Process and save without distributing
python cli_process.py --url "https://arxiv.org/abs/2301.12345" --save-only

# Reprocess existing paper (bypass duplicate check)
python cli_process.py --arxiv-id "2301.12345" --force

# Process from database of unprocessed papers
python cli_process.py --process-queue --limit 5
```

**Functions**:
- Download and analyze individual papers
- Display relevance scores and summaries
- Save results to database
- Bypass normal duplicate detection for testing

#### CLI Tool 3: Content Distributor (`cli_distribute.py`)
**Purpose**: Send papers to Slack/email channels

```bash
# Send specific paper
python cli_distribute.py --arxiv-id "2301.12345"

# Send papers above relevance threshold
python cli_distribute.py --min-relevance 7 --days 1

# Test message formatting without sending
python cli_distribute.py --arxiv-id "2301.12345" --dry-run

# Send to specific channel only
python cli_distribute.py --arxiv-id "2301.12345" --slack-only --channel "#test"
```

**Functions**:
- Send individual papers to configured channels
- Bulk send recent high-relevance papers
- Test message formatting
- Target specific channels for testing

#### CLI Tool 4: Database Query Tool (`cli_query.py`)
**Purpose**: Query and analyze stored papers

```bash
# Show recent papers with scores
python cli_query.py --recent --days 30

# Show papers by relevance range
python cli_query.py --relevance-range 7 10

# Search papers by keyword
python cli_query.py --search "recommendation system"

# Export papers to CSV
python cli_query.py --export papers_2024.csv --year 2024

# Show distribution statistics
python cli_query.py --stats --monthly
```

**Functions**:
- Query papers by date, relevance, keywords
- Generate reports and statistics
- Export data for analysis
- Show distribution success rates

### Core Library Components

#### Component 1: ArXiv Paper Processor (`arxiv_processor.py`)
**Purpose**: Accept ArXiv URL and generate relevance assessment + summary

**Key Functions**:
- `download_pdf(arxiv_url)`: Download PDF from ArXiv
- `extract_text(pdf_path)`: Extract text content from PDF
- `assess_relevance(paper_text)`: Use Claude to evaluate Etsy relevance (1-10 scale)
- `generate_summary(paper_text)`: Create executive summary with key findings
- `format_output()`: Structure results for distribution

**Dependencies**: 
- `requests` (PDF download)
- `anthropic` (Claude API with file upload)

**Input**: ArXiv URL string
**Output**: Dictionary with relevance score, summary, title, authors, abstract

#### Component 2: RSS Feed Monitor (`rss_monitor.py`)
**Purpose**: Monitor RSS feeds and track processed items

**Key Functions**:
- `fetch_feed(rss_url)`: Get latest RSS entries with error handling
- `parse_entries(feed_data)`: Extract ArXiv URLs and metadata
- `check_processed(arxiv_id)`: Query state database for duplicates
- `mark_processed(arxiv_id)`: Update state database
- `filter_new_papers()`: Return only unprocessed papers
- `handle_empty_feed()`: Gracefully handle feeds with no entries (skipDays)
- `validate_feed_health()`: Distinguish between empty feeds and broken feeds

**Dependencies**:
- `feedparser` (RSS parsing)
- `sqlite3` (built into Python standard library)
- `schedule` (periodic execution)

**ArXiv-Specific Handling**:
- Check feed's `skipDays` field to understand publication schedule
- Log empty feeds as normal behavior, not errors
- Track feed metadata to detect actual connectivity issues vs. scheduled gaps

#### Database Strategy

**Local Development (SQLite)**:
- Single `arxiv_monitor.db` file in project directory
- No additional database dependencies or setup required
- Built-in Python `sqlite3` module handles all operations
- Easy backup by copying the `.db` file

**Future Cloud Migration Path**:
- SQLite works perfectly on GCP (Cloud Run, Compute Engine, Cloud Functions)
- For higher scale: Easy migration to Cloud SQL (PostgreSQL) using similar schema
- Database abstraction layer allows switching backends without code changes

**Database Location**:
```python
# Local development
DB_PATH = "./data/arxiv_monitor.db"

# GCP deployment (persistent disk or Cloud SQL connection)
DB_PATH = os.getenv("DATABASE_URL", "./data/arxiv_monitor.db")
```
**SQLite Schema**:
```sql
CREATE TABLE processed_papers (
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
    pdf_path TEXT
);

CREATE TABLE feed_health (
    feed_url TEXT PRIMARY KEY,
    last_successful_fetch TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_entry_count INTEGER DEFAULT 0,
    skip_days TEXT,
    consecutive_empty_fetches INTEGER DEFAULT 0
);

CREATE TABLE distribution_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    arxiv_id TEXT,
    channel_type TEXT, -- 'slack' or 'email'
    channel_target TEXT, -- channel name or email address
    sent_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN,
    error_message TEXT,
    FOREIGN KEY (arxiv_id) REFERENCES processed_papers (arxiv_id)
);

CREATE INDEX idx_processed_date ON processed_papers(processed_date);
CREATE INDEX idx_relevance_score ON processed_papers(relevance_score);
CREATE INDEX idx_distribution_date ON distribution_log(sent_date);
```

#### Component 3: Content Distributor (`distributor.py`)
**Purpose**: Send summaries via Slack and email

**Key Functions**:
- `send_slack_message(channel, content)`: Post to Slack channel
- `send_email(recipients, subject, content)`: Send email notification
- `format_slack_message(paper_data)`: Create Slack-formatted message
- `format_email(paper_data)`: Create HTML email content
- `load_distribution_config()`: Get recipients and preferences
- `log_distribution(arxiv_id, channel_type, target, success, error)`: Track delivery

**Dependencies**:
- `slack_sdk` (Slack integration)
- `smtplib` + `email` (email sending)
- `jinja2` (email templating)

**Distribution Tracking**: All sends logged to `distribution_log` table for debugging and metrics

**Configuration**: JSON config file with:
```json
{
  "slack": {
    "enabled": true,
    "channels": ["#research", "#product"],
    "min_relevance": 6
  },
  "email": {
    "enabled": true,
    "recipients": ["team@etsy.com"],
    "min_relevance": 7
  }
}
```

### Main Orchestrator (`main.py`)
**Purpose**: Coordinate all components and handle scheduling

**Key Functions**:
- `run_monitoring_cycle()`: Execute full monitoring workflow
- `setup_logging()`: Configure application logging
- `load_config()`: Read RSS feeds and distribution settings
- `handle_errors()`: Graceful error handling and notifications

**Workflow**:
1. Fetch feeds from RSS sources
2. Check if empty feeds are expected (skipDays) vs. problematic
3. For each new paper above relevance threshold:
   - Process with ArXiv processor
   - Distribute via configured channels
   - Mark as processed
4. Update feed health metrics
5. Log results and actual errors (distinguish from expected empty feeds)

### Development Phases

#### Phase 1: Core Processing & CLI Tools (Week 1-2)
- Implement ArXiv paper processor with PDF upload to Claude
- Create `cli_process.py` for individual paper testing
- Single comprehensive Claude prompt for relevance assessment and summary generation
- Database schema creation and paper storage
- Error handling for PDF download and upload failures
- Unit tests for core functions

#### Phase 2: Feed Monitoring & CLI (Week 2-3)
- RSS feed parsing and monitoring
- Create `cli_rss.py` for feed testing and debugging
- State management database with skipDays handling
- Duplicate detection logic
- Integration with paper processor
- Feed health tracking and reporting

#### Phase 3: Distribution & CLI (Week 3-4)
- Slack integration and message formatting
- Email sending functionality
- Create `cli_distribute.py` for delivery testing
- Distribution logging and tracking
- Configuration management
- End-to-end workflow testing

#### Phase 4: Query Tools & Production Readiness (Week 4)
- Create `cli_query.py` for data analysis and reporting
- Database query and export functionality
- Error handling and retry logic
- Comprehensive logging and monitoring
- Configuration validation
- Deployment scripts and documentation

### Configuration Files

#### `config.yaml`
```yaml
rss_feeds:
  - url: "http://export.arxiv.org/rss/cs.IR"
    name: "Information Retrieval"
  - url: "http://export.arxiv.org/rss/cs.LG" 
    name: "Machine Learning"

claude_api:
  model: "claude-3-sonnet-20240229"
  max_tokens: 4000
  # API key loaded from environment: ANTHROPIC_API_KEY

monitoring:
  poll_interval_hours: 6
  min_relevance_threshold: 5

distribution:
  slack:
    enabled: true
    # Token loaded from environment: SLACK_BOT_TOKEN
    channels: ["#research-updates"]
  email:
    enabled: true
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
    # Credentials loaded from environment: EMAIL_USERNAME, EMAIL_PASSWORD
    recipients: ["research-team@etsy.com"]
```

#### `.env` file (local development - add to `.gitignore`)
```bash
# API Keys - NEVER commit these to Git
ANTHROPIC_API_KEY=your_claude_api_key_here
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
EMAIL_USERNAME=your_email@company.com
EMAIL_PASSWORD=your_app_password

# Optional: Database path override
DATABASE_URL=./data/arxiv_monitor.db
```

### Deployment & Operations

#### Environment Setup
- Python 3.9+ virtual environment
- Required API keys: Claude, Slack Bot Token
- SMTP credentials for email
- Cron job or systemd service for scheduling

#### Monitoring & Maintenance
- Application logs for debugging
- Weekly metrics reports (papers processed, relevance distribution)
- Monthly review of relevance accuracy
- Quarterly feed source evaluation

### Estimated Timeline
- **Total Development**: 4 weeks
- **Testing & Deployment**: 1 week
- **Initial Production Run**: 2 weeks monitoring and tuning

### Risk Mitigation
- **API Rate Limits**: Implement exponential backoff and request queuing
- **PDF Processing Failures**: Fallback to abstract-only analysis
- **False Positives**: Tune relevance prompts based on feedback
- **Service Downtime**: Implement health checks and alerting