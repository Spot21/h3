import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import json
import os
import shutil
from PIL import Image, ImageTk
import uuid


class QuizEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Редактор вопросов для телеграм-бота")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)

        # Переменные для хранения данных
        self.current_file_path = None
        self.data = {"topic": {"id": 1, "name": "", "description": ""}, "questions": []}
        self.current_question_index = -1
        self.image_path = None
        self.temp_image_path = None

        # Создание основного интерфейса
        self.create_menu()
        self.create_main_frame()

        # Обновление интерфейса
        self.update_topic_info()
        self.update_questions_list()

    def create_menu(self):
        """Создание главного меню"""
        menubar = tk.Menu(self.root)

        # Меню "Файл"
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Новый", command=self.new_file)
        file_menu.add_command(label="Открыть", command=self.open_file)
        file_menu.add_command(label="Сохранить", command=self.save_file)
        file_menu.add_command(label="Сохранить как...", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.root.quit)
        menubar.add_cascade(label="Файл", menu=file_menu)

        # Меню "Правка"
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Редактировать тему", command=self.edit_topic)
        edit_menu.add_command(label="Добавить вопрос", command=self.add_question)
        edit_menu.add_command(label="Удалить вопрос", command=self.delete_question)
        menubar.add_cascade(label="Правка", menu=edit_menu)

        # Меню "Помощь"
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="О программе", command=self.show_about)
        help_menu.add_command(label="Справка", command=self.show_help)
        menubar.add_cascade(label="Помощь", menu=help_menu)

        self.root.config(menu=menubar)

    def create_main_frame(self):
        """Создание основного интерфейса"""
        # Создаем панель инструментов
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="Новый", command=self.new_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Открыть", command=self.open_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Сохранить", command=self.save_file).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar, text="Редактировать тему", command=self.edit_topic).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Добавить вопрос", command=self.add_question).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Удалить вопрос", command=self.delete_question).pack(side=tk.LEFT, padx=2)

        # Создаем split view
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Левая панель - список вопросов
        left_frame = ttk.Frame(paned, width=300)
        paned.add(left_frame, weight=1)

        # Фрейм с информацией о теме
        topic_frame = ttk.LabelFrame(left_frame, text="Информация о теме")
        topic_frame.pack(fill=tk.X, padx=5, pady=5)

        self.topic_name_label = ttk.Label(topic_frame, text="Название: ")
        self.topic_name_label.pack(anchor=tk.W, padx=5, pady=2)

        self.topic_desc_label = ttk.Label(topic_frame, text="Описание: ")
        self.topic_desc_label.pack(anchor=tk.W, padx=5, pady=2)

        # Список вопросов
        questions_frame = ttk.LabelFrame(left_frame, text="Вопросы")
        questions_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.questions_list = ttk.Treeview(questions_frame, columns=("type", "difficulty"),
                                           show="headings", selectmode="browse")
        self.questions_list.heading("type", text="Тип")
        self.questions_list.heading("difficulty", text="Сложность")
        self.questions_list.column("type", width=70)
        self.questions_list.column("difficulty", width=70)
        self.questions_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.questions_list.bind("<<TreeviewSelect>>", self.on_question_select)

        # Правая панель - редактор вопроса
        right_frame = ttk.Frame(paned, width=600)
        paned.add(right_frame, weight=2)

        editor_frame = ttk.LabelFrame(right_frame, text="Редактор вопроса")
        editor_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Создаем вкладки для разных свойств вопроса
        self.notebook = ttk.Notebook(editor_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Вкладка основной информации
        general_tab = ttk.Frame(self.notebook)
        self.notebook.add(general_tab, text="Основное")

        # Поля для основной информации
        ttk.Label(general_tab, text="Текст вопроса:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.question_text = tk.Text(general_tab, height=5)
        self.question_text.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W + tk.E)

        ttk.Label(general_tab, text="Тип вопроса:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.question_type = ttk.Combobox(general_tab, values=["single", "multiple", "sequence"], state="readonly")
        self.question_type.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        self.question_type.set("single")
        self.question_type.bind("<<ComboboxSelected>>", self.on_question_type_change)

        ttk.Label(general_tab, text="Сложность:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.question_difficulty = ttk.Spinbox(general_tab, from_=1, to=5, width=5)
        self.question_difficulty.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        self.question_difficulty.set(1)

        ttk.Label(general_tab, text="Объяснение:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.question_explanation = tk.Text(general_tab, height=3)
        self.question_explanation.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W + tk.E)

        # Вкладка вариантов ответов
        options_tab = ttk.Frame(self.notebook)
        self.notebook.add(options_tab, text="Варианты ответов")

        # Список вариантов ответов
        self.options_frame = ttk.Frame(options_tab)
        self.options_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.options_list = []

        # Кнопки для работы с вариантами
        options_buttons = ttk.Frame(options_tab)
        options_buttons.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(options_buttons, text="Добавить вариант",
                   command=self.add_option).pack(side=tk.LEFT, padx=2)
        ttk.Button(options_buttons, text="Удалить выбранный",
                   command=self.delete_option).pack(side=tk.LEFT, padx=2)

        # Вкладка выбора ответов
        answers_tab = ttk.Frame(self.notebook)
        self.notebook.add(answers_tab, text="Правильные ответы")

        self.answers_frame = ttk.Frame(answers_tab)
        self.answers_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Вкладка медиа
        media_tab = ttk.Frame(self.notebook)
        self.notebook.add(media_tab, text="Изображение")

        # Медиафайл
        self.media_frame = ttk.LabelFrame(media_tab, text="Изображение к вопросу")
        self.media_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.media_preview = ttk.Label(self.media_frame, text="Нет изображения")
        self.media_preview.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        media_buttons = ttk.Frame(media_tab)
        media_buttons.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(media_buttons, text="Выбрать изображение",
                   command=self.select_image).pack(side=tk.LEFT, padx=2)
        ttk.Button(media_buttons, text="Удалить изображение",
                   command=self.remove_image).pack(side=tk.LEFT, padx=2)

        # Кнопки сохранения изменений
        buttons_frame = ttk.Frame(editor_frame)
        buttons_frame.pack(fill=tk.X, pady=5)

        ttk.Button(buttons_frame, text="Применить изменения",
                   command=self.save_question_changes).pack(side=tk.RIGHT, padx=5)

        # Настраиваем выравнивание колонок
        general_tab.columnconfigure(1, weight=1)

    def update_topic_info(self):
        """Обновление информации о теме"""
        topic = self.data["topic"]
        self.topic_name_label.config(text=f"Название: {topic['name']}")
        self.topic_desc_label.config(text=f"Описание: {topic['description']}")

    def update_questions_list(self):
        """Обновление списка вопросов"""
        # Очищаем список
        for item in self.questions_list.get_children():
            self.questions_list.delete(item)

        # Заполняем список вопросами
        for i, question in enumerate(self.data["questions"]):
            text = question["text"]
            short_text = (text[:40] + "...") if len(text) > 40 else text

            self.questions_list.insert("", tk.END, text=short_text,
                                       values=(question["question_type"], question["difficulty"]),
                                       iid=str(i))

    def on_question_select(self, event):
        """Обработчик выбора вопроса из списка"""
        selection = self.questions_list.selection()
        if selection:
            index = int(selection[0])
            self.current_question_index = index
            self.load_question(self.data["questions"][index])
        else:
            self.current_question_index = -1
            self.clear_question_form()

    def clear_question_form(self):
        """Очистка формы редактирования вопроса"""
        self.question_text.delete(1.0, tk.END)
        self.question_type.set("single")
        self.question_difficulty.set(1)
        self.question_explanation.delete(1.0, tk.END)
        self.clear_options()
        self.update_answers_widgets()
        self.remove_image()

    def load_question(self, question):
        """Загрузка данных вопроса в форму редактирования"""
        self.clear_question_form()

        # Заполняем основные поля
        self.question_text.insert(tk.END, question["text"])
        self.question_type.set(question["question_type"])
        self.question_difficulty.set(question["difficulty"])
        if "explanation" in question and question["explanation"]:
            self.question_explanation.insert(tk.END, question["explanation"])

        # Загружаем варианты ответов
        self.load_options(question["options"])

        # Загружаем правильные ответы
        self.update_answers_widgets(question["correct_answer"])

        # Загружаем изображение, если есть
        if "media_url" in question and question["media_url"]:
            self.image_path = question["media_url"]
            self.update_image_preview()

    def new_file(self):
        """Создание нового файла"""
        if messagebox.askyesno("Новый файл",
                               "Вы уверены, что хотите создать новый файл? Несохраненные изменения будут потеряны."):
            self.current_file_path = None
            self.data = {"topic": {"id": 1, "name": "", "description": ""}, "questions": []}
            self.current_question_index = -1
            self.clear_question_form()
            self.update_topic_info()
            self.update_questions_list()
            self.edit_topic()  # Сразу открываем диалог редактирования темы

    def open_file(self):
        """Открытие существующего JSON-файла"""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")])

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)

                if "topic" not in data or "questions" not in data:
                    messagebox.showerror("Ошибка",
                                         "Выбранный файл не содержит необходимых полей 'topic' и 'questions'.")
                    return

                self.data = data
                self.current_file_path = file_path
                self.current_question_index = -1
                self.clear_question_form()
                self.update_topic_info()
                self.update_questions_list()

                messagebox.showinfo("Информация", f"Файл '{os.path.basename(file_path)}' успешно открыт.")

            except json.JSONDecodeError:
                messagebox.showerror("Ошибка", "Выбранный файл содержит некорректный JSON.")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при открытии файла: {str(e)}")

    def save_file(self):
        """Сохранение текущего файла"""
        if self.current_file_path:
            self.save_to_file(self.current_file_path)
        else:
            self.save_file_as()

    def save_file_as(self):
        """Сохранение файла с выбором нового пути"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if file_path:
            self.save_to_file(file_path)
            self.current_file_path = file_path

    def save_to_file(self, file_path):
        """Сохранение данных в файл"""
        try:
            # Копируем изображения, если необходимо
            if self.temp_image_path and os.path.exists(self.temp_image_path):
                self.copy_image_to_media_folder()

            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(self.data, file, ensure_ascii=False, indent=2)

            messagebox.showinfo("Сохранение", f"Файл '{os.path.basename(file_path)}' успешно сохранен.")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при сохранении файла: {str(e)}")

    def edit_topic(self):
        """Редактирование информации о теме"""
        # Создаем модальное окно для редактирования темы
        topic_dialog = tk.Toplevel(self.root)
        topic_dialog.title("Редактирование темы")
        topic_dialog.geometry("400x250")
        topic_dialog.transient(self.root)
        topic_dialog.grab_set()

        # Задаем минимальный размер и запрещаем изменение размера
        topic_dialog.minsize(400, 250)
        topic_dialog.resizable(False, False)

        # Поля для редактирования
        ttk.Label(topic_dialog, text="ID темы:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        topic_id = ttk.Entry(topic_dialog)
        topic_id.grid(row=0, column=1, padx=10, pady=10, sticky=tk.W + tk.E)
        topic_id.insert(0, str(self.data["topic"]["id"]))

        ttk.Label(topic_dialog, text="Название:").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        topic_name = ttk.Entry(topic_dialog)
        topic_name.grid(row=1, column=1, padx=10, pady=10, sticky=tk.W + tk.E)
        topic_name.insert(0, self.data["topic"]["name"])

        ttk.Label(topic_dialog, text="Описание:").grid(row=2, column=0, padx=10, pady=10, sticky=tk.W + tk.N)
        topic_desc = tk.Text(topic_dialog, height=5, width=30)
        topic_desc.grid(row=2, column=1, padx=10, pady=10, sticky=tk.W + tk.E)
        topic_desc.insert(tk.END, self.data["topic"]["description"])

        # Кнопки
        buttons_frame = ttk.Frame(topic_dialog)
        buttons_frame.grid(row=3, column=0, columnspan=2, pady=10)

        def save_topic():
            try:
                self.data["topic"]["id"] = int(topic_id.get())
                self.data["topic"]["name"] = topic_name.get()
                self.data["topic"]["description"] = topic_desc.get(1.0, tk.END).strip()
                self.update_topic_info()
                topic_dialog.destroy()
            except ValueError:
                messagebox.showerror("Ошибка", "ID темы должен быть целым числом.")

        ttk.Button(buttons_frame, text="Сохранить", command=save_topic).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Отмена", command=topic_dialog.destroy).pack(side=tk.LEFT, padx=5)

        # Настройка размеров колонок
        topic_dialog.columnconfigure(1, weight=1)

    def add_question(self):
        """Добавление нового вопроса"""
        # Создаем новый вопрос со стандартными значениями
        new_question = {
            "id": len(self.data["questions"]) + 1,
            "text": "Новый вопрос",
            "options": ["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4"],
            "correct_answer": [0],
            "question_type": "single",
            "difficulty": 1,
            "explanation": ""
        }

        # Добавляем в список
        self.data["questions"].append(new_question)
        self.update_questions_list()

        # Выбираем новый вопрос
        self.current_question_index = len(self.data["questions"]) - 1
        self.questions_list.selection_set(str(self.current_question_index))
        self.load_question(new_question)

    def delete_question(self):
        """Удаление выбранного вопроса"""
        if self.current_question_index >= 0:
            if messagebox.askyesno("Удаление вопроса", "Вы уверены, что хотите удалить этот вопрос?"):
                del self.data["questions"][self.current_question_index]
                self.update_questions_list()
                self.current_question_index = -1
                self.clear_question_form()
        else:
            messagebox.showinfo("Информация", "Выберите вопрос для удаления.")

    def save_question_changes(self):
        """Сохранение изменений в текущем вопросе"""
        if self.current_question_index < 0:
            messagebox.showinfo("Информация", "Выберите вопрос для редактирования.")
            return

        try:
            # Создаем новый словарь вопроса
            question = {}

            # Если это существующий вопрос, сохраняем его ID
            if "id" in self.data["questions"][self.current_question_index]:
                question["id"] = self.data["questions"][self.current_question_index]["id"]
            else:
                question["id"] = self.current_question_index + 1

            # Основные поля
            question["text"] = self.question_text.get(1.0, tk.END).strip()
            question["question_type"] = self.question_type.get()
            question["difficulty"] = int(self.question_difficulty.get())
            question["explanation"] = self.question_explanation.get(1.0, tk.END).strip()

            # Варианты ответов
            question["options"] = self.get_options()

            # Правильные ответы
            question["correct_answer"] = self.get_correct_answers()

            # Изображение
            if self.image_path:
                question["media_url"] = self.image_path

            # Проверяем данные
            if not question["text"]:
                messagebox.showerror("Ошибка", "Текст вопроса не может быть пустым.")
                return

            if not question["options"] or len(question["options"]) < 2:
                messagebox.showerror("Ошибка", "Должно быть минимум 2 варианта ответа.")
                return

            if not question["correct_answer"]:
                messagebox.showerror("Ошибка", "Выберите хотя бы один правильный ответ.")
                return

            # Для sequence проверяем, что все варианты выбраны
            if question["question_type"] == "sequence" and len(question["correct_answer"]) != len(question["options"]):
                messagebox.showerror("Ошибка", "В вопросе с последовательностью нужно выбрать все варианты ответов.")
                return

            # Обновляем данные вопроса
            self.data["questions"][self.current_question_index] = question

            # Обновляем список вопросов
            self.update_questions_list()

            # Выбираем текущий вопрос снова
            self.questions_list.selection_set(str(self.current_question_index))

            messagebox.showinfo("Информация", "Изменения в вопросе сохранены.")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при сохранении вопроса: {str(e)}")

    def get_options(self):
        """Получение списка вариантов ответов"""
        options = []
        for option_entry in self.options_list:
            option_text = option_entry.get()
            if option_text.strip():
                options.append(option_text)
        return options

    def get_correct_answers(self):
        """Получение правильных ответов"""
        question_type = self.question_type.get()

        if question_type == "single":
            # Для одиночного выбора - это индекс выбранного варианта
            for i, var in enumerate(self.answer_vars):
                if var.get():
                    return [i]
            return [0]  # По умолчанию первый вариант

        elif question_type == "multiple":
            # Для множественного выбора - список индексов выбранных вариантов
            selected = []
            for i, var in enumerate(self.answer_vars):
                if var.get():
                    selected.append(i)
            return selected

        elif question_type == "sequence":
            # Для последовательности - порядок вариантов
            return [str(idx) for idx in self.sequence_order]

        return [0]  # По умолчанию

    def clear_options(self):
        """Очистка списка вариантов ответов"""
        for widget in self.options_frame.winfo_children():
            widget.destroy()
        self.options_list = []

    def load_options(self, options):
        """Загрузка вариантов ответов"""
        self.clear_options()

        for i, option in enumerate(options):
            option_frame = ttk.Frame(self.options_frame)
            option_frame.pack(fill=tk.X, padx=5, pady=2)

            ttk.Label(option_frame, text=f"{i + 1}.").pack(side=tk.LEFT, padx=(0, 5))

            option_entry = ttk.Entry(option_frame, width=50)
            option_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            option_entry.insert(0, option)

            self.options_list.append(option_entry)

    def add_option(self):
        """Добавление нового варианта ответа"""
        # Создаем новый фрейм для варианта
        option_frame = ttk.Frame(self.options_frame)
        option_frame.pack(fill=tk.X, padx=5, pady=2)

        # Номер варианта
        ttk.Label(option_frame, text=f"{len(self.options_list) + 1}.").pack(side=tk.LEFT, padx=(0, 5))

        # Поле для текста варианта
        option_entry = ttk.Entry(option_frame, width=50)
        option_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        option_entry.insert(0, f"Вариант {len(self.options_list) + 1}")

        self.options_list.append(option_entry)

        # Обновляем виджеты для выбора правильных ответов
        self.update_answers_widgets()

    def delete_option(self):
        """Удаление последнего варианта ответа"""
        if self.options_list:
            # Удаляем последний фрейм с вариантом
            self.options_frame.winfo_children()[-1].destroy()
            self.options_list.pop()

            # Обновляем виджеты для выбора правильных ответов
            self.update_answers_widgets()

    def on_question_type_change(self, event=None):
        """Обработчик изменения типа вопроса"""
        self.update_answers_widgets()

    def update_answers_widgets(self, correct_answers=None):
        """Обновление виджетов для выбора правильных ответов"""
        # Очищаем фрейм с правильными ответами
        for widget in self.answers_frame.winfo_children():
            widget.destroy()

        # Получаем текущие варианты ответов
        options = self.get_options()

        # Если нет вариантов, показываем сообщение
        if not options:
            ttk.Label(self.answers_frame, text="Сначала добавьте варианты ответов").pack(padx=5, pady=5)
            return

        question_type = self.question_type.get()

        if question_type == "single":
            # Для одиночного выбора - радиокнопки
            ttk.Label(self.answers_frame, text="Выберите правильный ответ:").pack(anchor=tk.W, padx=5, pady=5)

            selected_var = tk.IntVar(value=0)
            self.answer_vars = []

            for i, option in enumerate(options):
                var = tk.BooleanVar(value=False)
                self.answer_vars.append(var)

                radio = ttk.Radiobutton(self.answers_frame, text=option, variable=selected_var, value=i,
                                        command=lambda idx=i: self.select_single_answer(idx))
                radio.pack(anchor=tk.W, padx=20, pady=2)

            # Устанавливаем правильный ответ, если он передан
            if correct_answers and len(correct_answers) > 0:
                try:
                    selected_index = int(correct_answers[0])
                    selected_var.set(selected_index)
                    self.select_single_answer(selected_index)
                except (ValueError, IndexError):
                    pass

        elif question_type == "multiple":
            # Для множественного выбора - чекбоксы
            ttk.Label(self.answers_frame, text="Выберите все правильные ответы:").pack(anchor=tk.W, padx=5, pady=5)

            self.answer_vars = []

            for i, option in enumerate(options):
                var = tk.BooleanVar(value=False)
                self.answer_vars.append(var)

                check = ttk.Checkbutton(self.answers_frame, text=option, variable=var)
                check.pack(anchor=tk.W, padx=20, pady=2)

            # Устанавливаем правильные ответы, если они переданы
            if correct_answers:
                for idx in correct_answers:
                    try:
                        self.answer_vars[int(idx)].set(True)
                    except (ValueError, IndexError):
                        pass

        elif question_type == "sequence":
            # Для последовательности - перетаскивание
            ttk.Label(self.answers_frame,
                      text="Установите правильную последовательность (перетаскиванием недоступно):").pack(anchor=tk.W,
                                                                                                          padx=5,
                                                                                                          pady=5)

            # Инициализация порядка
            self.sequence_order = []

            # Контейнер для размещенных вариантов
            placed_frame = ttk.LabelFrame(self.answers_frame, text="Порядок")
            placed_frame.pack(fill=tk.X, padx=5, pady=5)

            # Контейнер для доступных вариантов
            available_frame = ttk.LabelFrame(self.answers_frame, text="Доступные варианты")
            available_frame.pack(fill=tk.X, padx=5, pady=5)

            # Функция для обновления отображения последовательности
            def update_sequence_display():
                # Очищаем фреймы
                for widget in placed_frame.winfo_children():
                    widget.destroy()
                for widget in available_frame.winfo_children():
                    widget.destroy()

                # Отображаем размещенные варианты
                for i, idx in enumerate(self.sequence_order):
                    try:
                        option_frame = ttk.Frame(placed_frame)
                        option_frame.pack(fill=tk.X, padx=5, pady=2)

                        ttk.Label(option_frame, text=f"{i + 1}.").pack(side=tk.LEFT, padx=(0, 5))
                        ttk.Label(option_frame, text=options[int(idx)]).pack(side=tk.LEFT, fill=tk.X, expand=True)

                        ttk.Button(option_frame, text="↑", width=3,
                                   command=lambda i=i: move_up(i)).pack(side=tk.RIGHT, padx=2)
                        ttk.Button(option_frame, text="↓", width=3,
                                   command=lambda i=i: move_down(i)).pack(side=tk.RIGHT, padx=2)
                        ttk.Button(option_frame, text="×", width=3,
                                   command=lambda i=i: remove_from_sequence(i)).pack(side=tk.RIGHT, padx=2)
                    except (ValueError, IndexError):
                        continue

                # Отображаем доступные варианты
                available_indices = [i for i in range(len(options)) if str(i) not in self.sequence_order]
                for i in available_indices:
                    btn = ttk.Button(available_frame, text=options[i],
                                     command=lambda idx=i: add_to_sequence(idx))
                    btn.pack(fill=tk.X, padx=5, pady=2)

            # Функции для управления последовательностью
            def add_to_sequence(index):
                self.sequence_order.append(str(index))
                update_sequence_display()

            def remove_from_sequence(position):
                if 0 <= position < len(self.sequence_order):
                    self.sequence_order.pop(position)
                    update_sequence_display()

            def move_up(position):
                if position > 0:
                    self.sequence_order[position], self.sequence_order[position - 1] = \
                        self.sequence_order[position - 1], self.sequence_order[position]
                    update_sequence_display()

            def move_down(position):
                if position < len(self.sequence_order) - 1:
                    self.sequence_order[position], self.sequence_order[position + 1] = \
                        self.sequence_order[position + 1], self.sequence_order[position]
                    update_sequence_display()

            # Инициализация последовательности
            if correct_answers:
                self.sequence_order = [str(idx) for idx in correct_answers]
            else:
                self.sequence_order = []

            # Обновляем отображение
            update_sequence_display()

    def select_single_answer(self, index):
        """Выбор одного правильного ответа"""
        for i, var in enumerate(self.answer_vars):
            var.set(i == index)

    def select_image(self):
        """Выбор изображения для вопроса"""
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif"), ("All files", "*.*")])

        if file_path:
            try:
                # Сохраняем путь к изображению
                self.temp_image_path = file_path

                # Создаем имя для нового файла
                file_ext = os.path.splitext(file_path)[1]
                new_filename = f"question_{uuid.uuid4().hex[:8]}{file_ext}"

                # Устанавливаем относительный путь для сохранения в JSON
                self.image_path = f"images/{new_filename}"

                # Обновляем превью
                self.update_image_preview()

            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при выборе изображения: {str(e)}")

    def update_image_preview(self):
        """Обновление превью изображения"""
        for widget in self.media_preview.winfo_children():
            widget.destroy()

        if not self.image_path:
            self.media_preview.config(text="Нет изображения")
            return

        try:
            # Пытаемся открыть изображение
            if self.temp_image_path and os.path.exists(self.temp_image_path):
                image_path = self.temp_image_path
            else:
                # Ищем в директории data/media
                media_dir = os.path.join("data", "media")
                image_path = os.path.join(media_dir, self.image_path)

                if not os.path.exists(image_path):
                    self.media_preview.config(text=f"Изображение не найдено: {self.image_path}")
                    return

            # Открываем и масштабируем изображение
            img = Image.open(image_path)
            img.thumbnail((400, 300))

            # Конвертируем в формат для Tkinter
            tk_img = ImageTk.PhotoImage(img)

            # Обновляем превью
            self.media_preview.config(text="")
            img_label = tk.Label(self.media_preview, image=tk_img)
            img_label.image = tk_img  # Сохраняем ссылку, чтобы избежать сборки мусора
            img_label.pack(padx=5, pady=5)

            # Информация о файле
            ttk.Label(self.media_preview, text=f"Файл: {self.image_path}").pack(padx=5, pady=5)

        except Exception as e:
            self.media_preview.config(text=f"Ошибка предпросмотра: {str(e)}")

    def copy_image_to_media_folder(self):
        """Копирование изображения в директорию медиафайлов"""
        if not self.temp_image_path or not self.image_path:
            return

        try:
            # Создаем директорию для медиафайлов
            media_dir = os.path.join("data", "media")
            os.makedirs(media_dir, exist_ok=True)

            # Создаем директорию для изображений
            images_dir = os.path.join(media_dir, "images")
            os.makedirs(images_dir, exist_ok=True)

            # Путь для сохранения файла
            target_path = os.path.join(media_dir, self.image_path)

            # Копируем файл
            shutil.copy2(self.temp_image_path, target_path)

            # Очищаем временный путь
            self.temp_image_path = None

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при копировании изображения: {str(e)}")

    def remove_image(self):
        """Удаление изображения из вопроса"""
        self.image_path = None
        self.temp_image_path = None

        for widget in self.media_preview.winfo_children():
            widget.destroy()

        self.media_preview.config(text="Нет изображения")

    def show_about(self):
        """Показ информации о программе"""
        messagebox.showinfo(
            "О программе",
            "Редактор вопросов для телеграм-бота\n"
            "Версия 1.0\n\n"
            "Позволяет создавать и редактировать вопросы для теста по истории."
        )

    def show_help(self):
        """Показ справки по программе"""
        help_text = """
        Инструкция по использованию:

        1. Создание нового файла:
           - Выберите "Файл" -> "Новый"
           - Заполните информацию о теме

        2. Работа с вопросами:
           - Нажмите "Добавить вопрос" для создания нового вопроса
           - Выберите вопрос из списка для редактирования
           - Заполните поля на вкладках "Основное", "Варианты ответов", "Правильные ответы"
           - При необходимости добавьте изображение на вкладке "Изображение"
           - Нажмите "Применить изменения" для сохранения изменений в вопросе

        3. Сохранение и открытие:
           - "Файл" -> "Сохранить" - сохранить текущий файл
           - "Файл" -> "Сохранить как..." - сохранить файл с новым именем
           - "Файл" -> "Открыть" - открыть существующий JSON-файл
        """

        help_dialog = tk.Toplevel(self.root)
        help_dialog.title("Справка")
        help_dialog.geometry("600x400")
        help_dialog.transient(self.root)

        text_widget = tk.Text(help_dialog, wrap="word", padx=10, pady=10)
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, help_text)
        text_widget.config(state="disabled")

        ttk.Button(help_dialog, text="Закрыть", command=help_dialog.destroy).pack(pady=10)


if __name__ == "__main__":
    root = tk.Tk()
    app = QuizEditorApp(root)
    root.mainloop()
