from .database import execute_query
import logging

logger = logging.getLogger(__name__)

async def create_user(user_id: int, role: str, username: str = None, contact_info: str = None, accepted_terms: bool = False):
    """Добавляет нового пользователя или обновляет существующего (кроме accepted_terms, registered_at)."""
    query = """
    INSERT INTO users (user_id, role, username, contact_info, accepted_terms, registered_at, is_blocked)
    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, FALSE)
    ON CONFLICT(user_id) DO UPDATE SET
        role = excluded.role,
        username = excluded.username,
        contact_info = excluded.contact_info
    """
    # При конфликте accepted_terms и registered_at не обновляются здесь,
    # accepted_terms обновляется отдельной функцией.
    # is_blocked по умолчанию FALSE при создании.
    try:
        await execute_query(query, (user_id, role, username, contact_info, 1 if accepted_terms else 0))
        logger.info(f"User {user_id} created/updated with role {role}.")
        return await get_user(user_id)
    except Exception as e:
        logger.error(f"Error in create_user for {user_id}: {e}")
        return None

async def get_user(user_id: int):
    """Получает информацию о пользователе по его ID."""
    query = "SELECT * FROM users WHERE user_id = ?"
    try:
        user = await execute_query(query, (user_id,), fetch_one=True)
        # logger.debug(f"User data for {user_id}: {user}")
        return user
    except Exception as e:
        logger.error(f"Error in get_user for {user_id}: {e}")
        return None

async def update_user_accepted_terms(user_id: int, accepted: bool):
    """Обновляет статус принятия условий пользователем."""
    query = "UPDATE users SET accepted_terms = ? WHERE user_id = ?"
    try:
        await execute_query(query, (1 if accepted else 0, user_id))
        logger.info(f"User {user_id} accepted_terms updated to {accepted}.")
    except Exception as e:
        logger.error(f"Error in update_user_accepted_terms for {user_id}: {e}")


async def update_user_role(user_id: int, role: str):
    """Обновляет роль пользователя."""
    query = "UPDATE users SET role = ? WHERE user_id = ?"
    try:
        await execute_query(query, (role, user_id))
        logger.info(f"User {user_id} role updated to {role}.")
    except Exception as e:
        logger.error(f"Error in update_user_role for {user_id}: {e}")


async def update_user_contact_info(user_id: int, contact_info: str):
    """Обновляет контактную информацию пользователя."""
    query = "UPDATE users SET contact_info = ? WHERE user_id = ?"
    try:
        await execute_query(query, (contact_info, user_id))
        logger.info(f"User {user_id} contact_info updated.")
    except Exception as e:
        logger.error(f"Error in update_user_contact_info for {user_id}: {e}")


async def log_agreement(user_id: int, agreement_type: str, vacancy_id: int = None):
    """Логирует принятие соглашения."""
    query = """
    INSERT INTO agreements (user_id, agreement_type, vacancy_id, accepted_at)
    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    """
    try:
        await execute_query(query, (user_id, agreement_type, vacancy_id))
        logger.info(f"Agreement logged for user {user_id}, type: {agreement_type}, vacancy_id: {vacancy_id}.")
    except Exception as e:
        logger.error(f"Error in log_agreement for user {user_id}, type {agreement_type}: {e}")


# Функции для вакансий
async def create_vacancy(employer_id: int, title: str, description: str, salary: str, contact_info: str) -> int | None:
    """Создает новую вакансию и возвращает ее ID."""
    query = """
    INSERT INTO vacancies (employer_id, title, description, salary, contact_info, status, created_at)
    VALUES (?, ?, ?, ?, ?, 'pending_moderation', CURRENT_TIMESTAMP)
    """
    try:
        vacancy_id = await execute_query(query, (employer_id, title, description, salary, contact_info), last_row_id=True)
        logger.info(f"Vacancy created with ID: {vacancy_id} by employer {employer_id}.")
        return vacancy_id
    except Exception as e:
        logger.error(f"Error creating vacancy for employer {employer_id}: {e}")
        return None

# Другие функции для вакансий, откликов, модерации и т.д. будут добавлены здесь.
