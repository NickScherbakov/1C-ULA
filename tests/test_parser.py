"""Тесты модуля Core.Parser."""
import os
import sys
import pytest

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.core.parser import parse_lines, parse_log_file, _parse_properties

_SAMPLE_DIR = os.path.join(os.path.dirname(__file__), 'sample_logs')


class TestParseProperties:
    """Юнит-тесты функции разбора свойств."""

    def test_simple_numeric(self):
        props = _parse_properties('duration=500,rows=10')
        assert props['duration'] == 500
        assert props['rows'] == 10

    def test_quoted_string(self):
        props = _parse_properties('Sql="SELECT * FROM t"')
        assert props['Sql'] == 'SELECT * FROM t'

    def test_quoted_with_escaped_quotes(self):
        props = _parse_properties('Descr="He said ""hello"""')
        assert props['Descr'] == 'He said "hello"'

    def test_mixed_properties(self):
        props = _parse_properties('process=rphost,Rows=150,Sql="SELECT 1"')
        assert props['process'] == 'rphost'
        assert props['Rows'] == 150
        assert props['Sql'] == 'SELECT 1'

    def test_key_without_value(self):
        props = _parse_properties('SomeFlag,key=val')
        assert props['SomeFlag'] is True
        assert props['key'] == 'val'

    def test_float_value(self):
        props = _parse_properties('ratio=1.5')
        assert props['ratio'] == 1.5

    def test_empty_string(self):
        props = _parse_properties('')
        assert props == {}


class TestParseTJFormat:
    """Тесты разбора формата технологического журнала."""

    def test_basic_event(self):
        lines = ['00:15.123456-0,SDBL,523,process=rphost,Rows=150']
        events = parse_lines(lines)
        assert len(events) == 1
        ev = events[0]
        assert ev['event_type'] == 'SDBL'
        assert ev['duration_ms'] == 523
        assert ev['timestamp_str'] == '00:15.123456'
        assert ev['pid'] == 0
        assert ev['format'] == 'tj'

    def test_properties_parsed(self):
        lines = ['00:16.234567-0,EXCP,0,process=rphost,Descr="Ошибка модуля"']
        ev = parse_lines(lines)[0]
        assert ev['properties']['process'] == 'rphost'
        assert ev['properties']['Descr'] == 'Ошибка модуля'

    def test_sql_with_spaces(self):
        lines = ['00:17.000000-0,SDBL,100,Sql="SELECT _IDRRef FROM _Reference42 WHERE _Fld = 1"']
        ev = parse_lines(lines)[0]
        assert 'SELECT' in ev['properties']['Sql']

    def test_tlock_event(self):
        lines = [
            '00:17.345678-0,TLOCK,1500,process=rphost,'
            'WaitConnections="4:S,5:X",Regions="AccumulationRegister.MyReg:RecordSet"'
        ]
        ev = parse_lines(lines)[0]
        assert ev['event_type'] == 'TLOCK'
        assert ev['duration_ms'] == 1500
        assert '4:S' in ev['properties']['WaitConnections']

    def test_mem_event(self):
        lines = ['00:18.456789-0,MEM,0,process=rphost,Memory=1073741824,VirtualMemory=2147483648']
        ev = parse_lines(lines)[0]
        assert ev['event_type'] == 'MEM'
        assert ev['properties']['Memory'] == 1073741824

    def test_call_event(self):
        lines = ['00:19.567890-0,CALL,15000,process=rphost,IName="ОбщийМодуль.ТяжелаяОперация"']
        ev = parse_lines(lines)[0]
        assert ev['event_type'] == 'CALL'
        assert ev['duration_ms'] == 15000

    def test_pid_parsing(self):
        lines = ['00:20.000000-12345,SDBL,100,Rows=1']
        ev = parse_lines(lines)[0]
        assert ev['pid'] == 12345

    def test_empty_lines_skipped(self):
        lines = ['', '  ', '00:01.000000-0,SDBL,100,Rows=1', '']
        events = parse_lines(lines)
        assert len(events) == 1

    def test_malformed_line_skipped(self):
        lines = ['not a valid log line at all', '00:01.000000-0,SDBL,100,Rows=1']
        events = parse_lines(lines)
        assert len(events) == 1

    def test_multiple_events(self):
        lines = [
            '00:01.000000-0,SDBL,100,Rows=1',
            '00:02.000000-0,EXCP,0,Descr="Error"',
            '00:03.000000-0,TLOCK,500,WaitConnections="1:X"',
        ]
        events = parse_lines(lines)
        assert len(events) == 3
        types = [e['event_type'] for e in events]
        assert types == ['SDBL', 'EXCP', 'TLOCK']


class TestParseOldFormat:
    """Тесты разбора старого формата {YYYYMMDDHHmmss,...}."""

    def test_basic_old_format(self):
        lines = ['{20240101120001,ERR,1cv8,client,Ошибка выполнения}']
        events = parse_lines(lines)
        assert len(events) == 1
        ev = events[0]
        assert ev['event_type'] == 'ERR'
        assert ev['timestamp_str'] == '20240101120001'
        assert ev['properties']['Descr'] == 'Ошибка выполнения'
        assert ev['format'] == 'old'

    def test_old_format_warn(self):
        lines = ['{20240101120002,WARN,1cv8,client,Предупреждение о чём-то}']
        ev = parse_lines(lines)[0]
        assert ev['event_type'] == 'WARN'

    def test_old_format_app_process(self):
        lines = ['{20240101120003,ERR,1cv8,server,Описание ошибки}']
        ev = parse_lines(lines)[0]
        assert ev['properties']['app'] == '1cv8'
        assert ev['properties']['process'] == 'server'


class TestParseLogFile:
    """Тесты чтения реальных файлов."""

    def test_parse_rphost_sample(self):
        path = os.path.join(_SAMPLE_DIR, 'sample_rphost.log')
        events = parse_log_file(path)
        assert len(events) >= 20
        for ev in events:
            assert 'event_type' in ev
            assert 'duration_ms' in ev
            assert 'properties' in ev

    def test_parse_rmngr_sample(self):
        path = os.path.join(_SAMPLE_DIR, 'sample_rmngr.log')
        events = parse_log_file(path)
        assert len(events) >= 20

    def test_parse_1cv8_sample(self):
        path = os.path.join(_SAMPLE_DIR, 'sample_1cv8.log')
        events = parse_log_file(path)
        assert len(events) >= 20
        for ev in events:
            assert ev['format'] == 'old'

    def test_parse_performance_10k(self, tmp_path):
        """Разбор 10 000 строк менее чем за 3 секунды."""
        import time
        log_file = tmp_path / 'perf_test.log'
        lines = []
        for i in range(10_000):
            lines.append(
                f'{i % 60:02d}:{i % 60:02d}.{i:06d}-0,'
                f'SDBL,{i % 2000},process=rphost,'
                f'Sql="SELECT _IDRRef FROM _Reference{i % 100}",Rows={i}'
            )
        log_file.write_text('\n'.join(lines), encoding='utf-8')

        t0 = time.perf_counter()
        events = parse_log_file(str(log_file))
        elapsed = time.perf_counter() - t0

        assert len(events) == 10_000
        assert elapsed < 3.0, f'Разбор занял {elapsed:.3f} с (лимит 3 с)'
