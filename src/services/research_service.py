"""Research service for web searching and evidence gathering."""

from __future__ import annotations

import os
from datetime import date, timedelta
from typing import List, Optional

from ..models.schemas import EvidenceItem, EvidencePack
from .llm_service import LLMService


class ResearchService:
    """Service for conducting web research."""

    SYSTEM_PROMPT = """You are a research synthesizer.

Given raw web search results, produce EvidenceItem objects.

Rules:
- Only include items with a non-empty url.
- Prefer relevant + authoritative sources.
- Normalize published_at to ISO YYYY-MM-DD if reliably inferable; else null (do NOT guess).
- Keep snippets short.
- Deduplicate by URL.
"""

    def __init__(self, llm_service: LLMService):
        """Initialize research service.

        Args:
            llm_service: LLM service for processing results
        """
        self.llm_service = llm_service

    def search_tavily(self, query: str, max_results: int = 5) -> List[dict]:
        """Search using Tavily API.

        Args:
            query: Search query
            max_results: Maximum results to return

        Returns:
            List of search results
        """
        if not os.getenv("TAVILY_API_KEY"):
            return []
        
        try:
            from langchain_community.tools.tavily_search import TavilySearchResults  # type: ignore
            tool = TavilySearchResults(max_results=max_results)
            results = tool.invoke({"query": query})
            out: List[dict] = []
            for r in results or []:
                out.append(
                    {
                        "title": r.get("title") or "",
                        "url": r.get("url") or "",
                        "snippet": r.get("content") or r.get("snippet") or "",
                        "published_at": r.get("published_date") or r.get("published_at"),
                        "source": r.get("source"),
                    }
                )
            return out
        except Exception:
            return []

    def gather_evidence(
        self,
        queries: List[str],
        as_of: str,
        recency_days: int,
        mode: str,
    ) -> List[EvidenceItem]:
        """Gather and synthesize evidence from multiple queries.

        Args:
            queries: List of search queries
            as_of: As-of date (ISO format)
            recency_days: Number of days for recency filter
            mode: Research mode (closed_book, hybrid, open_book)

        Returns:
            List of evidence items
        """
        queries = queries[:10]
        raw: List[dict] = []
        for q in queries:
            raw.extend(self.search_tavily(q, max_results=6))

        if not raw:
            return []

        pack = self.llm_service.invoke_structured(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=(
                f"As-of date: {as_of}\n"
                f"Recency days: {recency_days}\n\n"
                f"Raw results:\n{raw}"
            ),
            schema=EvidencePack,
        )

        # Deduplicate by URL
        dedup = {}
        for e in pack.evidence:
            if e.url:
                dedup[e.url] = e
        evidence = list(dedup.values())

        # Apply recency filter for open_book mode
        if mode == "open_book":
            as_of_date = date.fromisoformat(as_of)
            cutoff = as_of_date - timedelta(days=recency_days)
            evidence = [
                e for e in evidence 
                if (d := self._iso_to_date(e.published_at)) and d >= cutoff
            ]

        return evidence

    @staticmethod
    def _iso_to_date(s: Optional[str]) -> Optional[date]:
        """Convert ISO date string to date object."""
        if not s:
            return None
        try:
            return date.fromisoformat(s[:10])
        except Exception:
            return None
