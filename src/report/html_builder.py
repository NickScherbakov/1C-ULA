"""Report.HTMLBuilder — генерация самодостаточного HTML-отчёта."""
import html
from typing import Any, Dict, List

# ─── CSS ────────────────────────────────────────────────────────────────────
_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 14px;
    background: #f4f6f9;
    color: #333;
    padding: 20px;
}
h1 { color: #2c3e50; margin-bottom: 6px; }
h2 { color: #34495e; margin: 24px 0 10px; font-size: 1.1em; text-transform: uppercase;
     letter-spacing: .05em; border-bottom: 2px solid #dde3ea; padding-bottom: 6px; }
.subtitle { color: #7f8c8d; font-size: 0.85em; margin-bottom: 20px; }
/* ─── карточки сводки ─────────────────────────────── */
.summary-cards { display: flex; flex-wrap: wrap; gap: 14px; margin-bottom: 24px; }
.card {
    background: #fff;
    border-radius: 8px;
    padding: 16px 22px;
    min-width: 160px;
    box-shadow: 0 1px 4px rgba(0,0,0,.08);
    flex: 1;
}
.card-title { font-size: 0.78em; color: #7f8c8d; text-transform: uppercase;
              letter-spacing: .06em; margin-bottom: 6px; }
.card-value { font-size: 2em; font-weight: 700; color: #2c3e50; }
/* ─── значки серьёзности ──────────────────────────── */
.badge {
    display: inline-block;
    padding: 2px 9px;
    border-radius: 12px;
    font-size: 0.75em;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .04em;
}
.badge-critical { background: #fde8e8; color: #c0392b; }
.badge-high     { background: #fef0e0; color: #e67e22; }
.badge-medium   { background: #fefce0; color: #d4a017; }
.badge-low      { background: #e0f4ff; color: #2980b9; }
/* ─── таблица событий ─────────────────────────────── */
.section-box {
    background: #fff;
    border-radius: 8px;
    padding: 18px 20px;
    margin-bottom: 20px;
    box-shadow: 0 1px 4px rgba(0,0,0,.08);
    overflow-x: auto;
}
table { width: 100%; border-collapse: collapse; font-size: 0.86em; }
th {
    background: #f0f3f7;
    color: #555;
    font-weight: 600;
    text-align: left;
    padding: 8px 10px;
    border-bottom: 2px solid #dde3ea;
    white-space: nowrap;
}
td {
    padding: 7px 10px;
    border-bottom: 1px solid #eef1f5;
    vertical-align: top;
    word-break: break-word;
    max-width: 400px;
}
tr:last-child td { border-bottom: none; }
tr:hover td { background: #f9fbfd; }
.mono { font-family: 'Consolas', 'Courier New', monospace; font-size: 0.9em; }
/* ─── список проблем ──────────────────────────────── */
.problem-item {
    border: 1px solid #eef1f5;
    border-radius: 6px;
    padding: 12px 14px;
    margin-bottom: 10px;
    display: flex;
    align-items: flex-start;
    gap: 10px;
}
.problem-item:last-child { margin-bottom: 0; }
.problem-body { flex: 1; }
.problem-desc { color: #555; font-size: 0.9em; margin-top: 4px; }
.problem-meta { color: #999; font-size: 0.8em; margin-top: 4px; }
/* ─── рекомендации ────────────────────────────────── */
.rec-item {
    background: #f8fff8;
    border-left: 4px solid #27ae60;
    border-radius: 0 6px 6px 0;
    padding: 14px 16px;
    margin-bottom: 14px;
}
.rec-title { font-weight: 600; color: #1e7a41; margin-bottom: 4px; }
.rec-desc { color: #555; font-size: 0.9em; margin-bottom: 10px; }
.rec-actions { padding-left: 20px; color: #444; font-size: 0.88em; }
.rec-actions li { margin-bottom: 4px; }
/* ─── кнопка "показать ещё" ───────────────────────── */
.btn-show-more {
    display: block;
    margin: 12px auto 0;
    padding: 7px 22px;
    background: #3498db;
    color: #fff;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.88em;
    transition: background .2s;
}
.btn-show-more:hover { background: #217dbb; }
.hidden-row { display: none; }
/* ─── пустое состояние ────────────────────────────── */
.empty { color: #aaa; font-style: italic; padding: 10px 0; }
"""

# ─── JavaScript ─────────────────────────────────────────────────────────────
_JS = """
function showMoreEvents() {
    var rows = document.querySelectorAll('.hidden-row');
    var btn = document.getElementById('btnShowMore');
    var shown = 0;
    rows.forEach(function(r) {
        if (r.style.display === '' || r.style.display === 'none') {
            r.style.display = 'table-row';
            shown++;
        }
    });
    if (btn) btn.style.display = 'none';
}
"""

_SEVERITY_ORDER = ['critical', 'high', 'medium', 'low']
_SEVERITY_RU = {
    'critical': 'Критично',
    'high': 'Высокий',
    'medium': 'Средний',
    'low': 'Низкий',
}

_INITIAL_ROWS = 100


def _esc(value: Any) -> str:
    """HTML-экранирование строкового значения."""
    return html.escape(str(value) if value is not None else '')


def _badge(severity: str) -> str:
    cls = f'badge badge-{_esc(severity)}'
    label = _SEVERITY_RU.get(severity, severity)
    return f'<span class="{cls}">{_esc(label)}</span>'


def _build_summary_cards(
    log_type: str,
    total_events: int,
    total_problems: int,
    counts_by_problem: Dict[str, int],
    analysis_time: float,
) -> str:
    parts = [
        f'<div class="card"><div class="card-title">Тип лога</div>'
        f'<div class="card-value" style="font-size:1.3em">{_esc(log_type)}</div></div>',
        f'<div class="card"><div class="card-title">Всего событий</div>'
        f'<div class="card-value">{total_events}</div></div>',
        f'<div class="card"><div class="card-title">Проблем выявлено</div>'
        f'<div class="card-value">{total_problems}</div></div>',
    ]
    for ptype, cnt in sorted(counts_by_problem.items()):
        from src.core.classifier import PROBLEM_LABELS
        label = PROBLEM_LABELS.get(ptype, ptype)
        parts.append(
            f'<div class="card"><div class="card-title">{_esc(label)}</div>'
            f'<div class="card-value">{cnt}</div></div>'
        )
    parts.append(
        f'<div class="card"><div class="card-title">Время анализа</div>'
        f'<div class="card-value" style="font-size:1.1em">{analysis_time:.3f} с</div></div>'
    )
    return '<div class="summary-cards">' + ''.join(parts) + '</div>'


def _build_events_table(events: List[Dict[str, Any]]) -> str:
    if not events:
        return '<p class="empty">Событий не обнаружено.</p>'

    rows_html: List[str] = []
    for idx, ev in enumerate(events):
        props = ev.get('properties') or {}
        # Краткое описание: Descr или первые два свойства
        descr = props.get('Descr') or props.get('descr') or ''
        if not descr:
            sample = ', '.join(
                f'{k}={v}' for k, v in list(props.items())[:3]
            )
            descr = sample
        hidden_cls = ' class="hidden-row"' if idx >= _INITIAL_ROWS else ''
        rows_html.append(
            f'<tr{hidden_cls}>'
            f'<td class="mono">{_esc(ev.get("timestamp_str",""))}</td>'
            f'<td><strong>{_esc(ev.get("event_type",""))}</strong></td>'
            f'<td>{_esc(ev.get("duration_ms", 0))}</td>'
            f'<td>{_esc(ev.get("pid", 0))}</td>'
            f'<td style="max-width:500px">{_esc(str(descr)[:300])}</td>'
            f'</tr>'
        )

    show_more_btn = ''
    if len(events) > _INITIAL_ROWS:
        hidden_count = len(events) - _INITIAL_ROWS
        show_more_btn = (
            f'<button class="btn-show-more" id="btnShowMore" onclick="showMoreEvents()">'
            f'Показать ещё {hidden_count} событий</button>'
        )

    table = (
        '<table>'
        '<thead><tr>'
        '<th>Время</th><th>Тип события</th><th>Длит. (мс)</th><th>PID</th><th>Описание</th>'
        '</tr></thead>'
        '<tbody>' + ''.join(rows_html) + '</tbody>'
        '</table>' + show_more_btn
    )
    return table


def _build_problems_list(problems: List[Dict[str, Any]]) -> str:
    if not problems:
        return '<p class="empty">Проблем не обнаружено.</p>'

    from src.core.classifier import PROBLEM_LABELS

    # Сортировка: сначала по серьёзности, потом по типу
    sev_idx = {s: i for i, s in enumerate(_SEVERITY_ORDER)}
    sorted_problems = sorted(
        problems,
        key=lambda p: sev_idx.get(p.get('severity', 'low'), 99),
    )

    items: List[str] = []
    for pr in sorted_problems:
        ptype = pr.get('type', '')
        sev = pr.get('severity', 'low')
        label = PROBLEM_LABELS.get(ptype, ptype)
        desc = pr.get('description', '')
        ev = pr.get('event') or {}
        ts = ev.get('timestamp_str', '')
        etype = ev.get('event_type', '')
        dur = ev.get('duration_ms', 0)
        meta = ''
        if ts or etype:
            meta_parts = []
            if ts:
                meta_parts.append(f'Время: {ts}')
            if etype:
                meta_parts.append(f'Событие: {etype}')
            if dur:
                meta_parts.append(f'Длит.: {dur} мс')
            meta = f'<div class="problem-meta">{_esc(" | ".join(meta_parts))}</div>'
        items.append(
            f'<div class="problem-item">'
            f'{_badge(sev)}'
            f'<div class="problem-body">'
            f'<strong>{_esc(label)}</strong>'
            f'<div class="problem-desc">{_esc(desc)}</div>'
            f'{meta}'
            f'</div></div>'
        )

    return ''.join(items)


def _build_recommendations(recommendations: List[Dict[str, Any]]) -> str:
    if not recommendations:
        return '<p class="empty">Рекомендации отсутствуют.</p>'

    items: List[str] = []
    for rec in recommendations:
        title = rec.get('title', '')
        desc = rec.get('description', '')
        actions = rec.get('actions') or []
        li_items = ''.join(f'<li>{_esc(a)}</li>' for a in actions)
        items.append(
            f'<div class="rec-item">'
            f'<div class="rec-title">{_esc(title)}</div>'
            f'<div class="rec-desc">{_esc(desc)}</div>'
            f'<ul class="rec-actions">{li_items}</ul>'
            f'</div>'
        )
    return ''.join(items)


def build_html_report(
    log_type: str,
    events: List[Dict[str, Any]],
    problems: List[Dict[str, Any]],
    recommendations: List[Dict[str, Any]],
    analysis_time: float,
    source_file: str = '',
) -> str:
    """Генерирует самодостаточный HTML-отчёт.

    Args:
        log_type: Тип лога.
        events: Список разобранных событий.
        problems: Список выявленных проблем.
        recommendations: Список рекомендаций.
        analysis_time: Время анализа в секундах.
        source_file: Путь к исходному файлу (только для отображения).

    Returns:
        Строка с полным HTML-документом.
    """
    counts_by_problem: Dict[str, int] = {}
    for pr in problems:
        ptype = pr.get('type', 'unknown')
        counts_by_problem[ptype] = counts_by_problem.get(ptype, 0) + 1

    summary_html = _build_summary_cards(
        log_type, len(events), len(problems), counts_by_problem, analysis_time
    )
    events_html = _build_events_table(events)
    problems_html = _build_problems_list(problems)
    recs_html = _build_recommendations(recommendations)

    subtitle = ''
    if source_file:
        subtitle = f'<div class="subtitle">Источник: {_esc(source_file)}</div>'

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Отчёт анализатора логов 1С</title>
<style>{_CSS}</style>
</head>
<body>
<h1>Анализатор логов 1С — Отчёт</h1>
{subtitle}
<h2>Сводка</h2>
{summary_html}
<h2>События <small style="font-size:.75em;color:#999;font-weight:400;text-transform:none">
  (первые {_INITIAL_ROWS} из {len(events)})</small></h2>
<div class="section-box">{events_html}</div>
<h2>Выявленные проблемы ({len(problems)})</h2>
<div class="section-box">{problems_html}</div>
<h2>Рекомендации ({len(recommendations)})</h2>
<div class="section-box">{recs_html}</div>
<script>{_JS}</script>
</body>
</html>"""
