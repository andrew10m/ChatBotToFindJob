import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, User as TelegramUser
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
)
from telegram.constants import ParseMode

import utils
import config

logger = utils.logger

# --- Helper Functions ---
def get_user_mention(user: TelegramUser) -> str:
    if user.username:
        return f"@{user.username}"
    else:
        return f"[{user.first_name}](tg://user?id={user.id})"

async def send_error_message(update: Update, context: ContextTypes.DEFAULT_TYPE, error_details: str = "", message_key="error_generic"):
    user_facing_message = config.TEXTS_RU.get(message_key, "Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже.")
    context._custom_error_sent = True

    try:
        if update.callback_query:
            await update.callback_query.answer(user_facing_message, show_alert=True)
        elif update.message:
            await update.message.reply_text(user_facing_message)
        else:
            logger.error(f"send_error_message called without a message or callback_query in Update object.")
    except Exception as e_reply:
        logger.error(f"Failed to send user-facing error message: {e_reply}")

    logger.error(f"User-facing error processing. Details: {error_details if error_details else 'No specific details provided by caller.'} User: {update.effective_user.id if update.effective_user else 'N/A'}")

# --- Conversation States ---
(
    CHOOSE_ROLE, REGISTER_EMPLOYER_AGREEMENT, REGISTER_EMPLOYEE_AGREEMENT,
    EMPLOYER_ACTIONS, EMPLOYEE_ACTIONS, ADMIN_ACTIONS, ADMIN_PASSWORD_ENTRY,
    POST_VACANCY_TITLE, POST_VACANCY_DESCRIPTION, POST_VACANCY_SALARY,
    POST_VACANCY_CONTACTS, POST_VACANCY_CONFIRM, VIEW_VACANCIES_LIST,
    APPLY_VACANCY_CONFIRM_AGREEMENT, APPLY_VACANCY_SUBMIT_INFO,
    FILTER_VACANCIES_KEYWORDS, MODERATE_VACANCY_ID, CONFIRM_GENERAL_AGREEMENT
) = (
    config.CHOOSE_ROLE, config.REGISTER_EMPLOYER_AGREEMENT, config.REGISTER_EMPLOYEE_AGREEMENT,
    config.EMPLOYER_ACTIONS, config.EMPLOYEE_ACTIONS, config.ADMIN_ACTIONS, config.ADMIN_PASSWORD_ENTRY,
    config.POST_VACANCY_TITLE, config.POST_VACANCY_DESCRIPTION, config.POST_VACANCY_SALARY,
    config.POST_VACANCY_CONTACTS, config.POST_VACANCY_CONFIRM, config.VIEW_VACANCIES_LIST,
    config.APPLY_VACANCY_CONFIRM_AGREEMENT, config.APPLY_VACANCY_SUBMIT_INFO,
    config.FILTER_VACANCIES_KEYWORDS, config.MODERATE_VACANCY_ID, config.CONFIRM_GENERAL_AGREEMENT
)

# --- Start and Role Selection ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    telegram_user = update.effective_user
    if not telegram_user:
        logger.warning("start_command: update.effective_user is None.")
        return ConversationHandler.END

    try:
        db_user = utils.get_user(telegram_user.id)

        if db_user and db_user['user_type'] == 'admin':
             await update.message.reply_text(config.TEXTS_RU["welcome_admin"], reply_markup=admin_main_menu_keyboard())
             return ConversationHandler.END
        elif db_user and db_user['general_agreement_accepted']:
            if db_user['user_type'] == 'employer':
                await update.message.reply_text(config.TEXTS_RU["welcome_back_employer"], reply_markup=employer_main_menu_keyboard())
            elif db_user['user_type'] == 'employee':
                await update.message.reply_text(config.TEXTS_RU["welcome_back_employee"], reply_markup=employee_main_menu_keyboard())
            else:
                logger.warning(f"User {telegram_user.id} has accepted agreement but has unknown role: {db_user['user_type']}")
                await update.message.reply_text(config.TEXTS_RU["welcome_new_user"], reply_markup=role_selection_keyboard())
                return CHOOSE_ROLE
            return ConversationHandler.END

        await update.message.reply_text(config.TEXTS_RU["welcome_new_user"], reply_markup=role_selection_keyboard())
        return CHOOSE_ROLE
    except Exception as e:
        await send_error_message(update, context, error_details=f"Error in start_command for user {telegram_user.id}: {e}")
        return ConversationHandler.END

def role_selection_keyboard():
    keyboard = [
        [InlineKeyboardButton(config.TEXTS_RU["employer_button"], callback_data=config.CALLBACK_ROLE_EMPLOYER)],
        [InlineKeyboardButton(config.TEXTS_RU["employee_button"], callback_data=config.CALLBACK_ROLE_EMPLOYEE)],
        [InlineKeyboardButton(config.TEXTS_RU["admin_button"], callback_data=config.CALLBACK_ROLE_ADMIN)],
    ]
    return InlineKeyboardMarkup(keyboard)

async def choose_role_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    telegram_user = update.effective_user
    if not query or not telegram_user:
        logger.warning("choose_role_callback: query or telegram_user is None.")
        return ConversationHandler.END

    try:
        await query.answer()
        role_callback_data = query.data
        context.user_data['role_choice_callback'] = role_callback_data

        if role_callback_data == config.CALLBACK_ROLE_ADMIN:
            await query.edit_message_text(text=config.TEXTS_RU["admin_login_prompt"])
            return ADMIN_PASSWORD_ENTRY

        agreement_keyboard = [
            [InlineKeyboardButton(config.TEXTS_RU["accept_button"], callback_data=config.CALLBACK_ACCEPT_GENERAL_AGREEMENT)],
            [InlineKeyboardButton(config.TEXTS_RU["decline_button"], callback_data=config.CALLBACK_DECLINE_GENERAL_AGREEMENT)],
        ]
        reply_markup = InlineKeyboardMarkup(agreement_keyboard)

        await query.edit_message_text(
            text=config.TEXTS_RU["general_agreement_prompt"] + "\n\n" + config.GENERAL_USER_AGREEMENT_TEXT,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        return CONFIRM_GENERAL_AGREEMENT
    except Exception as e:
        await send_error_message(update, context, error_details=f"Error in choose_role_callback for user {telegram_user.id}: {e}")
        return ConversationHandler.END

async def admin_password_entry_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    telegram_user = update.effective_user
    if not update.message or not telegram_user:
        return ADMIN_PASSWORD_ENTRY

    try:
        password_attempt = update.message.text
        if password_attempt == config.ADMIN_PASSWORD:
            db_user_id = utils.create_user(telegram_id=telegram_user.id, user_type='admin',
                                           username=telegram_user.username, first_name=telegram_user.first_name,
                                           last_name=telegram_user.last_name)
            if db_user_id:
                utils.set_general_agreement_accepted(telegram_user.id, True)
                logger.info(f"Admin login successful for user {telegram_user.id}")
                await update.message.reply_text(config.TEXTS_RU["admin_login_success"], reply_markup=admin_main_menu_keyboard())
                return ConversationHandler.END
            else:
                logger.error(f"Failed to create/update admin user {telegram_user.id} after password success.")
                await update.message.reply_text(config.TEXTS_RU["error_generic"])
                return ConversationHandler.END
        else:
            logger.warning(f"Admin login failed for user {telegram_user.id} (incorrect password)")
            await update.message.reply_text(config.TEXTS_RU["admin_login_fail"])
            return ADMIN_PASSWORD_ENTRY
    except Exception as e:
        await send_error_message(update, context, error_details=f"Error in admin_password_entry_handler for user {telegram_user.id}: {e}")
        return ConversationHandler.END

async def general_agreement_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    telegram_user = update.effective_user
    if not query or not telegram_user:
        logger.warning("general_agreement_callback: query or telegram_user is None.")
        return ConversationHandler.END

    try:
        await query.answer()

        if query.data == config.CALLBACK_ACCEPT_GENERAL_AGREEMENT:
            role_callback_data = context.user_data.get('role_choice_callback')
            if not role_callback_data:
                logger.error(f"general_agreement_callback: role_choice_callback not found for user {telegram_user.id}")
                await query.edit_message_text(config.TEXTS_RU["error_generic"] + " (Ошибка выбора роли)")
                return ConversationHandler.END

            user_type = ''
            if role_callback_data == config.CALLBACK_ROLE_EMPLOYER:
                user_type = 'employer'
            elif role_callback_data == config.CALLBACK_ROLE_EMPLOYEE:
                user_type = 'employee'
            else:
                logger.error(f"general_agreement_callback: Unexpected role_choice_callback '{role_callback_data}' for user {telegram_user.id}")
                await query.edit_message_text(config.TEXTS_RU["error_generic"])
                return ConversationHandler.END

            db_user_id = utils.create_user(telegram_user.id, user_type, telegram_user.username, telegram_user.first_name, telegram_user.last_name)
            if not db_user_id:
                logger.error(f"Failed to create user {telegram_user.id} (type: {user_type}) in general_agreement_callback.")
                await query.edit_message_text(text=config.TEXTS_RU["error_generic"])
                return ConversationHandler.END

            if not utils.set_general_agreement_accepted(telegram_user.id, True):
                logger.error(f"Failed to set general agreement for user {telegram_user.id} (type: {user_type}).")
                await query.edit_message_text(text=config.TEXTS_RU["error_generic"])
                return ConversationHandler.END

            context.user_data['db_user_id'] = db_user_id
            context.user_data['user_type'] = user_type

            if user_type == 'employer':
                await query.edit_message_text(text=config.TEXTS_RU["registration_complete_employer"])
                await context.bot.send_message(chat_id=telegram_user.id, text=config.TEXTS_RU["employer_menu_prompt"], reply_markup=employer_main_menu_keyboard())
            elif user_type == 'employee':
                await query.edit_message_text(text=config.TEXTS_RU["registration_complete_employee"])
                await context.bot.send_message(chat_id=telegram_user.id, text=config.TEXTS_RU["employee_menu_prompt"], reply_markup=employee_main_menu_keyboard())
            return ConversationHandler.END

        elif query.data == config.CALLBACK_DECLINE_GENERAL_AGREEMENT:
            await query.edit_message_text(text=config.TEXTS_RU["agreement_declined_message"])
            return ConversationHandler.END

        else:
            logger.warning(f"general_agreement_callback: Unexpected callback data '{query.data}' for user {telegram_user.id}")
            return CONFIRM_GENERAL_AGREEMENT

    except Exception as e:
        await send_error_message(update, context, error_details=f"Error in general_agreement_callback for user {telegram_user.id}: {e}")
        return ConversationHandler.END

# --- Main Menu Keyboards ---
def employer_main_menu_keyboard():
    keyboard = [
        [config.TEXTS_RU["post_vacancy_button"]],
        [config.TEXTS_RU["my_vacancies_button"], config.TEXTS_RU["view_applications_button"]],
        [config.TEXTS_RU["help_message"].split('\n')[1].split(' - ')[0]]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def employee_main_menu_keyboard():
    keyboard = [
        [config.TEXTS_RU["view_vacancies_button"]],
        [config.TEXTS_RU["my_applications_button"], config.TEXTS_RU["filter_vacancies_button"]],
        [config.TEXTS_RU["help_message"].split('\n')[1].split(' - ')[0]]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def admin_main_menu_keyboard():
    keyboard = [
        [config.TEXTS_RU["moderate_vacancies_button"]],
        [config.TEXTS_RU["manage_users_button"]],
         [config.TEXTS_RU["help_message"].split('\n')[1].split(' - ')[0]]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

# --- Employer: Post Vacancy ---
async def post_vacancy_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    telegram_user = update.effective_user
    if not telegram_user or not update.message: return ConversationHandler.END
    try:
        db_user = utils.get_user(telegram_user.id)
        if not (db_user and db_user['user_type'] == 'employer' and db_user['general_agreement_accepted']):
            logger.info(f"User {telegram_user.id} attempted to post vacancy without proper role/agreement.")
            await update.message.reply_text("Пожалуйста, сначала зарегистрируйтесь как работодатель через /start.")
            return ConversationHandler.END

        context.user_data['vacancy_info'] = {}
        await update.message.reply_text(config.TEXTS_RU["enter_vacancy_title"], reply_markup=ReplyKeyboardRemove())
        return POST_VACANCY_TITLE
    except Exception as e:
        await send_error_message(update, context, error_details=f"Error in post_vacancy_start for user {telegram_user.id}: {e}")
        return ConversationHandler.END

async def post_vacancy_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    telegram_user = update.effective_user
    if not telegram_user or not update.message: return ConversationHandler.END
    try:
        title = update.message.text
        if not title or len(title.strip()) < 3:
            await update.message.reply_text("Название вакансии слишком короткое. Пожалуйста, введите более подробное название.")
            return POST_VACANCY_TITLE
        context.user_data['vacancy_info']['title'] = title.strip()
        await update.message.reply_text(config.TEXTS_RU["enter_vacancy_description"])
        return POST_VACANCY_DESCRIPTION
    except Exception as e:
        await send_error_message(update, context, error_details=f"Error in post_vacancy_title for user {telegram_user.id}: {e}")
        return ConversationHandler.END

async def post_vacancy_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    telegram_user = update.effective_user
    if not telegram_user or not update.message: return ConversationHandler.END
    try:
        description = update.message.text
        if not description or len(description.strip()) < 10:
            await update.message.reply_text("Описание вакансии слишком короткое. Пожалуйста, предоставьте больше деталей.")
            return POST_VACANCY_DESCRIPTION
        context.user_data['vacancy_info']['description'] = description.strip()
        await update.message.reply_text(config.TEXTS_RU["enter_vacancy_salary"])
        return POST_VACANCY_SALARY
    except Exception as e:
        await send_error_message(update, context, error_details=f"Error in post_vacancy_description for user {telegram_user.id}: {e}")
        return ConversationHandler.END

async def post_vacancy_salary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    telegram_user = update.effective_user
    if not telegram_user or not update.message: return ConversationHandler.END
    try:
        salary = update.message.text
        if not salary or len(salary.strip()) == 0:
            await update.message.reply_text("Поле зарплаты не может быть пустым. Укажите зарплату или 'По договоренности'.")
            return POST_VACANCY_SALARY
        context.user_data['vacancy_info']['salary'] = salary.strip()
        await update.message.reply_text(config.TEXTS_RU["enter_vacancy_contacts"])
        return POST_VACANCY_CONTACTS
    except Exception as e:
        await send_error_message(update, context, error_details=f"Error in post_vacancy_salary for user {telegram_user.id}: {e}")
        return ConversationHandler.END

async def post_vacancy_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    telegram_user = update.effective_user
    if not telegram_user or not update.message: return ConversationHandler.END
    try:
        contacts = update.message.text
        if not contacts or len(contacts.strip()) < 5:
            await update.message.reply_text("Контактные данные слишком короткие. Пожалуйста, укажите корректные контакты.")
            return POST_VACANCY_CONTACTS
        context.user_data['vacancy_info']['contacts'] = contacts.strip()

        vacancy = context.user_data.get('vacancy_info')
        if not vacancy or not all(k in vacancy for k in ['title', 'description', 'salary', 'contacts']):
            logger.error(f"Incomplete vacancy_info at confirmation step for user {telegram_user.id}. Data: {vacancy}")
            await update.message.reply_text(config.TEXTS_RU["error_generic"] + " (Неполные данные о вакансии)")
            return ConversationHandler.END

        confirm_text = config.TEXTS_RU["vacancy_confirm_prompt"].format(
            title=vacancy['title'], description=vacancy['description'],
            salary=vacancy['salary'], contacts=vacancy['contacts']
        )
        keyboard = [
            [InlineKeyboardButton(config.TEXTS_RU["publish_button"], callback_data=config.CALLBACK_PUBLISH_VACANCY)],
            [InlineKeyboardButton(config.TEXTS_RU["edit_button"], callback_data=config.CALLBACK_EDIT_VACANCY_FROM_CONFIRM)],
            [InlineKeyboardButton(config.TEXTS_RU["cancel_button"], callback_data=config.CALLBACK_CANCEL_VACANCY_POST)],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(confirm_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        return POST_VACANCY_CONFIRM
    except Exception as e:
        await send_error_message(update, context, error_details=f"Error in post_vacancy_contacts for user {telegram_user.id}: {e}")
        return ConversationHandler.END

async def post_vacancy_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    telegram_user = update.effective_user
    if not query or not telegram_user: return ConversationHandler.END

    try:
        await query.answer()
        db_user = utils.get_user(telegram_user.id)

        if query.data == config.CALLBACK_PUBLISH_VACANCY:
            if not db_user or not db_user['id']:
                logger.error(f"Publish vacancy: User {telegram_user.id} not found in DB or no ID.")
                await query.edit_message_text(config.TEXTS_RU["error_generic"] + " (Ошибка пользователя)")
                return ConversationHandler.END

            vacancy_info = context.user_data.get('vacancy_info', {})
            if not all(k in vacancy_info for k in ['title', 'description', 'salary', 'contacts']):
                logger.error(f"Publish vacancy: Incomplete vacancy_info for user {telegram_user.id}. Data: {vacancy_info}")
                await query.edit_message_text(config.TEXTS_RU["error_generic"] + " (Неполные данные вакансии)")
                context.user_data.pop('vacancy_info', None)
                return ConversationHandler.END

            vacancy_id = utils.create_vacancy(
                employer_id=db_user['id'], title=vacancy_info['title'],
                description=vacancy_info['description'], salary=vacancy_info['salary'],
                contact_details=vacancy_info['contacts'], status='pending_moderation'
            )
            if vacancy_id:
                logger.info(f"Vacancy {vacancy_id} created by user {telegram_user.id}, pending moderation.")
                await query.edit_message_text(config.TEXTS_RU["vacancy_published_moderation"], reply_markup=None)
                await context.bot.send_message(chat_id=telegram_user.id, text="Вы можете вернуться в главное меню.", reply_markup=employer_main_menu_keyboard())

                admin_message = f"Новая вакансия для модерации:\nID: {vacancy_id}\nНазвание: {vacancy_info['title']}\nРаботодатель: {get_user_mention(telegram_user)}"
                for admin_id in config.ADMIN_TELEGRAM_IDS:
                    try:
                        await context.bot.send_message(chat_id=admin_id, text=admin_message, parse_mode=ParseMode.MARKDOWN)
                    except Exception as e_admin_notify:
                        logger.error(f"Failed to send moderation alert to admin {admin_id}: {e_admin_notify}")
            else:
                logger.error(f"Failed to create vacancy in DB for user {telegram_user.id}. Info: {vacancy_info}")
                await query.edit_message_text(config.TEXTS_RU["error_generic"] + " (Ошибка сохранения вакансии)")
            context.user_data.pop('vacancy_info', None)
            return ConversationHandler.END

        elif query.data == config.CALLBACK_EDIT_VACANCY_FROM_CONFIRM:
            await query.edit_message_text(config.TEXTS_RU["restart_vacancy_posting"])
            context.user_data['vacancy_info'] = {}
            return POST_VACANCY_TITLE

        elif query.data == config.CALLBACK_CANCEL_VACANCY_POST:
            await query.edit_message_text(config.TEXTS_RU["vacancy_publication_cancelled"], reply_markup=None)
            await context.bot.send_message(chat_id=telegram_user.id, text="Вы можете вернуться в главное меню.", reply_markup=employer_main_menu_keyboard())
            context.user_data.pop('vacancy_info', None)
            return ConversationHandler.END

        return POST_VACANCY_CONFIRM
    except Exception as e:
        await send_error_message(update, context, error_details=f"Error in post_vacancy_confirm_callback for user {telegram_user.id}: {e}")
        context.user_data.pop('vacancy_info', None)
        return ConversationHandler.END

# --- Employee: View and Apply for Vacancies ---
async def view_vacancies_start(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    telegram_user = update.effective_user
    message_target = update.message if update.message else update.callback_query.message
    if not telegram_user or not message_target: return ConversationHandler.END

    try:
        db_user = utils.get_user(telegram_user.id)
        if not (db_user and db_user['user_type'] == 'employee' and db_user['general_agreement_accepted']):
            logger.info(f"User {telegram_user.id} attempted to view vacancies without proper role/agreement.")
            await message_target.reply_text("Пожалуйста, сначала зарегистрируйтесь как Работник через /start.")
            return ConversationHandler.END

        keywords = context.user_data.get('vacancy_filter_keywords')
        vacancies = utils.get_active_vacancies(limit=config.VACANCIES_PER_PAGE, offset=page * config.VACANCIES_PER_PAGE, keywords=keywords)
        context.user_data['current_vacancy_page'] = page

        if not vacancies and page == 0:
            no_vac_text = config.TEXTS_RU["no_active_vacancies"]
            if keywords:
                 no_vac_text = f"По вашему запросу '{keywords}' вакансий не найдено."
            await message_target.reply_text(no_vac_text, reply_markup=employee_main_menu_keyboard())
            return ConversationHandler.END
        elif not vacancies and page > 0:
             if update.callback_query: await update.callback_query.answer("Больше вакансий нет.", show_alert=False)
             return VIEW_VACANCIES_LIST


        text = "📄 *Активные вакансии*:\n\n"
        if keywords:
            text = f"🔎 *Результаты поиска по '{keywords}'*:\n\n"

        keyboard_rows = []
        for vacancy in vacancies:
            text += f"🔹 *{vacancy['title']}*\n"
            text += f"   Зарплата: {vacancy['salary']}\n"
            text += f"   (Подробнее: /vac_{vacancy['id']})\n\n"
            keyboard_rows.append([InlineKeyboardButton(f"Откликнуться: {vacancy['title'][:30]}...", callback_data=f"{config.CALLBACK_VACANCY_APPLY_PREFIX}{vacancy['id']}")])

        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(config.TEXTS_RU["prev_page_button"], callback_data=f"{config.CALLBACK_NAV_VACANCIES_PREV}{page-1}"))
        if len(vacancies) == config.VACANCIES_PER_PAGE:
            nav_buttons.append(InlineKeyboardButton(config.TEXTS_RU["next_page_button"], callback_data=f"{config.CALLBACK_NAV_VACANCIES_NEXT}{page+1}"))
        if nav_buttons:
            keyboard_rows.append(nav_buttons)

        if keywords:
            keyboard_rows.append([InlineKeyboardButton(config.TEXTS_RU["clear_filter_button"], callback_data="clear_vacancy_filter")])

        reply_markup = InlineKeyboardMarkup(keyboard_rows) if keyboard_rows else None

        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        else:
            await message_target.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

        return VIEW_VACANCIES_LIST
    except Exception as e:
        await send_error_message(update, context, error_details=f"Error in view_vacancies_start for user {telegram_user.id}: {e}")
        return ConversationHandler.END

async def view_vacancies_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    telegram_user = update.effective_user
    if not query or not telegram_user: return VIEW_VACANCIES_LIST

    try:
        data = query.data

        if data.startswith(config.CALLBACK_NAV_VACANCIES_NEXT):
            page = int(data.split(config.CALLBACK_NAV_VACANCIES_NEXT)[1])
            return await view_vacancies_start(update, context, page=page)
        elif data.startswith(config.CALLBACK_NAV_VACANCIES_PREV):
            page = int(data.split(config.CALLBACK_NAV_VACANCIES_PREV)[1])
            return await view_vacancies_start(update, context, page=page)
        elif data.startswith(config.CALLBACK_VACANCY_APPLY_PREFIX):
            vacancy_id = int(data.split(config.CALLBACK_VACANCY_APPLY_PREFIX)[1])
            context.user_data['current_vacancy_id_for_application'] = vacancy_id

            vacancy = utils.get_vacancy_by_id(vacancy_id)
            if not vacancy or vacancy['status'] != 'active':
                await query.answer("Вакансия не найдена или больше не активна.", show_alert=True)
                return await view_vacancies_start(update, context, page=context.user_data.get('current_vacancy_page', 0))


            agreement_text = config.TEXTS_RU["vacancy_application_agreement_prompt"] + "\n\n" + config.VACANCY_APPLICATION_AGREEMENT_TEXT
            keyboard = [
                [InlineKeyboardButton(config.TEXTS_RU["accept_and_apply_button"], callback_data=f"{config.CALLBACK_ACCEPT_VACANCY_AGREEMENT}{vacancy_id}")],
                [InlineKeyboardButton(config.TEXTS_RU["back_to_list_button"], callback_data="back_to_vacancy_list")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text=agreement_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            return APPLY_VACANCY_CONFIRM_AGREEMENT
        elif data == "clear_vacancy_filter":
            context.user_data.pop('vacancy_filter_keywords', None)
            await query.answer("Фильтр сброшен.")
            return await view_vacancies_start(update, context, page=0)
        elif data == "show_vacancy_list_from_details":
             return await show_vacancy_list_from_details_callback(update, context)

        await query.answer()
        return VIEW_VACANCIES_LIST
    except Exception as e:
        await send_error_message(update, context, error_details=f"Error in view_vacancies_callback_handler for user {telegram_user.id}: {e}")
        return VIEW_VACANCIES_LIST

async def apply_vacancy_agreement_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    telegram_user = update.effective_user
    if not query or not telegram_user: return ConversationHandler.END

    try:
        await query.answer()
        vacancy_id = context.user_data.get('current_vacancy_id_for_application')

        if not vacancy_id:
            logger.error(f"apply_vacancy_agreement_callback: current_vacancy_id_for_application not found for user {telegram_user.id}")
            await query.edit_message_text(config.TEXTS_RU["error_generic"] + " (Ошибка сессии)")
            return ConversationHandler.END

        if query.data.startswith(config.CALLBACK_ACCEPT_VACANCY_AGREEMENT):
            callback_vacancy_id = int(query.data.replace(config.CALLBACK_ACCEPT_VACANCY_AGREEMENT, ""))
            if callback_vacancy_id != vacancy_id:
                logger.error(f"Vacancy ID mismatch in apply_vacancy_agreement_callback. Context: {vacancy_id}, Callback: {callback_vacancy_id} for user {telegram_user.id}")
                await query.edit_message_text(config.TEXTS_RU["error_generic"] + " (Ошибка ID вакансии)")
                return ConversationHandler.END

            context.user_data['vacancy_agreement_accepted_for_current'] = True
            await query.edit_message_text(config.TEXTS_RU["send_resume_or_message_prompt"], reply_markup=ReplyKeyboardRemove())
            return APPLY_VACANCY_SUBMIT_INFO

        elif query.data == "back_to_vacancy_list":
            await query.delete_message()
            current_page = context.user_data.get('current_vacancy_page', 0)

            class DummyMessage:
                 chat = query.message.chat if query.message else None
                 async def reply_text(self, *args, **kwargs):
                     if self.chat:
                        return await context.bot.send_message(chat_id=self.chat.id, *args, **kwargs)
                     logger.warning("DummyMessage: chat object is None, cannot send message.")
                     return None

            class DummyUpdate:
                 effective_user = telegram_user
                 message = DummyMessage()
                 callback_query = None

            return await view_vacancies_start(DummyUpdate(), context, page=current_page)


        return APPLY_VACANCY_CONFIRM_AGREEMENT
    except Exception as e:
        await send_error_message(update, context, error_details=f"Error in apply_vacancy_agreement_callback for user {telegram_user.id}: {e}")
        return ConversationHandler.END

async def apply_vacancy_submit_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    telegram_user = update.effective_user
    if not telegram_user or not update.message: return ConversationHandler.END

    try:
        db_user = utils.get_user(telegram_user.id)
        vacancy_id = context.user_data.get('current_vacancy_id_for_application')
        agreement_accepted = context.user_data.get('vacancy_agreement_accepted_for_current', False)

        if not (db_user and db_user['id'] and vacancy_id and agreement_accepted):
            error_detail = f"Missing application context for user {telegram_user.id}. DBUser: {bool(db_user)}, VacID: {vacancy_id}, AgrAcc: {agreement_accepted}"
            logger.error(error_detail)
            await update.message.reply_text(config.TEXTS_RU["error_generic"] + " (Ошибка контекста заявки)", reply_markup=employee_main_menu_keyboard())
            return ConversationHandler.END

        application_content = ""
        if update.message.text:
            application_content = update.message.text.strip()
            if len(application_content) == 0:
                 await update.message.reply_text("Сообщение не может быть пустым. Пожалуйста, отправьте информацию о себе или резюме.")
                 return APPLY_VACANCY_SUBMIT_INFO
        elif update.message.document:
            application_content = f"Файл: {update.message.document.file_name} (ID: {update.message.document.file_id})"
        else:
            await update.message.reply_text("Пожалуйста, отправьте текстовое сообщение или файл.")
            return APPLY_VACANCY_SUBMIT_INFO

        app_id = utils.create_application(
            employee_id=db_user['id'],
            vacancy_id=vacancy_id,
            resume_or_message=application_content,
            agreement_accepted=True
        )

        if app_id:
            await update.message.reply_text(config.TEXTS_RU["application_sent"], reply_markup=employee_main_menu_keyboard())
            logger.info(f"Application {app_id} submitted by user {telegram_user.id} for vacancy {vacancy_id}")

            vacancy = utils.get_vacancy_by_id(vacancy_id)
            if vacancy and vacancy['employer_id']:
                employer_creator = utils.get_user_by_internal_id(db_id=vacancy['employer_id'])
                if employer_creator and employer_creator['telegram_id']:
                    notification_text = config.TEXTS_RU["new_application_notification_employer"].format(
                        vacancy_title=vacancy['title'], user_mention=get_user_mention(telegram_user)
                    )
                    try:
                        await context.bot.send_message(chat_id=employer_creator['telegram_id'], text=notification_text, parse_mode=ParseMode.MARKDOWN)
                    except Exception as e_notify:
                        logger.error(f"Failed to send application notification to employer {employer_creator['telegram_id']}: {e_notify}")
                else:
                    logger.warning(f"Could not find employer Telegram ID for DB ID {vacancy['employer_id']} to send application notification.")
        else:
            logger.error(f"Failed to create application in DB for user {telegram_user.id}, vacancy {vacancy_id}")
            await update.message.reply_text(config.TEXTS_RU["application_failed"], reply_markup=employee_main_menu_keyboard())

        context.user_data.pop('current_vacancy_id_for_application', None)
        context.user_data.pop('vacancy_agreement_accepted_for_current', None)
        return ConversationHandler.END
    except Exception as e:
        await send_error_message(update, context, error_details=f"Error in apply_vacancy_submit_info for user {telegram_user.id if telegram_user else 'N/A'}: {e}")
        context.user_data.pop('current_vacancy_id_for_application', None)
        context.user_data.pop('vacancy_agreement_accepted_for_current', None)
        return ConversationHandler.END

async def vacancy_details_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    telegram_user = update.effective_user
    if not telegram_user or not update.message: return ConversationHandler.END

    try:
        vacancy_id_str = update.message.text.split('_', 1)[1] if '_' in update.message.text else None
        if not vacancy_id_str or not vacancy_id_str.isdigit():
            logger.warning(f"Invalid vacancy_id format: {update.message.text} from user {telegram_user.id}")
            await update.message.reply_text("Неверный формат ID вакансии. Используйте /vac_ЧИСЛО.")
            return ConversationHandler.END

        vacancy_id = int(vacancy_id_str)
    except (IndexError, ValueError) as e:
        logger.warning(f"Invalid vacancy_id format (exception): {update.message.text}. Error: {e}. User: {telegram_user.id}")
        await update.message.reply_text("Неверный формат ID вакансии. Используйте /vac_ЧИСЛО.")
        return ConversationHandler.END

    try:
        vacancy = utils.get_vacancy_by_id(vacancy_id)
        if not vacancy or vacancy['status'] != 'active':
            logger.info(f"Vacancy with ID {vacancy_id} not found or not active for user {telegram_user.id}.")
            await update.message.reply_text("Вакансия не найдена или больше не активна.")
            return ConversationHandler.END

        text = f"📜 *Вакансия: {vacancy['title']}*\n\n"
        text += f"*Описание:*\n{vacancy['description']}\n\n"
        text += f"*Зарплата:* {vacancy['salary']}\n"
        text += f"*Контакты:* {vacancy['contact_details']}\n"
        text += f"*Опубликовано:* {str(vacancy['creation_timestamp']).split('.')[0]}\n"
        if vacancy['employer_username']:
            text += f"*Работодатель:* @{vacancy['employer_username']}\n"

        db_user = utils.get_user(telegram_user.id)
        keyboard_rows = []
        if db_user and db_user['user_type'] == 'employee' and db_user['general_agreement_accepted']:
            keyboard_rows.append([InlineKeyboardButton(f"✍️ Откликнуться на: {vacancy['title'][:20]}...", callback_data=f"{config.CALLBACK_VACANCY_APPLY_PREFIX}{vacancy['id']}")])

        keyboard_rows.append([InlineKeyboardButton("◀️ К списку вакансий", callback_data="show_vacancy_list_from_details")])
        reply_markup = InlineKeyboardMarkup(keyboard_rows)

        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        return VIEW_VACANCIES_LIST
    except Exception as e:
        await send_error_message(update, context, error_details=f"Error in vacancy_details_command for user {telegram_user.id}, vac_id {vacancy_id_str}: {e}")
        return ConversationHandler.END

async def show_vacancy_list_from_details_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    telegram_user = update.effective_user
    if not query or not telegram_user: return VIEW_VACANCIES_LIST

    try:
        await query.answer()
        await query.delete_message()
    except Exception as e:
        logger.error(f"Error deleting message in show_vacancy_list_from_details_callback for user {telegram_user.id}: {e}")

    current_page = context.user_data.get('current_vacancy_page', 0)

    class DummyMessage:
        chat = query.message.chat if query.message else None
        async def reply_text(self, *args, **kwargs):
            if self.chat:
                 return await context.bot.send_message(chat_id=self.chat.id, *args, **kwargs)
            logger.warning("DummyMessage: chat object is None, cannot send message.")
            return None

    class DummyUpdate:
        effective_user = telegram_user
        message = DummyMessage()
        callback_query = None

    return await view_vacancies_start(DummyUpdate(), context, page=current_page)

async def filter_vacancies_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    telegram_user = update.effective_user
    if not telegram_user or not update.message: return ConversationHandler.END
    try:
        db_user = utils.get_user(telegram_user.id)
        if not (db_user and db_user['user_type'] == 'employee' and db_user['general_agreement_accepted']):
            await update.message.reply_text("Пожалуйста, сначала зарегистрируйтесь как Работник через /start.")
            return ConversationHandler.END

        await update.message.reply_text(config.TEXTS_RU["enter_keywords_for_filter"], reply_markup=ReplyKeyboardRemove())
        return FILTER_VACANCIES_KEYWORDS
    except Exception as e:
        await send_error_message(update, context, error_details=f"Error in filter_vacancies_start for user {telegram_user.id}: {e}")
        return ConversationHandler.END

async def filter_vacancies_set_keywords(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    telegram_user = update.effective_user
    if not telegram_user or not update.message: return ConversationHandler.END
    try:
        keywords = update.message.text
        if not keywords or len(keywords.strip()) == 0:
            await update.message.reply_text("Вы не ввели ключевые слова. Фильтр не изменен.", reply_markup=employee_main_menu_keyboard())
            return ConversationHandler.END

        context.user_data['vacancy_filter_keywords'] = keywords.strip()
        logger.info(f"User {telegram_user.id} set vacancy filter keywords to: '{keywords.strip()}'")
        await update.message.reply_text(config.TEXTS_RU["filter_applied"])

        await view_vacancies_start(update, context, page=0)
        return VIEW_VACANCIES_LIST
    except Exception as e:
        await send_error_message(update, context, error_details=f"Error in filter_vacancies_set_keywords for user {telegram_user.id}: {e}")
        return ConversationHandler.END

async def my_applications_employee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_user = update.effective_user
    if not telegram_user or not update.message: return
    try:
        db_user = utils.get_user(telegram_user.id)
        if not (db_user and db_user['user_type'] == 'employee' and db_user['general_agreement_accepted']):
            logger.info(f"Access denied for my_applications_employee to user {telegram_user.id}")
            await update.message.reply_text("Доступ запрещен. Пожалуйста, зарегистрируйтесь как Работник.")
            return

        applications = utils.get_user_applications(db_user['id'])
        if not applications:
            await update.message.reply_text("У вас пока нет откликов.", reply_markup=employee_main_menu_keyboard())
            return

        text = "📋 *Мои отклики:*\n\n"
        for app_idx, app in enumerate(applications):
            if app_idx >= 10:
                text += f"... и еще {len(applications) - app_idx} откликов.\n"
                logger.info(f"User {telegram_user.id} has {len(applications)} applications, showing first {app_idx}.")
                break
            text += f"🔹 *Вакансия:* {app['vacancy_title']}\n"
            text += f"   *Сообщение/Резюме:* {(app['resume_or_message'] or '')[:50]}...\n"
            text += f"   *Дата отклика:* {str(app['application_timestamp']).split('.')[0]}\n"
            text += f"   *Согласие на вакансию:* {'Да' if app['vacancy_agreement_accepted'] else 'Нет'}\n\n"

        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=employee_main_menu_keyboard())
    except Exception as e:
        await send_error_message(update, context, error_details=f"Error in my_applications_employee for user {telegram_user.id}: {e}")

async def my_vacancies_employer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_user = update.effective_user
    if not telegram_user or not update.message: return
    try:
        db_user = utils.get_user(telegram_user.id)
        if not (db_user and db_user['user_type'] == 'employer' and db_user['general_agreement_accepted']):
            logger.info(f"Access denied for my_vacancies_employer to user {telegram_user.id}")
            await update.message.reply_text("Доступ запрещен. Пожалуйста, зарегистрируйтесь как работодатель.")
            return

        vacancies = utils.get_vacancies_by_employer(db_user['id'])
        if not vacancies:
            await update.message.reply_text("У вас пока нет опубликованных вакансий.", reply_markup=employer_main_menu_keyboard())
            return

        text = "📑 *Мои вакансии:*\n\n"
        for vac_idx, vac in enumerate(vacancies):
            if vac_idx >= 10:
                text += f"... и еще {len(vacancies) - vac_idx} вакансий.\n"
                logger.info(f"Employer {telegram_user.id} has {len(vacancies)} vacancies, showing first {vac_idx}.")
                break
            text += f"🔸 *{vac['title']}* (Статус: {vac['status']})\n"
            text += f"   ID: {vac['id']} (Просмотр: /vac_{vac['id']})\n"
            text += "\n"

        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=employer_main_menu_keyboard())
    except Exception as e:
        await send_error_message(update, context, error_details=f"Error in my_vacancies_employer for user {telegram_user.id}: {e}")

async def view_applications_employer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_user = update.effective_user
    if not telegram_user or not update.message: return
    try:
        logger.info(f"User {telegram_user.id} accessed placeholder view_applications_employer.")
        await update.message.reply_text("Функция 'Просмотреть отклики' в разработке.", reply_markup=employer_main_menu_keyboard())
    except Exception as e:
        await send_error_message(update, context, error_details=f"Error in view_applications_employer for user {telegram_user.id}: {e}")

async def moderate_vacancies_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_user = update.effective_user
    message_or_query_message = update.message or (update.callback_query.message if update.callback_query else None)
    if not telegram_user or not message_or_query_message: return

    try:
        db_user = utils.get_user(telegram_user.id)
        if not (db_user and db_user['user_type'] == 'admin' and telegram_user.id in config.ADMIN_TELEGRAM_IDS):
            logger.warning(f"Unauthorized access attempt to moderate_vacancies_admin by user {telegram_user.id}")
            await message_or_query_message.reply_text("Доступ запрещен.")
            return

        message_to_edit = None
        if update.callback_query and update.callback_query.data == config.CALLBACK_MODERATE_VACANCIES:
            await update.callback_query.answer()
            message_to_edit = update.callback_query.message

        pending_vacs = utils.get_vacancies_by_status('pending_moderation', limit=1)
        if not pending_vacs:
            reply_text = "Нет вакансий для модерации."
            if message_to_edit: await message_to_edit.edit_text(reply_text, reply_markup=None)
            else: await message_or_query_message.reply_text(reply_text, reply_markup=admin_main_menu_keyboard())
            return

        vacancy = pending_vacs[0]
        text = f"📝 *Вакансия на модерацию:*\n\n"
        text += f"*ID:* {vacancy['id']}\n"
        text += f"*Название:* {vacancy['title']}\n"
        text += f"*Описание:* {(vacancy['description'] or '')[:200]}...\n"
        text += f"*Зарплата:* {vacancy['salary']}\n"
        text += f"*Контакты:* {vacancy['contact_details']}\n"
        text += f"*Работодатель:* @{vacancy['employer_username'] if vacancy['employer_username'] else 'N/A'} (DB ID: {vacancy['employer_id']})\n"

        keyboard = [
            [
                InlineKeyboardButton("✅ Одобрить", callback_data=f"{config.CALLBACK_APPROVE_VACANCY}{vacancy['id']}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"{config.CALLBACK_REJECT_VACANCY}{vacancy['id']}")
            ],
            [InlineKeyboardButton("Следующая на модерацию", callback_data=config.CALLBACK_MODERATE_VACANCIES)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if message_to_edit:
            await message_to_edit.edit_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        else:
            await message_or_query_message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        await send_error_message(update, context, error_details=f"Error in moderate_vacancies_admin for user {telegram_user.id}: {e}")

async def admin_moderation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    telegram_user = update.effective_user

    if not query or not telegram_user:
        logger.warning("admin_moderation_callback: Missing query or user.")
        return

    try:
        await query.answer()
        data = query.data

        db_user = utils.get_user(telegram_user.id)
        if not (db_user and db_user['user_type'] == 'admin' and telegram_user.id in config.ADMIN_TELEGRAM_IDS):
            logger.warning(f"Unauthorized callback access to admin_moderation_callback by user {telegram_user.id}")
            await query.edit_message_text("Ошибка: У вас нет прав для этого действия.")
            return

        target_vacancy_id = None
        action = None

        if data.startswith(config.CALLBACK_APPROVE_VACANCY):
            target_vacancy_id = int(data.replace(config.CALLBACK_APPROVE_VACANCY, ""))
            action = 'approve'
        elif data.startswith(config.CALLBACK_REJECT_VACANCY):
            target_vacancy_id = int(data.replace(config.CALLBACK_REJECT_VACANCY, ""))
            action = 'reject'
        else:
            logger.warning(f"Unknown callback data in admin_moderation_callback: {data} by admin {telegram_user.id}")
            await query.edit_message_text("Неизвестное действие.")
            return

        if not target_vacancy_id or not action:
            logger.error(f"Admin moderation callback: missing vacancy_id or action. Data: {data}, Admin: {telegram_user.id}")
            await query.edit_message_text("Ошибка обработки команды.")
            return

        new_status = 'active' if action == 'approve' else 'rejected'
        success = utils.update_vacancy_status(target_vacancy_id, new_status)

        if success:
            logger.info(f"Admin {telegram_user.id} {action}d vacancy {target_vacancy_id}.")

            vacancy_details = utils.get_vacancy_by_id(target_vacancy_id)
            if vacancy_details and vacancy_details['employer_id']:
                employer = utils.get_user_by_internal_id(vacancy_details['employer_id'])
                if employer and employer['telegram_id']:
                    employer_notification = f"Ваша вакансия '{vacancy_details['title']}' была {'одобрена' if action == 'approve' else 'отклонена'} администратором."
                    try:
                        await context.bot.send_message(chat_id=employer['telegram_id'], text=employer_notification)
                    except Exception as e_notify:
                        logger.error(f"Failed to send moderation status to employer {employer['telegram_id']} for vacancy {target_vacancy_id}: {e_notify}")

            await moderate_vacancies_admin(update, context)
            return

        else:
            logger.error(f"Admin {telegram_user.id} failed to {action} vacancy {target_vacancy_id} (DB update failed).")
            await query.edit_message_text(f"Не удалось обновить статус вакансии ID {target_vacancy_id}. Попробуйте снова или проверьте логи.")

    except Exception as e:
        error_details = f"Error in admin_moderation_callback for admin {telegram_user.id if telegram_user else 'N/A'}: {e}"
        logger.error(error_details)
        try:
            await query.edit_message_text("Произошла ошибка при обработке вашего запроса. Следующая вакансия не будет загружена автоматически.")
        except Exception as e_final:
            logger.error(f"Failed to edit message in admin_moderation_callback error handler: {e_final}")
            if update.effective_chat:
                await context.bot.send_message(chat_id=update.effective_chat.id, text="Произошла критическая ошибка при модерации.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_user = update.effective_user
    if not telegram_user or not update.message: return
    try:
        reply_markup_to_use = ReplyKeyboardRemove()
        db_user = utils.get_user(telegram_user.id)
        if db_user and db_user['general_agreement_accepted']:
            if db_user['user_type'] == 'employer': reply_markup_to_use = employer_main_menu_keyboard()
            elif db_user['user_type'] == 'employee': reply_markup_to_use = employee_main_menu_keyboard()
            elif db_user['user_type'] == 'admin' and telegram_user.id in config.ADMIN_TELEGRAM_IDS:
                reply_markup_to_use = admin_main_menu_keyboard()

        await update.message.reply_text(config.TEXTS_RU["help_message"], reply_markup=reply_markup_to_use)
    except Exception as e:
        logger.error(f"Error in help_command for user {telegram_user.id if telegram_user else 'N/A'}: {e}")

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    telegram_user = update.effective_user
    if not telegram_user or not update.message: return ConversationHandler.END
    try:
        logger.info(f"User {telegram_user.id} initiated /cancel. Conversation data cleared: {list(context.user_data.keys())}")
        context.user_data.clear()

        await update.message.reply_text(config.TEXTS_RU["action_canceled"], reply_markup=ReplyKeyboardRemove())

        db_user = utils.get_user(telegram_user.id)
        if db_user and db_user['user_type'] == 'admin' and telegram_user.id in config.ADMIN_TELEGRAM_IDS :
             await update.message.reply_text(config.TEXTS_RU["admin_menu_prompt"], reply_markup=admin_main_menu_keyboard())
        elif db_user and db_user['general_agreement_accepted']:
            if db_user['user_type'] == 'employer':
                await update.message.reply_text(config.TEXTS_RU["employer_menu_prompt"], reply_markup=employer_main_menu_keyboard())
            elif db_user['user_type'] == 'employee':
                await update.message.reply_text(config.TEXTS_RU["employee_menu_prompt"], reply_markup=employee_main_menu_keyboard())
            else:
                 logger.warning(f"Cancel command: User {telegram_user.id} has agreement but unclear/invalid role '{db_user.get('user_type', 'N/A')}'. Sending to /start.")
                 await update.message.reply_text("Состояние не определено. Пожалуйста, используйте /start для возврата в главное меню.", reply_markup=ReplyKeyboardRemove())
        else:
            logger.info(f"Cancel command: User {telegram_user.id} not fully registered or no agreement. Sending to /start.")
            await update.message.reply_text("Для начала работы, пожалуйста, используйте команду /start.", reply_markup=ReplyKeyboardRemove())

        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in cancel_command for user {telegram_user.id if telegram_user else 'N/A'}: {e}")
        context.user_data.clear()
        return ConversationHandler.END

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_user = update.effective_user
    if not telegram_user or not update.message: return
    try:
        logger.info(f"Received unknown command '{update.message.text}' from user {telegram_user.id if telegram_user else 'N/A'}")
        await update.message.reply_text(config.TEXTS_RU["command_unknown"])
    except Exception as e:
        logger.error(f"Error in unknown_command for user {telegram_user.id if telegram_user else 'N/A'}: {e}")

async def ptb_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

    if isinstance(update, Update):
        chat_id = None
        is_callback = False
        try:
            if update.effective_chat:
                chat_id = update.effective_chat.id
            if update.callback_query:
                is_callback = True

            if chat_id and (not hasattr(context, '_custom_error_sent') or not context._custom_error_sent):
                user_message = "Произошла внутренняя ошибка сервера. Мы уже уведомлены и работаем над этим. Пожалуйста, попробуйте ваше действие позже. Вы можете использовать /cancel для отмены текущей операции."
                if is_callback:
                    await update.callback_query.answer(user_message, show_alert=True)
                else:
                    await context.bot.send_message(chat_id=chat_id, text=user_message)
        except Exception as e_notify:
            logger.error(f"Exception in global ptb_error_handler while trying to notify user {chat_id}: {e_notify}")

def main() -> None:
    utils.init_db()
    logger.info("Database initialization check complete from main.")

    if not config.TELEGRAM_BOT_TOKEN or config.TELEGRAM_BOT_TOKEN == "YOUR_FALLBACK_TOKEN_HERE":
        logger.critical("TELEGRAM_BOT_TOKEN is not set or is using fallback. Bot cannot start.")
        return

    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    application.add_error_handler(ptb_error_handler)

    registration_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            CHOOSE_ROLE: [CallbackQueryHandler(choose_role_callback, pattern=f"^{config.CALLBACK_ROLE_EMPLOYER}$|^{config.CALLBACK_ROLE_EMPLOYEE}$|^{config.CALLBACK_ROLE_ADMIN}$")],
            ADMIN_PASSWORD_ENTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_password_entry_handler)],
            CONFIRM_GENERAL_AGREEMENT: [CallbackQueryHandler(general_agreement_callback, pattern=f"^{config.CALLBACK_ACCEPT_GENERAL_AGREEMENT}$|^{config.CALLBACK_DECLINE_GENERAL_AGREEMENT}$")],
        },
        fallbacks=[CommandHandler("cancel", cancel_command), CommandHandler("start", start_command)],
        map_to_parent={ConversationHandler.END: ConversationHandler.END}
    )

    post_vacancy_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f"^{config.TEXTS_RU['post_vacancy_button']}$") & filters.ChatType.PRIVATE, post_vacancy_start)],
        states={
            POST_VACANCY_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_vacancy_title)],
            POST_VACANCY_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_vacancy_description)],
            POST_VACANCY_SALARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_vacancy_salary)],
            POST_VACANCY_CONTACTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_vacancy_contacts)],
            POST_VACANCY_CONFIRM: [CallbackQueryHandler(post_vacancy_confirm_callback, pattern=f"^{config.CALLBACK_PUBLISH_VACANCY}$|^{config.CALLBACK_EDIT_VACANCY_FROM_CONFIRM}$|^{config.CALLBACK_CANCEL_VACANCY_POST}$")],
        },
        fallbacks=[CommandHandler("cancel", cancel_command), CommandHandler("start", start_command)],
        map_to_parent={ConversationHandler.END: ConversationHandler.END}
    )

    view_apply_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(f"^{config.TEXTS_RU['view_vacancies_button']}$") & filters.ChatType.PRIVATE, view_vacancies_start),
            CommandHandler("vac", vacancy_details_command, filters=filters.COMMAND & filters.ChatType.PRIVATE)
        ],
        states={
            VIEW_VACANCIES_LIST: [
                CallbackQueryHandler(view_vacancies_callback_handler, pattern=f"^{config.CALLBACK_NAV_VACANCIES_NEXT}|^({config.CALLBACK_NAV_VACANCIES_PREV})|^({config.CALLBACK_VACANCY_APPLY_PREFIX})|^(clear_vacancy_filter)$|^(show_vacancy_list_from_details)$"),
            ],
            APPLY_VACANCY_CONFIRM_AGREEMENT: [CallbackQueryHandler(apply_vacancy_agreement_callback, pattern=f"^{config.CALLBACK_ACCEPT_VACANCY_AGREEMENT}|^back_to_vacancy_list$")],
            APPLY_VACANCY_SUBMIT_INFO: [MessageHandler(filters.TEXT | filters.Document.ALL & ~filters.COMMAND, apply_vacancy_submit_info)],
        },
        fallbacks=[CommandHandler("cancel", cancel_command), CommandHandler("start", start_command)],
        map_to_parent={ConversationHandler.END: ConversationHandler.END, VIEW_VACANCIES_LIST: VIEW_VACANCIES_LIST}
    )

    filter_vacancies_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f"^{config.TEXTS_RU['filter_vacancies_button']}$") & filters.ChatType.PRIVATE, filter_vacancies_start)],
        states={FILTER_VACANCIES_KEYWORDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, filter_vacancies_set_keywords)]},
        fallbacks=[CommandHandler("cancel", cancel_command), CommandHandler("start", start_command)],
        map_to_parent={VIEW_VACANCIES_LIST: VIEW_VACANCIES_LIST, ConversationHandler.END: ConversationHandler.END}
    )

    application.add_handler(registration_conv)
    application.add_handler(post_vacancy_conv)
    application.add_handler(view_apply_conv)
    application.add_handler(filter_vacancies_conv)

    application.add_handler(CallbackQueryHandler(admin_moderation_callback, pattern=f"^{config.CALLBACK_APPROVE_VACANCY}|^{config.CALLBACK_REJECT_VACANCY}$"))
    application.add_handler(CallbackQueryHandler(moderate_vacancies_admin, pattern=f"^{config.CALLBACK_MODERATE_VACANCIES}$"))

    application.add_handler(MessageHandler(filters.Regex(f"^{config.TEXTS_RU['my_vacancies_button']}$") & filters.ChatType.PRIVATE, my_vacancies_employer))
    application.add_handler(MessageHandler(filters.Regex(f"^{config.TEXTS_RU['view_applications_button']}$") & filters.ChatType.PRIVATE, view_applications_employer))
    application.add_handler(MessageHandler(filters.Regex(f"^{config.TEXTS_RU['my_applications_button']}$") & filters.ChatType.PRIVATE, my_applications_employee))
    application.add_handler(MessageHandler(filters.Regex(f"^{config.TEXTS_RU['moderate_vacancies_button']}$") & filters.ChatType.PRIVATE, moderate_vacancies_admin))

    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel_command))

    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    logger.info("Bot is starting...")
    application.run_polling()

if __name__ == "__main__":
    main()
