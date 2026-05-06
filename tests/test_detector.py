"""Тесты модуля Core.Detector."""
import os
import sys
import pytest

# Добавляем корень проекта в путь поиска модулей
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.core.detector import detect_log_type

_SAMPLE_DIR = os.path.join(os.path.dirname(__file__), 'sample_logs')


class TestDetectByFilename:
    """Определение типа лога по имени файла."""

    def test_rphost_filename(self, tmp_path):
        f = tmp_path / 'rphost_24010112.log'
        f.write_text('', encoding='utf-8')
        assert detect_log_type(str(f)) == 'rphost'

    def test_rmngr_filename(self, tmp_path):
        f = tmp_path / 'rmngr_24010112.log'
        f.write_text('', encoding='utf-8')
        assert detect_log_type(str(f)) == 'rmngr'

    def test_ras_filename(self, tmp_path):
        f = tmp_path / 'ras_24010112.log'
        f.write_text('', encoding='utf-8')
        assert detect_log_type(str(f)) == 'ras'

    def test_dbgsrv_filename(self, tmp_path):
        f = tmp_path / 'dbgsrv_24010112.log'
        f.write_text('', encoding='utf-8')
        assert detect_log_type(str(f)) == 'dbgsrv'

    def test_1cv8_filename(self, tmp_path):
        f = tmp_path / '1cv8.log'
        f.write_text('', encoding='utf-8')
        assert detect_log_type(str(f)) == '1cv8'

    def test_case_insensitive(self, tmp_path):
        f = tmp_path / 'RPHOST_24010112.LOG'
        f.write_text('', encoding='utf-8')
        assert detect_log_type(str(f)) == 'rphost'


class TestDetectByContent:
    """Определение типа лога по содержимому."""

    def test_rphost_content(self, tmp_path):
        f = tmp_path / 'unknown.log'
        f.write_text(
            '00:01.000000-0,SDBL,100,process=rphost,Sql="SELECT 1"\n',
            encoding='utf-8',
        )
        assert detect_log_type(str(f)) == 'rphost'

    def test_rmngr_content(self, tmp_path):
        f = tmp_path / 'unknown.log'
        f.write_text(
            '00:01.000000-0,HASP,0,process=rmngr,IName="cluster"\n',
            encoding='utf-8',
        )
        assert detect_log_type(str(f)) == 'rmngr'

    def test_1cv8_old_format_content(self, tmp_path):
        f = tmp_path / 'unknown.log'
        f.write_text(
            '{20240101120000,ERR,1cv8,client,Ошибка}\n',
            encoding='utf-8',
        )
        assert detect_log_type(str(f)) == '1cv8'

    def test_unknown_returns_unknown(self, tmp_path):
        f = tmp_path / 'totally_unknown.log'
        f.write_text(
            'some random content line 1\nsome random content line 2\n',
            encoding='utf-8',
        )
        assert detect_log_type(str(f)) == 'unknown'

    def test_missing_file_returns_unknown(self, tmp_path):
        result = detect_log_type(str(tmp_path / 'nonexistent.log'))
        assert result == 'unknown'


class TestDetectSampleFiles:
    """Определение типа лога на реальных тестовых файлах."""

    def test_sample_rphost(self):
        path = os.path.join(_SAMPLE_DIR, 'sample_rphost.log')
        assert detect_log_type(path) == 'rphost'

    def test_sample_rmngr(self):
        path = os.path.join(_SAMPLE_DIR, 'sample_rmngr.log')
        assert detect_log_type(path) == 'rmngr'

    def test_sample_1cv8(self):
        path = os.path.join(_SAMPLE_DIR, 'sample_1cv8.log')
        assert detect_log_type(path) == '1cv8'
