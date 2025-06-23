import logging
from aiogram import Router, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.inline_keyboards import start_agreement_keyboard, choose_role_keyboard
from keyboards.reply_keyboards import cancel_fsm_reply_keyboard
from db import queries as db_queries
from states.user_states import RegistrationStates
from config import (
    USER_AGREEMENT_PATH, PRIVACY_POLICY_PATH, DISCLAIMER_NOTICE_PATH,
    MODERATION_POLICY_PATH, ADMIN_IDS
)

logger = logging.getLogger(__name__)
router = Router()

async def read_document(file_path: str) -> str:
    """Читает текстовый файл и возвращает его содержимое."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.warning(f"Document not found: {file_path}")
        return "Документ не найден."
    except Exception as e:
        logger.error(f"Error reading document {file_path}: {e}")
        return f"Ошибка при чтении документа."

WELCOME_TEXT = """👋 **Добро пожаловать в JobBot!**

Я помогу вам разместить вакансии или найти работу.

Прежде чем мы начнем, пожалуйста, ознакомьтесь с нашими правилами:
- **Пользовательское соглашение** (определяет правила использования бота)
- **Политика конфиденциальности** (как мы обрабатываем ваши данные)

Нажимая «✅ Принять и продолжить», вы подтверждаете, что прочитали и согласны с этими документами, а также даете согласие на обработку ваших персональных данных.

Вы также можете прочитать **Уведомление об ограничении ответственности** (важная информация о роли платформы).
"""

DISCLAIMER_TEXT_SHORT = "JobBot является информационной платформой и не несет ответственности за договоренности между пользователями. Подробнее: /about или кнопка ниже."

# --- Document Reading and Close Button Logic ---

async def send_document_with_close_button(target_message: Message, doc_text: str, title: str):
    """Отправляет текст документа с кнопкой Закрыть."""
    MAX_LENGTH = 4096 # Максимальная длина сообщения Telegram
    chunks = [doc_text[i:i + MAX_LENGTH] for i in range(0, len(doc_text), MAX_LENGTH)]

    close_button_kb = InlineKeyboardBuilder()
    close_button_kb.button(text="❌ Закрыть", callback_data="close_message")

    await target_message.answer(f"**{title}**", parse_mode="Markdown") # Сначала заголовок
    for i, chunk in enumerate(chunks):
        if i == len(chunks) - 1: # Последний чанк
            await target_message.answer(chunk, parse_mode="Markdown", reply_markup=close_button_kb.as_markup())
        else:
            await target_message.answer(chunk, parse_mode="Markdown")

@router.callback_query(F.data == "close_message")
async def cq_close_message(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception as e:
        logger.warning(f"Could not delete message {callback.message.message_id}: {e}")
        try:
            await callback.message.edit_text("Окно закрыто.", reply_markup=None)
        except Exception as e_edit:
             logger.warning(f"Could not edit message {callback.message.message_id} to 'Окно закрыто': {e_edit}")
    await callback.answer()

# --- /start and Registration Flow ---

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = await db_queries.get_user(user_id)

    if user and user['accepted_terms'] and user['role'] and user['role'] != 'unknown' and user['contact_info']:
        await message.answer(f"С возвращением, {message.from_user.first_name}! Вы уже полностью зарегистрированы. Воспользуйтесь /menu для навигации.")
        return
    elif user and user['accepted_terms'] and (not user['role'] or user['role'] == 'unknown'):
        await message.answer("Вы уже приняли условия. Пожалуйста, выберите вашу роль:", reply_markup=choose_role_keyboard())
        await state.set_state(RegistrationStates.choosing_role)
        return
    elif user and user['accepted_terms'] and user['role'] and user['role'] != 'unknown' and not user['contact_info']:
        role_name = 'Работодатель' if user['role'] == 'employer' else 'Соискатель'
        await message.answer(
            f"Вы выбрали роль: **{role_name}**.\n"
            f"Пожалуйста, укажите ваши контактные данные (например, email или номер телефона).",
            reply_markup=cancel_fsm_reply_keyboard()
        )
        await state.set_state(RegistrationStates.entering_contact_info)
        return

    await message.answer(WELCOME_TEXT + "\n\n" + DISCLAIMER_TEXT_SHORT, reply_markup=start_agreement_keyboard(), parse_mode="Markdown")

@router.callback_query(F.data == "read_terms")
async def cq_read_terms(callback: CallbackQuery):
    terms_text = await read_document(USER_AGREEMENT_PATH)
    await send_document_with_close_button(callback.message, terms_text, "📜 Пользовательское соглашение JobBot")
    await callback.answer()

@router.callback_query(F.data == "read_privacy")
async def cq_read_privacy(callback: CallbackQuery):
    privacy_text = await read_document(PRIVACY_POLICY_PATH)
    await send_document_with_close_button(callback.message, privacy_text, "🔒 Политика конфиденциальности JobBot")
    await callback.answer()

@router.callback_query(F.data == "read_disclaimer_start")
async def cq_read_disclaimer_start(callback: CallbackQuery):
    disclaimer_text = await read_document(DISCLAIMER_NOTICE_PATH)
    await send_document_with_close_button(callback.message, disclaimer_text, "📄 Уведомление об ограничении ответственности")
    await callback.answer()

@router.callback_query(F.data == "accept_terms")
async def cq_accept_terms(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    username = callback.from_user.username
    user = await db_queries.get_user(user_id)

    if not user:
        await db_queries.create_user(user_id, role="unknown", username=username, accepted_terms=False)

    await db_queries.log_agreement(user_id, agreement_type='general_terms')
    await db_queries.log_agreement(user_id, agreement_type='privacy_policy')
    await db_queries.update_user_accepted_terms(user_id, accepted=True)

    await callback.message.edit_text(
        "Спасибо! Вы приняли условия. Теперь выберите вашу роль:",
        reply_markup=choose_role_keyboard()
    )
    await state.set_state(RegistrationStates.choosing_role)
    await callback.answer()

@router.callback_query(F.data == "decline_terms")
async def cq_decline_terms(callback: CallbackQuery, state: FSMContext):
    user = await db_queries.get_user(callback.from_user.id)
    if user: # Если пользователь существует, обновляем его статус
        await db_queries.update_user_accepted_terms(callback.from_user.id, accepted=False)
    await callback.message.edit_text(
        "Вы отказались принять условия. К сожалению, без этого вы не можете использовать JobBot. "
        "Если вы передумаете, просто нажмите /start снова."
    )
    await state.clear()
    await callback.answer()

@router.callback_query(RegistrationStates.choosing_role, F.data.startswith("role_"))
async def cq_choose_role(callback: CallbackQuery, state: FSMContext):
    role = callback.data.split("_")[1]
    user_id = callback.from_user.id
    await db_queries.update_user_role(user_id, role)
    role_name = 'Работодатель' if role == 'employer' else 'Соискатель'
    await callback.message.edit_text(
        f"Вы выбрали роль: **{role_name}**.\n"
        f"Теперь, пожалуйста, укажите ваши контактные данные (например, email или номер телефона). "
        f"Эта информация может понадобиться для связи с вами.",
        reply_markup=None
    )
    # Отправляем новое сообщение с ReplyKeyboard "Отмена"
    await callback.message.answer("Вы можете написать свои контакты или нажать 'Отмена'.", reply_markup=cancel_fsm_reply_keyboard())
    await state.set_state(RegistrationStates.entering_contact_info)
    await callback.answer()

@router.message(RegistrationStates.entering_contact_info, F.text)
async def process_contact_info(message: Message, state: FSMContext):
    user_id = message.from_user.id
    contact_info = message.text

    if message.text.lower() == "отмена":
        await state.clear()
        await message.answer("Ввод контактных данных отменен. Регистрация не завершена. "
                             "Вы можете начать заново с /start или выбрать роль, если уже приняли условия.",
                             reply_markup=ReplyKeyboardRemove())
        return

    await db_queries.update_user_contact_info(user_id, contact_info)
    await message.answer(
        f"Контактная информация сохранена: {contact_info}\n"
        f"Регистрация завершена! Теперь вы можете пользоваться функциями бота. "
        f"Используйте команду /menu для навигации.",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.clear()

# --- /menu command and role-based menus ---

def get_employer_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Разместить вакансию", callback_data="emp_post_vacancy")
    builder.button(text="📄 Мои вакансии", callback_data="emp_my_vacancies")
    builder.button(text="🔔 Просмотр откликов", callback_data="emp_view_applications")
    builder.button(text="⭐ Оценить соискателя", callback_data="emp_rate_applicant")
    builder.button(text="ℹ️ О платформе", callback_data="show_about_info") # Общая кнопка
    builder.button(text="📜 Правила и соглашения", callback_data="show_agreements_info")
    builder.adjust(1)
    return builder.as_markup()

def get_job_seeker_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔍 Найти вакансию", callback_data="js_find_vacancy")
    builder.button(text="📝 Мои отклики", callback_data="js_my_applications")
    builder.button(text="⭐ Оценить работодателя", callback_data="js_rate_employer")
    builder.button(text="ℹ️ О платформе", callback_data="show_about_info")
    builder.button(text="📜 Правила и соглашения", callback_data="show_agreements_info")
    builder.adjust(1)
    return builder.as_markup()

def get_admin_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="🛠️ Модерация вакансий", callback_data="adm_moderate_vacancies")
    builder.button(text="🚫 Блокировка пользователей", callback_data="adm_block_user")
    builder.button(text="📊 Статистика", callback_data="adm_view_stats")
    builder.button(text="ℹ️ О платформе", callback_data="show_about_info")
    builder.button(text="📜 Правила и соглашения", callback_data="show_agreements_info") # Админу тоже нужны
    builder.adjust(1)
    return builder.as_markup()

@router.message(Command(commands=["menu"]))
async def cmd_menu(message: Message, state: FSMContext):
    user = await db_queries.get_user(message.from_user.id)
    if not user or not user['accepted_terms']:
        await message.answer("Пожалуйста, сначала пройдите регистрацию и примите условия, используя команду /start.")
        return

    if not user['role'] or user['role'] == 'unknown' or not user['contact_info']:
        await message.answer("Пожалуйста, завершите регистрацию (выбор роли и ввод контактов) через команду /start.")
        # Можно добавить более точное направление на нужный шаг, если это возможно
        return

    text = f"Главное меню для роли: **{user['role']}**"
    markup = None
    if user['role'] == 'employer':
        markup = get_employer_menu()
    elif user['role'] == 'job_seeker':
        markup = get_job_seeker_menu()
    elif user['role'] == 'admin' and message.from_user.id in ADMIN_IDS:
        text = f"Главное меню для роли: **Администратор**"
        markup = get_admin_menu()
    elif user['role'] == 'admin' and message.from_user.id not in ADMIN_IDS: # Был админом, но убрали из списка
        await db_queries.update_user_role(message.from_user.id, "job_seeker") # Сброс роли
        await message.answer("Ваша роль администратора была отозвана. Пожалуйста, используйте /start для выбора новой роли.")
        return
    else: # Непредвиденная роль
        await message.answer("Ваша роль не определена корректно. Пожалуйста, используйте /start для перерегистрации.")
        return

    if markup:
        await message.answer(text, reply_markup=markup, parse_mode="Markdown")
    else:
        await message.answer("Для вашей текущей роли меню пока не настроено или у вас нет доступа.")

# --- Callback handlers for menu buttons (stubs for now) ---
# These will be expanded in their respective handler files later

@router.callback_query(F.data == "show_about_info")
async def cq_show_about_info(callback: CallbackQuery):
    # Это общая кнопка, ее можно оставить в common_handlers
    await cmd_about(callback.message) # Вызываем обработчик команды /about
    await callback.answer()


@router.callback_query(F.data == "show_agreements_info")
async def cq_show_agreements_info(callback: CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="📜 Пользовательское соглашение", callback_data="read_terms")
    kb.button(text="🔒 Политика конфиденциальности", callback_data="read_privacy")
    kb.button(text="⚖️ Правила модерации", callback_data="read_rules_menu")
    kb.button(text="📄 Уведомление об ответственности", callback_data="read_disclaimer_menu")
    kb.button(text="❌ Закрыть", callback_data="close_message")
    kb.adjust(1)
    # Используем edit_text если это колбэк от инлайн кнопки, иначе answer
    if callback.message.from_user.id == callback.bot.id : # Check if message is from bot (likely edited)
         await callback.message.edit_text("Юридическая информация и правила платформы:", reply_markup=kb.as_markup())
    else: # if message is from user (e.g. /menu command)
         await callback.message.answer("Юридическая информация и правила платформы:", reply_markup=kb.as_markup())
    await callback.answer()

# --- Direct command handlers for documents ---

@router.message(Command(commands=["terms"]))
async def cmd_terms(message: Message):
    terms_text = await read_document(USER_AGREEMENT_PATH)
    await send_document_with_close_button(message, terms_text, "📜 Пользовательское соглашение JobBot")

@router.message(Command(commands=["privacy"]))
async def cmd_privacy(message: Message):
    privacy_text = await read_document(PRIVACY_POLICY_PATH)
    await send_document_with_close_button(message, privacy_text, "🔒 Политика конфиденциальности JobBot")

@router.message(Command(commands=["rules"]))
async def cmd_rules(message: Message):
    rules_text = await read_document(MODERATION_POLICY_PATH)
    await send_document_with_close_button(message, rules_text, "⚖️ Правила модерации JobBot")

# Специальные обработчики для чтения документов из меню, чтобы кнопка "Закрыть" работала корректно
@router.callback_query(F.data == "read_rules_menu")
async def cq_read_rules_menu(callback: CallbackQuery):
    rules_text = await read_document(MODERATION_POLICY_PATH)
    # Удаляем предыдущее сообщение с меню документов, чтобы не было нагромождения
    try:
        await callback.message.delete()
    except Exception: pass
    await send_document_with_close_button(callback.message, rules_text, "⚖️ Правила модерации JobBot")
    await callback.answer()

@router.callback_query(F.data == "read_disclaimer_menu")
async def cq_read_disclaimer_menu(callback: CallbackQuery):
    disclaimer_text = await read_document(DISCLAIMER_NOTICE_PATH)
    try:
        await callback.message.delete()
    except Exception: pass
    await send_document_with_close_button(callback.message, disclaimer_text, "📄 Уведомление об ограничении ответственности")
    await callback.answer()


@router.message(Command(commands=["about"]))
async def cmd_about(message: Message):
    disclaimer_text = await read_document(DISCLAIMER_NOTICE_PATH)
    # TODO: Добавить более развернутое описание "О Платформе"
    custom_about_intro = (
        "**ℹ️ О платформе JobBot**\n\n"
        "JobBot - это инновационная платформа, созданная для упрощения процесса поиска работы и подбора персонала. "
        "Наша цель - соединить талантливых соискателей с лучшими работодателями.\n\n"
        "**Для соискателей:** Находите актуальные вакансии, фильтруйте их по своим предпочтениям и откликайтесь в несколько кликов.\n"
        "**Для работодателей:** Размещайте вакансии, получайте отклики от заинтересованных кандидатов и управляйте процессом найма прямо в Telegram.\n\n"
        "Мы стремимся обеспечить удобный, безопасный и эффективный инструмент для всех участников рынка труда.\n"
    )
    full_about_text = custom_about_intro + "\n\n" + "**Уведомление об ограничении ответственности:**\n" + disclaimer_text
    await send_document_with_close_button(message, full_about_text, "ℹ️ О платформе JobBot")


@router.message(Command(commands=["profile"]))
async def cmd_profile(message: Message):
    user = await db_queries.get_user(message.from_user.id)
    if not user or not user['accepted_terms'] or not user['role'] or user['role'] == 'unknown' or not user['contact_info']:
        await message.answer("Ваш профиль не полностью заполнен. Пожалуйста, завершите регистрацию через /start.")
        return

    role_rus = "Не определена"
    if user['role'] == 'employer':
        role_rus = "Работодатель"
    elif user['role'] == 'job_seeker':
        role_rus = "Соискатель"
    elif user['role'] == 'admin' and user['user_id'] in ADMIN_IDS:
        role_rus = "Администратор"

    # TODO: Добавить получение рейтинга пользователя
    # rating_info = await db_queries.get_user_average_rating(user['user_id'])
    # rating_str = f"{rating_info['avg_score']:.1f} ⭐ ({rating_info['count']} оценок)" if rating_info and rating_info['count'] > 0 else "Нет оценок"
    rating_str = "Пока не реализовано"

    profile_text = (
        f"👤 **Ваш профиль в JobBot**\n\n"
        f"**ID:** `{message.from_user.id}`\n"
        f"**Роль:** {role_rus}\n"
        f"**Telegram Username:** @{user['username'] if user['username'] else 'Не указан'}\n"
        f"**Контактная информация:** {user['contact_info']}\n"
        f"**Рейтинг:** {rating_str}\n"
        f"**Зарегистрирован:** {user['registered_at']}" # TODO: отформатировать дату
    )
    await message.answer(profile_text, parse_mode="Markdown")

@router.message(Command(commands=["appeal"]))
async def cmd_appeal(message: Message, state: FSMContext):
    # TODO: Реализовать логику подачи апелляции
    # 1. Проверить, есть ли у пользователя отклоненные вакансии или другие причины для апелляции.
    # 2. Перейти в состояние FSM для ввода текста апелляции.
    # 3. Сохранить апелляцию и уведомить администраторов.
    await message.answer("Функция подачи апелляции находится в разработке.")

# Важно, чтобы этот роутер был зарегистрирован в bot.py
# dp.include_router(common_handlers.router)
