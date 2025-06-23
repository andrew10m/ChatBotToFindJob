from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# Пример клавиатуры (будет расширяться)

def main_menu_reply_keyboard(): # Это будет общая клавиатура, возможно, стоит убрать
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="/menu"))
    builder.row(KeyboardButton(text="/profile"))
    return builder.as_markup(resize_keyboard=True)

def cancel_fsm_reply_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="Отмена"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

# Клавиатуры для запроса контактов и т.д.
# def request_contact_keyboard():
#     builder = ReplyKeyboardBuilder()
#     builder.button(text="Поделиться контактом", request_contact=True)
#     return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)
