import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pickle
import os


class ContentCache:
    """콘텐츠 요약 결과를 캐싱하고 관리하는 클래스"""
    
    def __init__(self, cache_dir: str = "./cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.summary_cache_file = self.cache_dir / "summary_cache.pkl"
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        
        # 캐시 로드
        self.summary_cache: Dict[str, dict] = self._load_cache()
        self.metadata = self._load_metadata()
    
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
        self._save_cache()
        print("모든 캐시가 정리되었습니다.")


# 전역 캐시 인스턴스
content_cache = ContentCache()

