"""Тесты модуля Core.Classifier."""
import os
import sys
import pytest

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.core.classifier import classify_event, classify_events

_SAMPLE_DIR = os.path.join(os.path.dirname(__file__), 'sample_logs')


def _make_event(event_type: str, duration_ms: int = 0, **props) -> dict:
    """Вспомогательная функция для создания тестового события."""
    return {
        'timestamp_str': '00:01.000000',
        'pid': 0,
        'event_type': event_type,
        'duration_ms': duration_ms,
        'properties': props,
        'raw_line': '',
        'format': 'tj',
    }


class TestErrorClassification:
    """Классификация ошибок."""

    def test_excp_is_error(self):
        ev = _make_event('EXCP', 0, Descr='Ошибка в модуле')
        problems = classify_event(ev)
        types = [p['type'] for p in problems]
        assert 'error' in types

    def test_excp_severity_critical(self):
        ev = _make_event('EXCP', 0, Descr='Ошибка')
        problems = classify_event(ev)
        error_problems = [p for p in problems if p['type'] == 'error']
        assert error_problems[0]['severity'] == 'critical'

    def test_err_event_type_is_error(self):
        ev = _make_event('ERR', 0, Descr='Системная ошибка')
        problems = classify_event(ev)
        types = [p['type'] for p in problems]
        assert 'error' in types

    def test_error_description_included(self):
        ev = _make_event('EXCP', 0, Descr='Конкретное описание ошибки')
        problems = classify_event(ev)
        error = next(p for p in problems if p['type'] == 'error')
        assert 'Конкретное описание ошибки' in error['description']

    def test_normal_event_no_error(self):
        ev = _make_event('SDBL', 100)
        problems = classify_event(ev)
        assert all(p['type'] != 'error' for p in problems)


class TestWarningClassification:
    """Классификация предупреждений."""

    def test_warning_event(self):
        ev = _make_event('WARNING', 0, Descr='Что-то не так')
        problems = classify_event(ev)
        types = [p['type'] for p in problems]
        assert 'warning' in types

    def test_warning_severity_low(self):
        ev = _make_event('WARNING', 0, Descr='Предупреждение')
        problems = classify_event(ev)
        warn = next(p for p in problems if p['type'] == 'warning')
        assert warn['severity'] == 'low'


class TestSlowSQLClassification:
    """Классификация медленных SQL-запросов."""

    def test_sdbl_over_500ms_is_slow(self):
        ev = _make_event('SDBL', 501, Sql='SELECT * FROM t')
        problems = classify_event(ev)
        types = [p['type'] for p in problems]
        assert 'slow_sql' in types

    def test_sdbl_exactly_500ms_not_slow(self):
        ev = _make_event('SDBL', 500, Sql='SELECT * FROM t')
        problems = classify_event(ev)
        assert all(p['type'] != 'slow_sql' for p in problems)

    def test_sdbl_under_500ms_not_slow(self):
        ev = _make_event('SDBL', 100, Sql='SELECT * FROM t')
        problems = classify_event(ev)
        assert all(p['type'] != 'slow_sql' for p in problems)

    def test_slow_sql_contains_duration(self):
        ev = _make_event('SDBL', 1234, Sql='SELECT * FROM big_table')
        problems = classify_event(ev)
        slow = next(p for p in problems if p['type'] == 'slow_sql')
        assert '1234' in slow['description']

    def test_slow_sql_severity_medium(self):
        ev = _make_event('SDBL', 600)
        problems = classify_event(ev)
        slow = next((p for p in problems if p['type'] == 'slow_sql'), None)
        assert slow is not None
        assert slow['severity'] == 'medium'


class TestDeadlockClassification:
    """Классификация взаимных блокировок."""

    def test_tdeadlock_is_deadlock(self):
        ev = _make_event('TDEADLOCK', 0)
        problems = classify_event(ev)
        types = [p['type'] for p in problems]
        assert 'deadlock' in types

    def test_deadlock_severity_critical(self):
        ev = _make_event('TDEADLOCK', 0)
        problems = classify_event(ev)
        dl = next(p for p in problems if p['type'] == 'deadlock')
        assert dl['severity'] == 'critical'

    def test_tlock_is_lock_wait(self):
        ev = _make_event('TLOCK', 1500, WaitConnections='4:S,5:X')
        problems = classify_event(ev)
        types = [p['type'] for p in problems]
        assert 'lock_wait' in types

    def test_lock_wait_severity_high(self):
        ev = _make_event('TLOCK', 500)
        problems = classify_event(ev)
        lw = next(p for p in problems if p['type'] == 'lock_wait')
        assert lw['severity'] == 'high'

    def test_lock_wait_includes_connections(self):
        ev = _make_event('TLOCK', 500, WaitConnections='4:S,5:X')
        problems = classify_event(ev)
        lw = next(p for p in problems if p['type'] == 'lock_wait')
        assert '4:S' in lw['description']


class TestLongTransactionClassification:
    """Классификация долгих транзакций."""

    def test_dbpostgrs_over_2000ms(self):
        ev = _make_event('DBPOSTGRS', 2001)
        problems = classify_event(ev)
        types = [p['type'] for p in problems]
        assert 'long_transaction' in types

    def test_dboracle_over_2000ms(self):
        ev = _make_event('DBORACLE', 3000)
        problems = classify_event(ev)
        types = [p['type'] for p in problems]
        assert 'long_transaction' in types

    def test_dbmssql_over_2000ms(self):
        ev = _make_event('DBMSSQL', 2500)
        problems = classify_event(ev)
        types = [p['type'] for p in problems]
        assert 'long_transaction' in types

    def test_dbpostgrs_under_2000ms_not_flagged(self):
        ev = _make_event('DBPOSTGRS', 2000)
        problems = classify_event(ev)
        assert all(p['type'] != 'long_transaction' for p in problems)

    def test_long_tx_severity_high(self):
        ev = _make_event('DBPOSTGRS', 5000)
        problems = classify_event(ev)
        lt = next(p for p in problems if p['type'] == 'long_transaction')
        assert lt['severity'] == 'high'


class TestMemoryClassification:
    """Классификация проблем с памятью."""

    def test_mem_over_1gb_is_issue(self):
        ev = _make_event('MEM', 0, Memory=1024 * 1024 * 1024 + 1)  # 1 ГБ + 1 байт
        problems = classify_event(ev)
        types = [p['type'] for p in problems]
        assert 'memory_issue' in types

    def test_mem_exactly_1gb_not_flagged(self):
        ev = _make_event('MEM', 0, Memory=1073741824)  # ровно 1 ГБ
        problems = classify_event(ev)
        assert all(p['type'] != 'memory_issue' for p in problems)

    def test_mem_under_1gb_not_flagged(self):
        ev = _make_event('MEM', 0, Memory=536870912)  # 512 МБ
        problems = classify_event(ev)
        assert all(p['type'] != 'memory_issue' for p in problems)

    def test_mem_issue_severity_high(self):
        ev = _make_event('MEM', 0, Memory=2147483648)  # 2 ГБ
        problems = classify_event(ev)
        mi = next(p for p in problems if p['type'] == 'memory_issue')
        assert mi['severity'] == 'high'

    def test_mem_description_has_gb(self):
        ev = _make_event('MEM', 0, Memory=2147483648)
        problems = classify_event(ev)
        mi = next(p for p in problems if p['type'] == 'memory_issue')
        assert 'ГБ' in mi['description']


class TestSlowCallClassification:
    """Классификация медленных вызовов."""

    def test_call_over_10s_is_slow(self):
        ev = _make_event('CALL', 10001)
        problems = classify_event(ev)
        types = [p['type'] for p in problems]
        assert 'slow_call' in types

    def test_call_exactly_10s_not_flagged(self):
        ev = _make_event('CALL', 10000)
        problems = classify_event(ev)
        assert all(p['type'] != 'slow_call' for p in problems)

    def test_slow_call_severity_medium(self):
        ev = _make_event('CALL', 15000)
        problems = classify_event(ev)
        sc = next(p for p in problems if p['type'] == 'slow_call')
        assert sc['severity'] == 'medium'


class TestMultipleProblemsInOneEvent:
    """Одно событие может порождать несколько проблем."""

    def test_no_double_classification_on_normal_sdbl(self):
        ev = _make_event('SDBL', 100, Sql='SELECT 1')
        problems = classify_event(ev)
        assert problems == []

    def test_classify_events_aggregates(self):
        events = [
            _make_event('EXCP', 0, Descr='Ошибка'),
            _make_event('SDBL', 600, Sql='SELECT * FROM t'),
            _make_event('TDEADLOCK', 0),
            _make_event('MEM', 0, Memory=2147483648),
        ]
        problems = classify_events(events)
        types = {p['type'] for p in problems}
        assert 'error' in types
        assert 'slow_sql' in types
        assert 'deadlock' in types
        assert 'memory_issue' in types


class TestClassifyRealLogs:
    """Тесты классификации на реальных файлах."""

    def test_rphost_sample_has_problems(self):
        from src.core.parser import parse_log_file
        path = os.path.join(_SAMPLE_DIR, 'sample_rphost.log')
        events = parse_log_file(path)
        problems = classify_events(events)
        assert len(problems) > 0

    def test_1cv8_sample_has_errors(self):
        from src.core.parser import parse_log_file
        path = os.path.join(_SAMPLE_DIR, 'sample_1cv8.log')
        events = parse_log_file(path)
        problems = classify_events(events)
        error_problems = [p for p in problems if p['type'] == 'error']
        assert len(error_problems) > 0

    def test_classification_accuracy_threshold(self):
        """Проверяем, что все заранее известные проблемы классифицированы."""
        # 8 событий с гарантированными проблемами
        known_problem_events = [
            _make_event('EXCP', 0, Descr='Ошибка'),          # error
            _make_event('SDBL', 600, Sql='SELECT 1'),          # slow_sql
            _make_event('TDEADLOCK', 0),                       # deadlock
            _make_event('TLOCK', 100, WaitConnections='1:X'),  # lock_wait
            _make_event('DBPOSTGRS', 3000),                    # long_transaction
            _make_event('MEM', 0, Memory=2147483648),          # memory_issue
            _make_event('CALL', 15000),                        # slow_call
            _make_event('WARNING', 0, Descr='Предупреждение'), # warning
        ]
        # 2 нормальных события
        normal_events = [
            _make_event('SDBL', 100, Sql='SELECT 1'),
            _make_event('CALL', 50),
        ]
        all_events = known_problem_events + normal_events
        problems = classify_events(all_events)

        # Все 8 известных проблем должны быть найдены
        problem_types = {p['type'] for p in problems}
        expected = {'error', 'slow_sql', 'deadlock', 'lock_wait',
                    'long_transaction', 'memory_issue', 'slow_call', 'warning'}
        assert expected.issubset(problem_types)
        # Нормальные события не должны порождать ложных срабатываний
        normal_problems = [
            p for p in problems
            if p['event'] in normal_events
        ]
        assert len(normal_problems) == 0
