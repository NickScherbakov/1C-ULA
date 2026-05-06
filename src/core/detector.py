"""Core.Detector — определение типа лога платформы 1С."""
import os
import re
from typing import Optional

# Порядок важен: более специфичные шаблоны первыми.
# Для «ras» используем границу, не зависящую от того, что _ — символ слова в \b.
_FILENAME_PATTERNS = [
    ('dbgsrv', re.compile(r'dbgsrv', re.IGNORECASE)),
    ('rphost', re.compile(r'rphost', re.IGNORECASE)),
    ('rmngr', re.compile(r'rmngr', re.IGNORECASE)),
    ('ras', re.compile(r'(?<![a-zA-Z0-9])ras(?![a-zA-Z0-9])', re.IGNORECASE)),
    ('1cv8', re.compile(r'1cv8', re.IGNORECASE)),
]

_CONTENT_PATTERNS = [
    ('dbgsrv', re.compile(r'process=dbgsrv|DEBUGGER', re.IGNORECASE)),
    ('rphost', re.compile(r'process=rphost', re.IGNORECASE)),
    ('rmngr', re.compile(r'process=rmngr', re.IGNORECASE)),
    ('ras', re.compile(r'process=ras\b', re.IGNORECASE)),
    ('1cv8', re.compile(r'^\{[0-9]{14},', re.MULTILINE)),
]

# Типы логов, поддерживаемые анализатором
SUPPORTED_LOG_TYPES = ('rphost', 'rmngr', 'ras', 'dbgsrv', '1cv8')


def detect_log_type(filepath: str, scan_lines: int = 30) -> str:
    """Определяет тип лога по имени файла и содержимому.

    Args:
        filepath: Путь к файлу лога.
        scan_lines: Количество строк для анализа содержимого.

    Returns:
        Строка с типом лога: 'rphost', 'rmngr', 'ras', 'dbgsrv', '1cv8' или 'unknown'.
    """
    filename = os.path.basename(filepath).lower()

    for log_type, pattern in _FILENAME_PATTERNS:
        if pattern.search(filename):
            return log_type

    try:
        lines: list = []
        with open(filepath, 'r', encoding='utf-8', errors='replace') as fh:
            for i, line in enumerate(fh):
                if i >= scan_lines:
                    break
                lines.append(line)
        content = ''.join(lines)
        for log_type, pattern in _CONTENT_PATTERNS:
            if pattern.search(content):
                return log_type
    except OSError:
        pass

    return 'unknown'
