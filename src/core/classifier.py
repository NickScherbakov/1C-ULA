"""Core.Classifier — классификация событий лога платформы 1С."""
from typing import Any, Dict, List

# Пороговые значения
_SLOW_SQL_MS = 500
_LONG_TX_MS = 2000
_SLOW_CALL_MS = 10_000
_MEMORY_THRESHOLD = 1024 * 1024 * 1024  # 1 ГБ

# Типы проблем → человекочитаемые названия
PROBLEM_LABELS: Dict[str, str] = {
    'error':            'Ошибка',
    'warning':          'Предупреждение',
    'slow_sql':         'Медленный SQL-запрос',
    'deadlock':         'Взаимная блокировка',
    'lock_wait':        'Ожидание блокировки',
    'long_transaction': 'Долгая транзакция',
    'memory_issue':     'Проблема с памятью',
    'slow_call':        'Медленный вызов',
}

# Уровни серьёзности
SEVERITY: Dict[str, str] = {
    'error':            'critical',
    'deadlock':         'critical',
    'lock_wait':        'high',
    'long_transaction': 'high',
    'memory_issue':     'high',
    'slow_sql':         'medium',
    'slow_call':        'medium',
    'warning':          'low',
}

# Типы событий, напрямую указывающие на транзакции БД
_DB_TX_EVENTS = frozenset({'DBPOSTGRS', 'DBORACLE', 'DBMSSQL', 'DBMSSQLCONN'})


def _get_memory(props: Dict[str, Any]) -> int:
    """Возвращает значение Memory из свойств события (в байтах)."""
    raw = props.get('Memory', props.get('memory', 0))
    if isinstance(raw, (int, float)):
        return int(raw)
    try:
        return int(str(raw).strip())
    except (ValueError, TypeError):
        return 0


def classify_event(event: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Классифицирует одно событие и возвращает список обнаруженных проблем."""
    problems: List[Dict[str, Any]] = []
    event_type: str = (event.get('event_type') or '').upper()
    duration_ms: int = int(event.get('duration_ms') or 0)
    props: Dict[str, Any] = event.get('properties') or {}

    def _problem(ptype: str, description: str) -> Dict[str, Any]:
        return {
            'type': ptype,
            'severity': SEVERITY.get(ptype, 'low'),
            'event': event,
            'description': description,
        }

    # ── Ошибки ──────────────────────────────────────────────────────────────
    if event_type in ('EXCP', 'ERR'):
        descr = str(props.get('Descr') or props.get('descr') or '')
        msg = f'Исключение: {descr}' if descr else 'Ошибка платформы 1С'
        problems.append(_problem('error', msg))

    # ── Предупреждения ───────────────────────────────────────────────────────
    if event_type == 'WARNING':
        descr = str(props.get('Descr') or props.get('descr') or 'Предупреждение')
        problems.append(_problem('warning', descr))

    # ── Медленный SQL (SDBL) ─────────────────────────────────────────────────
    if event_type == 'SDBL' and duration_ms > _SLOW_SQL_MS:
        sql_text = str(props.get('Sql') or props.get('sql') or '')
        snippet = sql_text[:200] + ('...' if len(sql_text) > 200 else '')
        problems.append(_problem(
            'slow_sql',
            f'Медленный SQL-запрос: {duration_ms} мс. SQL: {snippet}',
        ))

    # ── Взаимная блокировка ──────────────────────────────────────────────────
    if event_type == 'TDEADLOCK':
        problems.append(_problem('deadlock', 'Обнаружена взаимная блокировка (TDEADLOCK)'))

    # ── Ожидание блокировки ──────────────────────────────────────────────────
    if event_type == 'TLOCK':
        wc = props.get('WaitConnections') or ''
        rg = props.get('Regions') or ''
        desc = 'Ожидание блокировки'
        if wc:
            desc += f'. Конкурирующие соединения: {wc}'
        if rg:
            desc += f'. Области: {rg}'
        if duration_ms:
            desc += f'. Длительность: {duration_ms} мс'
        problems.append(_problem('lock_wait', desc))

    # ── Долгие транзакции БД ─────────────────────────────────────────────────
    if event_type in _DB_TX_EVENTS and duration_ms > _LONG_TX_MS:
        problems.append(_problem(
            'long_transaction',
            f'Долгая транзакция СУБД ({event_type}): {duration_ms} мс',
        ))

    # ── Проблемы с памятью ───────────────────────────────────────────────────
    if event_type == 'MEM':
        mem = _get_memory(props)
        if mem > _MEMORY_THRESHOLD:
            gb = mem / (1024 ** 3)
            problems.append(_problem(
                'memory_issue',
                f'Высокое потребление памяти: {gb:.2f} ГБ',
            ))

    # ── Медленные серверные вызовы ───────────────────────────────────────────
    if event_type == 'CALL' and duration_ms > _SLOW_CALL_MS:
        problems.append(_problem(
            'slow_call',
            f'Медленный серверный вызов: {duration_ms} мс',
        ))

    return problems


def classify_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Классифицирует список событий и возвращает список всех проблем."""
    problems: List[Dict[str, Any]] = []
    for event in events:
        problems.extend(classify_event(event))
    return problems
