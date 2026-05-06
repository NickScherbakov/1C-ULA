"""Core.Parser — разбор строк лога платформы 1С.

Поддерживаемые форматы:
  ТЖ (технологический журнал):
      MM:SS.microseconds-pid,EVENT,duration_ms[,key=value,...]
  Старый формат:
      {YYYYMMDDHHmmss,LEVEL,AppName,process,description}
"""
import re
from typing import Any, Dict, Iterator, List, Optional

# Регулярные выражения для двух форматов
_TJ_RE = re.compile(
    r'^(\d{1,2}:\d{2}\.\d+)-(\d+),'   # MM:SS.usec-pid
    r'([A-Z][A-Z0-9_]*),'              # EVENT
    r'(\d+)'                            # duration_ms
    r'(.*?)$',                          # optional ,key=value...
    re.DOTALL,
)

_OLD_RE = re.compile(
    r'^\{(\d{14}),'     # timestamp 14 digits
    r'([^,}]+),'        # level / event
    r'([^,}]*),'        # app name
    r'([^,}]*),'        # process
    r'(.*?)\}$',        # description
    re.DOTALL,
)


def _parse_properties(props_str: str) -> Dict[str, Any]:
    """Разбирает строку свойств формата key=value,key="value",...

    Поддерживает:
      - числовые значения (int/float)
      - строки в кавычках с экранированием ""
      - ключи без значений
    """
    props: Dict[str, Any] = {}
    i = 0
    n = len(props_str)

    while i < n:
        # Пропуск разделителей
        while i < n and props_str[i] in ', \t\r\n':
            i += 1
        if i >= n:
            break

        # Чтение ключа
        key_start = i
        while i < n and props_str[i] not in '=,\r\n':
            i += 1
        key = props_str[key_start:i].strip()

        if i >= n or props_str[i] != '=':
            if key:
                props[key] = True
            if i < n and props_str[i] == ',':
                i += 1
            continue

        i += 1  # пропуск '='

        if i >= n:
            if key:
                props[key] = None
            break

        # Чтение значения
        if props_str[i] == '"':
            i += 1  # пропуск открывающей кавычки
            chars: list = []
            while i < n:
                ch = props_str[i]
                if ch == '"':
                    if i + 1 < n and props_str[i + 1] == '"':
                        chars.append('"')
                        i += 2
                    else:
                        i += 1  # пропуск закрывающей кавычки
                        break
                else:
                    chars.append(ch)
                    i += 1
            value: Any = ''.join(chars)
        else:
            val_start = i
            while i < n and props_str[i] != ',':
                i += 1
            raw = props_str[val_start:i].strip()
            try:
                f = float(raw)
                has_decimal = '.' in raw
                has_exp = 'e' in raw.lower()
                is_whole = (f == int(f))
                value = int(f) if (is_whole and not has_decimal and not has_exp) else f
            except (ValueError, TypeError):
                value = raw

        # Пропуск запятой-разделителя
        if i < n and props_str[i] == ',':
            i += 1

        if key:
            props[key] = value

    return props


def _parse_tj_line(line: str) -> Optional[Dict[str, Any]]:
    """Разбирает строку технологического журнала."""
    m = _TJ_RE.match(line)
    if not m:
        return None

    timestamp_str = m.group(1)
    pid = int(m.group(2))
    event_type = m.group(3)
    duration_ms = int(m.group(4))
    props_tail = m.group(5)

    properties: Dict[str, Any] = {}
    if props_tail:
        raw = props_tail.lstrip(',')
        if raw:
            properties = _parse_properties(raw)

    return {
        'timestamp_str': timestamp_str,
        'pid': pid,
        'event_type': event_type,
        'duration_ms': duration_ms,
        'properties': properties,
        'raw_line': line,
        'format': 'tj',
    }


def _parse_old_line(line: str) -> Optional[Dict[str, Any]]:
    """Разбирает строку старого формата {YYYYMMDDHHmmss,...}."""
    m = _OLD_RE.match(line.strip())
    if not m:
        return None

    return {
        'timestamp_str': m.group(1),
        'pid': 0,
        'event_type': m.group(2).strip().upper(),
        'duration_ms': 0,
        'properties': {
            'app': m.group(3).strip(),
            'process': m.group(4).strip(),
            'Descr': m.group(5).strip(),
        },
        'raw_line': line,
        'format': 'old',
    }


def parse_log_file_iter(filepath: str) -> Iterator[Dict[str, Any]]:
    """Генератор событий из файла лога (эффективен для больших файлов)."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as fh:
        for raw_line in fh:
            line = raw_line.rstrip('\r\n')
            if not line.strip():
                continue
            event = _parse_tj_line(line) or _parse_old_line(line)
            if event:
                yield event


def parse_log_file(filepath: str) -> List[Dict[str, Any]]:
    """Разбирает файл лога и возвращает список событий."""
    return list(parse_log_file_iter(filepath))


def parse_lines(lines: List[str]) -> List[Dict[str, Any]]:
    """Разбирает список строк и возвращает список событий (для тестирования)."""
    events: List[Dict[str, Any]] = []
    for line in lines:
        stripped = line.rstrip('\r\n')
        if not stripped.strip():
            continue
        event = _parse_tj_line(stripped) or _parse_old_line(stripped)
        if event:
            events.append(event)
    return events
