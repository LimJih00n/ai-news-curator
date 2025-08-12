import asyncio
import concurrent.futures
from typing import List, Dict, Any
from dataclasses import dataclass
import time
from src.summarizers.openai_summarizer import summarize
from src.summarizers.detailed_summarizer import summarize_with_details, DetailedSummary
from src.cache_manager import content_cache
from src.models import ContentItem, Summary


@dataclass
class SummarizationTask:
    """요약 작업 정보"""
    item: Any
    task_id: int
    status: str = "pending"  # pending, processing, completed, failed
    result: DetailedSummary = None  # 상세 요약 결과
    error: str = None
    start_time: float = 0
    end_time: float = 0


class ParallelSummarizer:
    """병렬 요약 처리기"""
    
    def __init__(self, openai_api_key: str, max_workers: int = 5):
        self.openai_api_key = openai_api_key
        self.max_workers = max_workers
        self.tasks: List[SummarizationTask] = []
        self.results: List[ContentItem] = []
    
    def add_task(self, item: Any) -> int:
        """요약 작업 추가"""
        task_id = len(self.tasks)
        task = SummarizationTask(item=item, task_id=task_id)
        self.tasks.append(task)
        return task_id
    
    def _process_single_item(self, task: SummarizationTask) -> SummarizationTask:
        """단일 항목 요약 처리 (한줄 + 상세 요약)"""
        try:
            task.status = "processing"
            task.start_time = time.time()
            
            # 캐시 확인 (기존 형태)
            cached_summary = content_cache.get_cached_summary(
                task.item.title, 
                task.item.link, 
                task.item.content or ""
            )
            
            if cached_summary and 'detailed_summary' in cached_summary:
                # 새로운 캐시 형태 (상세 요약 포함)
                task.result = DetailedSummary(
                    title=cached_summary['title'],
                    url=cached_summary['url'],
                    brief_summary=cached_summary.get('summary', cached_summary.get('brief_summary', '')),
                    detailed_summary=cached_summary['detailed_summary']
                )
                task.status = "completed"
                print(f"상세 캐시 사용: {task.item.title[:50]}...")
            elif cached_summary:
                # 기존 캐시 형태 (한줄 요약만)
                brief_summary = cached_summary['summary']
                # 기존 한줄 요약을 기반으로 상세 요약 생성
                detailed_summary = summarize_with_details(
                    self.openai_api_key,
                    task.item.title,
                    task.item.link,
                    task.item.content or ""
                )
                task.result = detailed_summary
                task.status = "completed"
                
                # 새로운 형태로 캐시 업데이트
                content_cache.cache_summary(
                    task.item.title,
                    task.item.link,
                    task.item.content or "",
                    {
                        'title': detailed_summary.title,
                        'url': detailed_summary.url,
                        'brief_summary': detailed_summary.brief_summary,
                        'detailed_summary': detailed_summary.detailed_summary
                    }
                )
                print(f"캐시 업그레이드: {task.item.title[:50]}...")
            else:
                # 새로운 상세 요약 생성
                detailed_summary = summarize_with_details(
                    self.openai_api_key,
                    task.item.title,
                    task.item.link,
                    task.item.content or ""
                )
                task.result = detailed_summary
                task.status = "completed"
                
                # 캐시에 저장
                content_cache.cache_summary(
                    task.item.title,
                    task.item.link,
                    task.item.content or "",
                    {
                        'title': detailed_summary.title,
                        'url': detailed_summary.url,
                        'brief_summary': detailed_summary.brief_summary,
                        'detailed_summary': detailed_summary.detailed_summary
                    }
                )
                print(f"상세 요약 완료: {task.item.title[:50]}...")
            
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            print(f"요약 실패: {task.item.title[:50]}... Error: {e}")
        
        finally:
            task.end_time = time.time()
        
        return task
    
    def process_parallel(self, items: List[Any]) -> List[ContentItem]:
        """병렬로 요약 처리"""
        print(f"병렬 요약 시작: {len(items)}개 항목, {self.max_workers}개 워커")
        
        # 작업 추가
        for item in items:
            self.add_task(item)
        
        # 병렬 처리
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 모든 작업 제출
            future_to_task = {
                executor.submit(self._process_single_item, task): task 
                for task in self.tasks
            }
            
            # 완료된 작업 처리
            completed_count = 0
            for future in concurrent.futures.as_completed(future_to_task):
                task = future_to_task[future]
                completed_count += 1
                
                if task.status == "completed":
                    # ContentItem 생성 (상세 요약 포함)
                    content_item = ContentItem(
                        source=task.item.source,
                        title=task.item.title,
                        link=task.item.link,
                        published_at=getattr(task.item, 'published_at', None),
                        raw_content=task.item.content,
                        summary=task.result.brief_summary if task.result else None,
                    )
                    # 상세 요약 추가
                    if task.result:
                        content_item.detailed_summary = task.result.detailed_summary
                    
                    # 중요도 점수들 보존 (content_filter.py에서 추가된 속성들)
                    if hasattr(task.item, 'importance_score'):
                        content_item.importance_score = task.item.importance_score
                    if hasattr(task.item, 'relevance_score'):
                        content_item.relevance_score = task.item.relevance_score
                    if hasattr(task.item, 'combined_score'):
                        content_item.combined_score = task.item.combined_score
                    if hasattr(task.item, 'score_reason'):
                        content_item.score_reason = task.item.score_reason
                    
                    self.results.append(content_item)
                
                # 진행률 표시
                progress = (completed_count / len(self.tasks)) * 100
                print(f"진행률: {progress:.1f}% ({completed_count}/{len(self.tasks)})")
        
        # 결과 통계
        successful = len([t for t in self.tasks if t.status == "completed"])
        failed = len([t for t in self.tasks if t.status == "failed"])
        
        print(f"병렬 요약 완료: 성공 {successful}개, 실패 {failed}개")
        
        # 성능 통계
        total_time = sum(t.end_time - t.start_time for t in self.tasks if t.end_time > 0)
        avg_time = total_time / len(self.tasks) if self.tasks else 0
        
        print(f"총 소요 시간: {total_time:.2f}초, 평균: {avg_time:.2f}초/항목")
        
        return self.results
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """성능 통계 반환"""
        completed_tasks = [t for t in self.tasks if t.status == "completed"]
        failed_tasks = [t for t in self.tasks if t.status == "failed"]
        
        if not completed_tasks:
            return {"error": "완료된 작업이 없습니다"}
        
        processing_times = [t.end_time - t.start_time for t in completed_tasks if t.end_time > 0]
        
        return {
            "total_tasks": len(self.tasks),
            "completed": len(completed_tasks),
            "failed": len(failed_tasks),
            "success_rate": f"{(len(completed_tasks) / len(self.tasks)) * 100:.1f}%",
            "total_time": sum(processing_times),
            "avg_time": sum(processing_times) / len(processing_times) if processing_times else 0,
            "min_time": min(processing_times) if processing_times else 0,
            "max_time": max(processing_times) if processing_times else 0
        }


# 사용 예시
def summarize_items_parallel(openai_api_key: str, items: List[Any], max_workers: int = 5) -> List[ContentItem]:
    """병렬로 여러 항목 요약"""
    summarizer = ParallelSummarizer(openai_api_key, max_workers)
    return summarizer.process_parallel(items)

