"""UI.Form — графический интерфейс анализатора логов 1С на базе tkinter."""
import os
import sys
import threading
import time
import webbrowser
from typing import Any, Dict, List, Optional, Tuple

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    _TK_AVAILABLE = True
except ImportError:
    _TK_AVAILABLE = False


def _check_tk() -> None:
    if not _TK_AVAILABLE:
        print('Ошибка: модуль tkinter недоступен. Используйте CLI-режим.')
        sys.exit(1)


def _run_analysis(
    filepath: str,
) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], float]:
    """Выполняет полный цикл анализа и возвращает (log_type, events, problems, recs, time)."""
    # Импорты здесь, чтобы GUI загружался быстро
    from src.core.detector import detect_log_type
    from src.core.parser import parse_log_file
    from src.core.classifier import classify_events
    from src.core.knowledge_base import get_recommendations

    t0 = time.perf_counter()
    log_type = detect_log_type(filepath)
    events = parse_log_file(filepath)
    problems = classify_events(events)
    recommendations = get_recommendations(problems)
    elapsed = time.perf_counter() - t0
    return log_type, events, problems, recommendations, elapsed


class App(tk.Tk):
    """Главное окно приложения."""

    def __init__(self) -> None:
        super().__init__()
        self.title('1C Universal Log Analyzer')
        self.resizable(True, True)
        self.minsize(600, 420)

        # Результаты анализа
        self._log_type: str = ''
        self._events: List[Dict[str, Any]] = []
        self._problems: List[Dict[str, Any]] = []
        self._recommendations: List[Dict[str, Any]] = []
        self._analysis_time: float = 0.0
        self._json_content: str = ''
        self._html_content: str = ''

        self._build_ui()

    # ── построение интерфейса ────────────────────────────────────────────────

    def _build_ui(self) -> None:
        pad = {'padx': 12, 'pady': 6}

        # Заголовок
        title_frame = tk.Frame(self, bg='#2c3e50')
        title_frame.pack(fill=tk.X)
        tk.Label(
            title_frame,
            text='Анализатор логов платформы 1С',
            font=('Segoe UI', 14, 'bold'),
            bg='#2c3e50', fg='white',
            pady=10,
        ).pack()

        # Выбор файла
        file_frame = tk.LabelFrame(self, text='Файл лога', **pad)
        file_frame.pack(fill=tk.X, **pad)

        self._file_var = tk.StringVar(value='Файл не выбран')
        tk.Label(file_frame, textvariable=self._file_var, anchor='w',
                 width=60, relief=tk.SUNKEN).pack(side=tk.LEFT, padx=6, pady=6, fill=tk.X, expand=True)
        tk.Button(file_frame, text='Обзор…', command=self._browse_file,
                  width=10).pack(side=tk.RIGHT, padx=6, pady=6)

        # Кнопка анализа
        btn_frame = tk.Frame(self)
        btn_frame.pack(fill=tk.X, **pad)
        self._btn_analyze = tk.Button(
            btn_frame, text='Анализировать', command=self._start_analysis,
            bg='#27ae60', fg='white', font=('Segoe UI', 10, 'bold'),
            activebackground='#1e8449', relief=tk.FLAT, padx=20, pady=6,
        )
        self._btn_analyze.pack(side=tk.LEFT)

        # Прогресс-бар
        self._progress = ttk.Progressbar(self, mode='indeterminate')
        self._progress.pack(fill=tk.X, **pad)

        # Статус
        self._status_var = tk.StringVar(value='Выберите файл лога для начала анализа.')
        status_label = tk.Label(self, textvariable=self._status_var, anchor='w',
                                 fg='#555', wraplength=580)
        status_label.pack(fill=tk.X, padx=12, pady=2)

        # Результаты (только для чтения)
        result_frame = tk.LabelFrame(self, text='Результат', **pad)
        result_frame.pack(fill=tk.BOTH, expand=True, **pad)

        self._result_text = tk.Text(result_frame, height=8, state=tk.DISABLED,
                                     font=('Consolas', 9), bg='#f9f9f9')
        scrollbar = tk.Scrollbar(result_frame, command=self._result_text.yview)
        self._result_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._result_text.pack(fill=tk.BOTH, expand=True)

        # Кнопки сохранения / открытия
        save_frame = tk.Frame(self)
        save_frame.pack(fill=tk.X, **pad)

        self._btn_json = tk.Button(
            save_frame, text='Сохранить JSON', command=self._save_json,
            state=tk.DISABLED, width=16,
        )
        self._btn_json.pack(side=tk.LEFT, padx=4)

        self._btn_html = tk.Button(
            save_frame, text='Сохранить HTML', command=self._save_html,
            state=tk.DISABLED, width=16,
        )
        self._btn_html.pack(side=tk.LEFT, padx=4)

        self._btn_open = tk.Button(
            save_frame, text='Открыть HTML', command=self._open_html,
            state=tk.DISABLED, width=16, bg='#3498db', fg='white',
            activebackground='#217dbb', relief=tk.FLAT,
        )
        self._btn_open.pack(side=tk.LEFT, padx=4)

    # ── обработчики событий ──────────────────────────────────────────────────

    def _browse_file(self) -> None:
        path = filedialog.askopenfilename(
            title='Выберите файл лога 1С',
            filetypes=[('Файлы лога', '*.log'), ('Все файлы', '*.*')],
        )
        if path:
            self._file_var.set(path)
            self._status_var.set('Файл выбран. Нажмите «Анализировать».')

    def _start_analysis(self) -> None:
        filepath = self._file_var.get()
        if not filepath or filepath == 'Файл не выбран':
            messagebox.showwarning('Внимание', 'Выберите файл лога.')
            return
        if not os.path.isfile(filepath):
            messagebox.showerror('Ошибка', f'Файл не найден:\n{filepath}')
            return

        self._btn_analyze.config(state=tk.DISABLED)
        for btn in (self._btn_json, self._btn_html, self._btn_open):
            btn.config(state=tk.DISABLED)
        self._set_result_text('')
        self._status_var.set('Анализ выполняется…')
        self._progress.start(10)

        thread = threading.Thread(target=self._analysis_thread, args=(filepath,), daemon=True)
        thread.start()

    def _analysis_thread(self, filepath: str) -> None:
        try:
            log_type, events, problems, recs, elapsed = _run_analysis(filepath)
            self._log_type = log_type
            self._events = events
            self._problems = problems
            self._recommendations = recs
            self._analysis_time = elapsed

            # Формируем отчёты
            from src.report.json_builder import build_json_report
            from src.report.html_builder import build_html_report
            self._json_content = build_json_report(
                log_type, events, problems, recs, elapsed)
            self._html_content = build_html_report(
                log_type, events, problems, recs, elapsed, source_file=filepath)

            self.after(0, lambda: self._on_analysis_done(filepath, elapsed, len(events), len(problems)))
        except Exception as exc:  # pylint: disable=broad-except
            msg = str(exc)
            self.after(0, lambda: self._on_analysis_error(msg))

    def _on_analysis_done(
        self, filepath: str, elapsed: float, n_events: int, n_problems: int
    ) -> None:
        self._progress.stop()
        self._btn_analyze.config(state=tk.NORMAL)
        for btn in (self._btn_json, self._btn_html, self._btn_open):
            btn.config(state=tk.NORMAL)

        status = (
            f'Готово за {elapsed:.3f} с. '
            f'Событий: {n_events}, проблем: {n_problems}, '
            f'тип лога: {self._log_type}.'
        )
        self._status_var.set(status)

        summary_lines = [
            f'Файл:          {filepath}',
            f'Тип лога:      {self._log_type}',
            f'Событий:       {n_events}',
            f'Проблем:       {n_problems}',
            f'Время анализа: {elapsed:.3f} с',
            '',
        ]
        from src.core.classifier import PROBLEM_LABELS
        counts: Dict[str, int] = {}
        for pr in self._problems:
            ptype = pr.get('type', 'unknown')
            counts[ptype] = counts.get(ptype, 0) + 1
        if counts:
            summary_lines.append('Проблемы по типам:')
            for ptype, cnt in sorted(counts.items()):
                label = PROBLEM_LABELS.get(ptype, ptype)
                summary_lines.append(f'  {label}: {cnt}')

        self._set_result_text('\n'.join(summary_lines))

    def _on_analysis_error(self, msg: str) -> None:
        self._progress.stop()
        self._btn_analyze.config(state=tk.NORMAL)
        self._status_var.set(f'Ошибка анализа: {msg}')
        messagebox.showerror('Ошибка анализа', msg)

    def _save_json(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension='.json',
            filetypes=[('JSON', '*.json'), ('Все файлы', '*.*')],
            title='Сохранить JSON-отчёт',
        )
        if path:
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(self._json_content)
            self._status_var.set(f'JSON-отчёт сохранён: {path}')

    def _save_html(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension='.html',
            filetypes=[('HTML', '*.html'), ('Все файлы', '*.*')],
            title='Сохранить HTML-отчёт',
        )
        if path:
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(self._html_content)
            self._status_var.set(f'HTML-отчёт сохранён: {path}')

    def _open_html(self) -> None:
        import tempfile
        # Создаём временный файл рядом со скриптом
        out_dir = os.path.dirname(os.path.abspath(__file__))
        tmp_path = os.path.join(out_dir, '_report_preview.html')
        with open(tmp_path, 'w', encoding='utf-8') as fh:
            fh.write(self._html_content)
        webbrowser.open(f'file://{tmp_path}')

    # ── утилиты ──────────────────────────────────────────────────────────────

    def _set_result_text(self, text: str) -> None:
        self._result_text.config(state=tk.NORMAL)
        self._result_text.delete('1.0', tk.END)
        self._result_text.insert(tk.END, text)
        self._result_text.config(state=tk.DISABLED)


def launch_ui() -> None:
    """Запускает графический интерфейс."""
    _check_tk()
    app = App()
    app.mainloop()
