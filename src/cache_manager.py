import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
import pickle
import os
import re
from difflib import SequenceMatcher


class ContentCache:
    """콘텐츠 요약 결과를 캐싱하고 관리하는 클래스"""
    
    def __init__(self, cache_dir: str = "./cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.summary_cache_file = self.cache_dir / "summary_cache.pkl"
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        self.duplicate_cache_file = self.cache_dir / "duplicate_cache.pkl"
        
        # 캐시 로드
        self.summary_cache: Dict[str, dict] = self._load_cache()
        self.metadata = self._load_metadata()
        self.duplicate_cache: Dict[str, Set[str]] = self._load_duplicate_cache()
        
        # 중복 감지를 위한 제목 정규화 패턴
        self.title_normalization_patterns = [
            (r'\s+', ' '),  # 다중 공백을 단일 공백으로
            (r'[^\w\s]', ''),  # 특수문자 제거
            (r'\b(the|a|an)\b', ''),  # 관사 제거
            (r'\d+', ''),  # 숫자 제거 (버전 번호 등)
        ]
    
    def _load_cache(self) -> Dict[str, dict]:
        """캐시 파일에서 데이터 로드"""
        if self.summary_cache_file.exists():
            try:
                with open(self.summary_cache_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"캐시 로드 실패: {e}")
        return {}
    
    def _save_cache(self):
        """캐시 데이터를 파일에 저장"""
        try:
            with open(self.summary_cache_file, 'wb') as f:
                pickle.dump(self.summary_cache, f)
        except Exception as e:
            print(f"캐시 저장 실패: {e}")
    
    def _load_metadata(self) -> dict:
        """캐시 메타데이터 로드"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"메타데이터 로드 실패: {e}")
        return {"created_at": datetime.now().isoformat(), "cache_hits": 0, "cache_misses": 0}
    
    def _save_metadata(self):
        """메타데이터 저장"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"메타데이터 저장 실패: {e}")
    
    def _generate_cache_key(self, title: str, url: str, content: str) -> str:
        """콘텐츠의 고유 캐시 키 생성"""
        content_hash = hashlib.md5(f"{title}:{url}:{content[:100]}".encode()).hexdigest()
        return content_hash
    
    def get_cached_summary(self, title: str, url: str, content: str) -> Optional[dict]:
        """캐시된 요약 결과 조회"""
        cache_key = self._generate_cache_key(title, url, content)
        
        if cache_key in self.summary_cache:
            cached_item = self.summary_cache[cache_key]
            
            # 캐시 유효성 검사 (7일)
            cache_time = datetime.fromisoformat(cached_item['cached_at'])
            if datetime.now() - cache_time < timedelta(days=7):
                self.metadata['cache_hits'] += 1
                self._save_metadata()
                print(f"캐시 히트: {title[:50]}...")
                return cached_item['summary']
            else:
                # 만료된 캐시 삭제
                del self.summary_cache[cache_key]
        
        self.metadata['cache_misses'] += 1
        self._save_metadata()
        return None
    
    def cache_summary(self, title: str, url: str, content: str, summary: dict):
        """요약 결과를 캐시에 저장"""
        cache_key = self._generate_cache_key(title, url, content)
        
        self.summary_cache[cache_key] = {
            'title': title,
            'url': url,
            'summary': summary,
            'cached_at': datetime.now().isoformat()
        }
        
        self._save_cache()
        print(f"캐시 저장: {title[:50]}...")
    
    def get_cache_stats(self) -> dict:
        """캐시 통계 반환"""
        total_items = len(self.summary_cache)
        cache_hits = self.metadata.get('cache_hits', 0)
        cache_misses = self.metadata.get('cache_misses', 0)
        
        hit_rate = cache_hits / (cache_hits + cache_misses) * 100 if (cache_hits + cache_misses) > 0 else 0
        
        return {
            'total_cached_items': total_items,
            'cache_hits': cache_hits,
            'cache_misses': cache_misses,
            'hit_rate': f"{hit_rate:.1f}%",
            'cache_size_mb': self._get_cache_size_mb()
        }
    
    def _get_cache_size_mb(self) -> float:
        """캐시 파일 크기 (MB)"""
        if self.summary_cache_file.exists():
            size_bytes = self.summary_cache_file.stat().st_size
            return size_bytes / (1024 * 1024)
        return 0.0
    
    def clear_expired_cache(self, days: int = 7):
        """만료된 캐시 정리"""
        current_time = datetime.now()
        expired_keys = []
        
        for key, item in self.summary_cache.items():
            cache_time = datetime.fromisoformat(item['cached_at'])
            if current_time - cache_time > timedelta(days=days):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.summary_cache[key]
        
        if expired_keys:
            self._save_cache()
            print(f"{len(expired_keys)}개 만료된 캐시 항목 정리됨")
    
    def clear_all_cache(self):
        """모든 캐시 정리"""
        self.summary_cache.clear()
        self.duplicate_cache.clear()
        self._save_cache()
        self._save_duplicate_cache()
        print("모든 캐시가 정리되었습니다.")
    
    def _load_duplicate_cache(self) -> Dict[str, Set[str]]:
        """중복 캐시 로드"""
        if self.duplicate_cache_file.exists():
            try:
                with open(self.duplicate_cache_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"중복 캐시 로드 실패: {e}")
        return {}
    
    def _save_duplicate_cache(self):
        """중복 캐시 저장"""
        try:
            with open(self.duplicate_cache_file, 'wb') as f:
                pickle.dump(self.duplicate_cache, f)
        except Exception as e:
            print(f"중복 캐시 저장 실패: {e}")
    
    def _normalize_title(self, title: str) -> str:
        """제목 정규화 (중복 감지용)"""
        normalized = title.lower().strip()
        for pattern, replacement in self.title_normalization_patterns:
            normalized = re.sub(pattern, replacement, normalized)
        return normalized.strip()
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """두 텍스트의 유사도 계산 (0~1)"""
        return SequenceMatcher(None, text1, text2).ratio()
    
    def is_duplicate(self, title: str, content: str = "", threshold: float = 0.85) -> Tuple[bool, Optional[str]]:
        """
        중복 여부 확인
        
        Args:
            title: 확인할 제목
            content: 확인할 내용 (선택)
            threshold: 유사도 임계값 (0.85 = 85% 유사)
        
        Returns:
            (중복 여부, 중복된 원본 제목)
        """
        normalized_title = self._normalize_title(title)
        
        # 오늘 날짜 키
        today_key = datetime.now().strftime("%Y-%m-%d")
        
        # 오늘의 중복 캐시 초기화
        if today_key not in self.duplicate_cache:
            self.duplicate_cache[today_key] = set()
        
        # 기존 제목들과 비교
        for cached_title in self.duplicate_cache[today_key]:
            similarity = self._calculate_similarity(normalized_title, cached_title)
            if similarity >= threshold:
                return True, cached_title
        
        # 중복이 아니면 캐시에 추가
        self.duplicate_cache[today_key].add(normalized_title)
        self._save_duplicate_cache()
        
        # 7일 이상된 중복 캐시 정리
        self._clean_old_duplicate_cache()
        
        return False, None
    
    def _clean_old_duplicate_cache(self):
        """오래된 중복 캐시 정리"""
        cutoff_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        keys_to_remove = [key for key in self.duplicate_cache.keys() if key < cutoff_date]
        
        for key in keys_to_remove:
            del self.duplicate_cache[key]
        
        if keys_to_remove:
            self._save_duplicate_cache()
    
    def deduplicate_items(self, items: List, threshold: float = 0.85) -> List:
        """
        아이템 리스트에서 중복 제거
        
        Args:
            items: 중복 제거할 아이템 리스트
            threshold: 유사도 임계값
        
        Returns:
            중복이 제거된 아이템 리스트
        """
        unique_items = []
        seen_titles = set()
        
        for item in items:
            title = getattr(item, 'title', str(item))
            content = getattr(item, 'content', '')
            
            normalized = self._normalize_title(title)
            
            # 이미 본 제목과 비교
            is_dup = False
            for seen in seen_titles:
                if self._calculate_similarity(normalized, seen) >= threshold:
                    is_dup = True
                    print(f"  중복 제거: {title[:50]}...")
                    break
            
            if not is_dup:
                unique_items.append(item)
                seen_titles.add(normalized)
        
        print(f"중복 제거 완료: {len(items)}개 → {len(unique_items)}개")
        return unique_items


# 전역 캐시 인스턴스
content_cache = ContentCache()






