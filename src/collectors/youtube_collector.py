from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime, timedelta
import re
import requests
from bs4 import BeautifulSoup
import json

from youtube_transcript_api import YouTubeTranscriptApi

from src.models import YoutubeItem


# Inspired by summary-gpt-bot's transcript retrieval

def extract_video_id(url: str) -> Optional[str]:
    match = re.search(r"(?<=v=)[^&]+|(?<=youtu.be/)[^?\n]+", url)
    return match.group(0) if match else None


def extract_channel_id(url: str) -> Optional[str]:
    """채널 URL에서 채널 ID 또는 username 추출"""
    # @username 형식
    if "@" in url:
        match = re.search(r"@([^/]+)", url)
        return f"@{match.group(1)}" if match else None
    # /channel/UCxxxxxx 형식
    elif "/channel/" in url:
        match = re.search(r"/channel/([^/]+)", url)
        return match.group(1) if match else None
    # /c/channelname 또는 /user/username 형식
    elif "/c/" in url or "/user/" in url:
        match = re.search(r"/(c|user)/([^/]+)", url)
        return match.group(2) if match else None
    return None


def fetch_channel_videos_rss(channel_url: str, max_videos: int = 3) -> List[dict]:
    """
    YouTube 채널의 RSS 피드를 사용하여 최신 영상 정보 가져오기
    RSS는 YouTube Data API 없이도 사용 가능
    """
    videos = []
    
    try:
        # 채널 페이지에서 채널 ID 추출
        channel_id = None
        
        # @username 형식 처리
        if "@" in channel_url:
            username = extract_channel_id(channel_url)
            # @username을 채널 ID로 변환하기 위해 채널 페이지 접근
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9'
            }
            response = requests.get(f"https://www.youtube.com/{username}", headers=headers, timeout=10)
            if response.status_code == 200:
                # 페이지에서 채널 ID 찾기 (여러 패턴 시도)
                patterns = [
                    r'"channelId":"(UC[^"]+)"',
                    r'"browseId":"(UC[^"]+)"',
                    r'channel_id=(UC[^"&]+)',
                    r'/channel/(UC[^"]+)'
                ]
                for pattern in patterns:
                    match = re.search(pattern, response.text)
                    if match:
                        channel_id = match.group(1)
                        print(f"Found channel ID for {username}: {channel_id}")
                        break
        elif "/channel/" in channel_url:
            channel_id = extract_channel_id(channel_url)
        
        if not channel_id:
            print(f"Could not extract channel ID from {channel_url}")
            return videos
        
        # 채널 ID가 @로 시작하면 RSS를 직접 가져올 수 없으므로 스크래핑 필요
        if channel_id.startswith("@"):
            return fetch_channel_videos_scraping(channel_url, max_videos)
        
        # YouTube RSS 피드 URL
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        
        # RSS 피드 가져오기
        response = requests.get(rss_url, timeout=10)
        if response.status_code != 200:
            print(f"Failed to fetch RSS feed for channel {channel_id}")
            return videos
        
        # RSS XML 파싱
        soup = BeautifulSoup(response.content, 'xml')
        entries = soup.find_all('entry')[:max_videos]
        
        for entry in entries:
            video_id = entry.find('yt:videoId')
            title = entry.find('title')
            published = entry.find('published')
            author_name = entry.find('author').find('name') if entry.find('author') else None
            
            if video_id and title:
                video_info = {
                    'video_id': video_id.text,
                    'title': title.text,
                    'url': f"https://www.youtube.com/watch?v={video_id.text}",
                    'channel': author_name.text if author_name else "Unknown Channel",
                    'published_at': published.text if published else None
                }
                videos.append(video_info)
                
    except Exception as e:
        print(f"Error fetching RSS feed for {channel_url}: {e}")
        # RSS 실패 시 스크래핑 시도
        return fetch_channel_videos_scraping(channel_url, max_videos)
    
    return videos


def fetch_channel_videos_scraping(channel_url: str, max_videos: int = 3) -> List[dict]:
    """
    웹 스크래핑으로 YouTube 채널의 최신 영상 정보 가져오기 (RSS 실패 시 대체)
    """
    videos = []
    
    try:
        # 채널 비디오 페이지로 이동
        if "@" in channel_url:
            videos_url = f"{channel_url}/videos"
        else:
            videos_url = f"{channel_url}/videos" if not channel_url.endswith('/videos') else channel_url
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(videos_url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"Failed to fetch channel page: {videos_url}")
            return videos
        
        # 페이지에서 초기 데이터 추출
        match = re.search(r'var ytInitialData = ({.*?});', response.text)
        if not match:
            print(f"Could not find ytInitialData in page")
            return videos
        
        try:
            data = json.loads(match.group(1))
            
            # 비디오 목록 찾기 (YouTube 페이지 구조는 복잡하고 자주 변경됨)
            tabs = data.get('contents', {}).get('twoColumnBrowseResultsRenderer', {}).get('tabs', [])
            
            for tab in tabs:
                if 'tabRenderer' in tab and tab['tabRenderer'].get('selected'):
                    content = tab['tabRenderer'].get('content', {})
                    section_list = content.get('richGridRenderer', {}).get('contents', [])
                    
                    video_count = 0
                    for section in section_list:
                        if video_count >= max_videos:
                            break
                            
                        items = section.get('richItemRenderer', {}).get('content', {})
                        video_renderer = items.get('videoRenderer', {})
                        
                        if video_renderer:
                            video_id = video_renderer.get('videoId')
                            title_runs = video_renderer.get('title', {}).get('runs', [])
                            title = title_runs[0].get('text') if title_runs else None
                            
                            if video_id and title:
                                # 채널명 추출
                                channel_name = "Unknown Channel"
                                owner_text = video_renderer.get('ownerText', {}).get('runs', [])
                                if owner_text:
                                    channel_name = owner_text[0].get('text', channel_name)
                                
                                video_info = {
                                    'video_id': video_id,
                                    'title': title,
                                    'url': f"https://www.youtube.com/watch?v={video_id}",
                                    'channel': channel_name,
                                    'published_at': None  # 스크래핑으로는 정확한 날짜 얻기 어려움
                                }
                                videos.append(video_info)
                                video_count += 1
                                
        except json.JSONDecodeError as e:
            print(f"Failed to parse YouTube data: {e}")
            
    except Exception as e:
        print(f"Error scraping channel {channel_url}: {e}")
    
    return videos


def fetch_transcript(video_url: str, languages: List[str] | None = None, chunk_size: int = 10000) -> str | None:
    video_id = extract_video_id(video_url)
    if not video_id:
        return None
    if languages is None:
        # 영어를 최우선으로, 그 다음 한국어 (영어 자막이 더 정확한 경우가 많음)
        languages = ['en', 'en-US', 'ko', 'ja', 'de', 'fr', 'ru', 'it', 'es', 'pl', 'uk', 'nl', 'zh-TW', 'zh-CN', 'zh-Hant', 'zh-Hans']
    
    try:
        # YouTubeTranscriptApi의 get_transcript는 기본적으로 여러 언어를 시도함
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        text = ' '.join([item['text'] for item in transcript_list])
        return text[:chunk_size] if len(text) > chunk_size else text  # 너무 긴 경우 자르기
        
    except Exception as e:
        # 언어 지정 없이 시도
        try:
            # 사용 가능한 첫 번째 자막 가져오기
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            text = ' '.join([item['text'] for item in transcript_list])
            return text[:chunk_size] if len(text) > chunk_size else text
        except Exception as e2:
            print(f"Failed to fetch transcript for {video_url}: {e2}")
            # 자막이 없거나 비공개 영상일 수 있음
            return None


def build_youtube_item(url: str, title: str | None = None, channel: str | None = None) -> YoutubeItem | None:
    transcript = fetch_transcript(url)
    if transcript is None:
        return None
    
    # published_at 파싱 시도
    published_at = None
    
    return YoutubeItem(
        source="youtube",
        title=title or "YouTube Video",
        link=url,
        published_at=published_at,
        transcript=transcript,
        channel=channel,
    )


def fetch_channel_latest_videos(channel_urls: List[str], max_videos_per_channel: int = 3) -> List[YoutubeItem]:
    """
    여러 YouTube 채널에서 최신 영상을 가져와서 YoutubeItem 리스트로 반환
    
    Args:
        channel_urls: YouTube 채널 URL 리스트
        max_videos_per_channel: 각 채널당 가져올 최대 영상 수
    
    Returns:
        YoutubeItem 리스트
    """
    all_items = []
    
    for channel_url in channel_urls:
        print(f"Fetching videos from {channel_url}...")
        
        # RSS 또는 스크래핑으로 영상 정보 가져오기
        videos = fetch_channel_videos_rss(channel_url, max_videos_per_channel)
        
        if not videos:
            print(f"No videos found for {channel_url}")
            continue
        
        # 각 영상에 대해 transcript 가져와서 YoutubeItem 생성
        for video in videos:
            print(f"  Processing: {video['title'][:50]}...")
            
            item = build_youtube_item(
                url=video['url'],
                title=video['title'],
                channel=video['channel']
            )
            
            if item:
                # published_at 설정
                if video.get('published_at'):
                    try:
                        # ISO 8601 형식 파싱
                        item.published_at = datetime.fromisoformat(video['published_at'].replace('Z', '+00:00'))
                    except:
                        item.published_at = None
                
                all_items.append(item)
                print(f"    ✓ Added: {video['title'][:50]}...")
            else:
                print(f"    ✗ No transcript available for: {video['title'][:50]}...")
    
    return all_items