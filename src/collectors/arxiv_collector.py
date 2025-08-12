from __future__ import annotations

from dataclasses import dataclass
from typing import List
from datetime import datetime
import arxiv

from src.models import ArxivItem


def query_arxiv(search_query: str, start: int = 0, max_results: int = 10) -> List[ArxivItem]:
    """Query arXiv using the arxiv library for reliable results"""
    try:
        print(f"Querying arXiv with: {search_query}")
        
        # Create search query
        search = arxiv.Search(
            query=search_query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending
        )
        
        items: List[ArxivItem] = []
        
        for result in search.results():
            try:
                # Extract categories from the result
                categories = []
                if hasattr(result, 'categories'):
                    categories = result.categories
                
                # Extract authors
                authors = []
                if hasattr(result, 'authors'):
                    authors = [author.name for author in result.authors]
                
                items.append(
                    ArxivItem(
                        source="arXiv",
                        title=result.title,
                        link=result.entry_id,
                        published_at=result.published,
                        abstract=result.summary,
                        authors=authors,
                        categories=categories,
                    )
                )
                
                if len(items) >= max_results:
                    break
                    
            except Exception as e:
                print(f"  Failed to process arXiv result: {e}")
                continue
        
        print(f"Total arXiv items collected: {len(items)}")
        return items
        
    except Exception as e:
        print(f"Failed to query arXiv: {e}")
        return []
