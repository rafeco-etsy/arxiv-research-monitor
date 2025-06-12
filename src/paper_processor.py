import os
import logging
import requests
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

    def assess_relevance(self, title: str, abstract: str) -> Dict:
        """Use Claude to evaluate paper relevance and generate summary."""
        try:
            # Prepare context for Claude
            context = f"""Title: {title}

Abstract: {abstract}

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
                model="claude-3-haiku-20240307",
                max_tokens=1000,
                temperature=0,
                system="You are an expert on AI and ML, and your job is to evaluate the relevance of a research paper to Etsy both in terms of business opportunities and technical advances. You are also an expert in the field of e-commerce and marketplace dynamics.",
                messages=[{
                    "role": "user",
                    "content": context
                }]
            )

            # Parse Claude's response
            analysis = response.content[0].text
            
            # Extract components (this is a simple parsing, could be made more robust)
            sections = analysis.split('\n\n')
            
            # Find relevance score
            score_section = next(s for s in sections if 'relevance score' in s.lower())
            relevance_score = int(''.join(filter(str.isdigit, score_section.split('/')[0])))
            
            # Extract other sections
            summary_section = next(s for s in sections if 'executive summary' in s.lower())
            summary = summary_section.split(':', 1)[1].strip() if ':' in summary_section else summary_section
            
            findings_section = next(s for s in sections if 'key findings' in s.lower())
            findings = findings_section.split(':', 1)[1].strip() if ':' in findings_section else findings_section
            
            applications_section = next(s for s in sections if 'applications' in s.lower())
            applications = applications_section.split(':', 1)[1].strip() if ':' in applications_section else applications_section

            # Get token usage from response
            token_usage = response.usage.input_tokens + response.usage.output_tokens

            return {
                "relevance_score": relevance_score,
                "summary": summary,
                "key_findings": findings,
                "etsy_applications": applications,
                "token_usage": token_usage
            }

        except Exception as e:
            logger.error(f"Error getting Claude analysis: {e}")
            return {
                "relevance_score": 0,
                "summary": "Error analyzing paper",
                "key_findings": "Error analyzing paper",
                "etsy_applications": "Error analyzing paper",
                "token_usage": 0
            }

    def process_paper(self, paper_data: Dict) -> Dict:
        """Process a single paper: analyze abstract and title."""
        try:
            # Get Claude's analysis
            analysis = self.assess_relevance(paper_data["title"], paper_data["abstract"])

            # Combine all data
            processed_data = {
                **paper_data,
                **analysis
            }

            # Save to database and get updated data
            return self.db.save_paper(processed_data)

        except Exception as e:
            logger.error(f"Error processing paper {paper_data.get('arxiv_id')}: {e}")
            return None 