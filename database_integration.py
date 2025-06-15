"""
Модуль для интеграции JSON Theme Maker с основной базой данных проекта
Оптимизирован для работы в PyCharm на Windows 11
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import traceback
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, dialog
import shutil
from datetime import datetime


# Настройка путей для PyCharm на Windows
def setup_project_paths():
    """Настройка путей проекта для корректной работы в PyCharm на Windows"""
    # Получаем корневую директорию проекта
    current_file = Path(__file__).resolve()
    project_root = current_file.parent

    # Ищем корневую директорию проекта (где находится bot.py)
    while project_root.parent != project_root:
        if (project_root / "bot.py").exists():
            break
        project_root = project_root.parent

    # Добавляем корневую директорию в Python path
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    return project_root


# Инициализируем пути
PROJECT_ROOT = setup_project_paths()

# Улучшенная обработка импортов
try:
    from database.db_manager import get_session, check_connection
    from database.models import Topic, Question
    DB_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info(f"Database modules imported successfully. Project root: {PROJECT_ROOT}")
except ImportError as e:
    DB_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"Database modules unavailable: {e}")

try:
    from config import DB_ENGINE, MEDIA_DIR, DATA_DIR
    CONFIG_AVAILABLE = True
except ImportError as e:
    CONFIG_AVAILABLE = False
    # Fallback значения
    DATA_DIR = str(PROJECT_ROOT / "data")
    MEDIA_DIR = str(PROJECT_ROOT / "data" / "media")
    DB_ENGINE = f"sqlite:///{PROJECT_ROOT}/data/history_bot.db"
    logger.warning(f"Config not available, using fallback values: {e}")

try:
    from utils.validators import validate_question_data, validate_topic_data, validate_json_structure
    VALIDATORS_AVAILABLE = True
except ImportError as e:
    VALIDATORS_AVAILABLE = False
    logger.warning(f"Validators not available: {e}")

# Обновляем доступность функций
DB_AVAILABLE = DB_AVAILABLE and CONFIG_AVAILABLE


class DatabaseIntegration:
    """Класс для интеграции с базой данных проекта"""

    def __init__(self):
        self.db_available = DB_AVAILABLE
        self.project_root = PROJECT_ROOT

        # Создаем необходимые директории если их нет
        self._ensure_directories()

    def _ensure_directories(self):
        """Создание необходимых директорий"""
        try:
            if DB_AVAILABLE:
                # Создаем директории из config
                Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
                Path(MEDIA_DIR).mkdir(parents=True, exist_ok=True)
                Path(MEDIA_DIR, "images").mkdir(parents=True, exist_ok=True)
            else:
                # Создаем базовые директории
                data_dir = self.project_root / "data"
                media_dir = data_dir / "media"

                data_dir.mkdir(exist_ok=True)
                media_dir.mkdir(exist_ok=True)
                (media_dir / "images").mkdir(exist_ok=True)

        except Exception as e:
            logger.error(f"Ошибка создания директорий: {e}")

    def test_connection(self) -> Tuple[bool, str]:
        """Тестирование подключения к базе данных"""
        if not self.db_available:
            return False, "Модули базы данных недоступны. Проверьте зависимости."

        try:
            # Используем check_connection из db_manager
            if check_connection():
                return True, "Подключение к базе данных успешно"
            else:
                return False, "Не удалось подключиться к базе данных"

        except Exception as e:
            error_msg = f"Ошибка подключения: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def get_existing_topics(self) -> List[Dict[str, Any]]:
        """Получение существующих тем из базы данных"""
        if not self.db_available:
            return []

        try:
            with get_session() as session:
                topics = session.query(Topic).all()
                result = []

                for topic in topics:
                    result.append({
                        "id": topic.id,
                        "name": topic.name,
                        "description": topic.description or ""
                    })

                logger.info(f"Получено {len(result)} тем из базы данных")
                return result

        except Exception as e:
            logger.error(f"Ошибка получения тем: {e}")
            return []

    def get_topic_questions(self, topic_id: int) -> List[Dict[str, Any]]:
        """Получение вопросов для определенной темы"""
        if not self.db_available:
            return []

        try:
            with get_session() as session:
                questions = session.query(Question).filter(Question.topic_id == topic_id).all()
                result = []

                for question in questions:
                    try:
                        # Обработка JSON полей
                        options = question.options
                        if isinstance(options, str):
                            options = json.loads(options)

                        correct_answer = question.correct_answer
                        if isinstance(correct_answer, str):
                            correct_answer = json.loads(correct_answer)

                        # Обработка пути к изображению для Windows
                        media_url = question.media_url
                        if media_url:
                            media_url = self._normalize_media_path(media_url)

                        result.append({
                            "id": question.id,
                            "text": question.text,
                            "options": options,
                            "correct_answer": correct_answer,
                            "question_type": question.question_type,
                            "difficulty": question.difficulty,
                            "media_url": media_url,
                            "explanation": question.explanation or ""
                        })

                    except (json.JSONDecodeError, TypeError) as e:
                        logger.error(f"Ошибка парсинга данных вопроса {question.id}: {e}")
                        continue

                logger.info(f"Получено {len(result)} вопросов для темы {topic_id}")
                return result

        except Exception as e:
            logger.error(f"Ошибка получения вопросов: {e}")
            return []

    def _normalize_media_path(self, media_path: str) -> str:
        """Нормализация пути к медиафайлу для Windows"""
        if not media_path:
            return media_path

        try:
            # Конвертируем в Path объект для правильной обработки
            path = Path(media_path)

            # Если путь относительный, делаем его относительно MEDIA_DIR
            if not path.is_absolute():
                if DB_AVAILABLE:
                    full_path = Path(MEDIA_DIR) / path
                else:
                    full_path = self.project_root / "data" / "media" / path

                # Проверяем существование файла
                if full_path.exists():
                    return str(full_path)
                else:
                    # Ищем в подпапке images
                    image_path = full_path.parent / "images" / path.name
                    if image_path.exists():
                        return str(image_path)

            return str(path)

        except Exception as e:
            logger.error(f"Ошибка нормализации пути {media_path}: {e}")
            return media_path

    def export_topic_to_json(self, topic_id: int) -> Optional[Dict[str, Any]]:
        """Экспорт темы и её вопросов в формат JSON"""
        if not self.db_available:
            return None

        try:
            with get_session() as session:
                # Получаем тему
                topic = session.query(Topic).get(topic_id)
                if not topic:
                    logger.warning(f"Тема с ID {topic_id} не найдена")
                    return None

                # Получаем вопросы
                questions = self.get_topic_questions(topic_id)

                result = {
                    "topic": {
                        "id": topic.id,
                        "name": topic.name,
                        "description": topic.description or ""
                    },
                    "questions": questions
                }

                logger.info(f"Экспортирована тема '{topic.name}' с {len(questions)} вопросами")
                return result

        except Exception as e:
            logger.error(f"Ошибка экспорта темы: {e}")
            return None

    def import_json_to_database(self, json_data: Dict[str, Any],
                                update_existing: bool = False,
                                copy_images: bool = True) -> Tuple[bool, str]:
        """Импорт JSON данных в базу данных с улучшенной обработкой"""
        if not self.db_available:
            return False, "База данных недоступна"

        try:
            # Валидация данных
            valid, errors = self.validate_json_for_import(json_data)
            if not valid:
                return False, f"Ошибки валидации: {'; '.join(errors)}"

            with get_session() as session:
                # Обрабатываем тему
                topic_data = json_data.get("topic", {})
                topic_id = topic_data.get("id")

                # Проверяем существование темы
                existing_topic = None
                if topic_id:
                    existing_topic = session.query(Topic).get(topic_id)

                if existing_topic and not update_existing:
                    return False, f"Тема с ID {topic_id} уже существует. Включите опцию обновления."

                if existing_topic and update_existing:
                    # Обновляем существующую тему
                    existing_topic.name = topic_data["name"]
                    existing_topic.description = topic_data.get("description", "")
                    topic = existing_topic
                    logger.info(f"Обновлена тема: {topic.name}")
                else:
                    # Создаем новую тему
                    topic = Topic(
                        name=topic_data["name"],
                        description=topic_data.get("description", "")
                    )
                    session.add(topic)
                    session.flush()  # Получаем ID
                    logger.info(f"Создана новая тема: {topic.name}")

                # Обрабатываем вопросы
                questions_data = json_data.get("questions", [])
                imported_questions = 0
                updated_questions = 0

                for question_data in questions_data:
                    try:
                        success, q_type = self._import_single_question(
                            session, topic.id, question_data, update_existing, copy_images
                        )

                        if success:
                            if q_type == "imported":
                                imported_questions += 1
                            elif q_type == "updated":
                                updated_questions += 1

                    except Exception as e:
                        logger.error(f"Ошибка импорта вопроса: {e}")
                        continue

                # Фиксируем изменения
                session.commit()

                result_msg = f"Тема '{topic.name}': "
                if imported_questions > 0:
                    result_msg += f"создано {imported_questions} вопросов"
                if updated_questions > 0:
                    result_msg += f", обновлено {updated_questions} вопросов"

                logger.info(result_msg)
                return True, result_msg

        except Exception as e:
            logger.error(f"Ошибка импорта в базу данных: {e}")
            logger.error(traceback.format_exc())
            return False, f"Ошибка импорта: {str(e)}"

    def _import_single_question(self, session, topic_id: int, question_data: Dict[str, Any],
                                update_existing: bool, copy_images: bool) -> Tuple[bool, str]:
        """Импорт одного вопроса"""
        try:
            # Проверяем существование вопроса
            question_id = question_data.get("id")
            existing_question = None

            if question_id:
                existing_question = session.query(Question).filter(
                    Question.id == question_id,
                    Question.topic_id == topic_id
                ).first()

            if existing_question and not update_existing:
                return False, "skipped"  # Пропускаем существующий вопрос

            # Подготавливаем данные
            options = question_data["options"]
            correct_answer = question_data["correct_answer"]

            if not isinstance(options, str):
                options = json.dumps(options, ensure_ascii=False)
            if not isinstance(correct_answer, str):
                correct_answer = json.dumps(correct_answer, ensure_ascii=False)

            # Обрабатываем медиафайл
            media_url = question_data.get("media_url")
            if media_url and copy_images:
                media_url = self._copy_media_file(media_url)

            if existing_question and update_existing:
                # Обновляем существующий вопрос
                existing_question.text = question_data["text"]
                existing_question.options = options
                existing_question.correct_answer = correct_answer
                existing_question.question_type = question_data["question_type"]
                existing_question.difficulty = question_data.get("difficulty", 1)
                existing_question.media_url = media_url
                existing_question.explanation = question_data.get("explanation", "")
                return True, "updated"
            else:
                # Создаем новый вопрос
                question = Question(
                    topic_id=topic_id,
                    text=question_data["text"],
                    options=options,
                    correct_answer=correct_answer,
                    question_type=question_data["question_type"],
                    difficulty=question_data.get("difficulty", 1),
                    media_url=media_url,
                    explanation=question_data.get("explanation", "")
                )
                session.add(question)
                return True, "imported"

        except Exception as e:
            logger.error(f"Ошибка импорта отдельного вопроса: {e}")
            return False, "error"

    def _copy_media_file(self, media_path: str) -> Optional[str]:
        """Копирование медиафайла в папку проекта"""
        if not media_path:
            return None

        try:
            source_path = Path(media_path)

            # Если файл не существует, возвращаем исходный путь
            if not source_path.exists():
                logger.warning(f"Медиафайл не найден: {media_path}")
                return media_path

            # Определяем целевую директорию
            if DB_AVAILABLE:
                target_dir = Path(MEDIA_DIR) / "images"
            else:
                target_dir = self.project_root / "data" / "media" / "images"

            target_dir.mkdir(parents=True, exist_ok=True)

            # Создаем уникальное имя файла если файл уже существует
            target_file = target_dir / source_path.name
            counter = 1
            while target_file.exists():
                name_parts = source_path.stem, counter, source_path.suffix
                target_file = target_dir / f"{name_parts[0]}_{name_parts[1]}{name_parts[2]}"
                counter += 1

            # Копируем файл
            shutil.copy2(source_path, target_file)
            logger.info(f"Медиафайл скопирован: {source_path} -> {target_file}")

            # Возвращаем относительный путь
            return f"images/{target_file.name}"

        except Exception as e:
            logger.error(f"Ошибка копирования медиафайла {media_path}: {e}")
            return media_path

    def get_database_stats(self) -> Dict[str, Any]:
        """Получение статистики базы данных"""
        if not self.db_available:
            return {"error": "База данных недоступна"}

        try:
            with get_session() as session:
                # Основная статистика
                topics_count = session.query(Topic).count()
                questions_count = session.query(Question).count()

                # Статистика по типам вопросов
                question_types = {}
                for q_type in ['single', 'multiple', 'sequence']:
                    count = session.query(Question).filter(Question.question_type == q_type).count()
                    question_types[q_type] = count

                # Статистика по сложности
                difficulties = {}
                for difficulty in range(1, 6):
                    count = session.query(Question).filter(Question.difficulty == difficulty).count()
                    difficulties[str(difficulty)] = count

                # Статистика по темам
                topics_with_questions = []
                topics = session.query(Topic).all()
                for topic in topics:
                    q_count = session.query(Question).filter(Question.topic_id == topic.id).count()
                    topics_with_questions.append({
                        "name": topic.name,
                        "questions_count": q_count
                    })

                return {
                    "topics_count": topics_count,
                    "questions_count": questions_count,
                    "question_types": question_types,
                    "difficulties": difficulties,
                    "topics_details": topics_with_questions,
                    "db_engine": DB_ENGINE if DB_AVAILABLE else "Недоступно"
                }

        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {"error": str(e)}

    def validate_json_for_import(self, json_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Валидация JSON данных перед импортом"""
        if not DB_AVAILABLE or not VALIDATORS_AVAILABLE:
            # Базовая валидация без внешних модулей
            return self._basic_validation(json_data)

        try:
            # Используем валидаторы из utils
            valid, error = validate_json_structure(json_data)
            if not valid:
                return False, [error]
            return True, []

        except Exception as e:
            logger.error(f"Ошибка валидации: {e}")
            return self._basic_validation(json_data)

    def _basic_validation(self, json_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Базовая валидация без внешних модулей"""
        errors = []

        # Проверка структуры
        if "topic" not in json_data:
            errors.append("Отсутствует секция 'topic'")
        elif not isinstance(json_data["topic"], dict):
            errors.append("Секция 'topic' должна быть объектом")
        else:
            topic = json_data["topic"]
            if not topic.get("name", "").strip():
                errors.append("Название темы не может быть пустым")

        if "questions" not in json_data:
            errors.append("Отсутствует секция 'questions'")
        elif not isinstance(json_data["questions"], list):
            errors.append("Секция 'questions' должна быть массивом")
        else:
            questions = json_data["questions"]
            if not questions:
                errors.append("Список вопросов не может быть пустым")

            for i, question in enumerate(questions):
                if not isinstance(question, dict):
                    errors.append(f"Вопрос {i + 1} должен быть объектом")
                    continue

                # Проверка обязательных полей
                if not question.get("text", "").strip():
                    errors.append(f"Вопрос {i + 1}: отсутствует или пустой текст")

                if "options" not in question or not question["options"]:
                    errors.append(f"Вопрос {i + 1}: отсутствуют варианты ответов")
                elif len(question["options"]) < 2:
                    errors.append(f"Вопрос {i + 1}: должно быть минимум 2 варианта ответа")

                if "correct_answer" not in question:
                    errors.append(f"Вопрос {i + 1}: отсутствует правильный ответ")

                if question.get("question_type") not in ["single", "multiple", "sequence"]:
                    errors.append(f"Вопрос {i + 1}: неверный тип вопроса")

        return len(errors) == 0, errors

    def backup_database(self, backup_path: str) -> Tuple[bool, str]:
        """Создание резервной копии всех данных"""
        if not self.db_available:
            return False, "База данных недоступна"

        try:
            topics = self.get_existing_topics()
            backup_data = {
                "created_at": datetime.now().isoformat(),
                "topics": []
            }

            for topic in topics:
                topic_data = self.export_topic_to_json(topic["id"])
                if topic_data:
                    backup_data["topics"].append(topic_data)

            # Сохраняем резервную копию
            backup_file = Path(backup_path)
            backup_file.parent.mkdir(parents=True, exist_ok=True)

            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)

            return True, f"Резервная копия создана: {backup_file}"

        except Exception as e:
            logger.error(f"Ошибка создания резервной копии: {e}")
            return False, f"Ошибка: {str(e)}"


class DatabaseDialog:
    """Диалог для работы с базой данных в JSON Theme Maker"""

    def __init__(self, parent, db_integration: DatabaseIntegration):
        self.parent = parent
        self.db_integration = db_integration
        self.result = None

    def show_connection_dialog(self):
        """Показ диалога подключения к БД с расширенным функционалом"""
        dialog = tk.Toplevel(self.parent)
        dialog.title("Интеграция с базой данных")
        dialog.geometry("700x600")
        dialog.transient(self.parent)
        dialog.grab_set()

        # Настройка иконки для Windows
        try:
            dialog.iconbitmap(default="")  # Убираем стандартную иконку
        except:
            pass

        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Вкладка "Подключение"
        self._create_connection_tab(notebook)

        # Вкладка "Экспорт"
        self._create_export_tab(notebook)

        # Вкладка "Статистика"
        self._create_stats_tab(notebook)

        # Кнопки внизу
        buttons_frame = ttk.Frame(dialog)
        buttons_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        ttk.Button(buttons_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)

        return self.result

    def _create_connection_tab(self, notebook):
        """Создание вкладки подключения"""
        connection_tab = ttk.Frame(notebook)
        notebook.add(connection_tab, text="Подключение")

        # Тестирование подключения
        test_frame = ttk.LabelFrame(connection_tab, text="Статус подключения")
        test_frame.pack(fill=tk.X, padx=10, pady=10)

        self.status_label = ttk.Label(test_frame, text="Статус: Не проверено")
        self.status_label.pack(padx=10, pady=5)

        self.connection_details = tk.Text(test_frame, height=4, wrap=tk.WORD)
        self.connection_details.pack(fill=tk.X, padx=10, pady=5)

        def test_connection():
            success, message = self.db_integration.test_connection()
            status = "✅ Подключено" if success else "❌ Ошибка"
            self.status_label.config(text=f"Статус: {status}")

            details = f"Результат: {message}\n"
            if success:
                stats = self.db_integration.get_database_stats()
                if "error" not in stats:
                    details += f"Тем: {stats['topics_count']}\n"
                    details += f"Вопросов: {stats['questions_count']}\n"
                    details += f"БД: {stats.get('db_engine', 'Неизвестно')}"

            self.connection_details.delete(1.0, tk.END)
            self.connection_details.insert(1.0, details)

        ttk.Button(test_frame, text="Тестировать подключение", command=test_connection).pack(pady=5)

        # Резервное копирование
        backup_frame = ttk.LabelFrame(connection_tab, text="Резервное копирование")
        backup_frame.pack(fill=tk.X, padx=10, pady=10)

        def create_backup():
            file_path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")],
                title="Сохранить резервную копию"
            )

            if file_path:
                success, message = self.db_integration.backup_database(file_path)
                if success:
                    messagebox.showinfo("Успех", message)
                else:
                    messagebox.showerror("Ошибка", message)

        ttk.Button(backup_frame, text="Создать резервную копию всех данных",
                   command=create_backup).pack(pady=10)

        # Инициализация
        test_connection()

    def _create_export_tab(self, notebook):
        """Создание вкладки экспорта"""
        export_tab = ttk.Frame(notebook)
        notebook.add(export_tab, text="Экспорт из БД")

        # Список тем для экспорта
        topics_frame = ttk.LabelFrame(export_tab, text="Экспорт темы из базы данных")
        topics_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Фрейм с комбобоксом и кнопкой обновления
        selection_frame = ttk.Frame(topics_frame)
        selection_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(selection_frame, text="Выберите тему:").pack(anchor=tk.W)

        combo_frame = ttk.Frame(selection_frame)
        combo_frame.pack(fill=tk.X, pady=5)

        self.topics_combo = ttk.Combobox(combo_frame, state="readonly")
        self.topics_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)

        def refresh_topics():
            topics = self.db_integration.get_existing_topics()
            if topics:
                values = [f"{topic['id']}: {topic['name']} ({topic.get('description', '')[:50]}...)"
                          for topic in topics]
                self.topics_combo['values'] = values
            else:
                self.topics_combo['values'] = ["Темы не найдены"]

        ttk.Button(combo_frame, text="Обновить", command=refresh_topics).pack(side=tk.RIGHT, padx=(5, 0))

        # Информация о выбранной теме
        self.topic_info = tk.Text(topics_frame, height=8, wrap=tk.WORD, state=tk.DISABLED)
        self.topic_info.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        def on_topic_select(event):
            selection = self.topics_combo.get()
            if selection and not selection.startswith("Темы не найдены"):
                topic_id = int(selection.split(":")[0])
                questions = self.db_integration.get_topic_questions(topic_id)

                info = f"Вопросов в теме: {len(questions)}\n\n"

                # Статистика по типам
                types_count = {}
                difficulties_count = {}

                for q in questions:
                    q_type = q.get('question_type', 'unknown')
                    difficulty = q.get('difficulty', 1)

                    types_count[q_type] = types_count.get(q_type, 0) + 1
                    difficulties_count[difficulty] = difficulties_count.get(difficulty, 0) + 1

                info += "По типам:\n"
                for q_type, count in types_count.items():
                    info += f"  {q_type}: {count}\n"

                info += "\nПо сложности:\n"
                for diff in sorted(difficulties_count.keys()):
                    info += f"  Уровень {diff}: {difficulties_count[diff]}\n"

                self.topic_info.config(state=tk.NORMAL)
                self.topic_info.delete(1.0, tk.END)
                self.topic_info.insert(1.0, info)
                self.topic_info.config(state=tk.DISABLED)

        self.topics_combo.bind("<<ComboboxSelected>>", on_topic_select)

        # Кнопки экспорта
        export_buttons = ttk.Frame(topics_frame)
        export_buttons.pack(fill=tk.X, padx=10, pady=10)

        def export_selected_topic():
            selection = self.topics_combo.get()
            if not selection or selection.startswith("Темы не найдены"):
                messagebox.showwarning("Предупреждение", "Выберите тему для экспорта")
                return

            topic_id = int(selection.split(":")[0])
            data = self.db_integration.export_topic_to_json(topic_id)

            if data:
                self.result = {"action": "export", "data": data}
                messagebox.showinfo("Успех", f"Тема '{data['topic']['name']}' готова к импорту в редактор")
                dialog.destroy()
            else:
                messagebox.showerror("Ошибка", "Не удалось экспортировать тему")

        ttk.Button(export_buttons, text="Загрузить тему в редактор",
                   command=export_selected_topic).pack(side=tk.LEFT, padx=5)

        # Инициализация
        refresh_topics()

    def _create_stats_tab(self, notebook):
        """Создание вкладки статистики"""
        stats_tab = ttk.Frame(notebook)
        notebook.add(stats_tab, text="Статистика")

        stats_frame = ttk.LabelFrame(stats_tab, text="Статистика базы данных")
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.stats_text = tk.Text(stats_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.stats_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        def refresh_stats():
            stats = self.db_integration.get_database_stats()

            if "error" in stats:
                stats_info = f"Ошибка получения статистики: {stats['error']}"
            else:
                stats_info = f"📊 ОБЩАЯ СТАТИСТИКА\n"
                stats_info += f"{'=' * 50}\n\n"
                stats_info += f"Всего тем: {stats['topics_count']}\n"
                stats_info += f"Всего вопросов: {stats['questions_count']}\n"
                stats_info += f"База данных: {stats.get('db_engine', 'Неизвестно')}\n\n"

                stats_info += f"📝 ПО ТИПАМ ВОПРОСОВ:\n"
                stats_info += f"{'-' * 30}\n"
                for q_type, count in stats['question_types'].items():
                    stats_info += f"{q_type}: {count}\n"

                stats_info += f"\n🎯 ПО СЛОЖНОСТИ:\n"
                stats_info += f"{'-' * 30}\n"
                for difficulty, count in stats['difficulties'].items():
                    stats_info += f"Уровень {difficulty}: {count}\n"

                if stats.get('topics_details'):
                    stats_info += f"\n📚 ДЕТАЛИ ПО ТЕМАМ:\n"
                    stats_info += f"{'-' * 30}\n"
                    for topic in stats['topics_details']:
                        stats_info += f"{topic['name']}: {topic['questions_count']} вопросов\n"

            self.stats_text.config(state=tk.NORMAL)
            self.stats_text.delete(1.0, tk.END)
            self.stats_text.insert(1.0, stats_info)
            self.stats_text.config(state=tk.DISABLED)

        ttk.Button(stats_frame, text="Обновить статистику", command=refresh_stats).pack(pady=5)

        # Инициализация
        refresh_stats()

    def show_import_dialog(self, json_data: Dict[str, Any]):
        """Показ диалога импорта в БД с расширенными опциями"""
        dialog = tk.Toplevel(self.parent)
        dialog.title("Импорт в базу данных")
        dialog.geometry("700x700")
        dialog.transient(self.parent)
        dialog.grab_set()

        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Вкладка валидации
        validation_tab = ttk.Frame(notebook)
        notebook.add(validation_tab, text="Проверка данных")

        validation_frame = ttk.LabelFrame(validation_tab, text="Результаты проверки")
        validation_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        valid, errors = self.db_integration.validate_json_for_import(json_data)

        if valid:
            ttk.Label(validation_frame, text="✅ Данные прошли проверку",
                      foreground="green").pack(padx=10, pady=5)
        else:
            ttk.Label(validation_frame, text="❌ Обнаружены ошибки:",
                      foreground="red").pack(padx=10, pady=5)

        errors_text = tk.Text(validation_frame, height=10, wrap=tk.WORD)
        errors_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        if errors:
            errors_text.insert(tk.END, "\n".join(errors))
        else:
            errors_text.insert(tk.END, "Ошибок не обнаружено. Данные готовы к импорту.")
        errors_text.config(state=tk.DISABLED)

        # Вкладка опций
        options_tab = ttk.Frame(notebook)
        notebook.add(options_tab, text="Опции импорта")

        options_frame = ttk.LabelFrame(options_tab, text="Настройки импорта")
        options_frame.pack(fill=tk.X, padx=10, pady=10)

        update_existing = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Обновить существующие записи (иначе пропустить)",
                        variable=update_existing).pack(anchor=tk.W, padx=10, pady=5)

        copy_images = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Копировать изображения в папку проекта",
                        variable=copy_images).pack(anchor=tk.W, padx=10, pady=5)

        # Предварительный просмотр
        preview_frame = ttk.LabelFrame(options_tab, text="Предварительный просмотр")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        topic_name = json_data.get("topic", {}).get("name", "Неизвестно")
        questions_count = len(json_data.get("questions", []))

        preview_info = f"Тема: {topic_name}\n"
        preview_info += f"Описание: {json_data.get('topic', {}).get('description', 'Отсутствует')}\n"
        preview_info += f"Количество вопросов: {questions_count}\n\n"

        # Анализ вопросов
        questions = json_data.get("questions", [])
        if questions:
            types_count = {}
            difficulties_count = {}

            for q in questions:
                q_type = q.get('question_type', 'unknown')
                difficulty = q.get('difficulty', 1)

                types_count[q_type] = types_count.get(q_type, 0) + 1
                difficulties_count[difficulty] = difficulties_count.get(difficulty, 0) + 1

            preview_info += "Распределение по типам:\n"
            for q_type, count in types_count.items():
                preview_info += f"  {q_type}: {count}\n"

            preview_info += "\nРаспределение по сложности:\n"
            for diff in sorted(difficulties_count.keys()):
                preview_info += f"  Уровень {diff}: {difficulties_count[diff]}\n"

        preview_text = tk.Text(preview_frame, wrap=tk.WORD, state=tk.DISABLED)
        preview_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        preview_text.config(state=tk.NORMAL)
        preview_text.insert(tk.END, preview_info)
        preview_text.config(state=tk.DISABLED)

        # Кнопки
        buttons_frame = ttk.Frame(dialog)
        buttons_frame.pack(fill=tk.X, padx=10, pady=10)

        def perform_import():
            if not valid:
                messagebox.showerror("Ошибка", "Невозможно импортировать данные с ошибками")
                return

            # Показываем прогресс
            progress_dialog = tk.Toplevel(dialog)
            progress_dialog.title("Импорт...")
            progress_dialog.geometry("400x150")
            progress_dialog.transient(dialog)
            progress_dialog.grab_set()

            ttk.Label(progress_dialog, text="Выполняется импорт данных...").pack(pady=20)
            progress = ttk.Progressbar(progress_dialog, mode='indeterminate')
            progress.pack(fill=tk.X, padx=20, pady=10)
            progress.start()

            def do_import():
                try:
                    success, message = self.db_integration.import_json_to_database(
                        json_data, update_existing.get(), copy_images.get()
                    )

                    progress_dialog.destroy()

                    if success:
                        messagebox.showinfo("Успех", message)
                        self.result = {"action": "import", "success": True}
                        dialog.destroy()
                    else:
                        messagebox.showerror("Ошибка", message)

                except Exception as e:
                    progress_dialog.destroy()
                    messagebox.showerror("Ошибка", f"Неожиданная ошибка: {str(e)}")

            # Запускаем импорт через небольшой timeout для отображения прогресса
            dialog.after(100, do_import)

        ttk.Button(buttons_frame, text="Импортировать",
                   command=perform_import).pack(side=tk.RIGHT, padx=5)
        ttk.Button(buttons_frame, text="Отмена",
                   command=dialog.destroy).pack(side=tk.RIGHT, padx=5)

        return self.result


# Функции для интеграции с JSON Theme Maker
def add_database_menu_to_editor(editor_app):
    """Добавление меню базы данных в JSON Theme Maker"""
    try:
        db_integration = DatabaseIntegration()

        # Добавляем новое меню
        database_menu = tk.Menu(editor_app.root.nametowidget(".!menu"))
        editor_app.root.nametowidget(".!menu").add_cascade(label="База данных", menu=database_menu)

        def show_db_dialog():
            dialog = DatabaseDialog(editor_app.root, db_integration)
            result = dialog.show_connection_dialog()

            if result and result.get("action") == "export":
                # Загружаем данные в редактор
                data = result["data"]
                editor_app.data = data
                editor_app.current_file_path = None
                editor_app.update_topic_info()
                editor_app.update_questions_list()
                editor_app.update_stats()
                editor_app.unsaved_changes = True
                editor_app.update_window_title()

        def import_to_database():
            if not editor_app.data["questions"]:
                messagebox.showwarning("Предупреждение", "Нет данных для импорта в базу данных")
                return

            dialog = DatabaseDialog(editor_app.root, db_integration)
            dialog.show_import_dialog(editor_app.data)

        database_menu.add_command(label="Подключение и экспорт из БД", command=show_db_dialog)
        database_menu.add_command(label="Импорт в БД", command=import_to_database)
        database_menu.add_separator()
        database_menu.add_command(label="Статистика БД",
                                  command=lambda: DatabaseDialog(editor_app.root,
                                                                 db_integration).show_connection_dialog())

    except Exception as e:
        logger.error(f"Ошибка добавления меню БД: {e}")


if __name__ == "__main__":
    # Тестирование функциональности
    print(f"Корневая директория проекта: {PROJECT_ROOT}")
    print(f"База данных доступна: {DB_AVAILABLE}")

    db_integration = DatabaseIntegration()

    # Тест подключения
    success, message = db_integration.test_connection()
    print(f"Подключение: {success} - {message}")

    if success:
        # Получение статистики
        stats = db_integration.get_database_stats()
        print("Статистика БД:", stats)

        # Получение тем
        topics = db_integration.get_existing_topics()
        print(f"Доступные темы: {len(topics)}")

        for topic in topics[:3]:  # Показываем первые 3 темы
            print(f"  - {topic['name']} (ID: {topic['id']})")
