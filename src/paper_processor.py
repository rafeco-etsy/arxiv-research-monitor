import os
import logging
import requests
import PyPDF2
from typing import Dict, Optional
from pathlib import Path
from anthropic import Anthropic

from .db import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PaperProcessor:
    def __init__(self, db: Database, claude_api_key: str):
        self.db = db
        self.anthropic = Anthropic(api_key=claude_api_key)
        self.pdf_dir = Path("./data/pdfs")
        self.pdf_dir.mkdir(parents=True, exist_ok=True)

    def download_pdf(self, arxiv_id: str, url: str) -> Optional[str]:
        """Download PDF from ArXiv."""
        try:
            # Convert abstract URL to PDF URL if necessary
            pdf_url = url.replace('/abs/', '/pdf/') if '/abs/' in url else url
            if not pdf_url.endswith('.pdf'):
                pdf_url = f"{pdf_url}.pdf"

            response = requests.get(pdf_url)
            response.raise_for_status()

            pdf_path = self.pdf_dir / f"{arxiv_id}.pdf"
            with open(pdf_path, 'wb') as f:
                f.write(response.content)

            return str(pdf_path)

        except Exception as e:
            logger.error(f"Error downloading PDF for {arxiv_id}: {e}")
            return None

    def extract_text(self, pdf_path: str) -> Optional[str]:
        """Extract text content from PDF."""
        try:
            text_content = []
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    text_content.append(page.extract_text())
            
            return '\n'.join(text_content)

        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {e}")
            return None

    def assess_relevance(self, paper_text: str, title: str, abstract: str) -> Dict:
        """Use Claude to evaluate paper relevance and generate summary."""
        try:
            # Prepare context for Claude
            context = f"""Title: {title}

Abstract: {abstract}

Full Paper Text:
{paper_text[:10000]}  # Limit text length for API

Task: Analyze this research paper and evaluate its relevance to Etsy's business. Consider aspects like:
- E-commerce applications
- Marketplace dynamics
- Search and recommendation systems
- User behavior and psychology
- Economic insights
- Technical innovations applicable to Etsy's platform

Please provide:
1. Relevance score (1-10, where 10 is highly relevant)
2. Executive summary (2-3 sentences)
3. Key findings (bullet points)
4. Potential applications for Etsy (bullet points)"""

            # Get Claude's analysis
            response = self.anthropic.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1000,
                temperature=0,
                system="You are an expert in analyzing research papers for their business relevance to Etsy, the e-commerce marketplace.",
                messages=[{
                    "role": "user",
                    "content": context
                }]
            )

            # Parse Claude's response
            analysis = response.content[0].text
            
            # Extract components (this is a simple parsing, could be made more robust)
            lines = analysis.split('\n')
            
            # Find relevance score
            score_line = next(line for line in lines if 'relevance score' in line.lower())
            relevance_score = int(''.join(filter(str.isdigit, score_line)))
            
            # Extract sections
            sections = analysis.split('\n\n')
            summary = next(s for s in sections if 'summary' in s.lower() or len(s.split()) < 50)
            findings = next(s for s in sections if 'findings' in s.lower() or 'key points' in s.lower())
            applications = next(s for s in sections if 'applications' in s.lower() or 'recommendations' in s.lower())

            return {
                "relevance_score": relevance_score,
                "summary": summary,
                "key_findings": findings,
                "etsy_applications": applications
            }

        except Exception as e:
            logger.error(f"Error getting Claude analysis: {e}")
            return {
                "relevance_score": 0,
                "summary": "Error analyzing paper",
                "key_findings": "Error analyzing paper",
                "etsy_applications": "Error analyzing paper"
            }

    def process_paper(self, paper_data: Dict) -> Dict:
        """Process a single paper: download, extract text, and analyze."""
        try:
            # Skip if already processed
            if self.db.is_paper_processed(paper_data["arxiv_id"]):
                logger.info(f"Paper {paper_data['arxiv_id']} already processed")
                return self.db.get_paper_by_id(paper_data["arxiv_id"])

            # Download PDF
            pdf_path = self.download_pdf(paper_data["arxiv_id"], paper_data["arxiv_url"])
            if not pdf_path:
                raise Exception("Failed to download PDF")

            # Extract text
            paper_text = self.extract_text(pdf_path)
            if not paper_text:
                raise Exception("Failed to extract text from PDF")

            # Get Claude's analysis
            analysis = self.assess_relevance(paper_text, paper_data["title"], paper_data["abstract"])

            # Combine all data
            processed_data = {
                **paper_data,
                **analysis,
                "pdf_path": pdf_path
            }

            # Save to database
            self.db.save_paper(processed_data)
            return processed_data

        except Exception as e:
            logger.error(f"Error processing paper {paper_data.get('arxiv_id')}: {e}")
            return None 