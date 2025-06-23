from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Пример клавиатуры (будет расширяться)

def basic_test_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="Тест 1", callback_data="test_1")
    kb.button(text="Тест 2", callback_data="test_2")
    return kb.as_markup()

# Клавиатуры для /start (принятие соглашений)
def start_agreement_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📜 Пользовательское соглашение", callback_data="read_terms")
    )
    builder.row(
        InlineKeyboardButton(text="🔒 Политика конфиденциальности", callback_data="read_privacy")
    )
    builder.row(
        InlineKeyboardButton(text="📄 Уведомление об ответственности", callback_data="read_disclaimer_start") # Новая кнопка
    )
    builder.row(
        InlineKeyboardButton(text="✅ Принять и продолжить", callback_data="accept_terms"),
        InlineKeyboardButton(text="❌ Отказаться", callback_data="decline_terms")
    )
    return builder.as_markup()

def choose_role_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Я Работодатель", callback_data="role_employer"),
        InlineKeyboardButton(text="Я Соискатель", callback_data="role_job_seeker")
    )
    return builder.as_markup()


# Клавиатуры для главного меню (будут зависеть от роли)
# def employer_main_menu_keyboard():
#     pass

# def job_seeker_main_menu_keyboard():
#     pass

# def admin_main_menu_keyboard():
#     pass

# Другие специфичные клавиатуры...
