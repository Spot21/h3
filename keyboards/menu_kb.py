from telegram import ReplyKeyboardMarkup, KeyboardButton, BotCommand, BotCommandScopeChat, BotCommandScopeDefault


def student_main_menu() -> ReplyKeyboardMarkup:
    """Создание основного меню с кнопками для ученика"""
    keyboard = [
        [KeyboardButton("📝 Начать тест"), KeyboardButton("📊 Моя статистика")],
        [KeyboardButton("🎯 Рекомендации"), KeyboardButton("🏆 Достижения")],
        [KeyboardButton("🔍 Справка"), KeyboardButton("👨‍💻 Мой код")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def parent_main_menu() -> ReplyKeyboardMarkup:
    """Создание основного меню с кнопками для родителя"""
    keyboard = [
        [KeyboardButton("🔗 Привязать ученика"), KeyboardButton("📊 Отчеты")],
        [KeyboardButton("⚙️ Настройки"), KeyboardButton("🔍 Справка")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def admin_main_menu() -> ReplyKeyboardMarkup:
    """Создание основного меню с кнопками для администратора"""
    keyboard = [
        [KeyboardButton("👨‍💻 Панель администратора"), KeyboardButton("📊 Статистика")],
        [KeyboardButton("➕ Добавить вопрос"), KeyboardButton("📁 Импорт вопросов")],
        [KeyboardButton("📤 Экспорт в Excel"), KeyboardButton("⚙️ Настройки")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_bot_commands(role: str) -> list:
    """Получение списка команд бота в зависимости от роли пользователя"""
    if role == "student":
        return [
            ("start", "Запустить бота"),
            ("test", "Начать тестирование"),
            ("stats", "Показать статистику"),
            ("achievements", "Показать достижения"),
            ("mycode", "Получить код для родителя"),
            ("help", "Показать справку")
        ]
    elif role == "parent":
        return [
            ("start", "Запустить бота"),
            ("link", "Привязать ученика"),
            ("report", "Получить отчет"),
            ("settings", "Настройки уведомлений"),
            ("help", "Показать справку")
        ]
    elif role == "admin":
        return [
            ("start", "Запустить бота"),
            ("admin", "Панель администратора"),
            ("add_question", "Добавить вопрос"),
            ("import", "Импортировать вопросы"),
            ("export_excel", "Экспорт в Excel"),
            ("help", "Показать справку")
        ]
    else:
        # Базовый набор команд для неопределенной роли
        return [
            ("start", "Запустить бота"),
            ("help", "Показать справка")
        ]


async def set_commands_for_user(bot, user_id, role):
    """Устанавливает команды для конкретного пользователя в зависимости от его роли"""
    commands = get_bot_commands(role)
    bot_commands = [BotCommand(command, description) for command, description in commands]

    # Устанавливаем команды для конкретного пользователя
    try:
        # Устанавливаем команды для конкретного пользователя, используя область видимости чата
        await bot.set_my_commands(
            bot_commands,
            scope=BotCommandScopeChat(chat_id=user_id)
        )
        return True
    except Exception as e:
        # Если не удалось установить команды с областью видимости,
        # просто устанавливаем общие команды (в этом случае все пользователи увидят одинаковые команды)
        try:
            await bot.set_my_commands(bot_commands)
            return True
        except Exception as e2:
            return False


async def setup_default_commands(bot):
    """Устанавливает базовые команды для всех пользователей"""
    default_commands = [
        BotCommand("start", "Запустить бота"),
        BotCommand("help", "Показать справку")
    ]

    try:
        # Устанавливаем базовые команды для всех пользователей
        await bot.set_my_commands(
            default_commands,
            scope=BotCommandScopeDefault()
        )
        return True
    except Exception:
        # Если не удалось установить с областью видимости, устанавливаем обычным способом
        try:
            await bot.set_my_commands(default_commands)
            return True
        except Exception:
            return False