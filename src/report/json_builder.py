"""Report.JSONBuilder — генерация JSON-отчёта."""
import json
from typing import Any, Dict, List


def _event_to_dict(event: Dict[str, Any]) -> Dict[str, Any]:
    """Подготавливает событие для сериализации в JSON."""
    return {
        'timestamp_str': event.get('timestamp_str', ''),
        'pid': event.get('pid', 0),
        'event_type': event.get('event_type', ''),
        'duration_ms': event.get('duration_ms', 0),
        'properties': event.get('properties') or {},
        'format': event.get('format', 'unknown'),
    }


def _problem_to_dict(problem: Dict[str, Any]) -> Dict[str, Any]:
    """Подготавливает проблему для сериализации в JSON."""
    ev = problem.get('event') or {}
    return {
        'type': problem.get('type', ''),
        'severity': problem.get('severity', ''),
        'description': problem.get('description', ''),
        'event_timestamp': ev.get('timestamp_str', ''),
        'event_type': ev.get('event_type', ''),
        'duration_ms': ev.get('duration_ms', 0),
    }


def build_json_report(
    log_type: str,
    events: List[Dict[str, Any]],
    problems: List[Dict[str, Any]],
    recommendations: List[Dict[str, Any]],
    analysis_time: float,
) -> str:
    """Генерирует JSON-отчёт в виде отформатированной строки.

    Args:
        log_type: Тип лога (rphost, rmngr, ...).
        events: Список разобранных событий.
        problems: Список выявленных проблем.
        recommendations: Список рекомендаций.
        analysis_time: Время анализа в секундах.

    Returns:
        Строка JSON с отступами.
    """
    counts_by_event: Dict[str, int] = {}
    for ev in events:
        etype = ev.get('event_type') or 'UNKNOWN'
        counts_by_event[etype] = counts_by_event.get(etype, 0) + 1

    counts_by_problem: Dict[str, int] = {}
    for pr in problems:
        ptype = pr.get('type') or 'unknown'
        counts_by_problem[ptype] = counts_by_problem.get(ptype, 0) + 1

    report = {
        'summary': {
            'log_type': log_type,
            'total_events': len(events),
            'total_problems': len(problems),
            'counts_by_event_type': counts_by_event,
            'counts_by_problem_type': counts_by_problem,
            'analysis_time_sec': round(analysis_time, 3),
        },
        'events': [_event_to_dict(e) for e in events],
        'problems': [_problem_to_dict(p) for p in problems],
        'recommendations': recommendations,
    }

    return json.dumps(report, ensure_ascii=False, indent=2)
