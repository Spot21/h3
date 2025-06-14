
"""
Модуль для интеграции JSON Theme Maker с основной базой данных проекта
"""

import json
import logging
import os
import sys
from typing import Dict, List, Any, Optional, Tuple
import traceback

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    from database.db_manager import get_session
    from database.models import Topic, Question
    from config import DB_ENGINE, MEDIA_DIR

    DB_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Модули базы данных недоступны: {e}")
    DB_AVAILABLE = False

logger = logging.getLogger(__name__)


class DatabaseIntegration:
    """Класс для интеграции с базой данных проекта"""

    def __init__(self):
        self.db_available = DB_AVAILABLE

    def test_connection(self) -> Tuple[bool, str]:
        """Тестирование подключения к базе данных"""
        if not self.db_available:
            return False, "Модули базы данных недоступны"

        try:
            with get_session() as session:
                # Простой запрос для проверки соединения
                result = session.execute("SELECT 1").scalar()
                return True, "Подключение успешно"
        except Exception as e:
            return False, f"Ошибка подключения: {str(e)}"

    def get_existing_topics(self) -> List[Dict[str, Any]]:
        """Получение существующих тем из базы данных"""
        if not self.db_available:
            return []

        try:
            with get_session() as session:
                topics = session.query(Topic).all()
                return [
                    {
                        "id": topic.id,
                        "name": topic.name,
                        "description": topic.description or ""
                    }
                    for topic in topics
                ]
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
                        options = json.loads(question.options) if isinstance(question.options,
                                                                             str) else question.options
                        correct_answer = json.loads(question.correct_answer) if isinstance(question.correct_answer,
                                                                                           str) else question.correct_answer

                        result.append({
                            "id": question.id,
                            "text": question.text,
                            "options": options,
                            "correct_answer": correct_answer,
                            "question_type": question.question_type,
                            "difficulty": question.difficulty,
                            "media_url": question.media_url,
                            "explanation": question.explanation or ""
                        })
                    except json.JSONDecodeError as e:
                        logger.error(f"Ошибка парсинга JSON для вопроса {question.id}: {e}")
                        continue

                return result
        except Exception as e:
            logger.error(f"Ошибка получения вопросов: {e}")
            return []

    def export_topic_to_json(self, topic_id: int) -> Optional[Dict[str, Any]]:
        """Экспорт темы и её вопросов в формат JSON"""
        if not self.db_available:
            return None

        try:
            with get_session() as session:
                # Получаем тему
                topic = session.query(Topic).get(topic_id)
                if not topic:
                    return None

                # Получаем вопросы
                questions = self.get_topic_questions(topic_id)

                return {
                    "topic": {
                        "id": topic.id,
                        "name": topic.name,
                        "description": topic.description or ""
                    },
                    "questions": questions
                }
        except Exception as e:
            logger.error(f"Ошибка экспорта темы: {e}")
            return None

    def import_json_to_database(self, json_data: Dict[str, Any], update_existing: bool = False) -> Tuple[bool, str]:
        """Импорт JSON данных в базу данных"""
        if not self.db_available:
            return False, "База данных недоступна"

        try:
            with get_session() as session:
                # Обрабатываем тему
                topic_data = json_data.get("topic", {})
                topic_id = topic_data.get("id")

                # Проверяем существование темы
                existing_topic = None
                if topic_id:
                    existing_topic = session.query(Topic).get(topic_id)

                if existing_topic and not update_existing:
                    return False, f"Тема с ID {topic_id} уже существует. Используйте опцию обновления."

                if existing_topic and update_existing:
                    # Обновляем существующую тему
                    existing_topic.name = topic_data["name"]
                    existing_topic.description = topic_data.get("description", "")
                    topic = existing_topic
                else:
                    # Создаем новую тему
                    topic = Topic(
                        name=topic_data["name"],
                        description=topic_data.get("description", "")
                    )
                    session.add(topic)
                    session.flush()  # Получаем ID

                # Обрабатываем вопросы
                questions_data = json_data.get("questions", [])
                imported_questions = 0

                for question_data in questions_data:
                    try:
                        # Проверяем существование вопроса
                        question_id = question_data.get("id")
                        existing_question = None

                        if question_id:
                            existing_question = session.query(Question).filter(
                                Question.id == question_id,
                                Question.topic_id == topic.id
                            ).first()

                        if existing_question and not update_existing:
                            continue  # Пропускаем существующий вопрос

                        # Подготавливаем данные
                        options = question_data["options"]
                        correct_answer = question_data["correct_answer"]

                        if not isinstance(options, str):
                            options = json.dumps(options)
                        if not isinstance(correct_answer, str):
                            correct_answer = json.dumps(correct_answer)

                        if existing_question and update_existing:
                            # Обновляем существующий вопрос
                            existing_question.text = question_data["text"]
                            existing_question.options = options
                            existing_question.correct_answer = correct_answer
                            existing_question.question_type = question_data["question_type"]
                            existing_question.difficulty = question_data.get("difficulty", 1)
                            existing_question.media_url = question_data.get("media_url")
                            existing_question.explanation = question_data.get("explanation", "")
                        else:
                            # Создаем новый вопрос
                            question = Question(
                                topic_id=topic.id,
                                text=question_data["text"],
                                options=options,
                                correct_answer=correct_answer,
                                question_type=question_data["question_type"],
                                difficulty=question_data.get("difficulty", 1),
                                media_url=question_data.get("media_url"),
                                explanation=question_data.get("explanation", "")
                            )
                            session.add(question)

                        imported_questions += 1

                    except Exception as e:
                        logger.error(f"Ошибка импорта вопроса: {e}")
                        continue

                # Фиксируем изменения
                session.commit()

                return True, f"Успешно импортировано: тема '{topic.name}', вопросов: {imported_questions}"

        except Exception as e:
            logger.error(f"Ошибка импорта в базу данных: {e}")
            logger.error(traceback.format_exc())
            return False, f"Ошибка импорта: {str(e)}"

    def get_database_stats(self) -> Dict[str, Any]:
        """Получение статистики базы данных"""
        if not self.db_available:
            return {"error": "База данных недоступна"}

        try:
            with get_session() as session:
                topics_count = session.query(Topic).count()
                questions_count = session.query(Question).count()

                # Статистика по типам вопросов
                question_types = session.query(Question.question_type,
                                               session.query(Question).filter(
                                                   Question.question_type == Question.question_type).count()
                                               ).group_by(Question.question_type).all()

                # Статистика по сложности
                difficulties = session.query(Question.difficulty,
                                             session.query(Question).filter(
                                                 Question.difficulty == Question.difficulty).count()
                                             ).group_by(Question.difficulty).all()

                return {
                    "topics_count": topics_count,
                    "questions_count": questions_count,
                    "question_types": dict(question_types),
                    "difficulties": dict(difficulties)
                }
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {"error": str(e)}

    def validate_json_for_import(self, json_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Валидация JSON данных перед импортом"""
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


class DatabaseDialog:
    """Диалог для работы с базой данных"""

    def __init__(self, parent, db_integration: DatabaseIntegration):
        self.parent = parent
        self.db_integration = db_integration
        self.result = None

    def show_connection_dialog(self):
        """Показ диалога подключения к БД"""
        import tkinter as tk
        from tkinter import ttk, messagebox

        dialog = tk.Toplevel(self.parent)
        dialog.title("Подключение к базе данных")
        dialog.geometry("500x400")
        dialog.transient(self.parent)
        dialog.grab_set()

        # Тестирование подключения
        test_frame = ttk.LabelFrame(dialog, text="Тестирование подключения")
        test_frame.pack(fill=tk.X, padx=10, pady=10)

        status_label = ttk.Label(test_frame, text="Статус: Не проверено")
        status_label.pack(padx=10, pady=5)

        def test_connection():
            success, message = self.db_integration.test_connection()
            status = "✅ Подключено" if success else "❌ Ошибка"
            status_label.config(text=f"Статус: {status} - {message}")

            if success:
                stats = self.db_integration.get_database_stats()
                if "error" not in stats:
                    stats_text = f"Тем: {stats['topics_count']}, Вопросов: {stats['questions_count']}"
                    stats_label.config(text=stats_text)

        ttk.Button(test_frame, text="Тестировать подключение", command=test_connection).pack(pady=5)

        stats_label = ttk.Label(test_frame, text="")
        stats_label.pack(padx=10, pady=5)

        # Операции с базой данных
        operations_frame = ttk.LabelFrame(dialog, text="Операции")
        operations_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Список тем для экспорта
        ttk.Label(operations_frame, text="Экспорт темы из БД:").pack(anchor=tk.W, padx=5, pady=5)

        topics_frame = ttk.Frame(operations_frame)
        topics_frame.pack(fill=tk.X, padx=5, pady=5)

        self.topics_combo = ttk.Combobox(topics_frame, state="readonly")
        self.topics_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)

        def refresh_topics():
            topics = self.db_integration.get_existing_topics()
            values = [f"{topic['id']}: {topic['name']}" for topic in topics]
            self.topics_combo['values'] = values

        ttk.Button(topics_frame, text="Обновить", command=refresh_topics).pack(side=tk.RIGHT, padx=(5, 0))

        def export_selected_topic():
            selection = self.topics_combo.get()
            if not selection:
                messagebox.showwarning("Предупреждение", "Выберите тему для экспорта")
                return

            topic_id = int(selection.split(":")[0])
            data = self.db_integration.export_topic_to_json(topic_id)

            if data:
                self.result = {"action": "export", "data": data}
                dialog.destroy()
            else:
                messagebox.showerror("Ошибка", "Не удалось экспортировать тему")

        ttk.Button(operations_frame, text="Экспортировать выбранную тему",
                   command=export_selected_topic).pack(pady=5)

        # Кнопки
        buttons_frame = ttk.Frame(dialog)
        buttons_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(buttons_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)

        # Инициализация
        test_connection()
        refresh_topics()

        return self.result

    def show_import_dialog(self, json_data: Dict[str, Any]):
        """Показ диалога импорта в БД"""
        import tkinter as tk
        from tkinter import ttk, messagebox

        dialog = tk.Toplevel(self.parent)
        dialog.title("Импорт в базу данных")
        dialog.geometry("600x500")
        dialog.transient(self.parent)
        dialog.grab_set()

        # Валидация данных
        validation_frame = ttk.LabelFrame(dialog, text="Проверка данных")
        validation_frame.pack(fill=tk.X, padx=10, pady=10)

        valid, errors = self.db_integration.validate_json_for_import(json_data)

        if valid:
            ttk.Label(validation_frame, text="✅ Данные прошли проверку",
                      foreground="green").pack(padx=10, pady=5)
        else:
            ttk.Label(validation_frame, text="❌ Обнаружены ошибки:",
                      foreground="red").pack(padx=10, pady=5)

            errors_text = tk.Text(validation_frame, height=6, wrap=tk.WORD)
            errors_text.pack(fill=tk.X, padx=10, pady=5)
            errors_text.insert(tk.END, "\n".join(errors))
            errors_text.config(state=tk.DISABLED)

        # Опции импорта
        options_frame = ttk.LabelFrame(dialog, text="Опции импорта")
        options_frame.pack(fill=tk.X, padx=10, pady=10)

        update_existing = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Обновить существующие записи",
                        variable=update_existing).pack(anchor=tk.W, padx=10, pady=5)

        # Предварительный просмотр
        preview_frame = ttk.LabelFrame(dialog, text="Предварительный просмотр")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        topic_name = json_data.get("topic", {}).get("name", "Неизвестно")
        questions_count = len(json_data.get("questions", []))

        preview_text = f"Тема: {topic_name}\nКоличество вопросов: {questions_count}"
        ttk.Label(preview_frame, text=preview_text).pack(padx=10, pady=10)

        # Кнопки
        buttons_frame = ttk.Frame(dialog)
        buttons_frame.pack(fill=tk.X, padx=10, pady=10)

        def perform_import():
            if not valid:
                messagebox.showerror("Ошибка", "Невозможно импортировать данные с ошибками")
                return

            success, message = self.db_integration.import_json_to_database(
                json_data, update_existing.get()
            )

            if success:
                messagebox.showinfo("Успех", message)
                self.result = {"action": "import", "success": True}
                dialog.destroy()
            else:
                messagebox.showerror("Ошибка", message)

        ttk.Button(buttons_frame, text="Импортировать",
                   command=perform_import).pack(side=tk.RIGHT, padx=5)
        ttk.Button(buttons_frame, text="Отмена",
                   command=dialog.destroy).pack(side=tk.RIGHT, padx=5)

        return self.result


# Пример использования
if __name__ == "__main__":
    # Тестирование функциональности
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
        print("Доступные темы:", len(topics))

        for topic in topics[:3]:  # Показываем первые 3 темы
            print(f"  - {topic['name']} (ID: {topic['id']})")
