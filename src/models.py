from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


@dataclass
class ContentItem:
    source: str
    title: str
    link: str
    published_at: Optional[datetime]
    raw_content: Optional[str]
    summary: Optional[str] = None
    tags: Optional[List[str]] = None

    @property
    def content(self):
        """raw_content의 별칭 (호환성용)"""
        return self.raw_content


@dataclass
class ArxivItem:
    source: str
    title: str
    link: str
    published_at: Optional[datetime]
    abstract: Optional[str]
    authors: List[str]
    summary: Optional[str] = None
    categories: Optional[List[str]] = None
    
    @property
    def content(self):
        """ContentItem과의 호환성을 위한 프로퍼티"""
        return self.abstract


@dataclass
class YoutubeItem:
    source: str
    title: str
    link: str
    published_at: Optional[datetime]
    transcript: Optional[str]
    channel: Optional[str] = None
    summary: Optional[str] = None
    
    @property
    def content(self):
        """ContentItem과의 호환성을 위한 프로퍼티"""
        return self.transcript


@dataclass
class Summary:
    title: str
    url: str
    summary: str


@dataclass
class RawItem:
    source: str
    title: str
    link: str
    content: Optional[str] = None
    published_at: Optional[datetime] = None
