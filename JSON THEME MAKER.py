import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import json
import os
import shutil
import uuid
import sqlite3
import psycopg2
from datetime import datetime
from PIL import Image, ImageTk
from pathlib import Path
import sys

# Добавляем путь к проекту для импорта модулей
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    from config import MEDIA_DIR, QUESTIONS_DIR, DB_ENGINE
    from utils.validators import validate_question_data, validate_topic_data, validate_json_structure

    CONFIG_AVAILABLE = True
except ImportError:
    # Fallback значения если config недоступен
    MEDIA_DIR = "data/media"
    QUESTIONS_DIR = "data/questions"
    DB_ENGINE = "sqlite:///data/history_bot.db"
    CONFIG_AVAILABLE = False
    print("⚠️ Конфигурация проекта недоступна, используются значения по умолчанию")


class EnhancedQuizEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Улучшенный редактор вопросов для телеграм-бота")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)

        # Переменные для хранения данных
        self.current_file_path = None
        self.data = {"topic": {"id": 1, "name": "", "description": ""}, "questions": []}
        self.current_question_index = -1
        self.image_path = None
        self.temp_image_path = None
        self.unsaved_changes = False

        # Статистика
        self.stats = {
            "total_questions": 0,
            "by_difficulty": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            "by_type": {"single": 0, "multiple": 0, "sequence": 0}
        }

        # Настройка стилей
        self.setup_styles()

        # Создание интерфейса
        self.create_menu()
        self.create_toolbar()
        self.create_main_frame()
        self.create_status_bar()

        # Обновление интерфейса
        self.update_topic_info()
        self.update_questions_list()
        self.update_stats()

        # Привязка событий
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_styles(self):
        """Настройка стилей интерфейса"""
        style = ttk.Style()
        style.theme_use('clam')

        # Настраиваем цвета
        style.configure('Toolbar.TFrame', background='#f0f0f0')
        style.configure('Status.TLabel', background='#e0e0e0', padding=5)
        style.configure('Stats.TLabelframe', relief='raised')

    def create_toolbar(self):
        """Создание панели инструментов с дополнительными функциями"""
        toolbar = ttk.Frame(self.root, style='Toolbar.TFrame')
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        # Основные операции
        file_frame = ttk.LabelFrame(toolbar, text="Файл")
        file_frame.pack(side=tk.LEFT, padx=5)

        ttk.Button(file_frame, text="Новый", command=self.new_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(file_frame, text="Открыть", command=self.open_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(file_frame, text="Сохранить", command=self.save_file).pack(side=tk.LEFT, padx=2)

        # Операции с темами
        topic_frame = ttk.LabelFrame(toolbar, text="Тема")
        topic_frame.pack(side=tk.LEFT, padx=5)

        ttk.Button(topic_frame, text="Редактировать", command=self.edit_topic).pack(side=tk.LEFT, padx=2)
        ttk.Button(topic_frame, text="Проверить", command=self.validate_topic).pack(side=tk.LEFT, padx=2)

        # Операции с вопросами
        question_frame = ttk.LabelFrame(toolbar, text="Вопросы")
        question_frame.pack(side=tk.LEFT, padx=5)

        ttk.Button(question_frame, text="Добавить", command=self.add_question).pack(side=tk.LEFT, padx=2)
        ttk.Button(question_frame, text="Дублировать", command=self.duplicate_question).pack(side=tk.LEFT, padx=2)
        ttk.Button(question_frame, text="Удалить", command=self.delete_question).pack(side=tk.LEFT, padx=2)

        # Импорт/Экспорт
        import_frame = ttk.LabelFrame(toolbar, text="Импорт/Экспорт")
        import_frame.pack(side=tk.LEFT, padx=5)

        ttk.Button(import_frame, text="Импорт JSON", command=self.import_from_json).pack(side=tk.LEFT, padx=2)
        ttk.Button(import_frame, text="Экспорт JSON", command=self.export_to_json).pack(side=tk.LEFT, padx=2)

        if CONFIG_AVAILABLE:
            ttk.Button(import_frame, text="Импорт в БД", command=self.import_to_database).pack(side=tk.LEFT, padx=2)

        # Утилиты
        utils_frame = ttk.LabelFrame(toolbar, text="Утилиты")
        utils_frame.pack(side=tk.LEFT, padx=5)

        ttk.Button(utils_frame, text="Поиск", command=self.show_search).pack(side=tk.LEFT, padx=2)
        ttk.Button(utils_frame, text="Проверка дубликатов", command=self.check_duplicates).pack(side=tk.LEFT, padx=2)

    def create_main_frame(self):
        """Создание основного интерфейса с улучшенным функционалом"""
        # Создаем split view
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Левая панель
        left_frame = ttk.Frame(main_paned, width=350)
        main_paned.add(left_frame, weight=1)

        # Информация о теме с дополнительной статистикой
        topic_frame = ttk.LabelFrame(left_frame, text="Информация о теме", style='Stats.TLabelframe')
        topic_frame.pack(fill=tk.X, padx=5, pady=5)

        self.topic_name_label = ttk.Label(topic_frame, text="Название: ")
        self.topic_name_label.pack(anchor=tk.W, padx=5, pady=2)

        self.topic_desc_label = ttk.Label(topic_frame, text="Описание: ")
        self.topic_desc_label.pack(anchor=tk.W, padx=5, pady=2)

        # Статистика вопросов
        stats_frame = ttk.LabelFrame(left_frame, text="Статистика", style='Stats.TLabelframe')
        stats_frame.pack(fill=tk.X, padx=5, pady=5)

        self.stats_label = ttk.Label(stats_frame, text="")
        self.stats_label.pack(anchor=tk.W, padx=5, pady=2)

        # Поиск и фильтрация
        search_frame = ttk.LabelFrame(left_frame, text="Поиск и фильтрация")
        search_frame.pack(fill=tk.X, padx=5, pady=5)

        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.on_search_change)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, placeholder_text="Поиск вопросов...")
        search_entry.pack(fill=tk.X, padx=5, pady=2)

        filter_frame = ttk.Frame(search_frame)
        filter_frame.pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(filter_frame, text="Сложность:").pack(side=tk.LEFT)
        self.difficulty_filter = ttk.Combobox(filter_frame, values=["Все", "1", "2", "3", "4", "5"], state="readonly",
                                              width=8)
        self.difficulty_filter.set("Все")
        self.difficulty_filter.pack(side=tk.LEFT, padx=5)
        self.difficulty_filter.bind("<<ComboboxSelected>>", self.on_filter_change)

        ttk.Label(filter_frame, text="Тип:").pack(side=tk.LEFT, padx=(10, 0))
        self.type_filter = ttk.Combobox(filter_frame, values=["Все", "single", "multiple", "sequence"],
                                        state="readonly", width=10)
        self.type_filter.set("Все")
        self.type_filter.pack(side=tk.LEFT, padx=5)
        self.type_filter.bind("<<ComboboxSelected>>", self.on_filter_change)

        # Список вопросов с улучшенным отображением
        questions_frame = ttk.LabelFrame(left_frame, text="Вопросы")
        questions_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Фрейм для списка с прокруткой
        list_frame = ttk.Frame(questions_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.questions_list = ttk.Treeview(list_frame,
                                           columns=("type", "difficulty", "status"),
                                           show="tree headings",
                                           selectmode="browse")

        self.questions_list.heading("#0", text="Вопрос")
        self.questions_list.heading("type", text="Тип")
        self.questions_list.heading("difficulty", text="Сложность")
        self.questions_list.heading("status", text="Статус")

        self.questions_list.column("#0", width=200)
        self.questions_list.column("type", width=80)
        self.questions_list.column("difficulty", width=80)
        self.questions_list.column("status", width=80)

        # Скроллбар для списка
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.questions_list.yview)
        self.questions_list.configure(yscrollcommand=scrollbar.set)

        self.questions_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.questions_list.bind("<<TreeviewSelect>>", self.on_question_select)
        self.questions_list.bind("<Double-1>", self.on_question_double_click)

        # Правая панель - редактор с вкладками
        right_frame = ttk.Frame(main_paned, width=800)
        main_paned.add(right_frame, weight=2)

        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Вкладка редактирования
        self.create_editor_tab()

        # Вкладка предварительного просмотра
        self.create_preview_tab()

        # Вкладка валидации
        self.create_validation_tab()

    def create_editor_tab(self):
        """Создание вкладки редактирования"""
        editor_tab = ttk.Frame(self.notebook)
        self.notebook.add(editor_tab, text="Редактирование")

        # Скроллируемый фрейм
        canvas = tk.Canvas(editor_tab)
        scrollbar = ttk.Scrollbar(editor_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Основная информация
        info_frame = ttk.LabelFrame(scrollable_frame, text="Основная информация")
        info_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(info_frame, text="Текст вопроса:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.question_text = tk.Text(info_frame, height=5, wrap=tk.WORD)
        self.question_text.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W + tk.E)
        self.question_text.bind('<KeyRelease>', self.on_text_change)

        ttk.Label(info_frame, text="Тип вопроса:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.question_type = ttk.Combobox(info_frame, values=["single", "multiple", "sequence"], state="readonly")
        self.question_type.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        self.question_type.set("single")
        self.question_type.bind("<<ComboboxSelected>>", self.on_question_type_change)

        ttk.Label(info_frame, text="Сложность:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.question_difficulty = ttk.Spinbox(info_frame, from_=1, to=5, width=5)
        self.question_difficulty.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        self.question_difficulty.set(1)
        self.question_difficulty.bind('<KeyRelease>', self.on_text_change)

        ttk.Label(info_frame, text="Объяснение:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.question_explanation = tk.Text(info_frame, height=3, wrap=tk.WORD)
        self.question_explanation.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W + tk.E)
        self.question_explanation.bind('<KeyRelease>', self.on_text_change)

        info_frame.columnconfigure(1, weight=1)

        # Варианты ответов с улучшенным интерфейсом
        options_frame = ttk.LabelFrame(scrollable_frame, text="Варианты ответов")
        options_frame.pack(fill=tk.X, padx=10, pady=5)

        self.options_frame = ttk.Frame(options_frame)
        self.options_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.options_list = []

        options_buttons = ttk.Frame(options_frame)
        options_buttons.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(options_buttons, text="Добавить вариант", command=self.add_option).pack(side=tk.LEFT, padx=2)
        ttk.Button(options_buttons, text="Удалить выбранный", command=self.delete_option).pack(side=tk.LEFT, padx=2)
        ttk.Button(options_buttons, text="Переместить вверх", command=self.move_option_up).pack(side=tk.LEFT, padx=2)
        ttk.Button(options_buttons, text="Переместить вниз", command=self.move_option_down).pack(side=tk.LEFT, padx=2)

        # Правильные ответы
        answers_frame = ttk.LabelFrame(scrollable_frame, text="Правильные ответы")
        answers_frame.pack(fill=tk.X, padx=10, pady=5)

        self.answers_frame = ttk.Frame(answers_frame)
        self.answers_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Изображение
        media_frame = ttk.LabelFrame(scrollable_frame, text="Изображение")
        media_frame.pack(fill=tk.X, padx=10, pady=5)

        self.media_preview = ttk.Label(media_frame, text="Нет изображения")
        self.media_preview.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        media_buttons = ttk.Frame(media_frame)
        media_buttons.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(media_buttons, text="Выбрать изображение", command=self.select_image).pack(side=tk.LEFT, padx=2)
        ttk.Button(media_buttons, text="Удалить изображение", command=self.remove_image).pack(side=tk.LEFT, padx=2)
        ttk.Button(media_buttons, text="Предварительный просмотр", command=self.preview_image).pack(side=tk.LEFT,
                                                                                                    padx=2)

        # Кнопки действий
        actions_frame = ttk.Frame(scrollable_frame)
        actions_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(actions_frame, text="Применить изменения", command=self.save_question_changes).pack(side=tk.RIGHT,
                                                                                                       padx=5)
        ttk.Button(actions_frame, text="Отменить изменения", command=self.cancel_question_changes).pack(side=tk.RIGHT,
                                                                                                        padx=5)
        ttk.Button(actions_frame, text="Проверить вопрос", command=self.validate_current_question).pack(side=tk.RIGHT,
                                                                                                        padx=5)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def create_preview_tab(self):
        """Создание вкладки предварительного просмотра"""
        preview_tab = ttk.Frame(self.notebook)
        self.notebook.add(preview_tab, text="Предварительный просмотр")

        # Фрейм предварительного просмотра
        preview_frame = ttk.LabelFrame(preview_tab, text="Как будет выглядеть в боте")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.preview_text = tk.Text(preview_frame, state=tk.DISABLED, wrap=tk.WORD,
                                    font=("Arial", 12), padx=10, pady=10)
        self.preview_text.pack(fill=tk.BOTH, expand=True)

        # Кнопки предварительного просмотра
        preview_buttons = ttk.Frame(preview_tab)
        preview_buttons.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(preview_buttons, text="Обновить предварительный просмотр",
                   command=self.update_preview).pack(side=tk.LEFT, padx=5)
        ttk.Button(preview_buttons, text="Скопировать текст",
                   command=self.copy_preview_text).pack(side=tk.LEFT, padx=5)

    def create_validation_tab(self):
        """Создание вкладки валидации"""
        validation_tab = ttk.Frame(self.notebook)
        self.notebook.add(validation_tab, text="Проверка")

        # Результаты валидации
        validation_frame = ttk.LabelFrame(validation_tab, text="Результаты проверки")
        validation_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.validation_tree = ttk.Treeview(validation_frame, columns=("type", "message"), show="tree headings")
        self.validation_tree.heading("#0", text="Элемент")
        self.validation_tree.heading("type", text="Тип")
        self.validation_tree.heading("message", text="Сообщение")

        self.validation_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Кнопки валидации
        validation_buttons = ttk.Frame(validation_tab)
        validation_buttons.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(validation_buttons, text="Проверить все",
                   command=self.validate_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(validation_buttons, text="Проверить текущий вопрос",
                   command=self.validate_current_question).pack(side=tk.LEFT, padx=5)
        ttk.Button(validation_buttons, text="Очистить результаты",
                   command=self.clear_validation_results).pack(side=tk.LEFT, padx=5)

    def create_status_bar(self):
        """Создание строки состояния"""
        status_frame = ttk.Frame(self.root, style='Toolbar.TFrame')
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_label = ttk.Label(status_frame, text="Готов", style='Status.TLabel')
        self.status_label.pack(side=tk.LEFT, padx=5)

        self.file_label = ttk.Label(status_frame, text="Новый файл", style='Status.TLabel')
        self.file_label.pack(side=tk.RIGHT, padx=5)

    # Новые методы для улучшенной функциональности

    def on_text_change(self, event=None):
        """Обработчик изменения текста"""
        self.unsaved_changes = True
        self.update_window_title()

    def on_search_change(self, *args):
        """Обработчик изменения поискового запроса"""
        self.update_questions_list()

    def on_filter_change(self, event=None):
        """Обработчик изменения фильтров"""
        self.update_questions_list()

    def on_question_double_click(self, event):
        """Обработчик двойного клика по вопросу"""
        self.notebook.select(0)  # Переключаем на вкладку редактирования

    def update_window_title(self):
        """Обновление заголовка окна"""
        title = "Улучшенный редактор вопросов"
        if self.current_file_path:
            title += f" - {os.path.basename(self.current_file_path)}"
        else:
            title += " - Новый файл"

        if self.unsaved_changes:
            title += " *"

        self.root.title(title)

    def update_stats(self):
        """Обновление статистики"""
        self.stats = {
            "total_questions": len(self.data["questions"]),
            "by_difficulty": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            "by_type": {"single": 0, "multiple": 0, "sequence": 0}
        }

        for question in self.data["questions"]:
            difficulty = question.get("difficulty", 1)
            question_type = question.get("question_type", "single")

            if difficulty in self.stats["by_difficulty"]:
                self.stats["by_difficulty"][difficulty] += 1

            if question_type in self.stats["by_type"]:
                self.stats["by_type"][question_type] += 1

        # Обновляем отображение статистики
        stats_text = f"Всего вопросов: {self.stats['total_questions']}\n"
        stats_text += f"По сложности: "
        for diff, count in self.stats["by_difficulty"].items():
            if count > 0:
                stats_text += f"{diff}({count}) "
        stats_text += f"\nПо типу: "
        for q_type, count in self.stats["by_type"].items():
            if count > 0:
                stats_text += f"{q_type}({count}) "

        self.stats_label.config(text=stats_text)

    def show_search(self):
        """Показ окна расширенного поиска"""
        search_dialog = tk.Toplevel(self.root)
        search_dialog.title("Расширенный поиск")
        search_dialog.geometry("400x300")
        search_dialog.transient(self.root)
        search_dialog.grab_set()

        ttk.Label(search_dialog, text="Поиск по тексту:").pack(padx=10, pady=5)
        search_entry = ttk.Entry(search_dialog, width=50)
        search_entry.pack(padx=10, pady=5)

        ttk.Label(search_dialog, text="Поиск по объяснению:").pack(padx=10, pady=5)
        explanation_entry = ttk.Entry(search_dialog, width=50)
        explanation_entry.pack(padx=10, pady=5)

        def perform_search():
            # Реализация расширенного поиска
            text_query = search_entry.get().lower()
            explanation_query = explanation_entry.get().lower()

            found_questions = []
            for i, question in enumerate(self.data["questions"]):
                if (text_query in question.get("text", "").lower() or
                        explanation_query in question.get("explanation", "").lower()):
                    found_questions.append(i)

            if found_questions:
                self.highlight_questions(found_questions)
                messagebox.showinfo("Поиск", f"Найдено вопросов: {len(found_questions)}")
            else:
                messagebox.showinfo("Поиск", "Вопросы не найдены")

            search_dialog.destroy()

        ttk.Button(search_dialog, text="Найти", command=perform_search).pack(pady=20)

    def highlight_questions(self, question_indices):
        """Подсветка найденных вопросов"""
        # Очищаем предыдущую подсветку
        for item in self.questions_list.get_children():
            self.questions_list.set(item, "status", "")

        # Подсвечиваем найденные
        for idx in question_indices:
            if idx < len(self.questions_list.get_children()):
                item = self.questions_list.get_children()[idx]
                self.questions_list.set(item, "status", "Найден")

    def check_duplicates(self):
        """Проверка дубликатов вопросов"""
        duplicates = []
        questions_text = []

        for i, question in enumerate(self.data["questions"]):
            text = question.get("text", "").strip().lower()
            if text in questions_text:
                original_idx = questions_text.index(text)
                duplicates.append((original_idx, i))
            else:
                questions_text.append(text)

        if duplicates:
            message = "Найдены дублирующиеся вопросы:\n\n"
            for orig, dup in duplicates:
                message += f"Вопрос #{orig + 1} и #{dup + 1}\n"
            messagebox.showwarning("Дубликаты", message)
        else:
            messagebox.showinfo("Дубликаты", "Дубликаты не найдены")

    def duplicate_question(self):
        """Дублирование текущего вопроса"""
        if self.current_question_index >= 0:
            original = self.data["questions"][self.current_question_index].copy()
            original["id"] = len(self.data["questions"]) + 1
            original["text"] = f"[Копия] {original['text']}"

            self.data["questions"].append(original)
            self.update_questions_list()
            self.update_stats()
            self.unsaved_changes = True
            self.update_window_title()

    def move_option_up(self):
        """Перемещение варианта ответа вверх"""
        # Реализация перемещения опций
        pass

    def move_option_down(self):
        """Перемещение варианта ответа вниз"""
        # Реализация перемещения опций
        pass

    def preview_image(self):
        """Предварительный просмотр изображения"""
        if self.image_path and os.path.exists(self.image_path):
            preview_window = tk.Toplevel(self.root)
            preview_window.title("Предварительный просмотр изображения")

            img = Image.open(self.image_path)
            img.thumbnail((800, 600))
            photo = ImageTk.PhotoImage(img)

            label = tk.Label(preview_window, image=photo)
            label.image = photo  # Сохраняем ссылку
            label.pack(padx=10, pady=10)

    def update_preview(self):
        """Обновление предварительного просмотра"""
        if self.current_question_index >= 0:
            question = self.get_current_question_data()
            preview_text = self.format_question_for_bot(question)

            self.preview_text.config(state=tk.NORMAL)
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(1.0, preview_text)
            self.preview_text.config(state=tk.DISABLED)

    def copy_preview_text(self):
        """Копирование текста предварительного просмотра"""
        self.root.clipboard_clear()
        self.root.clipboard_append(self.preview_text.get(1.0, tk.END))
        messagebox.showinfo("Копирование", "Текст скопирован в буфер обмена")

    def format_question_for_bot(self, question):
        """Форматирование вопроса как в боте"""
        text = f"❓ {question.get('text', '')}\n\n"

        if question.get('question_type') == 'multiple':
            text += "Выберите все правильные варианты ответов:\n\n"
        elif question.get('question_type') == 'sequence':
            text += "Расположите варианты в правильном порядке:\n\n"
        else:
            text += "Выберите правильный вариант ответа:\n\n"

        options = question.get('options', [])
        for i, option in enumerate(options):
            text += f"{chr(65 + i)}. {option}\n"

        if question.get('explanation'):
            text += f"\n💡 Объяснение: {question['explanation']}"

        return text

    def validate_current_question(self):
        """Валидация текущего вопроса"""
        if self.current_question_index >= 0:
            question = self.get_current_question_data()
            if CONFIG_AVAILABLE:
                valid, error = validate_question_data(question)
                if valid:
                    messagebox.showinfo("Валидация", "Вопрос прошел проверку")
                else:
                    messagebox.showerror("Валидация", f"Ошибка: {error}")
            else:
                # Простая валидация без внешних модулей
                errors = []
                if not question.get('text', '').strip():
                    errors.append("Текст вопроса не может быть пустым")
                if len(question.get('options', [])) < 2:
                    errors.append("Должно быть минимум 2 варианта ответа")

                if errors:
                    messagebox.showerror("Валидация", "\n".join(errors))
                else:
                    messagebox.showinfo("Валидация", "Вопрос прошел базовую проверку")

    def validate_all(self):
        """Валидация всех вопросов"""
        self.clear_validation_results()

        # Проверка темы
        if not self.data["topic"].get("name", "").strip():
            self.validation_tree.insert("", "end", text="Тема", values=("Ошибка", "Название темы не может быть пустым"))

        # Проверка вопросов
        for i, question in enumerate(self.data["questions"]):
            question_id = f"Вопрос {i + 1}"

            if not question.get('text', '').strip():
                self.validation_tree.insert("", "end", text=question_id, values=("Ошибка", "Текст вопроса пустой"))

            if len(question.get('options', [])) < 2:
                self.validation_tree.insert("", "end", text=question_id,
                                            values=("Ошибка", "Недостаточно вариантов ответа"))

            if not question.get('correct_answer'):
                self.validation_tree.insert("", "end", text=question_id,
                                            values=("Ошибка", "Не указан правильный ответ"))

        # Если ошибок нет
        if not self.validation_tree.get_children():
            self.validation_tree.insert("", "end", text="Результат", values=("Успех", "Все проверки пройдены"))

    def clear_validation_results(self):
        """Очистка результатов валидации"""
        for item in self.validation_tree.get_children():
            self.validation_tree.delete(item)

    def get_current_question_data(self):
        """Получение данных текущего редактируемого вопроса"""
        return {
            "text": self.question_text.get(1.0, tk.END).strip(),
            "question_type": self.question_type.get(),
            "difficulty": int(self.question_difficulty.get()),
            "explanation": self.question_explanation.get(1.0, tk.END).strip(),
            "options": self.get_options(),
            "correct_answer": self.get_correct_answers(),
            "media_url": self.image_path
        }

    def import_to_database(self):
        """Импорт данных в базу данных проекта"""
        if not CONFIG_AVAILABLE:
            messagebox.showerror("Ошибка", "Конфигурация проекта недоступна")
            return

        try:
            # Здесь должна быть реализация импорта в БД
            messagebox.showinfo("Импорт в БД", "Функция импорта в базу данных будет реализована в следующей версии")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка импорта в БД: {str(e)}")

    def export_to_json(self):
        """Экспорт в JSON с дополнительными опциями"""
        if not self.data["questions"]:
            messagebox.showwarning("Предупреждение", "Нет вопросов для экспорта")
            return

        export_dialog = tk.Toplevel(self.root)
        export_dialog.title("Настройки экспорта")
        export_dialog.geometry("400x300")
        export_dialog.transient(self.root)
        export_dialog.grab_set()

        # Опции экспорта
        ttk.Label(export_dialog, text="Выберите опции экспорта:").pack(padx=10, pady=10)

        include_images = tk.BooleanVar(value=True)
        ttk.Checkbutton(export_dialog, text="Копировать изображения", variable=include_images).pack(anchor=tk.W,
                                                                                                    padx=20)

        minify_json = tk.BooleanVar(value=False)
        ttk.Checkbutton(export_dialog, text="Минифицированный JSON", variable=minify_json).pack(anchor=tk.W, padx=20)

        validate_before_export = tk.BooleanVar(value=True)
        ttk.Checkbutton(export_dialog, text="Проверить перед экспортом", variable=validate_before_export).pack(
            anchor=tk.W, padx=20)

        def perform_export():
            if validate_before_export.get():
                # Быстрая валидация
                errors = []
                if not self.data["topic"].get("name", "").strip():
                    errors.append("Название темы не указано")
                if not self.data["questions"]:
                    errors.append("Нет вопросов для экспорта")

                if errors:
                    messagebox.showerror("Ошибки валидации", "\n".join(errors))
                    return

            file_path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )

            if file_path:
                try:
                    if include_images.get():
                        self.copy_images_for_export(os.path.dirname(file_path))

                    indent = None if minify_json.get() else 2

                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(self.data, f, ensure_ascii=False, indent=indent)

                    messagebox.showinfo("Экспорт", f"Файл успешно экспортирован: {os.path.basename(file_path)}")
                    export_dialog.destroy()

                except Exception as e:
                    messagebox.showerror("Ошибка", f"Ошибка экспорта: {str(e)}")

        ttk.Button(export_dialog, text="Экспортировать", command=perform_export).pack(pady=20)

    def copy_images_for_export(self, export_dir):
        """Копирование изображений при экспорте"""
        images_dir = os.path.join(export_dir, "images")
        os.makedirs(images_dir, exist_ok=True)

        for question in self.data["questions"]:
            media_url = question.get("media_url")
            if media_url and os.path.exists(media_url):
                filename = os.path.basename(media_url)
                dest_path = os.path.join(images_dir, filename)
                shutil.copy2(media_url, dest_path)

    def import_from_json(self):
        """Импорт из JSON с дополнительными опциями"""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Валидация структуры
                if CONFIG_AVAILABLE:
                    valid, error = validate_json_structure(data)
                    if not valid:
                        messagebox.showerror("Ошибка валидации", error)
                        return

                # Диалог опций импорта
                import_dialog = tk.Toplevel(self.root)
                import_dialog.title("Настройки импорта")
                import_dialog.geometry("400x200")
                import_dialog.transient(self.root)
                import_dialog.grab_set()

                merge_questions = tk.BooleanVar(value=False)
                ttk.Checkbutton(import_dialog, text="Объединить с текущими вопросами",
                                variable=merge_questions).pack(anchor=tk.W, padx=20, pady=10)

                def perform_import():
                    if merge_questions.get():
                        # Добавляем к существующим
                        start_id = len(self.data["questions"]) + 1
                        for i, question in enumerate(data["questions"]):
                            question["id"] = start_id + i
                            self.data["questions"].append(question)
                    else:
                        # Заменяем полностью
                        self.data = data

                    self.current_file_path = file_path
                    self.unsaved_changes = False
                    self.update_topic_info()
                    self.update_questions_list()
                    self.update_stats()
                    self.update_window_title()

                    messagebox.showinfo("Импорт", "Данные успешно импортированы")
                    import_dialog.destroy()

                ttk.Button(import_dialog, text="Импортировать", command=perform_import).pack(pady=20)

            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка импорта: {str(e)}")

    def cancel_question_changes(self):
        """Отмена изменений в текущем вопросе"""
        if self.current_question_index >= 0:
            self.load_question(self.data["questions"][self.current_question_index])

    def on_closing(self):
        """Обработчик закрытия приложения"""
        if self.unsaved_changes:
            result = messagebox.askyesnocancel(
                "Несохраненные изменения",
                "Есть несохраненные изменения. Сохранить перед выходом?"
            )
            if result is True:  # Да
                self.save_file()
                self.root.destroy()
            elif result is False:  # Нет
                self.root.destroy()
            # Отмена - ничего не делаем
        else:
            self.root.destroy()

    # Переопределяем базовые методы с улучшениями
    def update_questions_list(self):
        """Обновленный метод обновления списка вопросов с фильтрацией"""
        # Очищаем список
        for item in self.questions_list.get_children():
            self.questions_list.delete(item)

        # Получаем параметры фильтрации
        search_text = self.search_var.get().lower()
        difficulty_filter = self.difficulty_filter.get()
        type_filter = self.type_filter.get()

        # Заполняем список отфильтрованными вопросами
        for i, question in enumerate(self.data["questions"]):
            # Применяем фильтры
            if search_text and search_text not in question["text"].lower():
                continue

            if difficulty_filter != "Все" and str(question.get("difficulty", 1)) != difficulty_filter:
                continue

            if type_filter != "Все" and question.get("question_type", "single") != type_filter:
                continue

            # Добавляем в список
            text = question["text"]
            short_text = (text[:50] + "...") if len(text) > 50 else text

            # Определяем статус
            status = "✓" if self.is_question_valid(question) else "⚠"

            self.questions_list.insert("", tk.END, text=short_text,
                                       values=(question["question_type"],
                                               question.get("difficulty", 1),
                                               status),
                                       iid=str(i))

    def is_question_valid(self, question):
        """Проверка валидности вопроса"""
        if not question.get("text", "").strip():
            return False
        if len(question.get("options", [])) < 2:
            return False
        if not question.get("correct_answer"):
            return False
        return True

    # Переопределяем существующие методы для поддержки новой функциональности
    def save_file(self):
        """Улучшенный метод сохранения"""
        if self.current_file_path:
            self.save_to_file(self.current_file_path)
        else:
            self.save_file_as()

    def save_to_file(self, file_path):
        """Улучшенный метод записи в файл"""
        try:
            # Обеспечиваем корректные пути для изображений
            self.ensure_media_paths()

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)

            self.unsaved_changes = False
            self.update_window_title()
            self.file_label.config(text=os.path.basename(file_path))
            self.status_label.config(text="Файл сохранен")

            messagebox.showinfo("Сохранение", f"Файл '{os.path.basename(file_path)}' успешно сохранен.")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при сохранении файла: {str(e)}")

    def ensure_media_paths(self):
        """Обеспечение корректных путей к медиафайлам"""
        media_dir = os.path.join(os.path.dirname(self.current_file_path or ""), "media",
                                 "images") if self.current_file_path else MEDIA_DIR
        os.makedirs(media_dir, exist_ok=True)

    # Остальные методы остаются такими же, как в оригинале, но с добавленными вызовами
    # self.unsaved_changes = True и self.update_window_title() где необходимо


if __name__ == "__main__":
    root = tk.Tk()
    app = EnhancedQuizEditorApp(root)
    root.mainloop()
