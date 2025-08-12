from __future__ import annotations

from typing import List
from datetime import datetime
from pathlib import Path
from src.models import ContentItem


def write_daily_md(path: str, title: str, items: List[ContentItem]) -> str:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Group items by source
    source_groups = {}
    for item in items:
        if item.source not in source_groups:
            source_groups[item.source] = []
        source_groups[item.source].append(item)
    
    lines = [f"# {title}", ""]
    
    # Add summary statistics
    total_items = len(items)
    lines.append(f"## 📊 수집 요약")
    lines.append(f"총 **{total_items}개** 항목이 수집되었습니다.")
    for source, source_items in source_groups.items():
        lines.append(f"- **{source}**: {len(source_items)}개")
    lines.append("")
    
    # Process each source group
    for source, source_items in source_groups.items():
        lines.append(f"## 📰 {source}")
        lines.append("")
        
        for item in source_items:
            lines.append(f"### {item.title}")
            if item.summary:
                lines.append("")
                lines.append(item.summary)
            lines.append("")
            lines.append(f"- **출처**: {item.source}")
            lines.append(f"- **링크**: [{item.link}]({item.link})")
            if item.tags:
                lines.append(f"- **태그**: {', '.join(item.tags)}")
            lines.append("")
            lines.append("---")
            lines.append("")
    
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return str(out_path)
