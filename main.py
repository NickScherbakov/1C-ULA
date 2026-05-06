#!/usr/bin/env python3
"""Точка входа в анализатор логов платформы 1С (1C-ULA).

Режимы запуска:
  CLI: python main.py <logfile> [--json output.json] [--html output.html]
  GUI: python main.py
"""
import argparse
import os
import sys
import time

# Гарантируем, что пакет src находится в пути поиска
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _run_cli(args: argparse.Namespace) -> int:
    """Выполняет анализ в режиме командной строки."""
    from src.core.detector import detect_log_type
    from src.core.parser import parse_log_file
    from src.core.classifier import classify_events
    from src.core.knowledge_base import get_recommendations
    from src.report.json_builder import build_json_report
    from src.report.html_builder import build_html_report

    filepath: str = args.logfile
    if not os.path.isfile(filepath):
        print(f'Ошибка: файл не найден: {filepath}', file=sys.stderr)
        return 1

    print(f'Анализируется: {filepath}')
    t0 = time.perf_counter()

    log_type = detect_log_type(filepath)
    print(f'  Тип лога:    {log_type}')

    events = parse_log_file(filepath)
    print(f'  Событий:     {len(events)}')

    problems = classify_events(events)
    print(f'  Проблем:     {len(problems)}')

    recommendations = get_recommendations(problems)
    elapsed = time.perf_counter() - t0
    print(f'  Время:       {elapsed:.3f} с')

    if args.json:
        json_content = build_json_report(
            log_type, events, problems, recommendations, elapsed
        )
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, 'w', encoding='utf-8') as fh:
            fh.write(json_content)
        print(f'  JSON-отчёт: {args.json}')

    if args.html:
        html_content = build_html_report(
            log_type, events, problems, recommendations, elapsed,
            source_file=filepath,
        )
        os.makedirs(os.path.dirname(os.path.abspath(args.html)), exist_ok=True)
        with open(args.html, 'w', encoding='utf-8') as fh:
            fh.write(html_content)
        print(f'  HTML-отчёт: {args.html}')

    if not args.json and not args.html:
        print('\nПодсказка: укажите --json <файл> и/или --html <файл> для сохранения отчётов.')

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Анализатор технологического журнала платформы 1С',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            'Примеры:\n'
            '  python main.py rphost_24010112.log --json report.json --html report.html\n'
            '  python main.py  # запуск GUI'
        ),
    )
    parser.add_argument(
        'logfile', nargs='?', default=None,
        help='Путь к файлу лога 1С',
    )
    parser.add_argument(
        '--json', metavar='FILE',
        help='Путь для сохранения JSON-отчёта',
    )
    parser.add_argument(
        '--html', metavar='FILE',
        help='Путь для сохранения HTML-отчёта',
    )

    args = parser.parse_args()

    if args.logfile:
        sys.exit(_run_cli(args))
    else:
        from src.ui.form import launch_ui
        launch_ui()


if __name__ == '__main__':
    main()
