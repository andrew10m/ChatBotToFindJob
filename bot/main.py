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

# Assuming utils.py and config.py are in the same directory (or bot.utils, bot.config if structured as a package)
import utils
import config

# Basic Logging Setup from utils
logger = utils.logger

# --- Helper Functions ---
def get_user_mention(user: TelegramUser) -> str:
    """Returns a markdown mention for a user."""
    if user.username:
        return f"@{user.username}"
    else:
        return f"[{user.first_name}](tg://user?id={user.id})"

async def send_error_message(update: Update, context: ContextTypes.DEFAULT_TYPE, error_details: str = "", message_key="error_generic"):
    """Sends a generic error message and logs details."""
    user_facing_message = config.TEXTS_RU.get(message_key, "Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже.")

    # Determine if it's a query or message to reply/edit
    if update.callback_query:
        await update.callback_query.answer(user_facing_message, show_alert=True) # Show alert for callbacks
        # Optionally, edit the message if appropriate, or send a new one if not.
        # For simplicity, we just show an alert here. If the message needs to be cleared/changed:
        # try:
        #     await update.callback_query.edit_message_text(user_facing_message)
        # except Exception: # If original message is gone or not editable
        #     await context.bot.send_message(chat_id=update.effective_chat.id, text=user_facing_message)

    elif update.message:
        await update.message.reply_text(user_facing_message)
    else: # Should not happen with typical handlers
        logger.error(f"send_error_message called without a message or callback_query in Update object.")

    logger.error(f"User-facing error sent. Details: {error_details if error_details else 'No specific details provided by caller.'} User: {update.effective_user.id if update.effective_user else 'N/A'}")


# --- Conversation States from config.py ---
(
    CHOOSE_ROLE, REGISTER_AGREEMENT, POST_VACANCY_TITLE, POST_VACANCY_DESCRIPTION,
    POST_VACANCY_SALARY, POST_VACANCY_CONTACTS, POST_VACANCY_CONFIRM,
    APPLY_VACANCY_CONFIRM_AGREEMENT, APPLY_VACANCY_SUBMIT_INFO, FILTER_VACANCIES_KEYWORDS
) = (
    config.CHOOSE_ROLE, config.REGISTER_AGREEMENT, config.POST_VACANCY_TITLE,
    config.POST_VACANCY_DESCRIPTION, config.POST_VACANCY_SALARY, config.POST_VACANCY_CONTACTS,
    config.POST_VACANCY_CONFIRM, config.APPLY_VACANCY_CONFIRM_AGREEMENT,
    config.APPLY_VACANCY_SUBMIT_INFO, config.FILTER_VACANCIES_KEYWORDS
)

# --- Start and Role Selection ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the /start command."""
    telegram_user = update.effective_user
    if not telegram_user:
        logger.warning("start_command: update.effective_user is None.")
        # Cannot reply if we don't know who the user is. This case should be rare.
        return ConversationHandler.END

    try:
        db_user = utils.get_user(telegram_user.id)

        if db_user and db_user['general_agreement_accepted']:
            if db_user['user_type'] == 'employer':
                await update.message.reply_text(config.TEXTS_RU["welcome_back_employer"], reply_markup=employer_main_menu_keyboard())
            elif db_user['user_type'] == 'job_seeker':
                await update.message.reply_text(config.TEXTS_RU["welcome_back_job_seeker"], reply_markup=job_seeker_main_menu_keyboard())
            elif db_user['user_type'] == 'admin':
                await update.message.reply_text(config.TEXTS_RU["welcome_admin"], reply_markup=admin_main_menu_keyboard())
            else: # Should not happen if data is consistent
                logger.warning(f"User {telegram_user.id} has accepted agreement but has unknown role: {db_user['user_type']}")
                await update.message.reply_text(config.TEXTS_RU["welcome_new_user"], reply_markup=role_selection_keyboard())
                return CHOOSE_ROLE
            return ConversationHandler.END

        # New user or user who hasn't accepted agreement / chosen role
        await update.message.reply_text(config.TEXTS_RU["welcome_new_user"], reply_markup=role_selection_keyboard())
        return CHOOSE_ROLE
    except Exception as e:
        await send_error_message(update, context, error_details=f"Error in start_command for user {telegram_user.id}: {e}")
        return ConversationHandler.END

def role_selection_keyboard():
    keyboard = [
        [InlineKeyboardButton(config.TEXTS_RU["employer_button"], callback_data=config.CALLBACK_ROLE_EMPLOYER)],
        [InlineKeyboardButton(config.TEXTS_RU["job_seeker_button"], callback_data=config.CALLBACK_ROLE_JOB_SEEKER)],
    ]
    return InlineKeyboardMarkup(keyboard)

async def choose_role_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles role selection from inline buttons."""
    query = update.callback_query
    telegram_user = update.effective_user
    if not query or not telegram_user:
        logger.warning("choose_role_callback: query or telegram_user is None.")
        return ConversationHandler.END # Or current state if appropriate

    try:
        await query.answer()
        role = query.data
        context.user_data['role_choice'] = role

        keyboard = [
            [InlineKeyboardButton(config.TEXTS_RU["accept_button"], callback_data=config.CALLBACK_ACCEPT_GENERAL_AGREEMENT)],
            [InlineKeyboardButton(config.TEXTS_RU["decline_button"], callback_data=config.CALLBACK_DECLINE_GENERAL_AGREEMENT)],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text=config.TEXTS_RU["general_agreement_prompt"] + "\n\n" + config.GENERAL_USER_AGREEMENT_TEXT,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        return REGISTER_AGREEMENT
    except Exception as e:
        await send_error_message(update, context, error_details=f"Error in choose_role_callback for user {telegram_user.id}: {e}")
        return ConversationHandler.END


async def general_agreement_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles acceptance/rejection of the General User Agreement."""
    query = update.callback_query
    telegram_user = update.effective_user
    if not query or not telegram_user:
        logger.warning("general_agreement_callback: query or telegram_user is None.")
        return ConversationHandler.END

    try:
        await query.answer()

        if query.data == config.CALLBACK_ACCEPT_GENERAL_AGREEMENT:
            role_choice = context.user_data.get('role_choice')
            if not role_choice:
                logger.warning(f"general_agreement_callback: role_choice not found in user_data for user {telegram_user.id}. Returning to role choice.")
                await query.edit_message_text(config.TEXTS_RU["welcome_new_user"], reply_markup=role_selection_keyboard())
                return CHOOSE_ROLE

            user_type = 'employer' if role_choice == config.CALLBACK_ROLE_EMPLOYER else 'job_seeker'

            db_user_id = utils.create_user(telegram_user.id, user_type, telegram_user.username, telegram_user.first_name, telegram_user.last_name)
            if not db_user_id:
                logger.error(f"Failed to create user {telegram_user.id} in general_agreement_callback.")
                await query.edit_message_text(text=config.TEXTS_RU["error_generic"])
                return ConversationHandler.END

            if not utils.set_general_agreement_accepted(telegram_user.id, True):
                logger.error(f"Failed to set general agreement for user {telegram_user.id}.")
                await query.edit_message_text(text=config.TEXTS_RU["error_generic"])
                return ConversationHandler.END

            context.user_data['db_user_id'] = db_user_id
            context.user_data['user_type'] = user_type

            if user_type == 'employer':
                await query.edit_message_text(text=config.TEXTS_RU["registration_complete_employer"], reply_markup=employer_main_menu_keyboard())
            else: # job_seeker
                await query.edit_message_text(text=config.TEXTS_RU["registration_complete_job_seeker"], reply_markup=job_seeker_main_menu_keyboard())
            return ConversationHandler.END

        elif query.data == config.CALLBACK_DECLINE_GENERAL_AGREEMENT:
            await query.edit_message_text(text=config.TEXTS_RU["agreement_declined_message"])
            return ConversationHandler.END

        else: # Should not happen
            logger.warning(f"general_agreement_callback: Unexpected callback data '{query.data}' for user {telegram_user.id}")
            return REGISTER_AGREEMENT

    except Exception as e:
        await send_error_message(update, context, error_details=f"Error in general_agreement_callback for user {telegram_user.id}: {e}")
        return ConversationHandler.END


# --- Main Menu Keyboards ---
def employer_main_menu_keyboard():
    keyboard = [
        [config.TEXTS_RU["post_vacancy_button"]],
        [config.TEXTS_RU["my_vacancies_button"], config.TEXTS_RU["view_applications_button"]],
        [config.TEXTS_RU["help_message"].split('\n')[1].split(' - ')[0]] # /help
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def job_seeker_main_menu_keyboard():
    keyboard = [
        [config.TEXTS_RU["view_vacancies_button"]],
        [config.TEXTS_RU["my_applications_button"], config.TEXTS_RU["filter_vacancies_button"]],
        [config.TEXTS_RU["help_message"].split('\n')[1].split(' - ')[0]] # /help
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def admin_main_menu_keyboard(): # Basic for now
    keyboard = [
        [config.TEXTS_RU["moderate_vacancies_button"]],
        [config.TEXTS_RU["manage_users_button"]],
         [config.TEXTS_RU["help_message"].split('\n')[1].split(' - ')[0]] # /help
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)


# --- Employer: Post Vacancy ---
async def post_vacancy_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the vacancy posting flow."""
    telegram_user = update.effective_user
    db_user = utils.get_user(telegram_user.id)
    if not (db_user and db_user['user_type'] == 'employer' and db_user['general_agreement_accepted']):
        await update.message.reply_text("Пожалуйста, сначала зарегистрируйтесь как работодатель через /start.")
        return ConversationHandler.END

    context.user_data['vacancy_info'] = {}
    await update.message.reply_text(config.TEXTS_RU["enter_vacancy_title"], reply_markup=ReplyKeyboardRemove())
    return POST_VACANCY_TITLE

async def post_vacancy_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['vacancy_info']['title'] = update.message.text
    await update.message.reply_text(config.TEXTS_RU["enter_vacancy_description"])
    return POST_VACANCY_DESCRIPTION

async def post_vacancy_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['vacancy_info']['description'] = update.message.text
    await update.message.reply_text(config.TEXTS_RU["enter_vacancy_salary"])
    return POST_VACANCY_SALARY

async def post_vacancy_salary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['vacancy_info']['salary'] = update.message.text
    await update.message.reply_text(config.TEXTS_RU["enter_vacancy_contacts"])
    return POST_VACANCY_CONTACTS

async def post_vacancy_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['vacancy_info']['contacts'] = update.message.text

    # Confirmation step
    vacancy = context.user_data['vacancy_info']
    confirm_text = config.TEXTS_RU["vacancy_confirm_prompt"].format(
        title=vacancy['title'],
        description=vacancy['description'],
        salary=vacancy['salary'],
        contacts=vacancy['contacts']
    )
    keyboard = [
        [InlineKeyboardButton(config.TEXTS_RU["publish_button"], callback_data=config.CALLBACK_PUBLISH_VACANCY)],
        [InlineKeyboardButton(config.TEXTS_RU["edit_button"], callback_data=config.CALLBACK_EDIT_VACANCY_FROM_CONFIRM)], # Simplified: "Начать заново"
        [InlineKeyboardButton(config.TEXTS_RU["cancel_button"], callback_data=config.CALLBACK_CANCEL_VACANCY_POST)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(confirm_text, reply_markup=reply_markup)
    return POST_VACANCY_CONFIRM

async def post_vacancy_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    telegram_user = update.effective_user
    db_user = utils.get_user(telegram_user.id) # Fetch current user from DB

    if query.data == config.CALLBACK_PUBLISH_VACANCY:
        if not db_user or not db_user['id']:
            await query.edit_message_text(config.TEXTS_RU["error_generic"] + " (User ID not found)")
            return ConversationHandler.END

        vacancy_info = context.user_data.get('vacancy_info', {})
        vacancy_id = utils.create_vacancy(
            employer_id=db_user['id'], # Use the id from the users table
            title=vacancy_info.get('title'),
            description=vacancy_info.get('description'),
            salary=vacancy_info.get('salary'),
            contact_details=vacancy_info.get('contacts'),
            status='pending_moderation' # Or 'active' if no moderation
        )
        if vacancy_id:
            # TODO: Notify admin if status is pending_moderation
            await query.edit_message_text(config.TEXTS_RU["vacancy_published_moderation"], reply_markup=employer_main_menu_keyboard())
        else:
            await query.edit_message_text(config.TEXTS_RU["error_generic"], reply_markup=employer_main_menu_keyboard())
        context.user_data.pop('vacancy_info', None)
        return ConversationHandler.END

    elif query.data == config.CALLBACK_EDIT_VACANCY_FROM_CONFIRM: # Simplified: Restart
        await query.edit_message_text(config.TEXTS_RU["restart_vacancy_posting"])
        context.user_data['vacancy_info'] = {} # Clear old info
        # No ReplyKeyboardRemove() here as we are sending a new prompt
        return POST_VACANCY_TITLE # Restart the flow by asking for title again

    elif query.data == config.CALLBACK_CANCEL_VACANCY_POST:
        await query.edit_message_text(config.TEXTS_RU["vacancy_publication_cancelled"], reply_markup=employer_main_menu_keyboard())
        context.user_data.pop('vacancy_info', None)
        return ConversationHandler.END

    return POST_VACANCY_CONFIRM


# --- Job Seeker: View and Apply for Vacancies ---
async def view_vacancies_start(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    """Displays active vacancies with pagination."""
    telegram_user = update.effective_user
    db_user = utils.get_user(telegram_user.id)
    if not (db_user and db_user['user_type'] == 'job_seeker' and db_user['general_agreement_accepted']):
        await update.message.reply_text("Пожалуйста, сначала зарегистрируйтесь как соискатель через /start.")
        return ConversationHandler.END # Should not be reachable if using main menu

    keywords = context.user_data.get('vacancy_filter_keywords')
    vacancies = utils.get_active_vacancies(limit=config.VACANCIES_PER_PAGE, offset=page * config.VACANCIES_PER_PAGE, keywords=keywords)

    message_target = update.message if update.message else update.callback_query.message

    if not vacancies:
        await message_target.reply_text(config.TEXTS_RU["no_active_vacancies"], reply_markup=job_seeker_main_menu_keyboard())
        return ConversationHandler.END

    text = "📄 *Активные вакансии*:\n\n"
    if keywords:
        text = f"🔎 *Результаты поиска по '{keywords}'*:\n\n"

    keyboard = []
    for vacancy in vacancies:
        text += f"🔹 *{vacancy['title']}*\n"
        text += f"   薪资: {vacancy['salary']}\n" # Using a different script char for salary for demo
        text += f"   /vac_{vacancy['id']}\n\n" # Command to view details
        # Inline button for each vacancy to apply directly
        keyboard.append([InlineKeyboardButton(f"Откликнуться: {vacancy['title'][:30]}...", callback_data=f"{config.CALLBACK_VACANCY_APPLY_PREFIX}{vacancy['id']}")])

    # Pagination buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(config.TEXTS_RU["prev_page_button"], callback_data=f"{config.CALLBACK_NAV_VACANCIES_PREV}{page-1}"))
    if len(vacancies) == config.VACANCIES_PER_PAGE: # More vacancies might exist
        nav_buttons.append(InlineKeyboardButton(config.TEXTS_RU["next_page_button"], callback_data=f"{config.CALLBACK_NAV_VACANCIES_NEXT}{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)

    # Clear filter button if filter is active
    if keywords:
        keyboard.append([InlineKeyboardButton(config.TEXTS_RU["clear_filter_button"], callback_data="clear_vacancy_filter")])


    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query: # If called from pagination or filter clear
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    else: # Initial call
        await message_target.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    return VIEW_VACANCIES_LIST # A state to handle callbacks from this message

async def view_vacancies_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles callbacks from the vacancy list (pagination, apply buttons)."""
    query = update.callback_query
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
        if not vacancy:
            await query.answer("Вакансия не найдена.", show_alert=True)
            return VIEW_VACANCIES_LIST

        # Display Vacancy Application Agreement
        agreement_text = config.TEXTS_RU["vacancy_application_agreement_prompt"] + "\n\n" + config.VACANCY_APPLICATION_AGREEMENT_TEXT
        keyboard = [
            [InlineKeyboardButton(config.TEXTS_RU["accept_and_apply_button"], callback_data=f"{config.CALLBACK_ACCEPT_VACANCY_AGREEMENT}{vacancy_id}")],
            [InlineKeyboardButton(config.TEXTS_RU["back_to_list_button"], callback_data="back_to_vacancy_list")], # Go back to list
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=agreement_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        return APPLY_VACANCY_CONFIRM_AGREEMENT
    elif data == "clear_vacancy_filter":
        context.user_data.pop('vacancy_filter_keywords', None)
        await query.answer("Фильтр сброшен.")
        return await view_vacancies_start(update, context, page=0) # Refresh list

    await query.answer() # Default answer if no specific action
    return VIEW_VACANCIES_LIST


async def apply_vacancy_agreement_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles acceptance of Vacancy Application Agreement."""
    query = update.callback_query
    await query.answer()

    vacancy_id = context.user_data.get('current_vacancy_id_for_application')
    if not vacancy_id: # Should not happen if flow is correct
        await query.edit_message_text(config.TEXTS_RU["error_generic"])
        return ConversationHandler.END

    if query.data.startswith(config.CALLBACK_ACCEPT_VACANCY_AGREEMENT):
        # Ensure the callback data's vacancy_id matches context, simple check
        if query.data != f"{config.CALLBACK_ACCEPT_VACANCY_AGREEMENT}{vacancy_id}":
            await query.edit_message_text(config.TEXTS_RU["error_generic"] + " (ID mismatch)")
            return ConversationHandler.END

        context.user_data['vacancy_agreement_accepted_for_current'] = True
        await query.edit_message_text(config.TEXTS_RU["send_resume_or_message_prompt"], reply_markup=ReplyKeyboardRemove())
        return APPLY_VACANCY_SUBMIT_INFO

    elif query.data == "back_to_vacancy_list": # Or DECLINE
        # Go back to the vacancy list view
        await query.delete_message() # Clean up agreement message
        return await view_vacancies_start(update, context, page=context.user_data.get('current_vacancy_page', 0))

    return APPLY_VACANCY_CONFIRM_AGREEMENT


async def apply_vacancy_submit_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles submission of resume/message for application."""
    telegram_user = update.effective_user
    db_user = utils.get_user(telegram_user.id)
    vacancy_id = context.user_data.get('current_vacancy_id_for_application')
    agreement_accepted = context.user_data.get('vacancy_agreement_accepted_for_current', False)

    if not (db_user and db_user['id'] and vacancy_id and agreement_accepted):
        await update.message.reply_text(config.TEXTS_RU["error_generic"] + " (Missing application context)", reply_markup=job_seeker_main_menu_keyboard())
        return ConversationHandler.END

    application_content = ""
    if update.message.text:
        application_content = update.message.text
    elif update.message.document:
        # For simplicity, store a placeholder or file_id. Real file handling is more complex.
        application_content = f"Файл: {update.message.document.file_name} (ID: {update.message.document.file_id})"
        # await update.message.reply_text("Файл получен. В реальной системе он был бы сохранен.")
    else:
        await update.message.reply_text("Пожалуйста, отправьте текстовое сообщение или файл.", reply_markup=job_seeker_main_menu_keyboard())
        return APPLY_VACANCY_SUBMIT_INFO # Stay in state

    app_id = utils.create_application(
        job_seeker_id=db_user['id'],
        vacancy_id=vacancy_id,
        resume_or_message=application_content,
        agreement_accepted=True # Already confirmed
    )

    if app_id:
        await update.message.reply_text(config.TEXTS_RU["application_sent"], reply_markup=job_seeker_main_menu_keyboard())

        # Notify Employer
        vacancy = utils.get_vacancy_by_id(vacancy_id)
        if vacancy and vacancy['employer_id']:
            employer_user_record = utils.get_user(vacancy['employer_id']) # This gets user by DB ID
            # We need employer's telegram_id to send message. Let's assume get_user can also take DB ID
            # Or, better, store telegram_id in vacancies table or join to get it.
            # For now, let's assume we can get employer's telegram_id.
            # This part needs refinement in utils.get_user or a new function get_user_by_db_id
            # For now, let's simulate this:
            employer_telegram_id = None
            # A proper way:
            # employer_db_user = utils.get_user_by_internal_id(vacancy['employer_id'])
            # if employer_db_user: employer_telegram_id = employer_db_user['telegram_id']

            # Simplified: If we had employer's telegram_id stored directly or easily accessible
            # For this example, we'll assume we don't have it readily without another query.
            # So, a full notification implementation would require fetching the employer's telegram_id.

            # Placeholder for notification logic
            logger.info(f"TODO: Notify employer (user_id: {vacancy['employer_id']}) for vacancy {vacancy_id} about new application {app_id}")
            # Example: await context.bot.send_message(chat_id=EMPLOYER_TELEGRAM_ID, text=...)
            # A more robust way is to get employer's telegram_id from users table using vacancy['employer_id']
            employer_creator = utils.get_user_by_internal_id(db_id=vacancy['employer_id']) # Use the new function
            if employer_creator and employer_creator['telegram_id']:
                 notification_text = config.TEXTS_RU["new_application_notification_employer"].format(
                    vacancy_title=vacancy['title'],
                    user_mention=get_user_mention(telegram_user) # The job seeker
                )
                 try:
                    await context.bot.send_message(chat_id=employer_creator['telegram_id'], text=notification_text, parse_mode=ParseMode.MARKDOWN)
                 except Exception as e:
                    logger.error(f"Failed to send notification to employer {employer_creator['telegram_id']}: {e}")
            else:
                logger.warning(f"Could not find employer Telegram ID for user DB ID {vacancy['employer_id']} to send notification.")


    else:
        await update.message.reply_text(config.TEXTS_RU["application_failed"], reply_markup=job_seeker_main_menu_keyboard())

    # Clean up context
    context.user_data.pop('current_vacancy_id_for_application', None)
    context.user_data.pop('vacancy_agreement_accepted_for_current', None)
    return ConversationHandler.END


# --- Vacancy Details (triggered by /vac_<id>) ---
async def vacancy_details_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Displays details for a specific vacancy and an option to apply."""
    try:
        vacancy_id = int(update.message.text.split('_')[1])
    except (IndexError, ValueError):
        await update.message.reply_text("Неверный формат ID вакансии.")
        return ConversationHandler.END

    vacancy = utils.get_vacancy_by_id(vacancy_id)
    if not vacancy:
        await update.message.reply_text("Вакансия не найдена.")
        return ConversationHandler.END

    text = f"📜 *Вакансия: {vacancy['title']}*\n\n"
    text += f"*Описание:*\n{vacancy['description']}\n\n"
    text += f"*Зарплата:* {vacancy['salary']}\n"
    text += f"*Контакты:* {vacancy['contact_details']}\n"
    text += f"*Опубликовано:* {vacancy['creation_timestamp'][:10]}\n" # Just date part
    if vacancy['employer_username']:
         text += f"*Работодатель:* @{vacancy['employer_username']}\n"

    # Check if user is a job seeker to show apply button
    telegram_user = update.effective_user
    db_user = utils.get_user(telegram_user.id)

    keyboard = []
    if db_user and db_user['user_type'] == 'job_seeker' and db_user['general_agreement_accepted']:
        keyboard.append([InlineKeyboardButton(f"✍️ Откликнуться на: {vacancy['title'][:20]}...", callback_data=f"{config.CALLBACK_VACANCY_APPLY_PREFIX}{vacancy['id']}")])

    # Back to list button (if they came from a list context, not direct /vac_ command)
    # For simplicity, this button is always added for now.
    keyboard.append([InlineKeyboardButton("◀️ К списку вакансий", callback_data="show_vacancy_list_from_details")])

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    return VIEW_VACANCIES_LIST # Re-use state to handle apply callback

async def show_vacancy_list_from_details_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback for 'Back to list' from vacancy details."""
    query = update.callback_query
    await query.answer()
    await query.delete_message() # Remove the detailed view
    # Show the main vacancy list (page 0 or last known page)
    return await view_vacancies_start(update, context, page=context.user_data.get('current_vacancy_page', 0))


# --- Filter Vacancies ---
async def filter_vacancies_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Asks the user for keywords to filter vacancies."""
    telegram_user = update.effective_user
    db_user = utils.get_user(telegram_user.id)
    if not (db_user and db_user['user_type'] == 'job_seeker' and db_user['general_agreement_accepted']):
        # This check might be redundant if called from job_seeker_main_menu_keyboard
        await update.message.reply_text("Пожалуйста, сначала зарегистрируйтесь как соискатель через /start.")
        return ConversationHandler.END

    await update.message.reply_text(config.TEXTS_RU["enter_keywords_for_filter"], reply_markup=ReplyKeyboardRemove())
    return FILTER_VACANCIES_KEYWORDS

async def filter_vacancies_set_keywords(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Sets the keywords and shows the filtered list."""
    keywords = update.message.text
    context.user_data['vacancy_filter_keywords'] = keywords
    await update.message.reply_text(config.TEXTS_RU["filter_applied"])
    # Automatically show the filtered list
    await view_vacancies_start(update, context, page=0)
    return VIEW_VACANCIES_LIST # End keyword entry, go to list view state


# --- My Applications (Job Seeker) ---
async def my_applications_js(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_user = update.effective_user
    db_user = utils.get_user(telegram_user.id)
    if not (db_user and db_user['user_type'] == 'job_seeker' and db_user['general_agreement_accepted']):
        await update.message.reply_text("Доступ запрещен.")
        return

    applications = utils.get_user_applications(db_user['id'])
    if not applications:
        await update.message.reply_text("У вас пока нет откликов.", reply_markup=job_seeker_main_menu_keyboard())
        return

    text = "📋 *Мои отклики:*\n\n"
    for app in applications:
        text += f"🔹 *Вакансия:* {app['vacancy_title']}\n"
        text += f"   *Сообщение/Резюме:* {app['resume_or_message'][:50]}...\n"
        text += f"   *Дата отклика:* {app['application_timestamp'][:10]}\n"
        text += f"   *Согласие на вакансию:* {'Да' if app['vacancy_agreement_accepted'] else 'Нет'}\n\n"

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=job_seeker_main_menu_keyboard())


# --- My Vacancies (Employer) ---
async def my_vacancies_employer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_user = update.effective_user
    db_user = utils.get_user(telegram_user.id)
    if not (db_user and db_user['user_type'] == 'employer' and db_user['general_agreement_accepted']):
        await update.message.reply_text("Доступ запрещен.")
        return

    # This is a simplified version. A real version would query vacancies by employer_id.
    # For now, let's assume a function get_vacancies_by_employer(employer_id) exists in utils.py
    # Example: vacancies = utils.get_vacancies_by_employer(db_user['id'])
    # If not implemented, this will just show a placeholder message.
    # Let's add a quick version to utils for this.
    # (Assume utils.get_vacancies_by_employer is added)
    # vacancies = utils.get_vacancies_by_employer(db_user['id'])
    # if not vacancies:
    #     await update.message.reply_text("У вас пока нет опубликованных вакансий.", reply_markup=employer_main_menu_keyboard())
    #     return

    # text = "📑 *Мои вакансии:*\n\n"
    # for vac in vacancies:
    #    text += f"🔸 *{vac['title']}* (Статус: {vac['status']})\n"
    #    text += f"   ID: {vac['id']} /vac_{vac['id']}\n"
    #    # Add buttons for manage, view applicants, close etc.
    #    text += "\n"

    # await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=employer_main_menu_keyboard())
    await update.message.reply_text("Функция 'Мои вакансии' в разработке. Вы можете просмотреть детали вакансии используя /vac_<ID вакансии>.", reply_markup=employer_main_menu_keyboard())


# --- View Applications (Employer) ---
async def view_applications_employer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # This would typically ask "For which vacancy?" or show a list of their vacancies to choose from.
    # For simplicity, let's say it's not fully implemented yet.
    await update.message.reply_text("Функция 'Просмотреть отклики' в разработке. Сначала выберите вакансию из 'Мои вакансии'.", reply_markup=employer_main_menu_keyboard())


# --- Admin: Basic Moderation (Conceptual) ---
async def moderate_vacancies_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_user = update.effective_user
    db_user = utils.get_user(telegram_user.id)
    if not (db_user and db_user['user_type'] == 'admin' and telegram_user.id in config.ADMIN_TELEGRAM_IDS):
        await update.message.reply_text("Доступ запрещен.")
        return

    # Example: Fetch vacancies with status 'pending_moderation'
    # pending_vacs = utils.get_vacancies_by_status('pending_moderation')
    # if not pending_vacs:
    #     await update.message.reply_text("Нет вакансий для модерации.", reply_markup=admin_main_menu_keyboard())
    #     return
    # For each vac, show details and buttons [Approve, Reject]
    # Callback handlers for approve/reject would update vacancy status and notify employer.
    await update.message.reply_text("Функция модерации в разработке.", reply_markup=admin_main_menu_keyboard())


# --- Help and Cancel ---
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays a help message."""
    await update.message.reply_text(config.TEXTS_RU["help_message"], reply_markup=ReplyKeyboardRemove()) # Consider context-aware keyboard

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the current conversation."""
    await update.message.reply_text(config.TEXTS_RU["action_canceled"], reply_markup=ReplyKeyboardRemove()) # Or role-specific menu

    # Determine user type and show appropriate menu
    db_user = utils.get_user(update.effective_user.id)
    if db_user and db_user['general_agreement_accepted']:
        if db_user['user_type'] == 'employer':
            await update.message.reply_text(config.TEXTS_RU["employer_menu_prompt"], reply_markup=employer_main_menu_keyboard())
        elif db_user['user_type'] == 'job_seeker':
            await update.message.reply_text(config.TEXTS_RU["job_seeker_menu_prompt"], reply_markup=job_seeker_main_menu_keyboard())
        # No admin check here, cancel usually doesn't apply to simple admin menus

    context.user_data.clear() # Clear any stored data for the conversation
    return ConversationHandler.END


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(config.TEXTS_RU["command_unknown"])


def main() -> None:
    """Run the bot."""
    # Initialize database first
    utils.init_db()
    logger.info("Database initialization check complete from main.")

    # Create the Application and pass it your bot's token.
    if not config.TELEGRAM_BOT_TOKEN or config.TELEGRAM_BOT_TOKEN == "YOUR_FALLBACK_TOKEN_HERE":
        logger.error("TELEGRAM_BOT_TOKEN is not set or is using fallback. Please set it in config.py or environment variables.")
        return

    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # --- Conversation Handlers ---
    # Registration Flow
    registration_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            CHOOSE_ROLE: [CallbackQueryHandler(choose_role_callback, pattern=f"^{config.CALLBACK_ROLE_EMPLOYER}$|^{config.CALLBACK_ROLE_JOB_SEEKER}$")],
            REGISTER_AGREEMENT: [CallbackQueryHandler(general_agreement_callback, pattern=f"^{config.CALLBACK_ACCEPT_GENERAL_AGREEMENT}$|^{config.CALLBACK_DECLINE_GENERAL_AGREEMENT}$")],
        },
        fallbacks=[CommandHandler("cancel", cancel_command), CommandHandler("start", start_command)], # Allow restart/cancel
        map_to_parent={ # After registration, fall back to other handlers or end
            ConversationHandler.END: ConversationHandler.END
        }
    )

    # Post Vacancy Flow (Employer)
    post_vacancy_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f"^{config.TEXTS_RU['post_vacancy_button']}$"), post_vacancy_start)],
        states={
            POST_VACANCY_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_vacancy_title)],
            POST_VACANCY_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_vacancy_description)],
            POST_VACANCY_SALARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_vacancy_salary)],
            POST_VACANCY_CONTACTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_vacancy_contacts)],
            POST_VACANCY_CONFIRM: [CallbackQueryHandler(post_vacancy_confirm_callback, pattern=f"^{config.CALLBACK_PUBLISH_VACANCY}$|^{config.CALLBACK_EDIT_VACANCY_FROM_CONFIRM}$|^{config.CALLBACK_CANCEL_VACANCY_POST}$")],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
    )

    # Apply for Vacancy Flow (Job Seeker)
    # This is more callback-driven from the vacancy list, but can be a mini-conversation
    apply_vacancy_conv_handler = ConversationHandler(
        entry_points=[
            # Entry is typically a CallbackQuery from view_vacancies_callback_handler
            # This state machine starts when user clicks "Apply" and needs to accept agreement
        ],
        states={
            # VIEW_VACANCIES_LIST is the "entry" for callbacks related to vacancy browsing
            VIEW_VACANCIES_LIST: [
                CallbackQueryHandler(view_vacancies_callback_handler, pattern=f"^{config.CALLBACK_NAV_VACANCIES_NEXT}|^({config.CALLBACK_NAV_VACANCIES_PREV})|^({config.CALLBACK_VACANCY_APPLY_PREFIX})|^(clear_vacancy_filter)$"),
                CallbackQueryHandler(show_vacancy_list_from_details_callback, pattern="^show_vacancy_list_from_details$") # For /vac_id back button
            ],
            APPLY_VACANCY_CONFIRM_AGREEMENT: [CallbackQueryHandler(apply_vacancy_agreement_callback, pattern=f"^{config.CALLBACK_ACCEPT_VACANCY_AGREEMENT}|^back_to_vacancy_list$")],
            APPLY_VACANCY_SUBMIT_INFO: [MessageHandler(filters.TEXT | filters.Document.ALL & ~filters.COMMAND, apply_vacancy_submit_info)],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
         map_to_parent={ # After applying, go back to main job seeker menu or end
            ConversationHandler.END: ConversationHandler.END
        }
    )

    # Filter Vacancies Flow (Job Seeker)
    filter_vacancies_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f"^{config.TEXTS_RU['filter_vacancies_button']}$"), filter_vacancies_start)],
        states={
            FILTER_VACANCIES_KEYWORDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, filter_vacancies_set_keywords)],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
        map_to_parent={ # After setting filter, it transitions to VIEW_VACANCIES_LIST
            VIEW_VACANCIES_LIST: VIEW_VACANCIES_LIST, # Stay in the apply_vacancy_conv_handler's list state
            ConversationHandler.END: ConversationHandler.END
        }
    )


    # --- Regular Message Handlers for Main Menus (after registration) ---
    # Employer Menu Actions
    application.add_handler(post_vacancy_conv_handler) # Regex for button is entry point
    application.add_handler(MessageHandler(filters.Regex(f"^{config.TEXTS_RU['my_vacancies_button']}$"), my_vacancies_employer))
    application.add_handler(MessageHandler(filters.Regex(f"^{config.TEXTS_RU['view_applications_button']}$"), view_applications_employer))

    # Job Seeker Menu Actions
    application.add_handler(MessageHandler(filters.Regex(f"^{config.TEXTS_RU['view_vacancies_button']}$"), view_vacancies_start)) # Entry to vacancy list
    application.add_handler(MessageHandler(filters.Regex(f"^{config.TEXTS_RU['my_applications_button']}$"), my_applications_js))
    application.add_handler(filter_vacancies_conv_handler) # Regex for button is entry point

    # Admin Menu Actions (Basic)
    application.add_handler(MessageHandler(filters.Regex(f"^{config.TEXTS_RU['moderate_vacancies_button']}$"), moderate_vacancies_admin))
    # application.add_handler(MessageHandler(filters.Regex(f"^{config.TEXTS_RU['manage_users_button']}$"), manage_users_admin)) # If implemented

    # --- Command Handlers ---
    application.add_handler(registration_handler) # /start is the entry point here
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel_command)) # General cancel

    # Handler for /vac_<id> commands
    application.add_handler(CommandHandler("vac", vacancy_details_command, filters=filters.COMMAND)) # Will match /vac_123 like commands

    # This handler should be part of apply_vacancy_conv_handler or standalone if it doesn't need conv state
    application.add_handler(apply_vacancy_conv_handler)


    # Unknown commands/messages (must be last)
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_text_message)) # Optional: if you want to reply to any text

    # Run the bot until the user presses Ctrl-C
    logger.info("Bot is starting...")
    application.run_polling()

if __name__ == "__main__":
    main()
